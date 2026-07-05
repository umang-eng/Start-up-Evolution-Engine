"""
ARQ Client — Enqueue background tasks from the API gateway.

This module provides a thin wrapper around arq's create_pool for
enqueuing jobs onto the Redis queue that the worker-engine consumes.
"""

import uuid
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from backend.core.config import settings
from backend.core.logging import logger


# Lazy singleton for the Redis connection pool
_pool = None


async def get_arq_pool():
    """Return a reusable arq Redis connection pool (creates on first call)."""
    global _pool
    if _pool is None:
        _pool = await create_pool(
            RedisSettings(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                database=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
            ),
        )
    return _pool


async def enqueue_compilation(
    project_id: uuid.UUID,
    correlation_id: str,
    target_stage: str | None = None,
) -> str:
    """
    Enqueue a compilation pipeline job onto the worker-engine queue.

    Returns the ARQ job ID (can be used for status polling if needed).
    """
    pool = await get_arq_pool()
    job_id = await pool.enqueue_job(
        "run_compilation_pipeline",
        str(project_id),
        correlation_id,
        target_stage,
        _job_id=f"compile:{project_id}:{correlation_id}",
        _queue_name="see:queue",
    )

    logger.info(
        f"Enqueued compilation job | project={project_id} "
        f"stage={target_stage or 'all'} job_id={job_id}"
    )

    return job_id
