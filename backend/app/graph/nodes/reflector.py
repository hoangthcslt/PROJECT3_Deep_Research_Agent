"""
Node 6: Reflector & Gap Analyzer
Evaluates collected findings against the research plan to identify
knowledge gaps and decide whether to loop or proceed to synthesis.

Maps from brainstorm: agent_flow_state_machine.md (Node 6)
           + system_prompt_api_schema.md (Reflector Prompt).
"""

import logging
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.graph.state import DeepResearchState
from app.models.schemas import KnowledgeGap

logger = logging.getLogger(__name__)

REFLECTOR_SYSTEM_PROMPT = """[ROLE]
Bạn là Chuyên gia Thẩm định Nghiên cứu (Peer Reviewer & Critical Thinker).
Nhiệm vụ của bạn là đọc các phát hiện hiện có, đối chiếu với Kế hoạch ban đầu và tìm ra các "Lỗ hổng Tri thức" (Knowledge Gaps).

[RULES]
1. Đánh giá khách quan: Các câu hỏi nghiên cứu đã có số liệu hoặc luận điểm chứng minh rõ ràng chưa?
2. Phát hiện mâu thuẫn: Có bài viết nào đưa ra kết luận trái ngược với bài khác không?
3. Tính toán "Coverage Score" (0.0 - 1.0):
   - Nếu Coverage Score >= 0.8: Đặt "has_enough_info" = True, không tạo thêm sub-questions mới.
   - Nếu Coverage Score < 0.8: Chỉ ra chính xác khía cạnh nào còn thiếu và sinh ra tối đa 2 search queries bổ sung.
4. CẢNH BÁO: Không được tự bịa ra thông tin để lấp lỗ hổng. Nếu tài liệu không nói, phải coi là "chưa có dữ liệu".

[OUTPUT FORMAT]
Return JSON with:
{
  "coverage_score": float (0.0-1.0),
  "has_enough_info": boolean,
  "summary": "Brief assessment of current knowledge state",
  "contradictions": ["List of contradictions found between sources"],
  "knowledge_gaps": [
    {
      "missing_aspect": "What is missing",
      "suggested_query": "Search query to fill the gap (in English)",
      "target_source": "academic" or "web"
    }
  ]
}
"""


async def reflector_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Evaluate collected findings against the research plan.
    Outputs knowledge gaps and increments loop counter.
    """
    logger.info("🪞 Reflector: Evaluating research coverage...")

    research_question = state["research_question"]
    research_plan = state.get("research_plan", [])
    findings = state.get("extracted_findings", [])
    loop_count = state.get("loop_count", 0)

    # ── Build context for LLM evaluation ──
    plan_summary = "\n".join([
        f"- [{sq.target_source}] {sq.question}" for sq in research_plan
    ])
    findings_summary = "\n".join([
        f"- [Confidence: {f.confidence_score:.1f}] {f.claim} (Sources: {', '.join(f.source_ids)})"
        for f in findings
    ])

    # ── Call LLM for reflection ──
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.1,
    )

    user_prompt = f"""
Câu hỏi nghiên cứu gốc: {research_question}

Kế hoạch nghiên cứu:
{plan_summary}

Các phát hiện đã thu thập ({len(findings)} findings):
{findings_summary}

Vòng lặp hiện tại: {loop_count + 1}
Vòng lặp tối đa: {state.get('max_loops', 3)}

Hãy đánh giá mức độ phủ kiến thức và chỉ ra các lỗ hổng (nếu có).
"""

    response = await llm.ainvoke([
        {"role": "system", "content": REFLECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    # ── Parse reflection result ──
    gaps, summary = _parse_reflection_response(response.content)

    logger.info(
        f"🪞 Reflector: Loop {loop_count + 1} — "
        f"Found {len(gaps)} knowledge gaps"
    )

    return {
        "knowledge_gaps": gaps,
        "reflection_summary": summary,
        "loop_count": loop_count + 1,
    }


def _parse_reflection_response(content: str) -> tuple[list[KnowledgeGap], str]:
    """Parse the LLM reflection response into gaps and summary."""
    import json

    try:
        cleaned = content.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        parsed = json.loads(cleaned)

        gaps = [
            KnowledgeGap(**gap) for gap in parsed.get("knowledge_gaps", [])
        ]
        summary = parsed.get("summary", "Reflection completed.")

        # If coverage is high enough, return no gaps
        if parsed.get("has_enough_info", False) or parsed.get("coverage_score", 0) >= 0.8:
            return [], summary

        return gaps, summary

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"⚠️ Failed to parse reflector response: {e}")
        return [], "Reflection parsing failed — proceeding to synthesis."
