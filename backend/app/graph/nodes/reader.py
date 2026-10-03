"""
Node 3: Document Reader & Ingest
Reads full content from web URLs (via Jina Reader) and uploaded PDFs,
then chunks and stores embeddings in Qdrant.

Maps from brainstorm: agent_flow_state_machine.md (Node 3).
"""

import logging
from typing import Any, Dict

from app.graph.state import DeepResearchState
from app.tools.read_url import read_url
from app.tools.parse_pdf import parse_pdf
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


async def reader_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Read full content from discovered sources:
    1. Web URLs → Jina Reader for clean markdown
    2. Uploaded PDFs → PyMuPDF4LLM for markdown extraction
    Then chunk and embed into Qdrant for semantic retrieval.
    """
    logger.info("📖 Reader: Starting document ingestion...")

    session_id = state["session_id"]
    sources = state.get("sources_found", [])
    uploaded_files = state.get("user_uploaded_files", [])

    documents_read: list[Dict[str, Any]] = []
    errors: list[str] = []

    # ── Read web sources ──
    for source in sources:
        if source.source_type in ("paper", "webpage") and source.url:
            try:
                result = await read_url(source.url)
                if result.full_text:
                    doc_entry = {
                        "source_id": source.source_id,
                        "title": result.title,
                        "content": result.full_text,
                        "url": source.url,
                        "source_type": source.source_type,
                    }
                    documents_read.append(doc_entry)

                    # Chunk & embed into Qdrant
                    await qdrant_service.ingest_document(
                        session_id=session_id,
                        source_id=source.source_id,
                        content=result.full_text,
                        metadata={
                            "source_url": source.url,
                            "source_type": source.source_type,
                            "title": result.title,
                        },
                    )
                    logger.info(f"📖 Reader: Ingested '{result.title}' ({source.source_id})")
                else:
                    logger.warning(f"⚠️ Reader: Empty content from {source.url}")

            except Exception as e:
                error_msg = f"Failed to read {source.url}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)

    # ── Read uploaded PDFs ──
    for file_path in uploaded_files:
        try:
            result = parse_pdf(file_path)
            if result.full_text:
                source_id = f"REF_PDF_{len(documents_read) + 1}"
                doc_entry = {
                    "source_id": source_id,
                    "title": result.metadata.get("title", file_path),
                    "content": result.full_text,
                    "file_path": file_path,
                    "source_type": "uploaded_pdf",
                    "page_count": result.page_count,
                }
                documents_read.append(doc_entry)

                await qdrant_service.ingest_document(
                    session_id=session_id,
                    source_id=source_id,
                    content=result.full_text,
                    metadata={
                        "source_type": "uploaded_pdf",
                        "title": result.metadata.get("title", file_path),
                        "page_count": result.page_count,
                    },
                )
                logger.info(f"📖 Reader: Ingested PDF '{file_path}' ({result.page_count} pages)")

        except Exception as e:
            error_msg = f"Failed to parse PDF {file_path}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)

    logger.info(f"📖 Reader: Total documents ingested: {len(documents_read)}")

    return {
        "documents_read": documents_read,
        "errors": errors,
    }
