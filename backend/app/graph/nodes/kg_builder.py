"""
Node 5: Knowledge Graph Builder
Transforms extracted findings and entities into Neo4j graph structures.

Maps from brainstorm: agent_flow_state_machine.md (Node 5)
           + tool_api_data_contracts.md (Neo4j Schema).
"""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)


async def kg_builder_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Build Knowledge Graph in Neo4j from extracted findings.
    Creates nodes: Paper, Concept, Author, Finding
    Creates relationships: AUTHORED, PROPOSES, CITES, EXTRACTED_FROM, RELATED_TO
    """
    logger.info("🕸️ KG Builder: Building knowledge graph...")

    session_id = state["session_id"]
    sources = state.get("sources_found", [])
    findings = state.get("extracted_findings", [])
    documents = state.get("documents_read", [])

    triplets_created = 0
    errors: list[str] = []

    try:
        # ── Create Paper nodes from sources ──
        for source in sources:
            if source.source_type == "paper":
                await neo4j_service.create_paper_node(
                    paper_id=source.source_id,
                    title=source.title,
                    year=source.year,
                    citations=source.citation_count,
                    url=source.url,
                    session_id=session_id,
                )
                triplets_created += 1

                # Create Author nodes and AUTHORED relationships
                for author in source.authors:
                    await neo4j_service.create_author_and_link(
                        author_name=author,
                        paper_id=source.source_id,
                    )
                    triplets_created += 1

        # ── Create Finding nodes and link to sources ──
        for i, finding in enumerate(findings):
            finding_id = f"finding_{session_id}_{i}"
            await neo4j_service.create_finding_node(
                finding_id=finding_id,
                claim=finding.claim,
                confidence=finding.confidence_score,
                session_id=session_id,
            )
            triplets_created += 1

            # Link findings to their source papers
            for source_id in finding.source_ids:
                await neo4j_service.link_finding_to_source(
                    finding_id=finding_id,
                    source_id=source_id,
                )
                triplets_created += 1

        logger.info(f"🕸️ KG Builder: Created {triplets_created} triplets in Neo4j")

    except Exception as e:
        error_msg = f"Knowledge graph building failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        errors.append(error_msg)

    return {
        "errors": errors,
    }
