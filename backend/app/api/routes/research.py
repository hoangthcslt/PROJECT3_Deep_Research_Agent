"""
REST API Routes for Research Operations.
Handles session creation, PDF upload, HITL resume, and graph data retrieval.

Maps from brainstorm: system_prompt_api_schema.md (REST Endpoints Schema).
"""

import logging
import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.models.schemas import (
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchResumeRequest,
    GraphDataResponse,
    ResearchSessionStatusResponse,
    ResearchReportResponse,
)
from app.models.budget import SessionBudget
from app.guardrails.content_safety import check_content_safety
from app.models.schemas import SourceMetadata
from app.services.neo4j_service import neo4j_service
from app.services.session_manager import SessionConflict, SessionNotFound
from app.services.research_sessions import session_manager
from app.services.pdf_storage import (
    PDFUploadError,
    PDFUploadTooLargeError,
    save_upload,
    stored_file,
)
from app.tools.parse_pdf import PDFParseError, PDFTooLargeError
from app.tools.source_ids import source_id_for_url

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchStartRequest):
    """
    POST /api/v1/research/start
    Create a session; upload files and start the graph in separate requests.
    """
    # ── Content Safety Check ──
    rejection = check_content_safety(request.question)
    if rejection:
        raise HTTPException(status_code=400, detail=rejection)

    # ── Create session ──
    session_id = str(uuid.uuid4())

    url_sources = [
        SourceMetadata(
            source_id=source_id_for_url(url),
            url=url,
            title=urlsplit(url).hostname or url,
            source_type="webpage",
            content_snippet="User-supplied URL",
            content_kind="webpage",
        )
        for url in request.urls
    ]

    # ── Prepare initial state ──
    initial_state = {
        "research_question": request.question,
        "session_id": session_id,
        "user_uploaded_files": [],
        "search_mode": request.search_mode,
        "input_urls": list(request.urls),
        "provided_source_ids": [source.source_id for source in url_sources],
        "selected_source_ids": [],
        "plan_approved": False,
        "report_approved": False,
        "user_feedback": None,
        "research_plan": [],
        "loop_count": 0,
        "max_loops": 1,
        "budget": SessionBudget().model_dump(),
        "sources_found": url_sources,
        "documents_read": [],
        "extracted_findings": [],
        "knowledge_gaps": [],
        "reflection_summary": "",
        "report_draft": None,
        "final_report": None,
        "errors": [],
        "source_errors": [],
    }

    session_manager.create(session_id, initial_state)

    logger.info("Research session created: %s", session_id)

    return ResearchStartResponse(
        session_id=session_id,
        status="created",
    )


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Validate and attach one PDF before the graph starts."""
    try:
        record = await session_manager.upload(
            session_id, lambda: save_upload(file, session_id)
        )
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (PDFUploadTooLargeError, PDFTooLargeError) as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (PDFUploadError, PDFParseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    source = record["source"]
    return {"file_id": source.source_id, "status": "uploaded", "source": source}


@router.get("/{session_id}/sources/{source_id}/pdf")
async def get_uploaded_pdf(session_id: str, source_id: str):
    """Serve a PDF only when its source ID belongs to this session."""
    try:
        if not await session_manager.has_uploaded_pdf(session_id, source_id):
            raise HTTPException(status_code=404, detail="PDF source was not found.")
        path = stored_file(session_id, source_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="PDF source was not found.") from exc
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.post("/{session_id}/resume", response_model=ResearchSessionStatusResponse)
async def resume_research(session_id: str, request: ResearchResumeRequest):
    """Resume the pending plan or report approval checkpoint."""
    try:
        return await session_manager.resume(
            session_id,
            request.interrupt_id,
            request.action,
            request.plan,
            request.selected_source_ids,
        )
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{session_id}/run", response_model=ResearchSessionStatusResponse)
async def run_research(session_id: str):
    """Start the graph once all selected files have uploaded."""
    try:
        return await session_manager.start(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=ResearchSessionStatusResponse)
async def get_research_status(session_id: str):
    """Return a safe snapshot for reloads and reconnects."""
    try:
        return await session_manager.snapshot(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{session_id}/report", response_model=ResearchReportResponse)
async def get_research_report(session_id: str):
    """Return the stored draft or final report without calling the model."""
    try:
        report = await session_manager.report_view(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=409, detail="No report draft or approved report is available yet.")
    return ResearchReportResponse(**report)


@router.get("/{session_id}/graph", response_model=GraphDataResponse)
async def get_knowledge_graph(session_id: str):
    """
    GET /api/v1/research/{session_id}/graph
    Retrieve Neo4j knowledge graph data for visualization.
    """
    graph_data = await neo4j_service.get_session_graph(session_id)
    return GraphDataResponse(**graph_data)
