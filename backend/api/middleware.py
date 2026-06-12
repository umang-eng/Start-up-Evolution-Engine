import time
import uuid
from typing import Any
from backend.core.logging import correlation_id_ctx, logger, performance_logger


class CorrelationIdMiddleware:
    """Injects a unique request tracing UUID into request/response context vars at the ASGI level."""
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.setdefault("headers", [])
        correlation_id = None
        for key, val in headers:
            if key == b"x-correlation-id":
                correlation_id = val.decode("utf-8")
                break

        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))

        correlation_id_ctx.set(correlation_id)

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                resp_headers = message.setdefault("headers", [])
                resp_headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """Logs incoming HTTP request details and execution latencies using ASGI wrapping."""
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        request_path = scope.get("path", "")
        request_method = scope.get("method", "")

        logger.info(
            f"HTTP Request: {request_method} {request_path}",
            extra_data={
                "method": request_method,
                "path": request_path,
                "query_params": scope.get("query_string", b"").decode("utf-8")
            }
        )

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                performance_logger.info(
                    f"HTTP Response: {status_code} in {duration_ms}ms",
                    extra_data={
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "path": request_path
                    }
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                f"HTTP Request Failed: {str(e)}",
                extra_data={
                    "duration_ms": duration_ms,
                    "path": request_path
                }
            )
            raise

