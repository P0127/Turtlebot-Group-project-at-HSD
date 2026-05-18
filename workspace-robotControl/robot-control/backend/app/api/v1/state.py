"""State streaming API (SSE)."""
from __future__ import annotations

import json
import queue

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.state_service import state_service
from app.core.controller import controller


router = APIRouter()


@router.get("/snapshot")
def get_snapshot():
    """GET /api/v1/state/snapshot"""
    return state_service.snapshot()


@router.get("/stream")
def stream_state():
    """GET /api/v1/state/stream"""
    q: queue.Queue[dict] = queue.Queue()

    subscription = state_service.subject().subscribe(lambda item: q.put(item))

    def event_generator():
        try:
            while True:
                item = q.get()
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            subscription.dispose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/push")
def push_state():
    """POST /api/v1/state/push"""
    payload = {
        "battery": controller.get_battery(),
        "map": controller.get_map(),
        "nav_status": controller.get_nav_status(),
        "camera": controller.get_camera_info(),
    }
    state_service.publish_robot_status(payload)
    return {"status": "ok"}