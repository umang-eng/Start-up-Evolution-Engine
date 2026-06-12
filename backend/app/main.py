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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages system startup and shutdown events."""
    # 1. Initialize logging
    setup_logging(log_level="INFO" if settings.ENVIRONMENT == "production" else "DEBUG")
    logger.info("Starting Start-up Evolution Engine backend app...")

    # 2. Initialize Redis connection pool
    redis_manager.initialize()
    health = await redis_manager.is_healthy()
    if health:
        logger.info("Redis cache connection verified successfully.")
    else:
        logger.error("Redis cache connection failed check during initialization!")

    yield

    # 3. Shutdown Redis connection pool
    await redis_manager.close()
    logger.info("Start-up Evolution Engine backend app shut down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Enforce Security CORS limitations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production environment configurations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# App-level logging and correlation tracing middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)


# Register main API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(BaseBusinessException)
async def business_exception_handler(request: Request, exc: BaseBusinessException) -> JSONResponse:
    """Global handler converting custom business exceptions into standard envelopes."""
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(
            code=exc.code,
            message=exc.message
        ),
        metadata=APIResponseMetadata()
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(mode="json")
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats validation errors into the standard JSON error schema."""
    details = [
        {"field": ".".join(map(str, err["loc"])), "issue": err["msg"]}
        for err in exc.errors()
    ]
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(
            code="SCHEMA_VALIDATION_ERROR",
            message="Input data validation failed",
            details=details
        ),
        metadata=APIResponseMetadata()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload.model_dump(mode="json")
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler catching unhandled application exceptions to prevent leakages."""
    logger.error("Unhandled runtime exception encountered", exc_info=exc)
    error_payload = BaseErrorResponse(
        success=False,
        error=APIError(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected system error occurred. Please try again later."
        ),
        metadata=APIResponseMetadata()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(mode="json")
    )
