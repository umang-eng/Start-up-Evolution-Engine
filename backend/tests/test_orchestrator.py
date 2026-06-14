import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.context import context_manager
from backend.modules.dna.module import DNAModule
from backend.models.project import Project
from backend.models.user import User
from backend.orchestrator.engine import BaseModule, orchestrator
from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


class DummySuccessModule(BaseModule):
    """Mock module returning success payload."""
    async def run(self, db: AsyncSession, project: Project, context: dict) -> dict:
        return {"compiled": True, "value": 42}


class DummyFailureModule(BaseModule):
    """Mock module raising exceptions."""
    async def run(self, db: AsyncSession, project: Project, context: dict) -> dict:
        raise RuntimeError("Failure module execution failed exception")


async def test_prompt_rendering() -> None:
    # Render with simple values
    dna_module = DNAModule()
    system, user = dna_module.render_prompt(
        system_template=dna_module.SYSTEM_INSTRUCTION,
        user_template=dna_module.PROMPT_TEMPLATE,
        variables={"startup_idea": "AI Broker", "industry": "Finance", "target_audience": "Banks", "notes": "None"}
    )
    assert "Feasibility" in system or "venture architect" in system
    assert "Evaluate the concept: AI Broker" in user
    assert "Target audience segment: Banks" in user


async def test_workflow_orchestrator_success(db_session: AsyncSession) -> None:
    # 1. Setup User and Project
    user_payload = UserCreate(email="workflow@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    
    project = Project(
        user_id=user.id,
        title="Evolution AI",
        description="A platform compiler",
        industry="SaaS"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 2. Register dummy modules for all stages
    success_module = DummySuccessModule()
    for stage in ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint"]:
        orchestrator.register_module(stage, success_module)

    # 3. Trigger orchestrator run
    session = await orchestrator.execute_run(db_session, project, correlation_id="corr-test-123")
    
    # 4. Verify DB records
    assert session.status == "COMPLETED"
    assert session.progress_percentage == 100.0
    assert session.current_stage == "blueprint"
    assert session.error_message is None


async def test_workflow_orchestrator_non_critical_failure(db_session: AsyncSession) -> None:
    # Register Dummy Success for critical stages and Failure for SWOT
    success_module = DummySuccessModule()
    failure_module = DummyFailureModule()
    
    user_payload = UserCreate(email="workflow-fail@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    
    project = Project(
        user_id=user.id,
        title="Faulty Startup Idea",
        description="SWOT will fail",
        industry="Tech"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Mount modules
    for stage in ["dna", "features", "roadmap", "team", "cost", "blueprint"]:
        orchestrator.register_module(stage, success_module)
    orchestrator.register_module("swot", failure_module)  # SWOT is non-critical

    # Trigger orchestrator run
    session = await orchestrator.execute_run(db_session, project, correlation_id="corr-test-456")
    
    # Assert execution did not halt, but transitioned to PARTIAL_SUCCESS or finished
    # Note: SWOT failed, but cost and blueprint succeeded.
    # So workflow finished with COMPLETED, but session logged error_message or registered warning.
    assert session.status == "COMPLETED"
