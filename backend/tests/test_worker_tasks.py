from typing import Any

import pytest

from backend.models.project import Project
from backend.models.workflow import GenerationSession
from backend.schemas.user import UserCreate
from backend.services.user import user_service
from backend.worker import tasks


pytestmark = pytest.mark.asyncio


async def test_worker_crash_marks_generation_failed(
    db_session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="worker-crash@test.com", password="Worker-test-pass-123!"),
    )
    project = Project(
        user_id=user.id,
        title="Worker crash",
        description="A worker crash regression test.",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.flush()
    session = GenerationSession(
        project_id=project.id,
        status="PENDING",
        correlation_id="worker-crash-test",
        current_stage="queued",
        progress_percentage=0,
    )
    db_session.add(session)
    await db_session.commit()

    def fail_to_initialize_orchestrator():
        raise RuntimeError("orchestrator startup failed")

    monkeypatch.setattr(tasks, "_get_orchestrator", fail_to_initialize_orchestrator)

    result = await tasks.run_compilation_pipeline(
        {},
        str(project.id),
        "worker-crash-test",
    )

    await db_session.refresh(session)
    assert result == {"success": False, "error": "orchestrator startup failed"}
    assert session.status == "FAILED"
    assert session.error_message == "Pipeline worker crashed: orchestrator startup failed"


async def test_local_pipeline_recovers_once_after_api_restart(
    db_session: Any,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(
            email="local-recovery@test.com",
            password="local-test-password",
        ),
    )
    project = Project(
        user_id=user.id,
        title="Local recovery",
        description="A local development recovery regression test.",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.flush()
    session = GenerationSession(
        project_id=project.id,
        status="RUNNING",
        correlation_id="local-recovery-test",
        current_stage="dna",
        progress_percentage=0,
        stage_cache_map={
            "_local_execution": {
                "target_stage": None,
                "start_from_stage": "stress_test",
                "recovery_attempts": 0,
            }
        },
    )
    db_session.add(session)
    await db_session.commit()

    jobs = await tasks.recover_local_pipeline_sessions(db_session)

    assert (str(project.id), "local-recovery-test", None, "stress_test") in jobs
    await db_session.refresh(session)
    assert session.status == "PENDING"
    assert session.current_stage == "queued"
    assert session.stage_cache_map["_local_execution"]["recovery_attempts"] == 1

    jobs = await tasks.recover_local_pipeline_sessions(db_session)

    assert jobs == []
    await db_session.refresh(session)
    assert session.status == "FAILED"
    assert "restarted repeatedly" in (session.error_message or "")
