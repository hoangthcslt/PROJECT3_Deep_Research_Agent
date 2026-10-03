"""
Citation Guardrail — ensures all inline citations in the report
map to actually collected sources. Removes hallucinated references.

Maps from brainstorm: guardrails_HITL.md (Trụ cột 3, Section 1).
"""

import logging
import re
from typing import Set

from app.graph.state import DeepResearchState

logger = logging.getLogger(__name__)


def validate_citations(state: DeepResearchState) -> dict:
    """
    Cross-check all [^REF_X] citations in the report against known sources.
    Returns errors if hallucinated citations are found.
    """
    report = state.get("report_draft", "")
    if not report:
        return {}

    valid_source_ids: Set[str] = {
        s.source_id for s in state.get("sources_found", [])
    }

    # Find all citation references in the report
    citations_in_report = set(re.findall(r"\[\^(REF_\w+)\]", report))

    # Detect hallucinated citations
    invalid_citations = citations_in_report - valid_source_ids

    if invalid_citations:
        logger.warning(
            f"⚠️ Citation Guardrail: Found {len(invalid_citations)} "
            f"hallucinated citations: {invalid_citations}"
        )
        return {
            "errors": [
                f"Hallucinated citation detected: {cid}" for cid in invalid_citations
            ]
        }

    # Check for claims without any citations (optional strict mode)
    uncited_sentences = _find_uncited_claims(report)
    if uncited_sentences:
        logger.info(
            f"ℹ️ Citation Guardrail: {len(uncited_sentences)} sentences without citations"
        )

    return {}


def _find_uncited_claims(report: str) -> list[str]:
    """
    Find factual-looking sentences that lack inline citations.
    Only flags sentences containing strong claim keywords.
    """
    claim_indicators = [
        "cho thấy", "chứng minh", "kết quả", "theo nghiên cứu",
        "demonstrates", "shows that", "according to", "results indicate",
        "achieves", "outperforms",
    ]

    uncited = []
    for line in report.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue

        has_claim = any(indicator in line.lower() for indicator in claim_indicators)
        has_citation = bool(re.search(r"\[\^REF_\w+\]", line))

        if has_claim and not has_citation:
            uncited.append(line[:100])

    return uncited
