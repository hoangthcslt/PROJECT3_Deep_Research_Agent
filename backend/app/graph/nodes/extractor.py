"""
Node 4: Finding Extractor
Queries Qdrant for relevant context per sub-question, then uses LLM
to extract key findings, entities, and citations.

Maps from brainstorm: agent_flow_state_machine.md (Node 4).
"""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.tools.extract_findings import extract_key_findings
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


async def extractor_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    For each sub-question, query Qdrant for relevant chunks,
    then use LLM to extract structured findings with source attribution.
    """
    logger.info("🔬 Extractor: Extracting key findings from documents...")

    session_id = state["session_id"]
    research_question = state["research_question"]
    sub_questions = state.get("research_plan", [])

    all_findings = []
    errors: list[str] = []

    for sq in sub_questions:
        try:
            # ── Retrieve relevant chunks from Qdrant ──
            relevant_chunks = await qdrant_service.search(
                session_id=session_id,
                query_text=sq.question,
                top_k=5,
            )

            if not relevant_chunks:
                logger.warning(f"⚠️ Extractor: No relevant chunks for '{sq.question}'")
                continue

            # ── Combine chunks into context ──
            context = "\n\n---\n\n".join([
                f"[Source: {chunk.get('source_id', 'unknown')}]\n{chunk.get('content', '')}"
                for chunk in relevant_chunks
            ])

            # ── Extract findings using LLM ──
            knowledge = await extract_key_findings(
                document_text=context,
                research_question=f"{research_question}\nSub-question: {sq.question}",
            )

            # Map findings to source IDs
            for finding in knowledge.findings:
                all_findings.append(finding)

            logger.info(
                f"🔬 Extractor: '{sq.question}' → "
                f"{len(knowledge.findings)} findings, {len(knowledge.entities)} entities"
            )

        except Exception as e:
            error_msg = f"Extraction failed for '{sq.question}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)

    logger.info(f"🔬 Extractor: Total findings extracted: {len(all_findings)}")

    return {
        "extracted_findings": all_findings,
        "errors": errors,
    }
