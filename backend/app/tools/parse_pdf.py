"""Parse bounded, text-bearing PDF excerpts without OCR."""

import logging
from pathlib import Path
from typing import Any

import pymupdf as fitz
import pymupdf4llm

from app.models.schemas import PDFParseResult

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_EXCERPT_PAGES = 10
MAX_EXCERPT_BYTES = 8_000


class PDFParseError(ValueError):
    """A PDF is unsafe, unsupported, or cannot be parsed."""


class PDFTooLargeError(PDFParseError):
    """A PDF exceeds the accepted byte or page limit."""


def parse_pdf(file_path: str | Path | bytes) -> PDFParseResult:
    """Parse only the first ten pages and return at most an 8 KB text excerpt."""
    doc = None
    display_path = "<memory>" if isinstance(file_path, bytes) else str(file_path)
    try:
        if isinstance(file_path, bytes):
            if len(file_path) > MAX_PDF_BYTES:
                raise PDFTooLargeError("PDF exceeds the 10 MiB size limit.")
            doc = fitz.open(stream=file_path, filetype="pdf")
        else:
            path = Path(file_path)
            if path.stat().st_size > MAX_PDF_BYTES:
                raise PDFTooLargeError("PDF exceeds the 10 MiB size limit.")
            doc = fitz.open(path)

        if not doc.is_pdf:
            raise PDFParseError("Uploaded file is not a valid PDF.")
        if doc.is_encrypted or doc.needs_pass:
            raise PDFParseError("Encrypted PDFs are not supported.")
        page_count = doc.page_count
        if page_count < 1:
            raise PDFParseError("PDF contains no pages.")
        if page_count > MAX_PDF_PAGES:
            raise PDFTooLargeError("PDF exceeds the 100 page limit.")

        excerpts = bytearray()
        tables_detected = 0
        text_found = False
        pages_extracted = 0
        truncated = page_count > MAX_EXCERPT_PAGES

        for page_number in range(min(page_count, MAX_EXCERPT_PAGES)):
            pages_extracted = page_number + 1
            page = doc.load_page(page_number)
            if not page.get_text("text").strip():
                continue
            text_found = True
            markdown = pymupdf4llm.to_markdown(
                doc,
                pages=[page_number],
                use_ocr=False,
                force_ocr=False,
            )
            tables_detected += markdown.count("|---|")
            page_text = markdown.encode("utf-8")
            separator = b"\n\n" if excerpts and page_text else b""
            remaining = MAX_EXCERPT_BYTES - len(excerpts)
            if len(separator) + len(page_text) > remaining:
                excerpts.extend((separator + page_text)[:remaining])
                truncated = True
                break
            excerpts.extend(separator)
            excerpts.extend(page_text)

        full_text = excerpts.decode("utf-8", errors="ignore").strip()
        if not text_found or not full_text:
            raise PDFParseError("PDF contains no extractable text; scanned or image-only PDFs are unsupported.")

        metadata: dict[str, Any] = dict(doc.metadata or {})
        metadata.update({"truncated": truncated, "pages_extracted": pages_extracted})
        logger.info("Parsed PDF excerpt (%s pages, %s bytes)", pages_extracted, len(full_text.encode("utf-8")))
        return PDFParseResult(
            file_path=display_path,
            page_count=page_count,
            metadata=metadata,
            tables_detected=tables_detected,
            full_text=full_text,
        )
    except PDFParseError:
        raise
    except Exception as exc:
        raise PDFParseError("PDF is malformed or cannot be parsed.") from exc
    finally:
        if doc is not None:
            doc.close()
