"""
Tool: parse_pdf — PyMuPDF4LLM PDF parser
Extracts text, tables, and metadata from uploaded PDF files into LLM-ready Markdown.

Maps from brainstorm: tool_api_data_contracts.md (Tool 4).
"""

import logging

import fitz  # PyMuPDF
import pymupdf4llm

from app.models.schemas import PDFParseResult

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> PDFParseResult:
    """
    Parse a PDF file into clean Markdown with table preservation.
    
    Args:
        file_path: Path to the PDF file on disk.
    
    Returns:
        PDFParseResult with full text, page count, metadata, and table count.
    """
    try:
        doc = fitz.open(file_path)
        page_count = doc.page_count
        metadata = dict(doc.metadata) if doc.metadata else {}
        doc.close()

        # pymupdf4llm converts PDF to LLM-ready markdown including tables
        md_text = pymupdf4llm.to_markdown(file_path)

        # Estimate number of tables by counting markdown table separators
        tables_count = md_text.count("|---|")

        logger.info(
            f"📄 parse_pdf('{file_path}') → {page_count} pages, "
            f"{len(md_text)} chars, {tables_count} tables"
        )

        return PDFParseResult(
            file_path=file_path,
            page_count=page_count,
            metadata=metadata,
            tables_detected=tables_count,
            full_text=md_text,
        )

    except Exception as e:
        logger.error(f"❌ PDF parsing failed for {file_path}: {e}")
        return PDFParseResult(
            file_path=file_path,
            page_count=0,
            metadata={},
            tables_detected=0,
            full_text="",
        )
