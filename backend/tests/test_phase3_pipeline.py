"""Provider-free regressions for the actual Phase 3 pipeline nodes and storage calls."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.models.budget import BudgetExhaustedError, SessionBudget
from app.models.schemas import ExtractedFinding, ResearchSubQuestion, SourceMetadata, WebScrapeResult


def _state(**overrides):
    state = {
        "research_question": "A sufficiently long pipeline regression question",
        "session_id": "session-a",
        "search_mode": "web",
        "input_urls": [],
        "provided_source_ids": [],
        "selected_source_ids": [],
        "user_uploaded_files": [],
        "research_plan": [ResearchSubQuestion(
            id="sq_1", question="A web research query", target_source="web"
        )],
        "loop_count": 0,
        "max_loops": 1,
        "sources_found": [],
        "documents_read": [],
        "extracted_findings": [],
        "knowledge_gaps": [],
        "reflection_summary": "",
        "budget": SessionBudget().model_dump(),
    }
    state.update(overrides)
    return state


def test_planner_caps_queries_to_search_budget_and_normalizes_output(monkeypatch):
    from app.graph.nodes import planner

    class FakeLLM:
        messages = None

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, messages):
            type(self).messages = messages
            return SimpleNamespace(content=json.dumps([
                {
                    "id": f"sq_{index}",
                    "question": f"Web question {index}",
                    "target_source": "academic",
                    "status": "completed",
                }
                for index in range(1, 5)
            ]))

    monkeypatch.setattr(planner, "ChatGoogleGenerativeAI", FakeLLM)
    budget = SessionBudget(max_tavily_calls=2, max_total_input_tokens=20_000)
    result = asyncio.run(planner.planner_node(_state(budget=budget.model_dump())))

    assert "tối đa 2" in FakeLLM.messages[0]["content"]
    assert len(result["research_plan"]) == 2
    assert all(question.target_source == "web" for question in result["research_plan"])
    assert all(question.status == "pending" for question in result["research_plan"])
    assert result["budget"]["current_total_input_tokens"] > 0


def test_planner_input_budget_fails_before_llm_call(monkeypatch):
    from app.graph.nodes import planner

    class NeverCalledLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            raise AssertionError("Planner provider should not be called.")

    monkeypatch.setattr(planner, "ChatGoogleGenerativeAI", NeverCalledLLM)
    budget = SessionBudget(max_total_input_tokens=0)
    with pytest.raises(BudgetExhaustedError):
        asyncio.run(planner.planner_node(_state(budget=budget.model_dump())))
    assert NeverCalledLLM.calls == 0


def test_search_budget_is_checked_before_tavily_call(monkeypatch):
    from app.graph.nodes import searcher

    called = False

    async def fake_search(*_args, **_kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(searcher, "search_web", fake_search)
    budget = SessionBudget(max_tavily_calls=0)
    state = _state(budget=budget.model_dump())

    with pytest.raises(BudgetExhaustedError):
        asyncio.run(searcher.searcher_node(state))
    assert not called


def test_searcher_fails_instead_of_reporting_empty_search_as_success(monkeypatch):
    from app.graph.nodes import searcher

    async def empty_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(searcher, "search_web", empty_search)
    from app.graph.errors import UserVisibleResearchError
    with pytest.raises(UserVisibleResearchError, match="no usable sources"):
        asyncio.run(searcher.searcher_node(_state()))


def test_reader_bounds_utf8_ingestion_and_propagates_embedding_failure(monkeypatch):
    from app.graph.nodes import reader

    source = SourceMetadata(
        source_id="REF_LONG", title="Long page", url="https://example.com/long", source_type="webpage"
    )
    observed = {}

    async def fake_read(_url):
        return WebScrapeResult(
            url=source.url, title=source.title, full_text="é" * 10_000, extracted_date="now"
        )

    async def fake_ingest(**kwargs):
        observed.update(kwargs)
        kwargs["budget"].reserve_input(kwargs["content"])
        return 1

    monkeypatch.setattr(reader, "read_url", fake_read)
    monkeypatch.setattr(reader.qdrant_service, "ingest_document", fake_ingest)
    result = asyncio.run(reader.reader_node(_state(
        sources_found=[source], selected_source_ids=[source.source_id]
    )))
    assert len(observed["content"].encode("utf-8")) <= reader.MAX_INDEXED_TEXT_BYTES
    assert result["documents_read"][0]["truncated"] is True
    assert result["budget"]["current_documents_read"] == 1

    async def failed_ingest(**_kwargs):
        raise RuntimeError("embedding provider failed")

    monkeypatch.setattr(reader.qdrant_service, "ingest_document", failed_ingest)
    with pytest.raises(RuntimeError, match="embedding provider failed"):
        asyncio.run(reader.reader_node(_state(
            sources_found=[source], selected_source_ids=[source.source_id]
        )))


def test_reader_document_limit_stops_before_network_read(monkeypatch):
    from app.graph.nodes import reader

    called = False

    async def forbidden_read(_url):
        nonlocal called
        called = True
        raise AssertionError("Page reader should not be called at a zero document limit.")

    monkeypatch.setattr(reader, "read_url", forbidden_read)
    source = SourceMetadata(
        source_id="REF_BLOCKED", title="Unavailable", url="https://example.com", source_type="webpage"
    )
    budget = SessionBudget(max_documents_to_read=0)
    result = asyncio.run(reader.reader_node(_state(
        sources_found=[source], selected_source_ids=[source.source_id], budget=budget.model_dump()
    )))
    assert not called
    assert result["documents_read"] == []
    assert "document read limit" in result["source_errors"][0]


def test_extractor_discards_findings_not_supported_by_read_session_sources(monkeypatch):
    from app.graph.nodes import extractor

    valid_source = SourceMetadata(
        source_id="REF_READ", title="Read source", url="https://example.com/read", source_type="webpage"
    )

    async def fake_search(**_kwargs):
        return [{"source_id": "REF_READ", "content": "evidence"},
                {"source_id": "REF_UNREAD", "content": "unread evidence"}]

    async def fake_extract(**_kwargs):
        return SimpleNamespace(findings=[
            ExtractedFinding(
                claim="Supported", evidence="Evidence", source_ids=["REF_READ"], confidence_score=0.9
            ),
            ExtractedFinding(
                claim="Unsupported", evidence="No evidence", source_ids=["REF_UNREAD"], confidence_score=0.8
            ),
        ])

    monkeypatch.setattr(extractor.qdrant_service, "search", fake_search)
    monkeypatch.setattr(extractor, "extract_key_findings", fake_extract)
    result = asyncio.run(extractor.extractor_node(_state(
        sources_found=[valid_source],
        documents_read=[{"source_id": "REF_READ", "title": "Read source"}],
    )))

    assert [finding.claim for finding in result["extracted_findings"]] == ["Supported"]
    assert result["extracted_findings"][0].source_ids == ["REF_READ"]


def test_extraction_input_budget_fails_before_llm_call(monkeypatch):
    from app.tools import extract_findings

    class NeverCalledLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        def with_structured_output(self, _schema):
            return self

        async def ainvoke(self, _prompt):
            type(self).calls += 1
            raise AssertionError("Extraction provider should not be called.")

    monkeypatch.setattr(extract_findings, "ChatGoogleGenerativeAI", NeverCalledLLM)
    with pytest.raises(BudgetExhaustedError):
        asyncio.run(extract_findings.extract_key_findings(
            "some context", "some question", SessionBudget(max_total_input_tokens=0)
        ))
    assert NeverCalledLLM.calls == 0


def test_reflection_input_budget_fails_before_llm_call(monkeypatch):
    from app.graph.nodes import reflector

    class NeverCalledLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            raise AssertionError("Reflection provider should not be called.")

    monkeypatch.setattr(reflector, "ChatGoogleGenerativeAI", NeverCalledLLM)
    budget = SessionBudget(max_total_input_tokens=0)
    with pytest.raises(BudgetExhaustedError):
        asyncio.run(reflector.reflector_node(_state(budget=budget.model_dump())))
    assert NeverCalledLLM.calls == 0


class _FakeResult:
    def __init__(self, record=None):
        self.record = record

    async def single(self):
        return self.record


class _FakeNeo4jSession:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None

    async def run(self, query, **params):
        self.calls.append((query, params))
        if "RETURN collect(DISTINCT" in query:
            return _FakeResult({"nodes": [], "links": []})
        return _FakeResult()


class _FakeNeo4jDriver:
    def __init__(self):
        self.calls = []

    def session(self):
        return _FakeNeo4jSession(self.calls)


def test_neo4j_nodes_relationships_and_retrieval_are_session_scoped():
    from app.services.neo4j_service import Neo4jService

    service = Neo4jService()
    driver = _FakeNeo4jDriver()
    service.driver = driver

    async def run():
        for session_id in ("session-a", "session-b"):
            await service.create_source_node(
                source_id="REF_1", title="Same URL", url="https://example.com",
                source_type="webpage", session_id=session_id,
            )
            await service.create_finding_node(
                finding_id="finding_1", claim="Same local finding", confidence=0.9,
                session_id=session_id,
            )
            await service.link_finding_to_source(
                finding_id="finding_1", source_id="REF_1", session_id=session_id,
            )
        await service.get_session_graph("session-a")

    asyncio.run(run())
    source_keys = [params["source_key"] for query, params in driver.calls if "MERGE (s:Source" in query]
    finding_keys = [params["finding_key"] for query, params in driver.calls if "MERGE (f:Finding" in query]
    relationships = [(query, params) for query, params in driver.calls if "EXTRACTED_FROM" in query]
    graph_query, graph_params = driver.calls[-1]

    assert source_keys == ["session-a:REF_1", "session-b:REF_1"]
    assert finding_keys == ["session-a:finding_1", "session-b:finding_1"]
    assert all(params["source_key"] == f"{params['session_id']}:REF_1" for _, params in relationships)
    assert all(params["finding_key"] == f"{params['session_id']}:finding_1" for _, params in relationships)
    assert graph_params["session_id"] == "session-a"
    assert "n.session_id = $session_id" in graph_query
    assert "m.session_id = $session_id" in graph_query


def test_kg_builder_persists_only_successfully_read_sources(monkeypatch):
    from app.graph.nodes import kg_builder

    calls = []

    async def record_source(**kwargs):
        calls.append(("source", kwargs))

    async def record_finding(**kwargs):
        calls.append(("finding", kwargs))

    async def record_link(**kwargs):
        calls.append(("link", kwargs))

    monkeypatch.setattr(kg_builder.neo4j_service, "create_source_node", record_source)
    monkeypatch.setattr(kg_builder.neo4j_service, "create_finding_node", record_finding)
    monkeypatch.setattr(kg_builder.neo4j_service, "link_finding_to_source", record_link)

    state = _state(
        sources_found=[
            SourceMetadata(source_id="REF_READ", title="Read", url="https://example.com/read", source_type="webpage"),
            SourceMetadata(source_id="REF_SEARCH", title="Search only", url="https://example.com/other", source_type="webpage"),
        ],
        documents_read=[{"source_id": "REF_READ", "title": "Read", "url": "https://example.com/read", "source_type": "webpage"}],
        extracted_findings=[ExtractedFinding(
            claim="Supported", evidence="Evidence", source_ids=["REF_READ"], confidence_score=0.9
        )],
    )

    asyncio.run(kg_builder.kg_builder_node(state))
    assert [kind for kind, _ in calls] == ["source", "finding", "link"]
    assert calls[0][1]["source_id"] == "REF_READ"
    assert all(call[1]["session_id"] == "session-a" for call in calls)
    assert calls[2][1]["source_id"] == "REF_READ"
