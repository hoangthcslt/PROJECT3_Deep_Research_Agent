"""Extract cited findings from indexed web pages in this session."""

import logging
from typing import Any, Dict

from app.graph.errors import UserVisibleResearchError
from app.graph.state import DeepResearchState
from app.models.budget import SessionBudget
from app.services.qdrant_service import qdrant_service
from app.tools.extract_findings import extract_key_findings

logger = logging.getLogger(__name__)


async def extractor_node(state: DeepResearchState) -> Dict[str, Any]:
    session_id = state["session_id"]
    research_question = state["research_question"]
    sub_questions = state.get("research_plan", [])
    read_source_ids = {
        document.get("source_id")
        for document in state.get("documents_read", [])
        if document.get("source_id")
    }
    budget = SessionBudget.model_validate(state.get("budget") or {})
    all_findings = []

    if not read_source_ids:
        raise UserVisibleResearchError(
            "None of the selected sources could be read and indexed. Review the source errors and choose another source."
        )

    documents_by_id = {
        document.get("source_id"): document
        for document in state.get("documents_read", [])
        if document.get("source_id")
    }

    for sub_question in sub_questions:
        relevant_chunks = await qdrant_service.search(
            session_id=session_id,
            query_text=sub_question.question,
            top_k=5,
            budget=budget,
        )
        relevant_chunks = [
            chunk for chunk in relevant_chunks
            if chunk.get("source_id") in read_source_ids and chunk.get("content", "").strip()
        ]
        if not relevant_chunks:
            continue

        context = "\n\n---\n\n".join(
            _source_context(chunk, documents_by_id.get(chunk["source_id"], {}))
            for chunk in relevant_chunks
        )
        allowed_ids = {chunk["source_id"] for chunk in relevant_chunks}
        knowledge = await extract_key_findings(
            document_text=context,
            research_question=f"{research_question}\nSub-question: {sub_question.question}",
            budget=budget,
        )

        for finding in knowledge.findings:
            valid_ids = sorted(set(finding.source_ids) & allowed_ids)
            if valid_ids:
                all_findings.append(finding.model_copy(update={"source_ids": valid_ids}))

    logger.info("Extracted %s findings from session %s", len(all_findings), session_id)
    return {
        "extracted_findings": all_findings,
        "budget": budget.model_dump(),
    }


def _source_context(chunk: dict[str, Any], document: dict[str, Any]) -> str:
    source_id = chunk["source_id"]
    content_kind = document.get("content_kind") or chunk.get("content_kind") or "webpage"
    page_count = document.get("page_count") or chunk.get("page_count")
    truncated = bool(document.get("truncated", chunk.get("truncated", False)))
    details = [f"content_kind={content_kind}"]
    if page_count is not None:
        details.append(f"pages={page_count}")
    if truncated:
        details.append("excerpt_truncated=true")
    if content_kind == "abstract":
        details.append("abstract_only; do not treat as full paper")
    return f"[Source: {source_id} | {'; '.join(details)}]\n{chunk['content']}"
