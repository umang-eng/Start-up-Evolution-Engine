"""Shared generation-session liveness checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.core.config import settings


ACTIVE_GENERATION_STATUSES = {"PENDING", "INITIALIZING", "RUNNING"}


def generation_stale_after() -> timedelta:
    """Allow two full model attempts plus setup time before declaring a run stuck."""
    timeout = max(float(settings.OLLAMA_TIMEOUT_SECONDS), 1.0)
    retries = max(int(settings.PIPELINE_STAGE_RETRIES), 2)
    return timedelta(seconds=max(timeout * retries + 60, 300))


def generation_session_is_stale(
    session: Any,
    now: datetime | None = None,
) -> bool:
    """Return whether an active session has stopped updating beyond its safe timeout."""
    if str(getattr(session, "status", "")).upper() not in ACTIVE_GENERATION_STATUSES:
        return False

    last_update = getattr(session, "updated_at", None) or getattr(session, "created_at", None)
    if not isinstance(last_update, datetime):
        return False
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    return current_time - last_update > generation_stale_after()


def mark_generation_session_stale(session: Any) -> str:
    """Transition an inactive session to FAILED and return its user-facing reason."""
    stage = getattr(session, "current_stage", None) or "unknown stage"
    message = (
        f"Generation stopped responding during {stage}; no progress update arrived within "
        f"{int(generation_stale_after().total_seconds() // 60)} minutes. Retry generation."
    )
    session.status = "FAILED"
    session.error_message = message
    return message
