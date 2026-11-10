import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ResearchResumeRequest,
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchSubQuestion,
    SourceMetadata,
)
from app.models.budget import SessionBudget
from app.services.session_manager import ResearchSessionManager, SessionConflict


def test_request_schemas_trim_validate_and_reject_payload_override():
    with pytest.raises(ValidationError):
        ResearchStartRequest(question="          ")
    with pytest.raises(ValidationError):
        ResearchSubQuestion(id="sq_1", question="  ", target_source="web")
    with pytest.raises(ValidationError):
        ResearchSubQuestion(id="sq_1", question="Query", target_source="internal")
    with pytest.raises(ValidationError):
        ResearchStartRequest(question="A sufficiently long question", depth="deep")
    assert ResearchStartRequest(
        question="A sufficiently long question",
        search_mode="academic",
        urls=["https://example.com/paper"],
    ).search_mode == "academic"
    for unsafe_url in (
        "http://localhost/private",
        "http://127.0.0.1/file.pdf",
        "https://user:pass@example.com/",
    ):
        with pytest.raises(ValidationError):
            ResearchStartRequest(question="A sufficiently long question", urls=[unsafe_url])
    with pytest.raises(ValidationError):
        ResearchResumeRequest(action="modify", interrupt_id="i1", plan=[])
    with pytest.raises(ValidationError):
        ResearchResumeRequest(
            action="modify",
            interrupt_id="i1",
            plan=[
                {"id": "sq_1", "question": "First", "target_source": "web"},
                {"id": "sq_1", "question": "Second", "target_source": "academic"},
            ],
        )
    assert ResearchResumeRequest(
        action="modify",
        interrupt_id="i1",
        plan=[{"id": "sq_1", "question": "Academic", "target_source": "academic"}],
    ).plan[0].target_source == "academic"
    with pytest.raises(ValidationError):
        ResearchResumeRequest(action="approve", interrupt_id="i1", payload={"action": "modify"})

    assert ResearchStartRequest(question="  A sufficiently long question  ").question == "A sufficiently long question"
    assert ResearchStartResponse(session_id="s1").status == "created"


def _snapshot(values=None, interrupt=None, next_nodes=()):
    tasks = () if interrupt is None else (
        SimpleNamespace(interrupts=(SimpleNamespace(value=interrupt),)),
    )
    return SimpleNamespace(values=values or {}, tasks=tasks, next=next_nodes)


class PendingWorkGraph:
    async def astream(self, *_args, **_kwargs):
        if False:
            yield {}

    async def aget_state(self, _config):
        return _snapshot(next_nodes=("searcher",))


def test_pending_graph_work_is_not_reported_as_complete():
    events = []

    async def publish(session_id, event, data):
        events.append((session_id, event, data))

    async def run():
        manager = ResearchSessionManager(PendingWorkGraph(), lambda value: value, publish)
        manager.create("s1", {})
        await manager.start("s1")
        await manager.get("s1").task
        return await manager.snapshot("s1")

    snapshot = asyncio.run(run())
    assert snapshot["status"] == "error"
    assert snapshot["current_step"] == "error"
    assert snapshot["error"].startswith("Research failed (RuntimeError)")
    assert events[-1][1] == "ERROR"


class CompletingGraph:
    def __init__(self):
        self.inputs = []
        self.state = _snapshot()

    async def astream(self, value, config, stream_mode):
        assert stream_mode == "updates"
        self.inputs.append((deepcopy(value), config["configurable"]["thread_id"]))
        self.state = _snapshot(values=value)
        yield {"planner": {}}

    async def aget_state(self, _config):
        return self.state


def test_upload_and_run_are_serialized_and_upload_is_available_before_run():
    async def run():
        graph = CompletingGraph()
        manager = ResearchSessionManager(graph, lambda value: {"resume": value})
        source = SourceMetadata(
            source_id="REF_PDF_" + "a" * 64,
            title="paper.pdf",
            url="/api/v1/research/s1/sources/REF_PDF_" + "a" * 64 + "/pdf",
            source_type="uploaded_pdf",
            content_kind="pdf_excerpt",
        )
        record = {"source_id": source.source_id, "source": source, "content": "PDF text"}
        manager.create("s1", {
            "search_mode": "web",
            "budget": SessionBudget().model_dump(),
            "sources_found": [],
            "provided_source_ids": [],
            "user_uploaded_files": [],
        })
        upload_entered = asyncio.Event()
        release_upload = asyncio.Event()

        async def save_upload():
            upload_entered.set()
            await release_upload.wait()
            return record

        upload_task = asyncio.create_task(manager.upload("s1", save_upload))
        await upload_entered.wait()
        run_task = asyncio.create_task(manager.start("s1"))
        await asyncio.sleep(0)
        assert not run_task.done()

        release_upload.set()
        await upload_task
        result = await run_task
        await manager.get("s1").task
        assert result["status"] == "running"
        assert graph.inputs[0][0]["user_uploaded_files"][0]["source_id"] == source.source_id

        with pytest.raises(SessionConflict):
            await manager.start("s1")

        manager.create("s2", {"user_uploaded_files": [], "budget": SessionBudget().model_dump()})
        await manager.start("s2")
        await manager.get("s2").task
        assert graph.inputs[0][0]["user_uploaded_files"] == []
        assert graph.inputs[0][1] == "s2"

    asyncio.run(run())


