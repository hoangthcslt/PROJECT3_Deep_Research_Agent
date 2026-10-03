"""
REST API Routes for Research Operations.
Handles session creation, PDF upload, HITL resume, and graph data retrieval.

Maps from brainstorm: system_prompt_api_schema.md (REST Endpoints Schema).
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.config import settings
from app.models.schemas import (
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchResumeRequest,
    GraphDataResponse,
)
from app.guardrails.content_safety import check_content_safety
from app.graph.workflow import research_graph
from app.services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store (upgrade to PostgreSQL/Redis for production)
_active_sessions: dict = {}

# Upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchStartRequest):
    """
    POST /api/v1/research/start
    Initialize a new research session and start the LangGraph pipeline.
    """
    # ── Content Safety Check ──
    rejection = check_content_safety(request.question)
    if rejection:
        raise HTTPException(status_code=400, detail=rejection)

    # ── Create session ──
    session_id = str(uuid.uuid4())

    # Map depth to max_loops
    depth_map = {"quick": 1, "standard": 2, "deep": 3}
    max_loops = depth_map.get(request.depth, 2)

    # ── Prepare initial state ──
    initial_state = {
        "research_question": request.question,
        "session_id": session_id,
        "user_uploaded_files": [],
        "plan_approved": False,
        "report_approved": False,
        "user_feedback": None,
        "research_plan": [],
        "loop_count": 0,
        "max_loops": max_loops,
        "sources_found": [],
        "documents_read": [],
        "extracted_findings": [],
        "knowledge_gaps": [],
        "reflection_summary": "",
        "report_draft": None,
        "final_report": None,
        "errors": [],
    }

    # Store session reference
    _active_sessions[session_id] = {
        "state": initial_state,
        "status": "started",
    }

    # ── Launch graph execution (async, non-blocking) ──
    # In production, this would be handled by a task queue (Celery, etc.)
    # For now, the WebSocket handler manages the streaming execution
    logger.info(f"🚀 Research session started: {session_id}")

    return ResearchStartResponse(
        session_id=session_id,
        status="started",
    )


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    POST /api/v1/research/upload-pdf
    Upload a PDF file for the agent to analyze.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    # Save to upload directory
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Update session state
    if session_id in _active_sessions:
        _active_sessions[session_id]["state"]["user_uploaded_files"].append(
            str(file_path)
        )

    logger.info(f"📄 PDF uploaded: {file.filename} → {file_path}")

    return {
        "file_id": file_id,
        "filename": file.filename,
        "pages": 0,  # Will be determined during parsing
        "status": "uploaded",
    }


@router.post("/{session_id}/resume")
async def resume_research(session_id: str, request: ResearchResumeRequest):
    """
    POST /api/v1/research/{session_id}/resume
    Send HITL decision (approve plan, select sources, or provide report feedback).
    """
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info(f"▶️ Resuming session {session_id} with action: {request.action}")

    # The actual resume logic is handled via LangGraph's Command(resume=...)
    # This endpoint receives the user's decision and forwards it
    _active_sessions[session_id]["hitl_response"] = {
        "action": request.action,
        **request.payload,
    }

    return {"status": "resumed"}


@router.get("/{session_id}/graph", response_model=GraphDataResponse)
async def get_knowledge_graph(session_id: str):
    """
    GET /api/v1/research/{session_id}/graph
    Retrieve Neo4j knowledge graph data for visualization.
    """
    graph_data = await neo4j_service.get_session_graph(session_id)
    return GraphDataResponse(**graph_data)
