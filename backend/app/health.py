from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.cache.redis import redis_manager
from backend.database.session import get_db
from backend.schemas.base import BaseResponse, APIResponseMetadata

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get("/liveness", response_model=BaseResponse[dict[str, str]])
async def check_liveness() -> dict[str, Any]:
    """Basic container health ping check."""
    return {
        "success": True,
        "data": {"status": "healthy"},
        "metadata": APIResponseMetadata()
    }


@router.get("/readiness")
async def check_readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Verifies operational readiness of database and cache dependencies."""
    db_healthy = False
    redis_healthy = False
    details = {}

    # 1. Database Ping Check
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
        details["database"] = "UP"
    except Exception as e:
        details["database"] = f"DOWN: {str(e)}"

    # 2. Redis Ping Check
    redis_healthy = await redis_manager.is_healthy()
    details["redis"] = "UP" if redis_healthy else "DOWN"

    is_ready = db_healthy and redis_healthy
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "success": is_ready,
            "data": {
                "status": "ready" if is_ready else "not_ready",
                "components": details
            },
            "metadata": {
                "timestamp": None,
                "api_version": "1.0.0"
            }
        }
    )
from typing import Any
