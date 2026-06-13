import asyncio
import json
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_token_payload
from backend.cache.redis import redis_manager
from backend.core.logging import logger

router = APIRouter(prefix="/streams", tags=["Streaming Telemetry"])

# Maximum SSE session lifetime (seconds). Clients auto-reconnect via EventSource.
SSE_MAX_DURATION_SECONDS = 300  # 5 minutes


async def sse_event_generator(
    request: Request,
    project_id: str,
    max_duration: float = SSE_MAX_DURATION_SECONDS,
) -> AsyncGenerator[str, None]:
    """Async generator subscribing to Redis Pub/Sub and yielding SSE format event frames.

    Args:
        request: FastAPI request object (for disconnect detection).
        project_id: UUID string of the target project channel.
        max_duration: Maximum stream lifetime in seconds before graceful close.
    """
    if not redis_manager.client:
        raise RuntimeError("Redis connection manager is offline.")

    pubsub = redis_manager.client.pubsub()
    channel_name = f"project:run:{project_id}:stream"
    await pubsub.subscribe(channel_name)

    # 1. Send initial session initialization handshake
    yield "event: system:init\ndata: {}\n\n"

    loop_start = asyncio.get_event_loop().time()
    last_heartbeat_time = loop_start
    heartbeat_interval = 15.0  # seconds

    try:
        while True:
            current_time = asyncio.get_event_loop().time()

            # Hard time-bound: close and let the client reconnect
            if current_time - loop_start >= max_duration:
                logger.info(f"SSE session max duration reached for project {project_id}. Closing.")
                yield "event: system:timeout\ndata: {\"reason\": \"max_duration_reached\"}\n\n"
                break

            # Check for client disconnection to release event loop resources
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected for project {project_id}")
                break

            # Non-blocking read of channel events
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message:
                data = message["data"]
                try:
                    payload = json.loads(data)
                    event_type = payload.get("event_type", "message")
                    yield f"event: {event_type}\ndata: {data}\n\n"

                    # Auto-close after workflow terminal events
                    if event_type in ("workflow:completed", "workflow:failed"):
                        logger.info(f"Workflow terminal event received for {project_id}. Closing stream.")
                        break
                except Exception:
                    yield f"data: {data}\n\n"

            # Heartbeat frames every 15 seconds to keep connection alive
            if current_time - last_heartbeat_time >= heartbeat_interval:
                yield ": heartbeat\n\n"
                last_heartbeat_time = current_time

            # Yield control back to event loop
            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        logger.info(f"SSE client closed stream connection for project {project_id}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()


@router.get("/progress/{project_id}")
async def get_progress_stream(
    project_id: str,
    request: Request,
    token: str = Query(..., description="JWT Bearer token passed via URL parameter"),
    db: Any = Depends(get_token_payload)  # Validate token via dependency
) -> StreamingResponse:
    """Establishes Server-Sent Events (SSE) channel to track active generator runs."""
    return StreamingResponse(
        sse_event_generator(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )
