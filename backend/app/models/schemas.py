"""
Pydantic v2 models for data contracts across the entire pipeline.
Maps directly from brainstorm: tool_api_data_contracts.md
"""

import ipaddress
from typing import Dict, List, Any, Literal, Optional
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import settings


# ═══════════════════════════════════════════════
#  Research Planning Models
# ═══════════════════════════════════════════════

class ResearchSubQuestion(BaseModel):
    """A sub-question decomposed from the main research question."""
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=80, description="Unique ID, e.g. 'sq_1', 'sq_2'")
    question: str = Field(min_length=1, max_length=500, description="The sub-question text (in English for optimal search)")
    target_source: Literal["academic", "web"]
    status: str = Field(
        default="pending",
        description="Status: 'pending', 'completed', 'failed'"
    )


# ═══════════════════════════════════════════════
#  Source & Document Models
# ═══════════════════════════════════════════════

class SourceMetadata(BaseModel):
    """Metadata for a discovered source (paper, web article, uploaded PDF)."""
    source_id: str = Field(description="Unique reference ID, e.g. 'REF_1', 'REF_2'")
    url: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    source_type: str = Field(description="'paper', 'webpage', 'uploaded_pdf'")
    content_snippet: Optional[str] = Field(
        default=None,
        description="Short snippet or abstract for preview"
    )
    credibility_tier: int = Field(
        default=2,
        description="Source trust level: 1=High (academic), 2=Medium (official docs), 3=Low (blogs)"
    )
    citation_count: Optional[int] = None
    open_access_pdf: Optional[str] = None
    content_kind: Literal["webpage", "abstract", "pdf_excerpt"] = "webpage"
    page_count: Optional[int] = None
    truncated: bool = False


# ═══════════════════════════════════════════════
#  Knowledge Extraction Models
# ═══════════════════════════════════════════════

class ExtractedFinding(BaseModel):
    """A key finding extracted from a document with evidence and source mapping."""
    claim: str = Field(description="The core claim or factual finding")
    evidence: str = Field(description="Supporting evidence or quote from the source")
    source_ids: List[str] = Field(description="References back to SourceMetadata.source_id")
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level from 0.0 to 1.0"
    )


class Entity(BaseModel):
    """An entity extracted for the Knowledge Graph."""
    name: str = Field(description="Entity name (e.g., 'LangGraph', 'Transformer', 'ReAct')")
    type: str = Field(description="Entity type: 'Technology', 'Methodology', 'Metric', 'Author'")
    description: str = Field(description="Brief description of the entity's role")


class ExtractedKnowledge(BaseModel):
    """Complete knowledge extraction result from a document."""
    findings: List[ExtractedFinding] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    citations: List[str] = Field(
        default_factory=list,
        description="Authors/sources cited within the document"
    )


class KnowledgeGap(BaseModel):
    """A gap in knowledge identified during reflection."""
    missing_aspect: str = Field(description="What aspect is missing or incomplete")
    suggested_query: str = Field(description="Suggested search query to fill the gap")
    target_source: str = Field(description="'academic' or 'web'")


# ═══════════════════════════════════════════════
#  Tool Output Models
# ═══════════════════════════════════════════════

class PaperSearchResult(BaseModel):
    """Result from Semantic Scholar API search."""
    paper_id: str
    title: str
    abstract: Optional[str] = "No abstract available"
    authors: List[str] = Field(default_factory=list)
    citation_count: int = 0
    year: Optional[int] = None
    url: str
    open_access_pdf: Optional[str] = None


class WebSearchResult(BaseModel):
    """Result from Tavily web search."""
    title: str
    url: str
    content_snippet: str
    relevance_score: float = 0.0


class WebScrapeResult(BaseModel):
    """Result from reading/scraping a URL via Jina Reader."""
    url: str
    title: str
    full_text: str
    extracted_date: str


class PDFParseResult(BaseModel):
    """Result from parsing an uploaded PDF."""
    file_path: str
    page_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tables_detected: int = 0
    full_text: str


# ═══════════════════════════════════════════════
#  API Request / Response Models
# ═══════════════════════════════════════════════

