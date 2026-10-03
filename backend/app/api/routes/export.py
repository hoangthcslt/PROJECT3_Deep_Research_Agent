"""
Export API Routes — handles report export in multiple formats.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Reference to active sessions (shared with research routes)
from app.api.routes.research import _active_sessions


@router.get("/{session_id}/export")
async def export_report(session_id: str, format: str = "md"):
    """
    GET /api/v1/research/{session_id}/export?format=md|pdf|docx
    Export the final research report.
    """
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    session = _active_sessions[session_id]
    report = session["state"].get("final_report") or session["state"].get("report_draft")

    if not report:
        raise HTTPException(status_code=400, detail="No report available for this session.")

    if format == "md":
        return PlainTextResponse(
            content=report,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=research_report_{session_id[:8]}.md"
            },
        )
    elif format == "pdf":
        # TODO: Implement PDF export (html2pdf or weasyprint)
        raise HTTPException(status_code=501, detail="PDF export not yet implemented.")
    elif format == "docx":
        # TODO: Implement DOCX export (python-docx)
        raise HTTPException(status_code=501, detail="DOCX export not yet implemented.")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
