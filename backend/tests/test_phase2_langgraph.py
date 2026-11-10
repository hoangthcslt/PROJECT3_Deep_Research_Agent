"""Real LangGraph checkpoint tests with provider calls and tools replaced."""

import importlib
import json
from types import SimpleNamespace

import pytest

for dependency in (
    "langgraph",
    "langchain_core",
    "langchain_google_genai",
    "tavily",
    "qdrant_client",
    "neo4j",
    "httpx",
    "pydantic_settings",
):
    pytest.importorskip(dependency)


def test_plan_and_report_approval_resume_without_repeating_llm_calls(monkeypatch):
    from langgraph.types import Command

    planner_module = importlib.import_module("app.graph.nodes.planner")
    synthesizer_module = importlib.import_module("app.graph.nodes.synthesizer")
    workflow_module = importlib.import_module("app.graph.workflow")
    from app.models.budget import SessionBudget
    from app.models.schemas import ExtractedFinding, SourceMetadata

    class PlannerLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            return SimpleNamespace(content=json.dumps([{
                "id": "sq_1",
                "question": "Generated question",
                "target_source": "academic",
                "status": "completed",
            }]))

    class SynthesizerLLM:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def ainvoke(self, _messages):
            type(self).calls += 1
            return SimpleNamespace(content=(
                "# Draft report\n\n"
                "The study shows that the test result is useful [^REF_TEST]."
            ))

    captured_plan = []
    source = SourceMetadata(
        source_id="REF_TEST",
        title="Test source",
        url="https://example.com/test",
        source_type="webpage",
    )

    async def searcher(state):
        captured_plan.extend(question.model_dump() for question in state["research_plan"])
        return {"sources_found": [source]}

    async def empty_reader(_state):
        return {"documents_read": [{
            "source_id": source.source_id,
            "title": source.title,
            "url": source.url,
            "source_type": "webpage",
            "content": "The page supports a test finding.",
        }]}

    async def empty_extractor(_state):
        return {"extracted_findings": [ExtractedFinding(
            claim="The study shows that the test result is useful.",
            evidence="A supported test result.",
            source_ids=[source.source_id],
            confidence_score=0.9,
        )]}

    async def empty_kg_builder(_state):
        return {}

    async def complete_reflection(_state):
        return {"knowledge_gaps": []}

    monkeypatch.setattr(planner_module, "ChatGoogleGenerativeAI", PlannerLLM)
    monkeypatch.setattr(synthesizer_module, "ChatGoogleGenerativeAI", SynthesizerLLM)
    monkeypatch.setattr(workflow_module, "searcher_node", searcher)
    monkeypatch.setattr(workflow_module, "reader_node", empty_reader)
    monkeypatch.setattr(workflow_module, "extractor_node", empty_extractor)
    monkeypatch.setattr(workflow_module, "kg_builder_node", empty_kg_builder)
    monkeypatch.setattr(workflow_module, "reflector_node", complete_reflection)
    graph = workflow_module.build_research_graph()
    config = {"configurable": {"thread_id": "phase2-approval-test"}}
    initial_state = {
        "research_question": "A sufficiently long integration test question",
        "session_id": "phase2-approval-test",
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
        async for _update in graph.astream(value, config, stream_mode="updates"):
            pass

    async def run():
        await drain(initial_state)
        plan_checkpoint = await graph.aget_state(config)
        assert plan_checkpoint.next == ("plan_approval",)
        assert PlannerLLM.calls == 1
        assert plan_checkpoint.values["research_plan"][0].status == "pending"
        assert plan_checkpoint.values["research_plan"][0].target_source == "web"

        await drain(Command(resume={
            "action": "modify",
            "plan": [{
                "id": "sq_1",
                "question": "Edited question",
                "target_source": "web",
                "status": "completed",
            }],
        }))
        report_checkpoint = await graph.aget_state(config)
        assert report_checkpoint.next == ("report_approval",)
        assert PlannerLLM.calls == 1
        assert SynthesizerLLM.calls == 1
        assert captured_plan == [{
            "id": "sq_1",
            "question": "Edited question",
            "target_source": "web",
            "status": "pending",
        }]
        assert "[^REF_TEST]" in report_checkpoint.tasks[0].interrupts[0].value["report_draft"]
        assert "https://example.com/test" in report_checkpoint.tasks[0].interrupts[0].value["report_draft"]

        await drain(Command(resume={"action": "approve"}))
        completed = await graph.aget_state(config)
        assert completed.next == ()
        assert "[^REF_TEST]" in completed.values["final_report"]
        assert PlannerLLM.calls == 1
        assert SynthesizerLLM.calls == 1

    import asyncio

    asyncio.run(run())