class ResearchStartRequest(BaseModel):
    """Request body for POST /api/v1/research/start"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=10, max_length=4_000, description="The research question")
    depth: Literal["quick"] = Field(default="quick", description="Quick one-loop research")
    search_mode: Literal["web", "academic", "mixed", "provided"] = "web"
    urls: List[str] = Field(
        default_factory=list,
        max_length=8,
        description="Optional URLs supplied as research sources",
    )

    @model_validator(mode="after")
    def reject_unsupported_inputs(self):
        normalized = set()
        for value in self.urls:
            if len(value) > 2_048 or any(ord(char) < 32 or char.isspace() for char in value):
                raise ValueError("Each URL must be at most 2048 characters without whitespace.")
            try:
                parsed = urlsplit(value)
                host = (parsed.hostname or "").rstrip(".").lower()
                _port = parsed.port
            except ValueError as exc:
                raise ValueError("A supplied URL is malformed.") from exc
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                address = None
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.netloc
                or not host
                or parsed.username is not None
                or parsed.password is not None
                or host == "localhost"
                or host.endswith((".localhost", ".local", ".internal"))
                or address is None and "." not in host
            ):
                raise ValueError("Only public HTTP(S) URLs without credentials are allowed.")
            if address is not None and not address.is_global:
                raise ValueError("Local or non-public IP addresses are not allowed in URLs.")
            canonical = parsed._replace(fragment="").geturl()
            if canonical in normalized:
                raise ValueError("Supplied URLs must be unique.")
            normalized.add(canonical)
        return self


class ResearchStartResponse(BaseModel):
    """Response body for POST /api/v1/research/start"""
    session_id: str
    status: Literal["created"] = "created"


class ResearchResumeRequest(BaseModel):
    """Request body for POST /api/v1/research/{session_id}/resume (HITL response)"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: Literal["approve", "modify", "select_sources"]
    interrupt_id: str = Field(min_length=1)
    plan: Optional[List[ResearchSubQuestion]] = Field(default=None, min_length=1)
    selected_source_ids: Optional[List[str]] = Field(
        default=None, min_length=1, max_length=settings.max_documents_to_read
    )

    @model_validator(mode="after")
    def validate_plan_action(self):
        if self.action == "modify" and not self.plan:
            raise ValueError("A non-empty plan is required when modifying the plan.")
        if self.action == "select_sources" and not self.selected_source_ids:
            raise ValueError("At least one source must be selected.")
        if self.action != "select_sources" and self.selected_source_ids is not None:
            raise ValueError("Sources can only be sent with select_sources.")
        if self.action == "select_sources" and self.plan is not None:
            raise ValueError("A plan cannot be sent with source selection.")
        if self.action == "modify" and self.selected_source_ids is not None:
            raise ValueError("Sources cannot be sent with plan modification.")
        if self.plan and len({question.id for question in self.plan}) != len(self.plan):
            raise ValueError("Plan question IDs must be unique.")
        if self.plan and len(self.plan) > max(settings.max_tavily_calls, settings.max_scholar_calls):
            raise ValueError("The edited plan exceeds the session search limit.")
        if self.action == "approve" and self.plan is not None:
            raise ValueError("A plan can only be sent with the modify action.")
        return self


class PendingResearchInterrupt(BaseModel):
    interrupt_id: str
    type: Literal["PLAN_APPROVAL_REQUIRED", "SOURCE_SELECTION_REQUIRED", "REPORT_APPROVAL_REQUIRED"]
    message: str
    plan: Optional[List[ResearchSubQuestion]] = None
    sources: Optional[List[SourceMetadata]] = None
    report_draft: Optional[str] = None


class ResearchSessionStatusResponse(BaseModel):
    session_id: str
    status: Literal["created", "running", "awaiting_plan", "awaiting_sources", "awaiting_report", "completed", "error"]
    revision: int
    current_step: str
    progress_percent: int
    research_plan: List[ResearchSubQuestion] = Field(default_factory=list)
    sources_found: List[SourceMetadata] = Field(default_factory=list)
    selected_source_ids: List[str] = Field(default_factory=list)
    source_errors: List[str] = Field(default_factory=list)
    pending_interrupt: Optional[PendingResearchInterrupt] = None
    error: Optional[str] = None


class ResearchReportResponse(BaseModel):
    session_id: str
    status: Literal["created", "running", "awaiting_plan", "awaiting_sources", "awaiting_report", "completed", "error"]
    report_markdown: str
    approved: bool


class GraphDataResponse(BaseModel):
    """Response body for GET /api/v1/research/{session_id}/graph"""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════
#  WebSocket Message Protocol
# ═══════════════════════════════════════════════

class WSMessage(BaseModel):
    """Standard WebSocket message envelope."""
    event: str = Field(
        description="Event type: 'STEP_UPDATE', 'LOG_STREAM', 'HITL_TRIGGER', "
                    "'REPORT_CHUNK', 'DONE', 'ERROR'"
    )
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)
