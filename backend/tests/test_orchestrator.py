import pytest
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.context import context_manager
from backend.modules.dna.module import DNAModule
from backend.models.project import Project
from backend.models.user import User
from backend.orchestrator.engine import BaseModule, WorkflowOrchestrator
from backend.core.exceptions import BaseBusinessException
from backend.schemas.user import UserCreate
from backend.services.user import user_service
from backend.core.config import settings
from backend.utils.checksum import compute_stage_checksum, STAGE_INPUT_DEPENDENCIES

class DummySuccessModule(BaseModule):
    """Mock module returning success payload."""
    async def run(self, db: AsyncSession, project: Project, context: dict) -> dict:
        return {"compiled": True, "value": 42}


class DummyFailureModule(BaseModule):
    """Mock module raising exceptions."""
    async def run(self, db: AsyncSession, project: Project, context: dict) -> dict:
        raise RuntimeError("Failure module execution failed exception")


class DummyCloudFailureModule(BaseModule):
    async def run(self, db: AsyncSession, project: Project, context: dict) -> dict:
        raise BaseBusinessException(
            "Ollama Cloud usage credits are required.",
            code="OLLAMA_CLOUD_CREDITS_REQUIRED",
            status_code=402,
        )


@pytest.mark.asyncio
async def test_prompt_rendering() -> None:
    dna_module = DNAModule()
    system, user = dna_module.render_prompt(
        system_template=dna_module.SYSTEM_INSTRUCTION,
        user_template=dna_module.PROMPT_TEMPLATE,
        variables={"startup_idea": "AI Broker", "industry": "Finance", "target_audience": "Banks", "notes": "None"}
    )
    assert "feasibility" in system.lower() or "venture architect" in system.lower()
    assert "Startup Idea: AI Broker" in user
    assert "Target Audience: Banks" in user


@pytest.mark.asyncio
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

    # 2. Create a fresh orchestrator instance and register dummy modules
    orchestrator = WorkflowOrchestrator()
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

    # 5. Verify cache tracking
    assert session.cache_hits == 0
    assert session.cache_misses == 7
    assert session.stage_cache_map is not None
    assert all(v == "miss" for v in session.stage_cache_map.values())


