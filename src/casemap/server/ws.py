"""WebSocket real-time status sync (SP-4).

Per-project in-memory broadcast queue. On any REST status change (PATCH, bulk
import, CI report), every connected client for the matching project gets a JSON
status_changed message pushed down its WS.

Auth uses a ?token= query param because browsers cannot set the Authorization
header on `new WebSocket(...)`. Token is validated against the same sha256
hash that the REST Bearer flow uses.

v1 trade-offs:
- In-memory queue, no Redis. Multi-process / multi-host scaling means broadcasts
  don't cross worker boundaries. Move to a pub/sub backend when needed.
- Server-push only. Client→server messages are ignored (the spec doesn't ask for
  client→server control).
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from casemap.server.auth import find_project_by_token
from casemap.server.db import get_db

# project_id -> set of connected WebSockets (one client may have multiple tabs)
_connections: dict[str, set[WebSocket]] = defaultdict(set)
_lock = asyncio.Lock()

router = APIRouter(prefix="/projects/{project_id}", tags=["ws"])


async def _register(project_id: str, ws: WebSocket) -> None:
    async with _lock:
        _connections[project_id].add(ws)


async def _unregister(project_id: str, ws: WebSocket) -> None:
    async with _lock:
        bucket = _connections.get(project_id)
        if bucket is not None:
            bucket.discard(ws)
            if not bucket:
                _connections.pop(project_id, None)


async def broadcast(project_id: str, message: dict[str, Any]) -> None:
    """Push `message` (JSON-serializable) to every WS for `project_id`.

    Safe to call when no one is connected — silently no-ops. Per-connection
    send failures are caught and dropped so one dead client doesn't take down
    the rest. Cleanup happens in the endpoint's WebSocketDisconnect handler too.
    """
    payload = json.dumps(message, default=str)
    async with _lock:
        bucket = list(_connections.get(project_id, ()))
    for ws in bucket:
        try:
            await ws.send_text(payload)
        except Exception:  # noqa: BLE001
            await _unregister(project_id, ws)


@router.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    project_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
) -> None:
    # ponytail: WebSocket cannot raise HTTPException from a Depends() in the way
    # REST routes can — we authenticate inline and close with 1008 (policy
    # violation) on failure. This is the standard FastAPI WS pattern.
    project = find_project_by_token(db, token) if token else None
    if project is None or project.id != project_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await _register(project_id, websocket)
    try:
        # Server-push only. Drain client messages to detect disconnect; ignore
        # payload content per spec.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _unregister(project_id, websocket)


__all__ = ["router", "broadcast"]
