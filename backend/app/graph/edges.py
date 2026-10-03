"""
Conditional edge functions for LangGraph routing.
Controls the reflect loop circuit breaker and HITL branching.

Maps from brainstorm: agent_flow_state_machine.md (Section 4).
"""

from app.graph.state import DeepResearchState


def should_continue(state: DeepResearchState) -> str:
    """
    Conditional edge after the Reflector node.
    Decides whether to loop back to Searcher or proceed to Synthesizer.

    Exit conditions (→ synthesizer):
    1. No knowledge gaps remaining.
    2. Loop count reached max_loops (circuit breaker).

    Continue condition (→ searcher):
    - Gaps exist AND loop_count < max_loops.
    """
    gaps = state.get("knowledge_gaps", [])
    current_loop = state.get("loop_count", 0)
    max_loops = state.get("max_loops", 3)

    # Circuit Breaker: hard stop at max iterations
    if current_loop >= max_loops:
        return "synthesizer"

    # No more gaps → proceed to synthesis
    if not gaps or len(gaps) == 0:
        return "synthesizer"

    # Still have gaps and budget → loop back
    return "searcher"


def route_after_plan_hitl(state: DeepResearchState) -> str:
    """
    Conditional edge after HITL plan approval.
    Routes to searcher if approved, back to planner if rejected.
    """
    if state.get("plan_approved", False):
        return "searcher"
    return "planner"


def route_after_report_hitl(state: DeepResearchState) -> str:
    """
    Conditional edge after HITL report review.
    Routes to end if approved, back to synthesizer if feedback given.
    """
    if state.get("report_approved", False):
        return "end"
    # User gave feedback → re-synthesize
    return "synthesizer"
