"""Tests for product execution engine."""

import pytest
from backend.modules.product_execution.schemas import (
    ProductExecutionOutput, UserStory, SprintBacklog,
    TechnicalArchitecture, ReleasePlan
)
from backend.modules.evidence.types import ConfidenceScore


class TestUserStory:
    def test_create_user_story(self):
        story = UserStory(
            id="US-001",
            title="User login",
            user_type="End user",
            action="log in to the system",
            benefit="access my dashboard",
            acceptance_criteria=[
                "User can enter credentials",
                "System validates credentials",
                "User is redirected to dashboard",
            ],
            priority="P0",
            effort_estimate="S",
            feature_id="F-01",
        )
        assert story.id == "US-001"
        assert story.priority == "P0"
        assert len(story.acceptance_criteria) == 3


class TestSprintBacklog:
    def test_create_sprint(self):
        story = UserStory(
            id="US-001", title="Login", user_type="User",
            action="log in", benefit="access dashboard",
            acceptance_criteria=["Valid credentials"],
            priority="P0", effort_estimate="S",
        )
        sprint = SprintBacklog(
            sprint_number=1,
            sprint_name="Foundation",
            duration_weeks=2,
            goal="Set up authentication",
            stories=[story],
            total_effort_points=8,
            risks=["Third-party auth dependency"],
        )
        assert sprint.sprint_number == 1
        assert len(sprint.stories) == 1


class TestTechnicalArchitecture:
    def test_create_architecture(self):
        arch = TechnicalArchitecture(
            system_overview="Microservices architecture with API gateway",
            components=[
                {"name": "Auth Service", "description": "Handles authentication"},
                {"name": "API Gateway", "description": "Routes requests"},
            ],
            data_flow="Client → Gateway → Service → Database",
            api_endpoints=[
                {"method": "POST", "path": "/auth/login", "description": "User login"},
            ],
            database_schema=[
                {"table": "users", "columns": "id, email, password_hash"},
            ],
            infrastructure="AWS ECS with RDS PostgreSQL",
            security_considerations=["JWT tokens", "HTTPS only", "Rate limiting"],
        )
        assert arch.system_overview == "Microservices architecture with API gateway"
        assert len(arch.components) == 2


class TestReleasePlan:
    def test_create_release(self):
        release = ReleasePlan(
            release_name="MVP",
            version="1.0.0",
            target_date="2026-03-01",
            features=["Authentication", "Core features"],
            milestones=[
                {"name": "Alpha", "date": "2026-01-15"},
                {"name": "Beta", "date": "2026-02-15"},
            ],
            success_metrics=["95% uptime", " < 2s response time"],
            rollback_plan="Redeploy previous version",
        )
        assert release.version == "1.0.0"
        assert len(release.features) == 2


class TestProductExecutionOutput:
    def test_create_output(self):
        output = ProductExecutionOutput(
            product_vision="Build the best project management tool",
            prd_summary="MVP focusing on core task management",
            user_stories=[],
            technical_architecture=TechnicalArchitecture(
                system_overview="Monolith", components=[],
                data_flow="Simple", api_endpoints=[],
                database_schema=[], infrastructure="Heroku",
                security_considerations=["Basic auth"],
            ),
            sprints=[],
            release_plan=ReleasePlan(
                release_name="MVP", version="0.1",
                target_date="TBD", features=[], milestones=[],
                success_metrics=[], rollback_plan="Redeploy",
            ),
            qa_strategy=["Unit tests"],
            deployment_strategy=["CI/CD"],
            confidence=ConfidenceScore(score=40.0),
            explanation="Execution plan generated",
        )
        assert output.product_vision == "Build the best project management tool"


class TestProductExecutionModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.product_execution.module import ProductExecutionModule
        module = ProductExecutionModule()
        assert module.stage_name == "product_execution"
        assert "roadmap" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_output(self):
        from backend.modules.product_execution.module import ProductExecutionModule
        module = ProductExecutionModule()
        output = module._fallback_output([], "No features")
        assert isinstance(output, ProductExecutionOutput)
        assert output.product_vision is not None
