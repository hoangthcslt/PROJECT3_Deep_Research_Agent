"""
Node 7: Report Synthesizer
Generates a structured research report from all extracted findings.
Includes HITL interrupt for user review before finalization.

Maps from brainstorm: agent_flow_state_machine.md (Node 7)
           + system_prompt_api_schema.md (Synthesizer Prompt).
"""

import logging
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from app.config import settings
from app.graph.state import DeepResearchState

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


async def synthesizer_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Synthesize a structured research report from all collected findings.
    Triggers HITL interrupt for user review before finalization.
    """
    logger.info("📝 Synthesizer: Generating research report...")

    research_question = state["research_question"]
    findings = state.get("extracted_findings", [])
    sources = state.get("sources_found", [])
    reflection_summary = state.get("reflection_summary", "")
    user_feedback = state.get("user_feedback")

    # ── Build context for synthesis ──
    findings_text = "\n".join([
        f"### Finding (Sources: {', '.join(f.source_ids)}, Confidence: {f.confidence_score:.1f})\n"
        f"**Claim:** {f.claim}\n**Evidence:** {f.evidence}\n"
        for f in findings
    ])

    sources_reference = "\n".join([
        f"- {s.source_id}: {s.title} ({s.source_type})"
        + (f" — {s.url}" if s.url else "")
        + (f" — {', '.join(s.authors)}" if s.authors else "")
        for s in sources
    ])

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
{feedback_instruction}

Hãy viết báo cáo nghiên cứu hoàn chỉnh theo đúng cấu trúc đã quy định.
"""

    # ── Generate report with LLM ──
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

    report_draft = response.content

    logger.info(f"📝 Synthesizer: Generated report ({len(report_draft)} chars)")

    # ── HITL Interrupt: Ask user to review the report ──
    user_action = interrupt({
        "type": "REPORT_APPROVAL_REQUIRED",
        "report_draft": report_draft,
        "sources_count": len(sources),
        "findings_count": len(findings),
        "message": "Báo cáo nghiên cứu đã sẵn sàng. Bạn có muốn chỉnh sửa phần nào không?",
    })

    # ── Process user response ──
    if isinstance(user_action, dict) and user_action.get("action") == "feedback":
        # User wants revisions → store feedback, report will be re-synthesized
        return {
            "report_draft": report_draft,
            "user_feedback": user_action.get("comment", ""),
            "report_approved": False,
        }

    # User approved → finalize
    final_content = report_draft
    if isinstance(user_action, dict):
        final_content = user_action.get("final_content", report_draft)

    return {
        "report_draft": report_draft,
        "final_report": final_content,
        "report_approved": True,
    }
