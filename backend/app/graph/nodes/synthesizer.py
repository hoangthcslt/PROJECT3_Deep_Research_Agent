"""
Node 7: Report Synthesizer
Generates a structured research report from all extracted findings.
Commits the draft before the separate report approval node pauses the graph.

Maps from brainstorm: agent_flow_state_machine.md (Node 7)
           + system_prompt_api_schema.md (Synthesizer Prompt).
"""

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from app.config import settings
from app.graph.state import DeepResearchState
from app.guardrails.citation_guard import (
    canonical_references,
    format_canonical_references,
    strip_generated_references,
    validate_report_citations,
)
from app.models.budget import SessionBudget

logger = logging.getLogger(__name__)

SYNTHESIZER_SYSTEM_PROMPT = """[ROLE]
Bạn là Tác giả Tổng hợp Báo cáo Khoa học (Lead Scientific Writer).
Nhiệm vụ của bạn là viết một báo cáo chuyên sâu, mạch lạc dựa DUY NHẤT trên các thông tin đã được trích xuất.

[CONSTRAINTS & GROUNDING]
1. NGUYÊN TẮC BẤT DI BẤT DỊCH: Mọi khẳng định (claim) đều PHẢI có trích dẫn inline trỏ về mã nguồn, định dạng [^REF_X].
2. Nếu hai tài liệu có kết luận trái ngược nhau, hãy trình bày cả hai góc nhìn dưới dạng thảo luận phản biện (Critique).
3. Tuyệt đối không sử dụng tri thức ngoài context được cung cấp. Nếu thiếu thông tin, hãy viết: "Hiện chưa có đủ công trình công bố về khía cạnh này".

[OUTPUT FORMAT]
Báo cáo viết bằng Markdown chuẩn:
# [Tiêu đề Báo cáo]
## 1. Tóm tắt Điều hành (Executive Summary)
## 2. Bối cảnh & Cơ sở Lý thuyết
## 3. Phân tích Chuyên sâu & Ma trận So sánh
## 4. Những hạn chế & Thảo luận mở (Limitations & Discussion)
## 5. Danh mục Tài liệu Tham khảo (Bắt buộc ánh xạ đúng [^REF_X] -> URL/Tác giả)
"""


async def synthesizer_node(state: DeepResearchState) -> dict[str, Any]:
    """
    Synthesize a structured research report from all collected findings.
    Triggers HITL interrupt for user review before finalization.
    """
    logger.info("📝 Synthesizer: Generating research report...")

    research_question = state["research_question"]
    findings = state.get("extracted_findings", [])
    reflection_summary = state.get("reflection_summary", "")
    user_feedback = state.get("user_feedback")
    budget = SessionBudget.model_validate(state.get("budget") or {})

    references = canonical_references(state)
    if not references:
        raise RuntimeError("Cannot synthesize a report without indexed web sources.")
    readable_ids = set(references)
    findings = [
        finding for finding in findings
        if finding.source_ids and set(finding.source_ids) <= readable_ids
    ]
    if not findings:
        raise RuntimeError("Cannot synthesize a report without source-backed findings.")

    # ── Build context for synthesis ──
    findings_text = "\n".join([
        f"### Finding (Sources: {', '.join(f.source_ids)}, Confidence: {f.confidence_score:.1f})\n"
        f"**Claim:** {f.claim}\n**Evidence:** {f.evidence}\n"
        for f in findings
    ])

    sources_reference = format_canonical_references(references)
    source_limitations = _source_limitations(state)

    feedback_instruction = ""
    if user_feedback:
        feedback_instruction = f"\n\n[USER FEEDBACK - PLEASE ADDRESS THIS]\n{user_feedback}\n"

    user_prompt = f"""
Câu hỏi nghiên cứu: {research_question}

Đánh giá từ Reflector: {reflection_summary}

CÁC PHÁT HIỆN ĐÃ TRÍCH XUẤT:
{findings_text}

DANH MỤC NGUỒN TÀI LIỆU (dùng [^REF_X] để trích dẫn):
{sources_reference}

PHẠM VI ĐỌC VÀ GIỚI HẠN NGUỒN (không mô tả abstract/PDF excerpt như toàn văn):
{source_limitations}
{feedback_instruction}

Hãy viết báo cáo nghiên cứu hoàn chỉnh theo đúng cấu trúc đã quy định.
"""

    # ── Generate report with LLM ──
    budget.reserve_input(f"{SYNTHESIZER_SYSTEM_PROMPT}\n{user_prompt}")
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
        max_output_tokens=4096,
    )

    response = await llm.ainvoke([
        {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    if not isinstance(response.content, str) or len(response.content) > 50_000:
        raise ValueError("Synthesizer response exceeded the allowed output size.")

    generated_report = response.content.strip()
    validate_report_citations(generated_report, references)
    report_draft = strip_generated_references(generated_report)
    if source_limitations:
        report_draft = report_draft.rstrip() + "\n\n## Sources and reading limitations\n\n" + source_limitations
    # Replace generated references with title/URL pairs from indexed sources.
    report_draft = report_draft.rstrip() + "\n\n" + format_canonical_references(references)

    logger.info(f"📝 Synthesizer: Generated report ({len(report_draft)} chars)")

    # ── HITL Interrupt: Ask user to review the report ──
    return {
        "report_draft": report_draft,
        "report_approved": False,
        "budget": budget.model_dump(),
    }


def _source_limitations(state: DeepResearchState) -> str:
    sources = {
        source.source_id if hasattr(source, "source_id") else source.get("source_id"): source
        for source in state.get("sources_found", [])
    }
    lines = []
    for document in state.get("documents_read", []):
        source_id = document.get("source_id")
        kind = document.get("content_kind", "webpage")
        details = []
        if kind == "abstract":
            details.append("abstract only; this is not full paper text")
        elif kind == "pdf_excerpt":
            pages = document.get("page_count")
            details.append(
                f"PDF excerpt, at most the first 10 pages"
                + (f" of {pages} pages" if pages is not None else "")
            )
        else:
            details.append("web page text excerpt")
        if document.get("truncated"):
            details.append("excerpt truncated to the indexing limit")
        source = sources.get(source_id)
        title = (
            source.title if hasattr(source, "title") else source.get("title", "")
        ) if source else document.get("title", "")
        lines.append(f"- [^{source_id}] {title[:160]}: {'; '.join(details)}.")

    for error in state.get("source_errors", [])[:12]:
        if isinstance(error, str):
            lines.append(f"- {error[:300]}")
    return "\n".join(lines)


async def report_approval_node(state: DeepResearchState) -> dict[str, Any]:
    """Commit report approval separately so resuming never repeats synthesis."""
    user_action = interrupt({
        "type": "REPORT_APPROVAL_REQUIRED",
        "report_draft": state.get("report_draft") or "",
        "message": "Báo cáo nghiên cứu đã sẵn sàng. Vui lòng xem xét và phê duyệt.",
    })
    if not isinstance(user_action, dict) or user_action.get("action") != "approve":
        raise ValueError("Only report approval is supported in this phase.")
    return {
        "report_approved": True,
        "final_report": state.get("report_draft"),
    }
