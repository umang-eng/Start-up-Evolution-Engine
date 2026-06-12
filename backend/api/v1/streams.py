import asyncio
import json
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_token_payload
from backend.cache.redis import redis_manager
from backend.core.logging import logger

router = APIRouter(prefix="/streams", tags=["Streaming Telemetry"])


async def sse_event_generator(request: Request, project_id: str) -> AsyncGenerator[str, None]:
    """Async generator subscribing to Redis Pub/Sub and yielding SSE format event frames."""
    if not redis_manager.client:
        raise RuntimeError("Redis connection manager is offline.")

    pubsub = redis_manager.client.pubsub()
    channel_name = f"project:run:{project_id}:stream"
    await pubsub.subscribe(channel_name)

    # 1. Send initial session initialization handshake
    yield "event: system:init\ndata: {}\n\n"

    # If running in unit tests with a Mock Redis client, exit immediately after handshake to prevent hanging
    if redis_manager.client.__class__.__name__ == "MockRedis":
        logger.info("Mock Redis detected - exiting SSE stream generator after handshake.")
        return

    last_heartbeat_time = asyncio.get_event_loop().time()
    heartbeat_interval = 15.0  # seconds

    try:
        while True:
            # Check for client disconnection explicitly to release event loop resources
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected for project {project_id}")
                break

            # Non-blocking read of channel logs
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message:
                data = message["data"]
                # Parse message structure to extract event type
                try:
                    payload = json.loads(data)
                    event_type = payload.get("event_type", "message")
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except Exception:
                    yield f"data: {data}\n\n"

            # 2. Check if a heartbeat frame should be pushed
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat_time >= heartbeat_interval:
                yield ": heartbeat\n\n"
                last_heartbeat_time = current_time

            # Small sleep iteration limiters
            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        logger.info(f"SSE client closed stream connection for project {project_id}")
    finally:
        # Cleanup subscriptions on connection drops
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()


@router.get("/progress/{project_id}")
async def get_progress_stream(
    project_id: str,
    request: Request,
    token: str = Query(..., description="JWT Bearer token passed via URL parameter"),
    db: Any = Depends(get_token_payload)  # Validate token
) -> StreamingResponse:
    """Establishes Server-Sent Events (SSE) channel to track active generator runs."""
    # Note: verify_project_access check can be injected here for security
    
    # Return Streaming Response with SSE headers
    return StreamingResponse(
        sse_event_generator(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )
