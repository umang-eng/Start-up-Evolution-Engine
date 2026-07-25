"""
ARQ Worker Entrypoint — Start-up Evolution Engine

Runs as a standalone process inside the worker-engine container.
Consumes jobs from the Redis queue (default: "see:queue") and executes
the background compilation pipeline tasks.
"""

import asyncio
import signal
import sys
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from arq.worker import Worker

from backend.core.config import settings
from backend.core.logging import setup_logging, logger
from backend.worker.tasks import run_compilation_pipeline


# ── ARQ Job Configuration ──────────────────────────────────────────
# Maps task names (strings) to their async callables.
# ARQ workers use this dict to resolve job names to functions.

async def startup(ctx: dict[str, Any]) -> None:
    """Called once when the worker process starts."""
    setup_logging(log_level="INFO" if settings.ENVIRONMENT == "production" else "DEBUG")
    logger.info("[Worker-Engine] ARQ worker starting up...")

    # Initialize database connectivity (reuse existing fallback logic)
    from backend.database.session import verify_db_connectivity
    await verify_db_connectivity()

    # Initialize Redis connection pool
    from backend.cache.redis import redis_manager
    redis_manager.initialize()
    await redis_manager.is_healthy()

    # Clean any stuck jobs from previous worker crashes
    cleaned = await redis_manager.clean_stuck_jobs()
    if cleaned > 0:
        logger.info(f"[Worker-Engine] Cleaned {cleaned} stuck job(s)")

    ctx["redis_manager"] = redis_manager
    logger.info("[Worker-Engine] Startup complete — ready to consume jobs.")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Called once when the worker process shuts down."""
    logger.info("[Worker-Engine] Shutting down...")
    redis_manager = ctx.get("redis_manager")
    if redis_manager:
        await redis_manager.close()
    logger.info("[Worker-Engine] Shutdown complete.")


# ── ARQ Worker Settings ────────────────────────────────────────────
# These settings are read by `python -m backend.worker.main`

class WorkerSettings:
    """ARQ worker configuration — consumed by `arq backend.worker.main.WorkerSettings`."""

    functions = [
        run_compilation_pipeline,
    ]

    on_startup = startup
    on_shutdown = shutdown

    # Redis connection for the job queue
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )

    # Queue name: both api-gateway and worker-engine use the same channel
    queue_name = "see:queue"

    # Job settings
    job_timeout = 600          # 10 minutes max per job (pipeline can be slow)
    retry_delay = 5            # Seconds between retries
    max_tries = 3              # Max retry attempts per job
    health_check_interval = 10 # Seconds between health checks

    # Concurrency: limit simultaneous pipeline runs
    # Adjust based on GEMINI_API_KEY rate limits and DB pool size
    max_jobs = 3


# ── Direct Execution Entry Point ───────────────────────────────────
# Allows running via: python -m backend.worker.main

if __name__ == "__main__":
    from arq import run_worker

    setup_logging(
        log_level="INFO" if settings.ENVIRONMENT == "production" else "DEBUG"
    )
    logger.info("[Worker-Engine] Starting ARQ worker via direct execution...")

    # Run the worker in the current event loop
    asyncio.run(
        run_worker(
            WorkerSettings,
            handle_signals=True,
        )
    )
