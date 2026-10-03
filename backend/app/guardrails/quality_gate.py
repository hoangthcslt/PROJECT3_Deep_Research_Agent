"""
Quality Gatekeeper — ensures minimum data quality before synthesis.
Checks source count and diversity to prevent single-source bias.

Maps from brainstorm: guardrails_HITL.md (Trụ cột 4).
"""

import logging
from typing import List

from app.models.schemas import ExtractedFinding

logger = logging.getLogger(__name__)


def check_minimum_sources(sources_count: int, minimum: int = 3) -> bool:
    """
    Check if enough independent sources were collected.
    
    Args:
        sources_count: Number of sources read.
        minimum: Minimum required (default: 3).
    
    Returns:
        True if sufficient, False otherwise.
    """
    passed = sources_count >= minimum
    if not passed:
        logger.warning(
            f"⚠️ Quality Gate: Only {sources_count} sources (minimum: {minimum})"
        )
    return passed


def check_source_diversity(findings: List[ExtractedFinding]) -> bool:
    """
    Check that no single source dominates more than 50% of all findings.
    Prevents single-source bias in the report.
    
    Args:
        findings: List of extracted findings with source_ids.
    
    Returns:
        True if diverse enough, False if single-source bias detected.
    """
    total_findings = len(findings)
    if total_findings == 0:
        return False

    source_counts: dict[str, int] = {}
    for finding in findings:
        for source_id in finding.source_ids:
            source_counts[source_id] = source_counts.get(source_id, 0) + 1

    # Check if any source dominates > 50% of findings
    for source_id, count in source_counts.items():
        ratio = count / total_findings
        if ratio > 0.5 and len(source_counts) > 1:
            logger.warning(
                f"⚠️ Quality Gate: Source {source_id} dominates "
                f"{ratio:.0%} of findings — single-source bias detected"
            )
            return False

    return True
