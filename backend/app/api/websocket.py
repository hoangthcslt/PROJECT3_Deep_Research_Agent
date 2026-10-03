"""
WebSocket handler for real-time research progress streaming.
Implements the WSMessage protocol for STEP_UPDATE, LOG_STREAM, HITL_TRIGGER, etc.

Maps from brainstorm: system_prompt_api_schema.md (WebSocket Event Protocol).
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections per session
_ws_connections: dict[str, WebSocket] = {}


@router.websocket("/ws/research/{session_id}")
async def research_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time research progress.
    
    Server → Client events:
      - STEP_UPDATE: Current pipeline step and progress
      - LOG_STREAM: Real-time agent log messages
      - HITL_TRIGGER: Pause for user interaction (plan approval, source selection, report review)
      - REPORT_CHUNK: Streaming report content
      - DONE: Research complete
      - ERROR: Error occurred
    
    Client → Server events:
      - HITL_RESPONSE: User's decision for HITL checkpoints
    """
    await websocket.accept()
    _ws_connections[session_id] = websocket
    logger.info(f"🔌 WebSocket connected: {session_id}")

    try:
        # Send initial connection confirmation
        await _send_ws_event(websocket, "STEP_UPDATE", {
            "current_step": "connected",
            "message": "Kết nối thành công. Đang khởi tạo nghiên cứu...",
            "progress_percent": 0,
        })

        # Listen for client messages (HITL responses)
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "HITL_RESPONSE":
                logger.info(f"📨 HITL response received: {message.get('data', {})}")
                # TODO: Forward HITL response to LangGraph via Command(resume=...)

            elif message.get("event") == "START_PIPELINE":
                logger.info(f"▶️ Pipeline start requested for {session_id}")
                # TODO: Trigger graph execution and stream events back

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        _ws_connections.pop(session_id, None)


async def _send_ws_event(websocket: WebSocket, event: str, data: dict):
    """Send a standardized WebSocket message."""
    message = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    await websocket.send_text(json.dumps(message, ensure_ascii=False))


async def broadcast_to_session(session_id: str, event: str, data: dict):
    """
    Broadcast an event to the WebSocket connection for a specific session.
    Called by graph nodes to stream progress to the frontend.
    """
    websocket = _ws_connections.get(session_id)
    if websocket:
        try:
            await _send_ws_event(websocket, event, data)
        except Exception as e:
            logger.warning(f"⚠️ Failed to broadcast to {session_id}: {e}")
