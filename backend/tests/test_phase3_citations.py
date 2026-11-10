import pytest

from app.guardrails.citation_guard import (
    CitationValidationError,
    canonical_references,
    format_canonical_references,
    strip_generated_references,
    validate_report_citations,
)

REFERENCES = {"REF_A": "A source — <https://source.test/article>"}


def test_reference_only_report_is_rejected():
    report = "## 5. Danh mục Tài liệu Tham khảo\n\n[^REF_A]: Fake — <https://fake.test>"

    with pytest.raises(CitationValidationError, match="no inline source citations"):
        validate_report_citations(report, REFERENCES)


@pytest.mark.parametrize(
    "report",
    [
        "```markdown\nA result shows that [^REF_A].\n```",
        "~~~text\n[^REF_A]\n~~~",
        "The literal `[^REF_A]` is shown here.",
        "    [^REF_A]\n",
        "<!-- [^REF_A] -->\n",
    ],
)
def test_citations_in_fenced_or_inline_code_do_not_count(report):
    with pytest.raises(CitationValidationError, match="no inline source citations"):
        validate_report_citations(report, REFERENCES)


def test_unknown_body_citation_is_rejected():
    with pytest.raises(CitationValidationError, match="REF_OTHER"):
        validate_report_citations(
            "The results show that this finding holds [^REF_A] and [^REF_OTHER].",
            REFERENCES,
        )


def test_uncited_vietnamese_claim_is_rejected_even_when_another_line_is_cited():
    report = "Phân tích cho thấy xu hướng này [^REF_A].\nKết quả cho thấy mức tăng rõ rệt."

    with pytest.raises(CitationValidationError, match="claim is missing"):
        validate_report_citations(report, REFERENCES)


def test_generated_vietnamese_references_are_replaced_and_code_is_preserved():
    report = (
        "# Findings\n\n"
        "```markdown\n## References\n[^REF_BAD]: code example\n```\n\n"
        "The study shows that the result holds [^REF_A].\n\n"
        "## 5. Danh mục Tài liệu Tham khảo\n"
        "[^REF_A]: Wrong title — <https://wrong.test>\n"
    )

    stripped = strip_generated_references(report)
    final = stripped + "\n\n" + format_canonical_references(REFERENCES)

    assert "[^REF_BAD]: code example" in final
    assert "Wrong title" not in final
    assert "https://wrong.test" not in final
    assert "[^REF_A]: A source — <https://source.test/article>" in final
    assert "- [^REF_A]:" not in final
    validate_report_citations(report, REFERENCES)


def test_canonical_references_require_a_read_source_and_safe_http_url():
    state = {
        "sources_found": [
            {"source_id": "REF_READ", "title": "Search title", "url": "https://read.test/page"},
            {"source_id": "REF_SEARCH_ONLY", "title": "Search only", "url": "https://search.test/"},
            {"source_id": "REF_BAD_URL", "title": "Unsafe", "url": "javascript:alert(1)"},
        ],
        "documents_read": [
            {
                "source_id": "REF_READ",
                "title": "Read [title]*",
                "url": "https://read.test/page",
                "content": "indexed text",
            },
            {"source_id": "REF_BAD_URL", "title": "Unsafe", "url": "javascript:alert(1)"},
            {"source_id": "REF_MISSING", "title": "No matching source", "url": "https://missing.test/"},
        ],
    }

    references = canonical_references(state)
    rendered = format_canonical_references(references)

    assert set(references) == {"REF_READ"}
    assert "Read \\[title\\]\\* — <https://read.test/page>" in rendered
    assert "Search only" not in rendered
    assert "javascript:" not in rendered


def test_valid_body_citation_passes_when_generated_definition_is_present():
    report = (
        "The results show that the outcome is consistent [^REF_A].\n\n"
        "[^REF_UNREAD]: Should not count as a body citation.\n"
    )

    validate_report_citations(report, REFERENCES)