def test_report_view_returns_stored_draft_then_only_approved_final_for_export():
    async def run():
        manager = ResearchSessionManager(CompletingGraph(), lambda value: value)
        manager.create("s1", {"report_draft": "# Draft", "report_approved": False})

        draft = await manager.report_view("s1")
        assert draft == {
            "session_id": "s1",
            "status": "created",
            "report_markdown": "# Draft",
            "approved": False,
        }
        assert await manager.report("s1") is None

        session = manager.get("s1")
        session.status = "completed"
        session.state["report_approved"] = True
        session.state["final_report"] = "# Approved"
        final = await manager.report_view("s1")
        assert final == {
            "session_id": "s1",
            "status": "completed",
            "report_markdown": "# Approved",
            "approved": True,
        }
        assert await manager.report("s1") == "# Approved"

    asyncio.run(run())


class ApprovalGraph:
    def __init__(self):
        self.calls = 0
        self.thread_ids = []
        self.decisions = []
        self.state = _snapshot()
        self.release_second_run = asyncio.Event()
        self.plan = [{
            "id": "sq_1",
            "question": "Suggested question",
            "target_source": "academic",
            "status": "pending",
        }]

    async def astream(self, value, config, stream_mode):
        assert stream_mode == "updates"
        self.calls += 1
        self.thread_ids.append(config["configurable"]["thread_id"])
        if self.calls == 1:
            self.state = _snapshot(
                values={"research_plan": self.plan},
                interrupt={
                    "type": "PLAN_APPROVAL_REQUIRED",
                    "plan": self.plan,
                    "message": "Approve the plan.",
                },
                next_nodes=("plan_approval",),
            )
            yield {"planner": {}}
        elif self.calls == 2:
            decision = value["resume"]
            self.decisions.append(decision)
            plan = decision.get("plan", self.plan)
            report = "# Draft report"
            self.state = _snapshot(
                values={"research_plan": plan, "report_draft": report},
                interrupt={
                    "type": "REPORT_APPROVAL_REQUIRED",
                    "report_draft": report,
                    "message": "Review the report.",
                },
                next_nodes=("report_approval",),
            )
            yield {"searcher": {}}
            await self.release_second_run.wait()
        elif self.calls == 3:
            self.decisions.append(value["resume"])
            self.state = _snapshot(
                values={"research_plan": self.state.values["research_plan"], "final_report": "# Draft report"},
            )
            yield {"report_approval": {}}
        else:
            raise AssertionError("Graph was started more than once for a transition.")

    async def aget_state(self, _config):
        return self.state


def test_duplicate_and_stale_resumes_do_not_advance_the_wrong_checkpoint():
    events = []

    async def publish(session_id, event, data):
        events.append((session_id, event, data))

    async def run():
        graph = ApprovalGraph()
        manager = ResearchSessionManager(graph, lambda value: {"resume": value}, publish)
        manager.create("s1", {
            "research_plan": [],
            "search_mode": "web",
            "budget": SessionBudget().model_dump(),
        })
        await manager.start("s1")
        await manager.get("s1").task
        plan_snapshot = await manager.snapshot("s1")
        original_id = plan_snapshot["pending_interrupt"]["interrupt_id"]

        assert plan_snapshot["status"] == "awaiting_plan"
        assert graph.calls == 1
        assert (await manager.snapshot("s1"))["revision"] == plan_snapshot["revision"]
        assert graph.calls == 1  # Status reads never start the graph.

        edited_plan = [{
            "id": "sq_1",
            "question": "Edited question",
            "target_source": "web",
            "status": "completed",
        }]
        replies = await asyncio.gather(
            manager.resume("s1", original_id, "modify", edited_plan),
            manager.resume("s1", original_id, "modify", edited_plan),
            return_exceptions=True,
        )
        assert sum(isinstance(reply, dict) for reply in replies) == 1
        assert sum(isinstance(reply, SessionConflict) for reply in replies) == 1
        second_task = manager.get("s1").task
        assert second_task is not None
        graph.release_second_run.set()
        await second_task

        report_snapshot = await manager.snapshot("s1")
        new_id = report_snapshot["pending_interrupt"]["interrupt_id"]
        assert report_snapshot["status"] == "awaiting_report"
        assert report_snapshot["pending_interrupt"]["report_draft"] == "# Draft report"
        assert new_id != original_id
        assert graph.calls == 2

        with pytest.raises(SessionConflict):
            await manager.resume("s1", original_id, "approve")
        assert graph.calls == 2

        await manager.resume("s1", new_id, "approve")
        final_task = manager.get("s1").task
        assert final_task is not None
        await final_task
        final_snapshot = await manager.snapshot("s1")
        assert final_snapshot["status"] == "completed"
        assert graph.calls == 3
        assert graph.thread_ids == ["s1", "s1", "s1"]
        assert [event for _, event, _ in events].count("HITL_TRIGGER") == 2
        revisions = [data["revision"] for _, _, data in events]
        assert revisions == sorted(set(revisions))

    asyncio.run(run())


class FailingGraph:
    async def astream(self, *_args, **_kwargs):
        raise RuntimeError("internal provider details are not sent to the client")
        yield {}

    async def aget_state(self, _config):
        raise AssertionError("No state should be read after a failed graph call.")


def test_graph_exception_becomes_an_observable_error_snapshot():
    events = []

    async def publish(session_id, event, data):
        events.append((session_id, event, data))

    async def run():
        manager = ResearchSessionManager(FailingGraph(), lambda value: value, publish)
        manager.create("s1", {})
        await manager.start("s1")
        await manager.get("s1").task
        return await manager.snapshot("s1")

    snapshot = asyncio.run(run())
    assert snapshot["status"] == "error"
    assert snapshot["current_step"] == "error"
    assert "internal provider details" not in snapshot["error"]
    assert events[-1][1] == "ERROR"
