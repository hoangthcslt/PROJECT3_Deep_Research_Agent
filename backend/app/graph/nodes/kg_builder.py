"""Persist this session's indexed sources and findings in Neo4j."""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)


def _field(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


async def kg_builder_node(state: DeepResearchState) -> Dict[str, Any]:
    session_id = state["session_id"]
    sources = { _field(source, "source_id"): source for source in state.get("sources_found", []) }
    documents = state.get("documents_read", [])
    read_source_ids = {document.get("source_id") for document in documents if document.get("source_id")}

    for document in documents:
        source_id = document.get("source_id")
        source = sources.get(source_id)
        await neo4j_service.create_source_node(
            source_id=source_id,
            title=document.get("title") or _field(source, "title", "Untitled"),
            url=document.get("url") or _field(source, "url"),
            source_type=document.get("source_type", "webpage"),
            session_id=session_id,
        )

    for index, finding in enumerate(state.get("extracted_findings", [])):
        source_ids = set(_field(finding, "source_ids", []))
        if not source_ids or not source_ids <= read_source_ids:
            continue
        finding_id = f"finding_{index}"
        await neo4j_service.create_finding_node(
            finding_id=finding_id,
            claim=_field(finding, "claim", ""),
            confidence=_field(finding, "confidence_score", 0.0),
            session_id=session_id,
        )
        for source_id in sorted(source_ids):
            await neo4j_service.link_finding_to_source(
                finding_id=finding_id,
                source_id=source_id,
                session_id=session_id,
            )

    logger.info(
        "Stored %s read sources and %s findings for session %s",
        len(read_source_ids),
        len(state.get("extracted_findings", [])),
        session_id,
    )
    return {"errors": []}
