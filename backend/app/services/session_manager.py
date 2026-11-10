"""Single-process lifecycle for research sessions and their graph tasks."""

import asyncio
import copy
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.graph.errors import UserVisibleResearchError
from app.models.schemas import ResearchSubQuestion, SourceMetadata

logger = logging.getLogger(__name__)

EventPublisher = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class SessionNotFound(Exception):
    pass


class SessionConflict(Exception):
    pass


@dataclass
class ResearchSession:
    session_id: str
    state: dict[str, Any]
    status: str = "created"
    revision: int = 0
    current_step: str = "idle"
    progress_percent: int = 0
    pending_interrupt: dict[str, Any] | None = None
    error: str | None = None
    task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ResearchSessionManager:
    """Own session state and schedule exactly one graph run per transition."""

    # shortcut: RAM-only sessions and checkpoints are lost on restart; Phase 7 needs shared persistence.
    _PUBLISH_TIMEOUT_SECONDS = 0.5
    _NODE_PROGRESS = {
        "planner": ("planning", 5),
        "plan_approval": ("planning", 10),
        "searcher": ("searching", 25),
        "source_approval": ("selecting_sources", 35),
        "reader": ("reading", 45),
        "extractor": ("extracting", 60),
        "kg_builder": ("extracting", 70),
        "reflector": ("reflecting", 80),
        "synthesizer": ("synthesizing", 90),
        "report_approval": ("synthesizing", 95),
    }

    def __init__(
        self,
        graph: Any,
        command_factory: Callable[[dict[str, Any]], Any],
        publish: EventPublisher | None = None,
    ) -> None:
        self.graph = graph
        self.command_factory = command_factory
        self.publish = publish
        self.sessions: dict[str, ResearchSession] = {}

    def create(self, session_id: str, initial_state: dict[str, Any]) -> ResearchSession:
        if session_id in self.sessions:
            raise SessionConflict("Session already exists.")
        session = ResearchSession(session_id=session_id, state=copy.deepcopy(initial_state))
        self.sessions[session_id] = session
        return session

    def get(self, session_id: str) -> ResearchSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise SessionNotFound("Session not found.") from exc

    async def snapshot(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        async with session.lock:
            return self._snapshot_unlocked(session)

    async def report(self, session_id: str) -> str | None:
        session = self.get(session_id)
        async with session.lock:
            if session.status != "completed" or not session.state.get("report_approved"):
                return None
            return session.state.get("final_report")

    async def report_view(self, session_id: str) -> dict[str, Any] | None:
        """Return only a stored draft or approved report; never generate one here."""
        session = self.get(session_id)
        async with session.lock:
            approved = session.status == "completed" and bool(session.state.get("report_approved"))
            report = session.state.get("final_report") if approved else session.state.get("report_draft")
            if not report:
                return None
            return {
                "session_id": session.session_id,
                "status": session.status,
                "report_markdown": report,
                "approved": approved,
            }

    async def upload(
        self, session_id: str, save_upload: Callable[[], Awaitable[dict[str, Any]]]
    ) -> dict[str, Any]:
        session = self.get(session_id)
        async with session.lock:
            if session.status != "created":
                raise SessionConflict("Files can only be uploaded before the research run starts.")
            if len(session.state.get("user_uploaded_files", [])) >= 3:
                raise SessionConflict("A session can contain at most 3 uploaded PDFs.")
            record = await save_upload()
            source = SourceMetadata.model_validate(record.get("source"))
            record = {**record, "source_id": source.source_id, "source": source}
            existing = {
                item.get("source_id")
                for item in session.state.get("user_uploaded_files", [])
            }
            if source.source_id not in existing:
                session.state.setdefault("user_uploaded_files", []).append(record)
                session.state.setdefault("sources_found", []).append(source)
                session.state.setdefault("provided_source_ids", []).append(source.source_id)
                session.revision += 1
            return copy.deepcopy(record)

    async def has_uploaded_pdf(self, session_id: str, source_id: str) -> bool:
        session = self.get(session_id)
        async with session.lock:
            return any(
                record.get("source_id") == source_id
                for record in session.state.get("user_uploaded_files", [])
            )

    async def start(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        async with session.lock:
            if session.status != "created":
                raise SessionConflict("Research can only be started once.")
            if (
                session.state.get("search_mode") == "provided"
                and not session.state.get("sources_found")
            ):
                raise SessionConflict("Provided mode needs at least one URL or uploaded PDF before run.")
            session.status = "running"
            session.current_step = "planning"
            session.progress_percent = 1
            session.revision += 1
            session.task = asyncio.create_task(self._run(session, copy.deepcopy(session.state)))
            return self._snapshot_unlocked(session)

    async def resume(
        self,
        session_id: str,
        interrupt_id: str,
        action: str,
        plan: list[Any] | None = None,
        selected_source_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.get(session_id)
        async with session.lock:
            pending = session.pending_interrupt
            if pending is None or session.status not in {"awaiting_plan", "awaiting_sources", "awaiting_report"}:
                raise SessionConflict("This session is not waiting for approval.")
            if pending["interrupt_id"] != interrupt_id:
                raise SessionConflict("This approval is stale or has already been used.")
            if pending["type"] == "PLAN_APPROVAL_REQUIRED":
                if action not in {"approve", "modify"}:
                    raise SessionConflict("Unsupported plan action.")
                if action == "modify" and not plan:
                    raise SessionConflict("A non-empty plan is required.")
                if action == "approve" and (plan is not None or selected_source_ids is not None):
                    raise SessionConflict("A plan can only be sent with the modify action.")
                if action == "modify" and selected_source_ids is not None:
                    raise SessionConflict("Source IDs cannot be sent with plan modification.")
                if action == "modify":
                    plan = self._validate_plan_for_session(session, plan or [])
            elif pending["type"] == "SOURCE_SELECTION_REQUIRED":
                if action != "select_sources" or plan is not None:
                    raise SessionConflict("Only source selection is available at this checkpoint.")
                self._validate_selected_sources(session, pending, selected_source_ids)
            elif action != "approve" or plan is not None or selected_source_ids is not None:
                raise SessionConflict("Only approval is available at this checkpoint.")

            decision: dict[str, Any] = {"action": action}
            if plan is not None:
                decision["plan"] = self._plain(plan)
            if selected_source_ids is not None:
                decision["selected_source_ids"] = list(selected_source_ids)

            session.pending_interrupt = None
            session.status = "running"
            session.revision += 1
            session.task = asyncio.create_task(
                self._run(session, self.command_factory(decision))
            )
            return self._snapshot_unlocked(session)

    async def _run(self, session: ResearchSession, graph_input: Any) -> None:
        config = {"configurable": {"thread_id": session.session_id}}
        try:
            async for update in self.graph.astream(graph_input, config, stream_mode="updates"):
                nodes = update.keys() if isinstance(update, dict) else ()
                for node in nodes:
                    step = self._NODE_PROGRESS.get(node)
                    if node == "__interrupt__" or step is None:
                        continue
                    state_snapshot = await self.graph.aget_state(config)
                    async with session.lock:
                        values = getattr(state_snapshot, "values", None)
                        if isinstance(values, dict):
                            session.state = copy.deepcopy(values)
                        session.current_step, session.progress_percent = step
                        session.revision += 1
                        snapshot = self._snapshot_unlocked(session)
                    await self._emit(session.session_id, "STEP_UPDATE", snapshot)

            state_snapshot = await self.graph.aget_state(config)
            values = getattr(state_snapshot, "values", None)
            interrupt = self._find_interrupt(state_snapshot)
            pending_nodes = getattr(state_snapshot, "next", None)
            if interrupt is None and pending_nodes is None:
                raise RuntimeError("Research graph completion could not be verified.")
            if interrupt is None and pending_nodes:
                raise RuntimeError("Research graph stopped with pending nodes and no approval interrupt.")
            async with session.lock:
                if isinstance(values, dict):
                    session.state = copy.deepcopy(values)
                if interrupt is None:
                    session.pending_interrupt = None
                    session.status = "completed"
                    session.current_step = "done"
                    session.progress_percent = 100
                    event = "DONE"
                else:
                    interrupt_type = interrupt.get("type")
                    if interrupt_type not in {
                        "PLAN_APPROVAL_REQUIRED",
                        "SOURCE_SELECTION_REQUIRED",
                        "REPORT_APPROVAL_REQUIRED",
                    }:
                        raise ValueError("Graph paused at an unsupported approval checkpoint.")
                    session.pending_interrupt = {
                        "interrupt_id": str(uuid.uuid4()),
                        "type": interrupt_type,
                        "message": str(interrupt.get("message", "Approval required.")),
                    }
                    if interrupt_type == "PLAN_APPROVAL_REQUIRED":
                        session.pending_interrupt["plan"] = self._plain(interrupt.get("plan", []))
                        session.status = "awaiting_plan"
                        session.current_step = "planning"
                        session.progress_percent = 10
                    elif interrupt_type == "SOURCE_SELECTION_REQUIRED":
                        candidates = interrupt.get("sources", [])
                        session.pending_interrupt["sources"] = self._public_sources(
                            session, candidates
                        )
                        session.status = "awaiting_sources"
                        session.current_step = "selecting_sources"
                        session.progress_percent = 35
                    else:
                        session.pending_interrupt["report_draft"] = str(
                            interrupt.get("report_draft", "")
                        )
                        session.status = "awaiting_report"
                        session.current_step = "synthesizing"
                        session.progress_percent = 95
                    event = "HITL_TRIGGER"
                session.task = None
                session.revision += 1
                snapshot = self._snapshot_unlocked(session)
            await self._emit(session.session_id, event, snapshot)
        except Exception as exc:
            logger.error("Research session %s failed (%s)", session.session_id, type(exc).__name__)
            try:
                state_snapshot = await self.graph.aget_state(config)
                values = getattr(state_snapshot, "values", None)
            except Exception:
                values = None
            async with session.lock:
                if isinstance(values, dict):
                    session.state = copy.deepcopy(values)
                session.pending_interrupt = None
                session.status = "error"
                session.current_step = "error"
                session.error = (
                    str(exc)[:500]
                    if isinstance(exc, UserVisibleResearchError)
                    else f"Research failed ({type(exc).__name__}). Check backend logs."
                )
                session.task = None
                session.revision += 1
                snapshot = self._snapshot_unlocked(session)
            await self._emit(session.session_id, "ERROR", snapshot)

    async def _emit(self, session_id: str, event: str, data: dict[str, Any]) -> None:
        if self.publish is None:
            return
        try:
            await asyncio.wait_for(
                self.publish(session_id, event, data),
                timeout=self._PUBLISH_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.warning("Failed to publish %s for session %s", event, session_id)

    async def shutdown(self) -> None:
        tasks = [session.task for session in self.sessions.values() if session.task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for session in self.sessions.values():
            async with session.lock:
                if session.status == "running":
                    session.status = "error"
                    session.current_step = "error"
                    session.error = "Backend shut down before research completed."
                    session.task = None
                    session.revision += 1

    @staticmethod
    def _find_interrupt(state_snapshot: Any) -> dict[str, Any] | None:
        for task in getattr(state_snapshot, "tasks", ()):
            for interrupt in getattr(task, "interrupts", ()):
                value = getattr(interrupt, "value", None)
                if isinstance(value, dict):
                    return value
        return None

    @classmethod
    def _public_sources(
        cls, session: ResearchSession, sources: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        candidates = sources if sources is not None else session.state.get("sources_found", [])
        read_metadata = {
            document.get("source_id"): document
            for document in session.state.get("documents_read", [])
            if document.get("source_id")
        }
        public_sources = []
        for source in candidates:
            source_data = cls._plain(source)
            if not isinstance(source_data, dict):
                continue
            source_id = source_data.get("source_id")
            document = read_metadata.get(source_id, {})
            for key in ("content_kind", "page_count", "truncated"):
                if key in document:
                    source_data[key] = document[key]
            public_sources.append(SourceMetadata.model_validate(source_data).model_dump())
        return public_sources

    @staticmethod
    def _validate_plan_for_session(
        session: ResearchSession, plan: list[Any]
    ) -> list[dict[str, Any]]:
        search_mode = session.state.get("search_mode", "web")
        if search_mode not in {"web", "academic", "mixed", "provided"}:
            raise SessionConflict("The session has an unsupported search mode.")
        budget = session.state.get("budget") or {}
        max_web = budget.get("max_tavily_calls", 0)
        max_academic = budget.get("max_scholar_calls", 0)
        mode_targets = {
            "web": {"web"},
            "academic": {"academic"},
            "mixed": {"web", "academic"},
            "provided": {"web"},
        }[search_mode]
        counts = {"web": 0, "academic": 0}
        max_provided_questions = budget.get("max_documents_to_read", 0)
        result = []
        ids = set()
        for raw in plan:
            question = raw if isinstance(raw, ResearchSubQuestion) else ResearchSubQuestion.model_validate(raw)
            if question.id in ids:
                raise SessionConflict("Plan question IDs must be unique.")
            if question.target_source not in mode_targets:
                raise SessionConflict("A plan question uses a search provider outside this mode.")
            counts[question.target_source] += 1
            if search_mode == "provided" and len(plan) > max_provided_questions:
                raise SessionConflict("The provided-source plan exceeds the document limit.")
            if search_mode != "provided" and counts[question.target_source] > (
                max_web if question.target_source == "web" else max_academic
            ):
                raise SessionConflict("The plan exceeds a provider's search budget.")
            ids.add(question.id)
            result.append(question.model_copy(update={"status": "pending"}).model_dump())
        if not result:
            raise SessionConflict("A non-empty plan is required.")
        return result

    @staticmethod
    def _validate_selected_sources(
        session: ResearchSession,
        pending: dict[str, Any],
        selected_source_ids: list[str] | None,
    ) -> None:
        if not isinstance(selected_source_ids, list) or not selected_source_ids:
            raise SessionConflict("At least one source must be selected.")
        if len(selected_source_ids) != len(set(selected_source_ids)):
            raise SessionConflict("Selected source IDs must be unique.")
        budget = session.state.get("budget") or {}
        available = max(
            0,
            budget.get("max_documents_to_read", 0)
            - budget.get("current_documents_read", 0),
        )
        if len(selected_source_ids) > available:
            raise SessionConflict("Selection exceeds the remaining document read budget.")
        known_ids = {
            source.get("source_id")
            for source in pending.get("sources", [])
            if isinstance(source, dict)
        }
        if set(selected_source_ids) - known_ids:
            raise SessionConflict("Selection includes an unknown source ID.")

    @classmethod
    def _plain(cls, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return cls._plain(value.model_dump())
        if isinstance(value, dict):
            return {key: cls._plain(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._plain(item) for item in value]
        return value

    @classmethod
    def _snapshot_unlocked(cls, session: ResearchSession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "status": session.status,
            "revision": session.revision,
            "current_step": session.current_step,
            "progress_percent": session.progress_percent,
            "research_plan": cls._plain(session.state.get("research_plan", [])),
            "sources_found": cls._public_sources(session),
            "selected_source_ids": list(session.state.get("selected_source_ids", [])),
            "source_errors": list(session.state.get("source_errors", [])),
            "pending_interrupt": cls._plain(session.pending_interrupt),
            "error": session.error,
        }
