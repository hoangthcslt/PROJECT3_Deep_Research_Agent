"""
Export API Routes — handles report export in multiple formats.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)
router = APIRouter()

from app.services.research_sessions import session_manager
from app.services.session_manager import SessionNotFound


@router.get("/{session_id}/export")
async def export_report(session_id: str, format: str = "md"):
    """
    GET /api/v1/research/{session_id}/export?format=md|pdf|docx
    Export the final research report.
    """
    if format in {"pdf", "docx"}:
        raise HTTPException(status_code=501, detail=f"{format.upper()} export not yet implemented.")
    if format != "md":
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    try:
        report = await session_manager.report(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not report:
        raise HTTPException(status_code=409, detail="Only an approved final report can be exported.")

    if format == "md":
        return PlainTextResponse(
            content=report,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=research_report_{session_id[:8]}.md"
            },
        )
