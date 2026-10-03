"""
LangGraph State Schema — the central data structure that flows through
all 7 nodes of the research pipeline.

Uses Annotated types with operator.add reducer for appendable lists,
ensuring each node appends data without overwriting previous iterations.

Maps from brainstorm: agent_flow_state_machine.md (Section 2).
"""

import operator
from typing import Annotated, Any, Dict, List, Optional

from typing_extensions import TypedDict

from app.models.schemas import (
    ExtractedFinding,
    KnowledgeGap,
    ResearchSubQuestion,
    SourceMetadata,
)


class DeepResearchState(TypedDict):
    """
    Main LangGraph state schema.
    
    Convention:
    - Fields with Annotated[..., operator.add] are APPENDABLE (each node adds, never overwrites).
    - Other fields are OVERWRITABLE (latest write wins).
    """

    # ═══ User Input & Session ═══
    research_question: str
    session_id: str
    user_uploaded_files: List[str]          # File paths to local PDFs

    # ═══ HITL Control Flags ═══
    plan_approved: bool
    report_approved: bool
    user_feedback: Optional[str]

    # ═══ Planning Phase ═══
    research_plan: List[ResearchSubQuestion]

    # ═══ Loop Counter & Limits ═══
    loop_count: int
    max_loops: int

    # ═══ Knowledge Accumulation (Appendable) ═══
    sources_found: Annotated[List[SourceMetadata], operator.add]
    documents_read: Annotated[List[Dict[str, Any]], operator.add]
    extracted_findings: Annotated[List[ExtractedFinding], operator.add]

    # ═══ Reflection Phase ═══
    knowledge_gaps: List[KnowledgeGap]
    reflection_summary: str

    # ═══ Output Phase ═══
    report_draft: Optional[str]
    final_report: Optional[str]

    # ═══ Error & Audit Logging (Appendable) ═══
    errors: Annotated[List[str], operator.add]
