"""
Content Safety Guardrail — rejects unsafe research topics at the planning stage.
Uses Gemini safety settings + keyword-based pre-filter.

Maps from brainstorm: guardrails_HITL.md (Trụ cột 3, Section 3).
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Topics that should be immediately rejected
UNSAFE_PATTERNS = [
    r"chế tạo\s*(vũ khí|bom|chất nổ|chất độc)",
    r"(hack|crack|exploit|bypass)\s*(security|firewall|password)",
    r"(tấn công|attack)\s*(mạng|network|ddos|sql injection)",
    r"(lừa đảo|phishing|scam|fraud)\s*(guide|hướng dẫn|how to)",
    r"(make|build|create)\s*(bomb|weapon|explosive|poison)",
    r"(how to|guide)\s*(hack|crack|exploit|bypass)",
]


def check_content_safety(query: str) -> Optional[str]:
    """
    Pre-screen a research query for unsafe content.
    
    Args:
        query: The research question to evaluate.
    
    Returns:
        None if safe, or a rejection reason string if unsafe.
    """
    query_lower = query.lower().strip()

    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, query_lower):
            logger.warning(f"🚫 Content Safety: Rejected query matching pattern '{pattern}'")
            return (
                "REJECTED_UNSAFE_TOPIC: Yêu cầu này vi phạm chính sách an toàn nội dung. "
                "Hệ thống chỉ hỗ trợ nghiên cứu học thuật và công nghệ hợp pháp."
            )

    return None