@pytest.mark.asyncio
async def test_workflow_orchestrator_non_critical_failure(db_session: AsyncSession) -> None:
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

    # Create a fresh orchestrator instance and mount modules
    orchestrator = WorkflowOrchestrator()
    for stage in ["dna", "features", "roadmap", "team", "cost", "blueprint"]:
        orchestrator.register_module(stage, success_module)
    orchestrator.register_module("swot", failure_module)

    session = await orchestrator.execute_run(db_session, project, correlation_id="corr-test-456")

    # SWOT failed (non-critical), but cost and blueprint succeeded
    assert session.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ollama_cloud_failure_stops_after_noncritical_stage(db_session: AsyncSession) -> None:
    success_module = DummySuccessModule()
    user_payload = UserCreate(
        email="workflow-cloud-fail@test.com",
        password="Test-password-for-cloud-error-123!",
    )
    user = await user_service.register_user(db_session, obj_in=user_payload)
    project = Project(
        user_id=user.id,
        title="Cloud failure startup",
        description="Test stopping on a cloud provider error",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    orchestrator = WorkflowOrchestrator()
    for stage in ["dna", "features", "roadmap", "team", "cost", "blueprint"]:
        orchestrator.register_module(stage, success_module)
    orchestrator.register_module("swot", DummyCloudFailureModule())

    session = await orchestrator.execute_run(db_session, project, correlation_id="cloud-402")

    assert session.status == "FAILED"
    assert session.current_stage == "swot"
    assert "credits are required" in (session.error_message or "")


def test_legacy_stage_context_receives_persisted_and_runtime_outputs() -> None:
    orchestrator = WorkflowOrchestrator()
    context = {
        "dna": {"category": "industrial"},
        "features": {"features": [{"name": "Prediction"}]},
    }
    runtime_outputs = {"financial_intelligence": {"metrics": {"arr": 0}}}

    orchestrator._add_output_aliases(context, runtime_outputs)

    assert context["dna_output"] is context["dna"]
    assert context["features_output"] is context["features"]
    assert context["financial_intelligence_output"] is runtime_outputs["financial_intelligence"]


# ── Checksum Unit Tests ────────────────────────────────────────────


def test_checksum_determinism() -> None:
    """Same inputs always produce the same checksum."""
    ctx = {"dna": {"category": "SaaS", "scores": {"feasibility": 85}}}

    h1 = compute_stage_checksum("features", "MyApp", "Tech", "A platform", ctx)
    h2 = compute_stage_checksum("features", "MyApp", "Tech", "A platform", ctx)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_checksum_sensitivity_to_inputs() -> None:
    """Different project titles produce different checksums."""
    ctx = {"dna": {"category": "SaaS"}}

    h1 = compute_stage_checksum("features", "App A", "Tech", "Desc", ctx)
    h2 = compute_stage_checksum("features", "App B", "Tech", "Desc", ctx)
    assert h1 != h2


def test_checksum_sensitivity_to_upstream() -> None:
    """Different upstream results produce different checksums."""
    ctx1 = {"dna": {"category": "SaaS", "scores": {"feasibility": 85}}}
    ctx2 = {"dna": {"category": "SaaS", "scores": {"feasibility": 90}}}

    h1 = compute_stage_checksum("features", "MyApp", "Tech", "Desc", ctx1)
    h2 = compute_stage_checksum("features", "MyApp", "Tech", "Desc", ctx2)
    assert h1 != h2


def test_checksum_ignores_irrelevant_context() -> None:
    """Adding context keys not in the dependency list doesn't change the hash."""
    ctx_base = {"dna": {"category": "SaaS"}}
    ctx_extra = {"dna": {"category": "SaaS"}, "features": {"features": []}}

    # features stage only depends on dna, not features
    h1 = compute_stage_checksum("features", "MyApp", "Tech", "Desc", ctx_base)
    h2 = compute_stage_checksum("features", "MyApp", "Tech", "Desc", ctx_extra)
    assert h1 == h2


def test_blueprint_checksum_includes_intelligence_results() -> None:
    context_a = {
        "dna": {"category": "SaaS"},
        "financial_intelligence": {"metrics": {"arr": 0}},
    }
    context_b = {
        "dna": {"category": "SaaS"},
        "financial_intelligence": {"metrics": {"arr": 25_000}},
    }

    checksum_a = compute_stage_checksum("blueprint", "MyApp", "Tech", "Desc", context_a)
    checksum_b = compute_stage_checksum("blueprint", "MyApp", "Tech", "Desc", context_b)

    assert checksum_a != checksum_b


def test_checksum_changes_when_model_profile_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    context = {"dna": {"category": "SaaS"}}
    current = compute_stage_checksum("features", "MyApp", "Tech", "Desc", context)
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "test-cloud-model")

    updated = compute_stage_checksum("features", "MyApp", "Tech", "Desc", context)

    assert current != updated


def test_stage_dependency_graph_completeness() -> None:
    """All core and legal stages are defined in the dependency graph."""
    expected_stages = {
        "dna", "features", "roadmap", "team", "swot", "cost",
        "blueprint", "legal_compliance",
    }
    assert set(STAGE_INPUT_DEPENDENCIES.keys()) == expected_stages


def test_dna_stage_has_no_upstream_deps() -> None:
    """DNA stage depends only on project base inputs, no upstream results."""
    assert STAGE_INPUT_DEPENDENCIES["dna"] == []


def test_context_manager_checksum_matches() -> None:
    """ContextManager.compute_input_checksum produces same hash as raw function."""
    # Simulate a project with minimal data
    project = SimpleNamespace(
        title="TestApp",
        industry="Finance",
        description="A test platform",
    )

    context = {"dna": {"category": "Finance", "scores": {"feasibility": 80}}}

    # Raw checksum
    raw_hash = compute_stage_checksum(
        "features", "TestApp", "Finance", "A test platform", context
    )

    # Via context manager
    cm_hash = context_manager.compute_input_checksum("features", project, context)
    assert raw_hash == cm_hash
