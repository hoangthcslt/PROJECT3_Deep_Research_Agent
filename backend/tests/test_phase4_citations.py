import uuid

import pytest

from app.guardrails.citation_guard import (
    CitationValidationError,
    canonical_references,
    format_canonical_references,
    validate_report_citations,
)


def _uploaded_state(session_id: str, url: str, source_type="uploaded_pdf"):
    source_id = "REF_PDF_" + "a" * 64
    source = {
        "source_id": source_id,
        "title": "Uploaded report.pdf",
        "url": url,
        "source_type": source_type,
    }
    document = {
        "source_id": source_id,
        "title": "Uploaded report.pdf",
        "url": url,
        "source_type": source_type,
        "content": "Extracted PDF text",
    }
    return {"session_id": session_id, "sources_found": [source], "documents_read": [document]}, source_id


def test_uploaded_pdf_citation_uses_exact_session_source_and_validates():
    session_id = str(uuid.uuid4())
    source_id = "REF_PDF_" + "a" * 64
    url = f"/api/v1/research/{session_id}/sources/{source_id}/pdf"
    state, _ = _uploaded_state(session_id, url)

    references = canonical_references(state)
    rendered = format_canonical_references(references)

    assert set(references) == {source_id}
    assert f"[Uploaded report\\.pdf](<{url}>)" in rendered
    validate_report_citations(f"The results show that the claim is supported [^{source_id}].", references)


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/research/other-session/sources/REF_PDF_" + "a" * 64 + "/pdf",
        "/uploads/private.pdf",
        "file:///private/report.pdf",
        "https://example.test/report.pdf",
    ],
)
def test_uploaded_pdf_citation_rejects_cross_session_and_arbitrary_urls(url):
    state, source_id = _uploaded_state(str(uuid.uuid4()), url)

    references = canonical_references(state)

    assert references == {}
    with pytest.raises(CitationValidationError, match="No successfully read sources"):
        validate_report_citations(f"The results show that [^{source_id}].", references)


def test_relative_source_url_is_not_allowed_for_non_pdf_source():
    session_id = str(uuid.uuid4())
    source_id = "REF_PDF_" + "a" * 64
    url = f"/api/v1/research/{session_id}/sources/{source_id}/pdf"
    state, _ = _uploaded_state(session_id, url, source_type="webpage")

    assert canonical_references(state) == {}
