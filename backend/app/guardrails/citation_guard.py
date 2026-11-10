"""Validate report citations against successfully read session sources."""

import re
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlsplit

CITATION_PATTERN = re.compile(r"(?<!\\)\[\^(REF_[A-Za-z0-9_-]+)\]")
SOURCE_ID_PATTERN = re.compile(r"REF_[A-Za-z0-9_-]+")
REFERENCE_HEADING = re.compile(
    r"(?i)^\s{0,3}#{1,6}\s+(?:\d+(?:\.\d+)*[.)]?\s+)?"
    r"(?:references?|bibliography|sources?|danh\s+mục\s+tài\s+liệu\s+tham\s+khảo|"
    r"tài\s+liệu\s+tham\s+khảo)\b"
)
REFERENCE_DEFINITION = re.compile(
    r"(?i)^[ \t]*(?:[-*+][ \t]+)?\[\^REF_[A-Za-z0-9_-]+\]:"
)
FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(?P<ticks>`+)(?!`).*?(?<!`)(?P=ticks)(?!`)", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)
CLAIM_INDICATORS = (
    "shows that", "demonstrates", "according to", "results indicate",
    "evidence suggests", "the study found", "reported that", "achieves",
    "outperforms", "indicates that", "according to research", "results show",
    "cho thấy", "chứng minh", "kết quả", "kết quả cho thấy", "theo nghiên cứu",
    "nghiên cứu cho thấy", "báo cáo rằng", "kết luận rằng",
)


class CitationValidationError(ValueError):
    """Raised before a draft can be shown when it has unsafe citations."""


def _field(value: Any, name: str, default: Any = "") -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _safe_http_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value or any(char.isspace() or ord(char) < 32 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or "\\" in parsed.netloc
        or (port is not None and port == 0)
    ):
        return None
    # Angle brackets and other non-URI characters cannot escape the Markdown link target.
    return quote(value, safe=":/?#[]@!$&'()*+,;=%")


def _markdown_title(value: str) -> str:
    title = " ".join(value.split())
    title = title.replace("&", "&amp;")
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>])", r"\\\1", title)


def canonical_references(state: Mapping[str, Any]) -> dict[str, str]:
    """Build references only from documents the reader successfully indexed."""
    sources = {
        _field(source, "source_id"): source
        for source in state.get("sources_found", [])
        if _field(source, "source_id")
    }
    references: dict[str, str] = {}
    for document in state.get("documents_read", []):
        source_id = _field(document, "source_id")
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
            continue
        source = sources.get(source_id)
        if source is None:
            continue
        content = _field(document, "content")
        if not isinstance(content, str) or not content.strip():
            continue
        title = _field(document, "title") or _field(source, "title")
        raw_url = _field(source, "url")
        document_url = _field(document, "url")
        if document_url and document_url != raw_url:
            continue
        source_type = _field(source, "source_type")
        if source_type == "uploaded_pdf":
            session_id = state.get("session_id")
            try:
                session_key = str(uuid.UUID(session_id))
            except (AttributeError, ValueError, TypeError):
                continue
            if (
                _field(document, "source_type") != "uploaded_pdf"
                or session_key != session_id
                or not re.fullmatch(r"REF_PDF_[0-9a-f]{64}", source_id)
                or raw_url != f"/api/v1/research/{session_key}/sources/{source_id}/pdf"
                or document_url != raw_url
            ):
                continue
            url = raw_url
            citation = f"[{_markdown_title(title)}](<{url}>)" if isinstance(title, str) else ""
        else:
            url = _safe_http_url(raw_url)
            citation = f"{_markdown_title(title)} — <{url}>" if isinstance(title, str) and url else ""
        if isinstance(title, str) and title.strip() and url:
            references[source_id] = citation
    return references


def _fenced_lines(report: str):
    """Yield each line with whether it belongs to a fenced code block."""
    fence: str | None = None
    for line in report.splitlines(keepends=True):
        if fence:
            yield line, True
            if re.match(rf"^[ \t]{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$", line):
                fence = None
            continue
        opening = FENCE_OPEN.match(line)
        if opening:
            fence = opening.group(1)
            yield line, True
        else:
            yield line, False


def strip_generated_references(report: str) -> str:
    """Remove model-written bibliography sections and footnote definitions."""
    body: list[str] = []
    skip_definition_continuation = False
    for line, in_code in _fenced_lines(report):
        if in_code:
            skip_definition_continuation = False
            body.append(line)
            continue
        if REFERENCE_HEADING.match(line):
            break
        if REFERENCE_DEFINITION.match(line):
            skip_definition_continuation = True
            continue
        if skip_definition_continuation and (not line.strip() or line.startswith((" ", "\t"))):
            continue
        skip_definition_continuation = False
        body.append(line)
    return "".join(body).rstrip()


def _citation_body(report: str) -> str:
    text = "".join(
        line for line, in_code in _fenced_lines(report)
        if not in_code and not line.startswith(("    ", "\t"))
    )
    return HTML_COMMENT.sub("", INLINE_CODE.sub("", text))


def validate_report_citations(report: str, references: Mapping[str, str]) -> None:
    """Reject uncited claims, missing citations, and citations outside read docs."""
    if not references:
        raise CitationValidationError("No successfully read sources are available to cite.")
    if not report or not report.strip():
        raise CitationValidationError("The generated report is empty.")

    citation_body = _citation_body(strip_generated_references(report))
    citations = set(CITATION_PATTERN.findall(citation_body))
    if not citations:
        raise CitationValidationError("The report body contains no inline source citations.")
    invalid = citations - set(references)
    if invalid:
        raise CitationValidationError(
            "The report cites sources that were not read in this session: "
            + ", ".join(sorted(invalid))
        )

    for line in citation_body.splitlines():
        content = line.strip().lstrip("-*+").strip()
        if not content or content.startswith(("#", ">")):
            continue
        if any(indicator in content.lower() for indicator in CLAIM_INDICATORS) and not CITATION_PATTERN.search(content):
            raise CitationValidationError("A factual claim is missing an inline source citation.")


def format_canonical_references(references: Mapping[str, str]) -> str:
    """Render valid Markdown footnote definitions from canonical references."""
    lines = [
        f"[^{source_id}]: {citation}"
        for source_id, citation in sorted(references.items())
        if isinstance(source_id, str) and SOURCE_ID_PATTERN.fullmatch(source_id)
    ]
    return "## References\n" + "\n".join(lines)
