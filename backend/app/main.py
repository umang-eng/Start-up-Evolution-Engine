"""
FastAPI Application — API Gateway

This is the entrypoint for the api-gateway container. It serves the REST API
(auth, metadata, proxying, SSE streaming) but does NOT run the orchestrator
pipeline — that lives in the worker-engine container.

Service role is controlled by the SERVICE_ROLE environment variable.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from backend.api.v1.router import api_router
from backend.cache.redis import redis_manager
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import setup_logging, logger
from backend.schemas.base import BaseErrorResponse, APIError, APIResponseMetadata

# Ensure all SQLAlchemy models are registered in the mapper registry before
# any queries run. Without this, string-based relationship() references like
# "AuditLog" in User can't be resolved when PostgreSQL is used directly.
import backend.models.audit  # noqa: F401
import backend.models.analytics  # noqa: F401


SERVICE_ROLE = settings.ENVIRONMENT  # overridden by SERVICE_ROLE env var in container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages system startup and shutdown events for the API gateway."""
    import os
    role = os.environ.get("SERVICE_ROLE", "api-gateway")
    setup_logging(log_level="INFO" if settings.ENVIRONMENT == "production" else "DEBUG")
    logger.info(f"Starting Start-up Evolution Engine [{role}]...")

    # 1. Database connectivity check (with SQLite fallback)
    from backend.database.session import verify_db_connectivity
    await verify_db_connectivity()

    # 2. Redis connection pool
    redis_manager.initialize()
    await redis_manager.is_healthy()

    yield

    # Shutdown
    await redis_manager.close()
    logger.info(f"Start-up Evolution Engine [{role}] shut down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-Id", "Accept"],
)

# Request logging and correlation tracing
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Mount all API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Global Exception Handlers ──────────────────────────────────────

@app.exception_handler(BaseBusinessException)
async def business_exception_handler(request: Request, exc: BaseBusinessException) -> JSONResponse:
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(code=exc.code, message=exc.message),
        metadata=APIResponseMetadata(),
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(map(str, err["loc"])), "issue": err["msg"]}
        for err in exc.errors()
    ]
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(
            code="SCHEMA_VALIDATION_ERROR",
            message="Input data validation failed",
            details=details,
        ),
        metadata=APIResponseMetadata(),
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_payload.model_dump(mode="json"))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled runtime exception", exc_info=exc)
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected system error occurred. Please try again later.",
        ),
        metadata=APIResponseMetadata(),
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_payload.model_dump(mode="json"))
