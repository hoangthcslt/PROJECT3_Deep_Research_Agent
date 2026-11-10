"""Connected Quick workflow using real LangGraph/Qdrant and fake provider boundaries."""

import asyncio
import hashlib
import json
import re
from types import SimpleNamespace

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams


def test_quick_workflow_runs_real_nodes_and_persists_session_budget(monkeypatch):
    from langgraph.types import Command

    from app.graph.nodes import extractor, planner, reader, reflector, searcher, synthesizer
    from app.tools import extract_findings
    from app.graph.workflow import build_research_graph
    from app.models.budget import SessionBudget
    from app.models.schemas import ExtractedFinding, ExtractedKnowledge, WebScrapeResult, WebSearchResult
    from app.services.neo4j_service import neo4j_service
    from app.services.qdrant_service import QdrantService
    import app.services.qdrant_service as qdrant_module

    page_url = "https://example.com/quick-research"
    source_id = "REF_" + hashlib.sha256(page_url.encode("utf-8")).hexdigest()[:16]

    class PlannerLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            return SimpleNamespace(content=json.dumps([{
                "id": "sq_1",
                "question": "How does the example approach work?",
                "target_source": "academic",
                "status": "completed",
            }]))

    class ExtractionLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema):
            return self

        async def ainvoke(self, prompt):
            type(self).calls += 1
            match = re.search(r"\[Source: (REF_[A-Za-z0-9_-]+)\]", prompt)
            assert match
            return ExtractedKnowledge(findings=[ExtractedFinding(
                claim="The documented approach reduces setup time.",
                evidence="The page describes a shorter setup process.",
                source_ids=[match.group(1)],
                confidence_score=0.9,
            )])

    class ReflectorLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            return SimpleNamespace(content=json.dumps({
                "coverage_score": 0.95,
                "has_enough_info": True,
                "summary": "The source addresses the research question.",
                "knowledge_gaps": [],
            }))

    class SynthesizerLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            return SimpleNamespace(content=(
                "# Quick report\n\n"
                f"The evidence shows that the documented approach reduces setup time [^{source_id}]."
            ))

    async def fake_web_search(query, max_results=5):
        assert query
        assert max_results == 5
        return [WebSearchResult(
            title="Example documentation",
            url=page_url,
            content_snippet="A short search snippet.",
        )]

    async def fake_read_url(url):
        assert url == page_url
        return WebScrapeResult(
            url=url,
            title="Example documentation",
            full_text=("This page documents a shorter setup process. " * 30),
            extracted_date="2026-11-09",
        )

    async def fake_embed_texts(texts):
        assert texts and all(text.strip() for text in texts)
        return [[1.0] + [0.0] * 767 for _ in texts]

    async def fake_embed_single(text):
        assert text.strip()
        return [1.0] + [0.0] * 767

    class RecordResult:
        async def single(self):
            return None

    class RecordNeo4jSession:
        def __init__(self, calls):
            self.calls = calls

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

        async def run(self, query, **params):
            self.calls.append((query, params))
            return RecordResult()

    class RecordNeo4jDriver:
        def __init__(self):
            self.calls = []

        def session(self):
            return RecordNeo4jSession(self.calls)

    qdrant = QdrantService()
    qdrant.collection_name = "phase3_quick_test"
    neo_driver = RecordNeo4jDriver()
    monkeypatch.setattr(neo4j_service, "driver", neo_driver, raising=False)
    monkeypatch.setattr(planner, "ChatGoogleGenerativeAI", PlannerLLM)
    monkeypatch.setattr(extract_findings, "ChatGoogleGenerativeAI", ExtractionLLM)
    monkeypatch.setattr(reflector, "ChatGoogleGenerativeAI", ReflectorLLM)
    monkeypatch.setattr(synthesizer, "ChatGoogleGenerativeAI", SynthesizerLLM)
    monkeypatch.setattr(searcher, "search_web", fake_web_search)
    monkeypatch.setattr(reader, "read_url", fake_read_url)
    monkeypatch.setattr(extractor, "qdrant_service", qdrant)
    monkeypatch.setattr(reader, "qdrant_service", qdrant)
    monkeypatch.setattr(qdrant_module.embedding_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(qdrant_module.embedding_service, "embed_single", fake_embed_single)

    async def run():
        qdrant.client = AsyncQdrantClient(location=":memory:")
        await qdrant.client.create_collection(
            collection_name=qdrant.collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        graph = build_research_graph()
        config = {"configurable": {"thread_id": "session-quick"}}
        initial_state = {
            "research_question": "How can setup time be reduced in this workflow?",
            "session_id": "session-quick",
            "user_uploaded_files": [],
            "plan_approved": False,
            "report_approved": False,
            "user_feedback": None,
            "research_plan": [],
            "loop_count": 0,
            "max_loops": 1,
            "budget": SessionBudget().model_dump(),
            "sources_found": [],
            "documents_read": [],
            "extracted_findings": [],
            "knowledge_gaps": [],
            "reflection_summary": "",
            "report_draft": None,
            "final_report": None,
            "errors": [],
        }

        async def drain(value):
            async for _event in graph.astream(value, config, stream_mode="updates"):
                pass

        try:
            await drain(initial_state)
            plan_checkpoint = await graph.aget_state(config)
            assert plan_checkpoint.next == ("plan_approval",)
            assert PlannerLLM.calls == 1

            await drain(Command(resume={
                "action": "modify",
                "plan": [{
                    "id": "sq_1",
                    "question": "How does the example approach work?",
                    "target_source": "web",
                    "status": "completed",
                }],
            }))
            report_checkpoint = await graph.aget_state(config)
            assert report_checkpoint.next == ("report_approval",)
            assert PlannerLLM.calls == 1
            assert ExtractionLLM.calls == 1
            assert ReflectorLLM.calls == 1
            assert SynthesizerLLM.calls == 1

            values = report_checkpoint.values
            assert values["sources_found"][0].source_id == source_id
            assert values["documents_read"][0]["source_id"] == source_id
            assert values["extracted_findings"][0].source_ids == [source_id]
            budget = SessionBudget.model_validate(values["budget"])
            assert budget.current_tavily_calls == 1
            assert budget.current_documents_read == 1
            assert budget.current_loop == 1
            assert budget.current_total_input_tokens > 0

            same_session_chunks = await qdrant.search(
                session_id="session-quick",
                query_text="setup time",
                budget=SessionBudget(),
            )
            other_session_chunks = await qdrant.search(
                session_id="another-session",
                query_text="setup time",
                budget=SessionBudget(),
            )
            assert same_session_chunks
            assert {chunk["source_id"] for chunk in same_session_chunks} == {source_id}
            assert other_session_chunks == []

            await drain(Command(resume={"action": "approve"}))
            final = await graph.aget_state(config)
            assert final.next == ()
            assert source_id in final.values["final_report"]
            assert "https://example.com/quick-research" in final.values["final_report"]
            assert PlannerLLM.calls == 1
            assert SynthesizerLLM.calls == 1

            source_writes = [params for query, params in neo_driver.calls if "MERGE (s:Source" in query]
            finding_writes = [params for query, params in neo_driver.calls if "MERGE (f:Finding" in query]
            links = [params for query, params in neo_driver.calls if "EXTRACTED_FROM" in query]
            assert source_writes and source_writes[0]["source_key"] == f"session-quick:{source_id}"
            assert finding_writes and finding_writes[0]["finding_key"].startswith("session-quick:")
            assert links and links[0]["source_key"] == f"session-quick:{source_id}"
        finally:
            await qdrant.close()

    asyncio.run(run())
