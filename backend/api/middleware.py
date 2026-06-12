import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.logging import correlation_id_ctx, logger, performance_logger


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Injects a unique request tracing UUID into request/response context vars."""
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_ctx.set(correlation_id)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP request payloads, routing details, and execution times."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        
        # Log incoming request
        logger.info(
            f"HTTP Request: {request.method} {request.url.path}",
            extra_data={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params)
            }
        )
        
        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Log successful response and performance metric
            performance_logger.info(
                f"HTTP Response: {response.status_code} in {duration_ms}ms",
                extra_data={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "path": request.url.path
                }
            )
            return response
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                f"HTTP Request Failed: {str(e)}",
                extra_data={
                    "duration_ms": duration_ms,
                    "path": request.url.path
                }
            )
            raise
from typing import Any
