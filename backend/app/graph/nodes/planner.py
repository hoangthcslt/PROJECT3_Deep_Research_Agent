"""
Node 1: Research Planner
Decomposes the research question into 3-5 sub-questions with search strategy.
Includes HITL interrupt for user plan approval.

Maps from brainstorm: agent_flow_state_machine.md (Node 1) + system_prompt_api_schema.md
"""

import logging
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from app.config import settings
from app.graph.state import DeepResearchState
from app.models.schemas import ResearchSubQuestion

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """[ROLE]
Bạn là Trưởng nhóm Nghiên cứu Học thuật (Lead Research Strategist).
Nhiệm vụ của bạn là phân tích câu hỏi nghiên cứu của người dùng và lập kế hoạch thu thập thông tin đa tầng.

[RULES]
1. Phân rã câu hỏi lớn thành 3-5 câu hỏi phụ (sub-questions) độc lập nhưng bổ trợ cho nhau.
2. Với mỗi câu hỏi, chỉ định rõ nguồn dữ liệu tối ưu:
   - "academic": Nếu cần định nghĩa, thuật toán, công thức toán, hoặc so sánh khoa học (sẽ tìm trên Semantic Scholar).
   - "web": Nếu cần thông tin thực tế, cập nhật thị trường, tài liệu hãng, case study 2024-2025 (sẽ tìm qua Tavily).
3. Đặt mục tiêu tìm kiếm (search queries) bằng tiếng Anh chuẩn học thuật, dù câu hỏi gốc là tiếng Việt.
4. Trả về đúng định dạng JSON được quy định. Không thêm lời chào hỏi.

[OUTPUT FORMAT]
Return a JSON array of sub-questions. Each item has:
- "id": string (e.g., "sq_1")
- "question": string (search query in English)
- "target_source": "academic" or "web"
"""


async def planner_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Decompose the research question into sub-questions using LLM,
    then trigger HITL interrupt for user approval.
    """
    logger.info("📋 Planner: Decomposing research question...")

    research_question = state["research_question"]

    # ── Call LLM to generate research plan ──
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )

    response = await llm.ainvoke([
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Câu hỏi nghiên cứu: {research_question}"},
    ])

    # ── Parse LLM response into structured sub-questions ──
    # TODO: Use with_structured_output for reliable JSON parsing
    generated_plan = _parse_plan_response(response.content)

    logger.info(f"📋 Planner: Generated {len(generated_plan)} sub-questions")

    # ── HITL Interrupt: Ask user to approve/modify the plan ──
    user_action = interrupt({
        "type": "PLAN_APPROVAL_REQUIRED",
        "plan": [sq.model_dump() for sq in generated_plan],
        "message": "Vui lòng xem xét, xóa bớt hoặc thêm các hướng nghiên cứu.",
    })

    # ── Process user response ──
    if isinstance(user_action, dict) and user_action.get("action") == "modify":
        modified_plan = [
            ResearchSubQuestion(**sq) for sq in user_action.get("modified_plan", [])
        ]
        return {
            "research_plan": modified_plan,
            "plan_approved": True,
            "loop_count": 0,
        }

    return {
        "research_plan": generated_plan,
        "plan_approved": True,
        "loop_count": 0,
    }


def _parse_plan_response(content: str) -> list[ResearchSubQuestion]:
    """
    Parse the LLM response into a list of ResearchSubQuestion.
    Falls back to a single question if parsing fails.
    """
    import json

    try:
        # Try to extract JSON from the response
        # Handle cases where LLM wraps JSON in markdown code blocks
        cleaned = content.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        parsed = json.loads(cleaned)

        if isinstance(parsed, list):
            return [ResearchSubQuestion(**item) for item in parsed]
        elif isinstance(parsed, dict) and "sub_questions" in parsed:
            return [ResearchSubQuestion(**item) for item in parsed["sub_questions"]]
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning(f"⚠️ Failed to parse planner response: {e}")

    # Fallback: create a single sub-question from the original query
    return [
        ResearchSubQuestion(
            id="sq_1",
            question=content[:200],
            target_source="web",
            status="pending",
        )
    ]
