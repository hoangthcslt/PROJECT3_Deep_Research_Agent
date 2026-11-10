"""Read-only WebSocket observer for research session snapshots and progress."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.research_sessions import session_manager
from app.services.session_manager import SessionNotFound

logger = logging.getLogger(__name__)
router = APIRouter()
_ws_connections: dict[str, set[WebSocket]] = {}
_SEND_TIMEOUT_SECONDS = 0.25


@router.websocket("/ws/research/{session_id}")
async def research_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _ws_connections.setdefault(session_id, set()).add(websocket)
    try:
        try:
            snapshot = await session_manager.snapshot(session_id)
        except SessionNotFound:
            await asyncio.wait_for(websocket.close(code=4404), timeout=_SEND_TIMEOUT_SECONDS)
            return

        await asyncio.wait_for(
            _send_ws_event(websocket, "SNAPSHOT", snapshot),
            timeout=_SEND_TIMEOUT_SECONDS,
        )
        while True:
            await websocket.receive_text()
            await asyncio.wait_for(
                websocket.close(code=1008, reason="This connection only observes session progress."),
                timeout=_SEND_TIMEOUT_SECONDS,
            )
            return
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as exc:
        logger.warning("WebSocket connection failed for %s (%s)", session_id, type(exc).__name__)
    finally:
        connections = _ws_connections.get(session_id)
        if connections is not None:
            connections.discard(websocket)
            if not connections:
                _ws_connections.pop(session_id, None)


async def _send_ws_event(websocket: WebSocket, event: str, data: dict[str, Any]) -> None:
    message = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    await websocket.send_text(json.dumps(message, ensure_ascii=False))


async def broadcast_to_session(session_id: str, event: str, data: dict[str, Any]) -> None:
    connections = tuple(_ws_connections.get(session_id, ()))
    if not connections:
        return

    async def send_one(websocket: WebSocket) -> None:
        try:
            await asyncio.wait_for(
                _send_ws_event(websocket, event, data),
                timeout=_SEND_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("WebSocket publish failed for %s (%s)", session_id, type(exc).__name__)
            observers = _ws_connections.get(session_id)
            if observers is not None:
                observers.discard(websocket)
                if not observers:
                    _ws_connections.pop(session_id, None)
            try:
                await asyncio.wait_for(
                    websocket.close(code=1011),
                    timeout=_SEND_TIMEOUT_SECONDS,
                )
            except Exception:
                pass

    await asyncio.gather(*(send_one(websocket) for websocket in connections))
