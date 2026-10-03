"""
Pydantic v2 models for data contracts across the entire pipeline.
Maps directly from brainstorm: tool_api_data_contracts.md
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════
#  Research Planning Models
# ═══════════════════════════════════════════════

class ResearchSubQuestion(BaseModel):
    """A sub-question decomposed from the main research question."""
    id: str = Field(description="Unique ID, e.g. 'sq_1', 'sq_2'")
    question: str = Field(description="The sub-question text (in English for optimal search)")
    target_source: str = Field(
        description="Preferred source: 'academic' (Semantic Scholar) or 'web' (Tavily)"
    )
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
    question: str = Field(min_length=10, description="The research question")
    depth: str = Field(
        default="standard",
        description="Research depth: 'quick' (1 loop), 'standard' (2 loops), 'deep' (3 loops)"
    )
    urls: List[str] = Field(
        default_factory=list,
        description="Optional list of URLs for the agent to prioritize reading"
    )


class ResearchStartResponse(BaseModel):
    """Response body for POST /api/v1/research/start"""
    session_id: str
    status: str = "started"


class ResearchResumeRequest(BaseModel):
    """Request body for POST /api/v1/research/{session_id}/resume (HITL response)"""
    action: str = Field(description="'approve', 'modify', 'feedback'")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Modified plan, selected sources, or feedback text"
    )


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
