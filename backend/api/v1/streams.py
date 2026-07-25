"""
Streaming Telemetry — Server-Sent Events Endpoint

Subscribes to the Redis Pub/Sub channel for a given session and streams
real-time pipeline progress events back to the frontend via SSE.

Uses sse-starlette's EventSourceResponse for proper SSE protocol handling.
"""

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.cache.redis import redis_manager
from backend.core.logging import logger
from backend.database.session import get_db
from backend.models.workflow import GenerationSession

router = APIRouter(prefix="/streams", tags=["Streaming Telemetry"])

# Maximum SSE session lifetime before the connection is closed.
# Clients (EventSource) auto-reconnect with Last-Event-ID.
SSE_MAX_DURATION_SECONDS = 300  # 5 minutes


async def _event_generator(
    request,
    session_id: str,
    project_id: str,
    max_duration: float = SSE_MAX_DURATION_SECONDS,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE event dicts from a Redis Pub/Sub channel.

    Each yield produces a dict with keys: event, data, id (optional).
    sse-starlette's EventSourceResponse serialises these automatically.
    """
    if not redis_manager.client:
        raise RuntimeError("Redis connection manager is offline.")

    pubsub = redis_manager.client.pubsub()
    channel_name = f"project:run:{project_id}:stream"
    await pubsub.subscribe(channel_name)

    # Initial handshake event
    yield {
        "event": "system:init",
        "data": json.dumps({
            "session_id": session_id,
            "project_id": project_id,
            "message": "SSE channel established",
        }),
    }

    loop_start = asyncio.get_event_loop().time()
    last_heartbeat = loop_start
    heartbeat_interval = 15.0
    event_id = 0

    try:
        while True:
            now = asyncio.get_event_loop().time()

            # Hard time-bound
            if now - loop_start >= max_duration:
                logger.info(f"SSE max duration reached for session {session_id}")
                yield {
                    "event": "system:timeout",
                    "data": json.dumps({"reason": "max_duration_reached"}),
                }
                break

            # Client disconnect check
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected for session {session_id}")
                break

            # Non-blocking read from Redis Pub/Sub
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)

            if message and message.get("data"):
                raw = message["data"]
                try:
                    payload = json.loads(raw)
                    event_type = payload.get("event_type", "message")

                    # Include a monotonically increasing event ID for client reconnection
                    event_id += 1

                    yield {
                        "event": event_type,
                        "data": raw,
                        "id": str(event_id),
                    }

                    # Auto-close after terminal workflow events
                    if event_type in ("workflow:completed", "workflow:failed"):
                        logger.info(f"Terminal event received for session {session_id} — closing stream")
                        break
                except (json.JSONDecodeError, TypeError):
                    event_id += 1
                    yield {
                        "event": "message",
                        "data": raw if isinstance(raw, str) else str(raw),
                        "id": str(event_id),
                    }

            # Heartbeat to keep connection alive through proxies
            if now - last_heartbeat >= heartbeat_interval:
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"ts": now}),
                }
                last_heartbeat = now

            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        logger.info(f"SSE generator cancelled for session {session_id}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/progress/{project_id}")
async def stream_project_progress(
    project_id: str,
    request: Request,
    token: str = Query(..., description="JWT Bearer token passed via query param"),
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload),
) -> EventSourceResponse:
    """Stream real-time pipeline progress for a project.

    The frontend connects via:
        GET /api/v1/streams/progress/{project_id}?token=<jwt>

    The worker-engine publishes events to Redis Pub/Sub on channel:
        project:run:{project_id}:stream

    This endpoint bridges the two, piping worker events straight to the client.
    """
    stmt = (
        select(GenerationSession)
        .where(GenerationSession.project_id == uuid.UUID(project_id))
        .order_by(GenerationSession.created_at.desc())
        .limit(1)
    )
    session = (await db.execute(stmt)).scalars().first()

    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No generation session found for this project")

    session_id = str(session.id)

    return EventSourceResponse(
        _event_generator(request, session_id, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}")
async def stream_session_progress(
    session_id: str,
    request: Request,
    token: str = Query(..., description="JWT Bearer token passed via query param"),
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload),
) -> EventSourceResponse:
    """Stream real-time pipeline progress for a given GenerationSession.

    The frontend connects via:
        GET /api/v1/streams/{session_id}?token=<jwt>

    The worker-engine publishes events to Redis Pub/Sub on channel:
        project:run:{project_id}:stream

    This endpoint bridges the two, piping worker events straight to the client.
    """
    stmt = select(GenerationSession).where(GenerationSession.id == session_id)
    session = (await db.execute(stmt)).scalars().first()

    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Generation session not found")

    project_id = str(session.project_id)

    return EventSourceResponse(
        _event_generator(request, session_id, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
