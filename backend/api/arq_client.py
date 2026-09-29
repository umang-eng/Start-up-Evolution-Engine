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
from backend.cache.redis import redis_manager


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
    
    If a job is already running for this project, it will clean the stuck
    job and enqueue a fresh one.
    """
    pool = await get_arq_pool()
    
    # Try to clean any stuck jobs for this project first
    job_key = f"compile:{project_id}:"
    try:
        # Find and clean stuck jobs for this project
        if redis_manager.client:
            cursor = 0
            while True:
                cursor, keys = await redis_manager.client.scan(
                    cursor, match=f"arq:job:compile:{project_id}:*", count=100
                )
                for key in keys:
                    job_data = await redis_manager.client.hgetall(key)
                    if job_data and job_data.get("status") == "running":
                        logger.info(f"Cleaning stuck job for project {project_id}: {key}")
                        await redis_manager.client.delete(key)
                if cursor == 0:
                    break
    except Exception as e:
        logger.warning(f"Failed to clean stuck jobs: {e}")
    
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
