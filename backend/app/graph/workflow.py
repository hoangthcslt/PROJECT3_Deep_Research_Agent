"""
LangGraph workflow builder — assembles the 7-node research pipeline
with conditional edges, HITL interrupts, and checkpointing.

Maps from brainstorm: agent_flow_state_machine.md (Sections 1 & 5).
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import DeepResearchState
from app.graph.edges import should_continue
from app.graph.nodes.planner import planner_node, plan_approval_node
from app.graph.nodes.searcher import searcher_node
from app.graph.nodes.source_approval import source_approval_node
from app.graph.nodes.reader import reader_node
from app.graph.nodes.extractor import extractor_node
from app.graph.nodes.kg_builder import kg_builder_node
from app.graph.nodes.reflector import reflector_node
from app.graph.nodes.synthesizer import synthesizer_node, report_approval_node


def build_research_graph():
    """
    Build and compile the Deep Research Agent LangGraph workflow.

    Flow:
        START → planner → (HITL: plan approval) → searcher → reader →
        extractor → kg_builder → reflector → (should_continue?) →
            ├─ searcher (loop back if gaps remain)
            └─ synthesizer → (HITL: report review) → END
    
    Returns:
        Compiled LangGraph with MemorySaver checkpointer for HITL interrupts.
    """
    workflow = StateGraph(DeepResearchState)

    # ── Register Nodes ──
    workflow.add_node("planner", planner_node)
    workflow.add_node("plan_approval", plan_approval_node)
    workflow.add_node("searcher", searcher_node)
    workflow.add_node("source_approval", source_approval_node)
    workflow.add_node("reader", reader_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("kg_builder", kg_builder_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("report_approval", report_approval_node)

    # ── Define Edges ──
    # Entry point
    workflow.add_edge(START, "planner")

    # The plan is checkpointed before the approval interrupt.
    workflow.add_edge("planner", "plan_approval")
    workflow.add_edge("plan_approval", "searcher")

    # Sequential execution pipeline
    workflow.add_edge("searcher", "source_approval")
    workflow.add_edge("source_approval", "reader")
    workflow.add_edge("reader", "extractor")
    workflow.add_edge("extractor", "kg_builder")
    workflow.add_edge("kg_builder", "reflector")

    # Conditional loop: Reflector decides continue or synthesize
    workflow.add_conditional_edges(
        "reflector",
        should_continue,
        {
            "searcher": "searcher",       # Loop back if gaps exist
            "synthesizer": "synthesizer",  # Proceed if complete or max loops
        },
    )

    # The report is checkpointed before the approval interrupt.
    workflow.add_edge("synthesizer", "report_approval")
    workflow.add_edge("report_approval", END)

    # ── Compile with Checkpointer ──
    # MemorySaver for development; swap to PostgresSaver for production
    checkpointer = MemorySaver()

    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[],   # We use interrupt() inside nodes instead
        interrupt_after=[],
    )

    return graph


# Singleton graph instance
research_graph = build_research_graph()
