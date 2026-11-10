"""Pause after discovery so users choose which candidates are read and indexed."""

from typing import Any, Dict

from langgraph.types import interrupt

from app.graph.state import DeepResearchState
from app.models.budget import SessionBudget


async def source_approval_node(state: DeepResearchState) -> Dict[str, Any]:
    candidates = state.get("sources_found", [])
    if not candidates:
        raise ValueError("No source candidates are available for selection.")
    public_sources = [
        source.model_dump() if hasattr(source, "model_dump") else dict(source)
        for source in candidates
    ]
    user_action = interrupt({
        "type": "SOURCE_SELECTION_REQUIRED",
        "sources": public_sources,
        "message": "Vui lòng chọn tối đa số nguồn cho phép để đọc sâu và lập chỉ mục.",
    })
    if not isinstance(user_action, dict) or user_action.get("action") != "select_sources":
        raise ValueError("A source selection is required before reading.")

    selected = user_action.get("selected_source_ids")
    if not isinstance(selected, list) or not selected:
        raise ValueError("At least one source must be selected.")
    if len(selected) != len(set(selected)):
        raise ValueError("Selected source IDs must be unique.")

    budget = SessionBudget.model_validate(state.get("budget") or {})
    remaining = max(0, budget.max_documents_to_read - budget.current_documents_read)
    if len(selected) > remaining:
        raise ValueError("Selected sources exceed the remaining document read budget.")

    known_ids = {
        source.source_id if hasattr(source, "source_id") else source.get("source_id")
        for source in candidates
    }
    unknown = set(selected) - known_ids
    if unknown:
        raise ValueError("Selection includes source IDs that were not found.")
    return {"selected_source_ids": selected}
