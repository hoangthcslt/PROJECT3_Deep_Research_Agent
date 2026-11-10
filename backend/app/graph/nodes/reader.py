"""Read only selected sources and index bounded, source-labelled excerpts."""

import logging
from typing import Any

from app.graph.errors import UserVisibleResearchError
from app.graph.state import DeepResearchState
from app.models.budget import SessionBudget
from app.services.qdrant_service import qdrant_service
from app.tools.parse_pdf import PDFParseError
from app.tools.read_url import read_pdf_url, read_url

logger = logging.getLogger(__name__)
MAX_INDEXED_TEXT_BYTES = 8_000


def _get(source: Any, name: str, default: Any = None) -> Any:
    return source.get(name, default) if isinstance(source, dict) else getattr(source, name, default)


def _truncate_utf8(text: str, max_bytes: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip(), True


async def reader_node(state: DeepResearchState) -> dict[str, Any]:
    """Read only the explicitly selected candidates, then ingest each source once."""
    session_id = state["session_id"]
    sources = state.get("sources_found", [])
    candidates = {
        _get(source, "source_id"): source
        for source in sources
        if _get(source, "source_id")
    }
    selected_ids = state.get("selected_source_ids", [])
    if not selected_ids or set(selected_ids) - set(candidates):
        raise UserVisibleResearchError("Select one or more available sources before reading.")

    uploaded = {
        record.get("source_id"): record
        for record in state.get("user_uploaded_files", [])
        if record.get("source_id")
    }
    existing_documents = state.get("documents_read", [])
    existing_ids = {document.get("source_id") for document in existing_documents}
    budget = SessionBudget.model_validate(state.get("budget") or {})
    documents_read: list[dict[str, Any]] = []
    source_errors: list[str] = []

    for source_id in selected_ids:
        if source_id in existing_ids:
            continue
        if not budget.can_read_document():
            source_errors.append(
                f"Could not read selected source {source_id}; the document read limit was reached."
            )
            continue
        budget.increment_document_read()
        source = candidates[source_id]
        source_type = _get(source, "source_type", "webpage")
        url = _get(source, "url")
        title = str(_get(source, "title", "Untitled source"))[:500]
        authors = list(_get(source, "authors", []) or [])
        year = _get(source, "year")
        page_count = _get(source, "page_count")
        truncated = bool(_get(source, "truncated", False))
        content_kind = "webpage"
        content = ""
        read_title = title

        if source_id in uploaded:
            record = uploaded[source_id]
            content = str(record.get("content", ""))
            content_kind = "pdf_excerpt"
            page_count = record.get("page_count")
            truncated = bool(record.get("truncated", False))
        elif source_type == "paper":
            pdf_url = _get(source, "open_access_pdf")
            abstract = str(_get(source, "content_snippet", "") or "").strip()
            if pdf_url:
                try:
                    parsed = await read_pdf_url(pdf_url)
                    content = str(parsed.get("full_text", ""))
                    page_count = parsed.get("page_count")
                    truncated = bool(parsed.get("truncated", False))
                    content_kind = "pdf_excerpt"
                    if not content.strip():
                        raise PDFParseError("No readable PDF text.")
                except Exception:
                    if abstract:
                        content = abstract
                        content_kind = "abstract"
                        source_errors.append(
                            f"Could not read full text for source {source_id}; the abstract was used instead."
                        )
                    else:
                        source_errors.append(
                            f"Could not read selected source {source_id}; no readable text was available."
                        )
            elif abstract:
                content = abstract
                content_kind = "abstract"
            else:
                source_errors.append(
                    f"Could not read selected source {source_id}; no readable text was available."
                )
        elif isinstance(url, str) and url.lower().split("?", 1)[0].split("#", 1)[0].endswith(".pdf"):
            try:
                parsed = await read_pdf_url(url)
                content = str(parsed.get("full_text", ""))
                page_count = parsed.get("page_count")
                truncated = bool(parsed.get("truncated", False))
                content_kind = "pdf_excerpt"
                if not content.strip():
                    source_errors.append(
                        f"Could not read selected source {source_id}; no readable text was available."
                    )
            except Exception:
                source_errors.append(
                    f"Could not read selected source {source_id}; the PDF was invalid or unavailable."
                )
        elif isinstance(url, str):
            result = await read_url(url)
            content = result.full_text
            read_title = str(result.title or title)[:500]
            content_kind = "webpage"
            if not content.strip():
                source_errors.append(
                    f"Could not read selected source {source_id}; no readable text was available."
                )
        elif source_type == "paper":
            content = str(_get(source, "content_snippet", "") or "")
            content_kind = "abstract"
        else:
            source_errors.append(
                f"Could not read selected source {source_id}; no readable text was available."
            )

        if not content.strip():
            continue

        indexed_text, index_truncated = _truncate_utf8(content, MAX_INDEXED_TEXT_BYTES)
        truncated = truncated or index_truncated
        indexed_chunks = await qdrant_service.ingest_document(
            session_id=session_id,
            source_id=source_id,
            content=indexed_text,
            metadata={
                "source_url": url,
                "source_type": source_type,
                "title": read_title,
                "authors": authors,
                "year": year,
                "content_kind": content_kind,
                "page_count": page_count,
                "truncated": truncated,
            },
            budget=budget,
        )
        if not indexed_chunks:
            raise RuntimeError("A selected source could not be indexed.")

        documents_read.append({
            "source_id": source_id,
            "title": read_title,
            "content": indexed_text,
            "url": url,
            "source_type": source_type,
            "content_kind": content_kind,
            "page_count": page_count,
            "truncated": truncated,
        })
        existing_ids.add(source_id)
        logger.info("Indexed selected source %s (%s chunks)", source_id, indexed_chunks)

    return {
        "documents_read": documents_read,
        "errors": source_errors,
        "source_errors": source_errors,
        "budget": budget.model_dump(),
    }
