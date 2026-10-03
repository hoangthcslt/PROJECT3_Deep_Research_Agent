"""
Tool: extract_key_findings — LLM Structured Output Extraction
Uses Gemini with structured output to extract findings, entities, and citations
from document context.

Maps from brainstorm: tool_api_data_contracts.md (Tool 5).
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.models.schemas import ExtractedKnowledge

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """
Bạn là chuyên gia trích xuất thông tin nghiên cứu.
Câu hỏi nghiên cứu: {research_question}

Nội dung tài liệu:
\"\"\"{document_text}\"\"\"

Hãy trích xuất:
1. **findings**: Các phát hiện/luận điểm quan trọng (mỗi finding có claim, evidence, confidence_score 0.0-1.0)
2. **entities**: Các thực thể liên quan (tên, loại: Technology/Methodology/Metric/Author, mô tả ngắn)
3. **citations**: Các nguồn/tác giả được bài viết trích dẫn nội bộ

Chỉ trích xuất thông tin có trong tài liệu. Không bịa thêm.
"""


async def extract_key_findings(
    document_text: str,
    research_question: str,
) -> ExtractedKnowledge:
    """
    Extract structured knowledge from document text using LLM.
    
    Args:
        document_text: The document content (will be truncated to 15000 chars).
        research_question: The research question for context.
    
    Returns:
        ExtractedKnowledge with findings, entities, and citations.
    """
    # Truncate to prevent context overflow
    truncated_text = document_text[:15_000]

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(ExtractedKnowledge)

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            research_question=research_question,
            document_text=truncated_text,
        )

        result = await structured_llm.ainvoke(prompt)

        logger.info(
            f"🔬 extract_key_findings → "
            f"{len(result.findings)} findings, {len(result.entities)} entities"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return ExtractedKnowledge(findings=[], entities=[], citations=[])
