"""
Allow running the worker via: python -m backend.worker
"""

import asyncio
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from arq import run_worker
from backend.core.config import settings
from backend.core.logging import setup_logging
from backend.worker.main import WorkerSettings

if __name__ == "__main__":
    setup_logging(
        log_level="INFO" if settings.ENVIRONMENT == "production" else "DEBUG"
    )
    asyncio.run(run_worker(WorkerSettings, handle_signals=True))
