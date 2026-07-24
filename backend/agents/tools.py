"""Agent Mesh — Tool system for agent tool-use.

Every Tool.execute() call is wrapped; failures return a ToolCallResult
with ok=False and a message — they never raise past the tool boundary.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from backend.agents.types import ToolCallResult
from backend.core.logging import logger


class Tool(ABC):
    """Abstract base for all agent tools."""

    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool. Implementations must NOT raise — return error in dict."""
        pass

    async def safe_execute(self, **kwargs: Any) -> ToolCallResult:
        """Wrap execute() with timing and error handling. Never raises."""
        start = time.monotonic()
        try:
            data = await self.execute(**kwargs)
            latency_ms = int((time.monotonic() - start) * 1000)
            return ToolCallResult(
                tool_name=self.name,
                ok=True,
                data=data,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(f"[Tool] {self.name} failed: {e}")
            return ToolCallResult(
                tool_name=self.name,
                ok=False,
                error=str(e),
                latency_ms=latency_ms,
            )


# ── Concrete Tools ────────────────────────────────────────────────

class WebSearchTool(Tool):
    """Wraps SearchProvider for real-time web intelligence gathering."""

    name = "web_search"
    description = "Search the web for market data, funding schemes, and competitive intelligence"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from backend.utils.search import search_provider

        queries: list[str] = kwargs.get("queries", [])
        region: str = kwargs.get("region", "US")
        industry: str = kwargs.get("industry", "")
        max_results_per_query: int = kwargs.get("max_results_per_query", 3)

        if not search_provider.is_configured:
            return {
                "responses": [],
                "formatted_market": "[REAL-TIME_MARKET_DATA] Search provider not configured[/REAL-TIME_MARKET_DATA]",
                "formatted_funding": "[REAL-TIME_FUNDING_DATA] Search provider not configured[/REAL-TIME_FUNDING_DATA]",
            }

        responses = await search_provider.search_multi(
            queries=queries,
            region=region,
            industry=industry,
            max_results_per_query=max_results_per_query,
        )

        formatted_market = search_provider.format_for_llm(responses)
        formatted_funding = search_provider.format_grants(responses)

        return {
            "responses": [r.__dict__ for r in responses],
            "formatted_market": formatted_market,
            "formatted_funding": formatted_funding,
        }


class DatabaseTool(Tool):
    """Queries project data and existing stage results."""

    name = "database"
    description = "Query project metadata and existing stage results from the database"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.database.session import AsyncSessionLocal
        from backend.models.project import Project
        from sqlalchemy.orm import selectinload

        query_type: str = kwargs.get("query_type", "project_overview")
        project_id: str = kwargs.get("project_id", "")

        if not project_id:
            return {"error": "project_id is required"}

        async with AsyncSessionLocal() as db:
            stmt = (
                select(Project)
                .where(Project.id == project_id)
                .options(
                    selectinload(Project.dna_result),
                    selectinload(Project.feature_result),
                    selectinload(Project.roadmap_result),
                    selectinload(Project.team_result),
                    selectinload(Project.swot_result),
                    selectinload(Project.cost_result),
                    selectinload(Project.legal_compliance_result),
                )
            )
            project = (await db.execute(stmt)).scalar_one_or_none()

            if not project:
                return {"error": f"Project {project_id} not found"}

            if query_type == "project_overview":
                return {
                    "title": project.title,
                    "industry": project.industry,
                    "description": project.description,
                }
            elif query_type == "all_results":
                results = {}
                for attr in ["dna_result", "feature_result", "roadmap_result",
                             "team_result", "swot_result", "cost_result",
                             "legal_compliance_result"]:
                    obj = getattr(project, attr, None)
                    if obj and hasattr(obj, "data"):
                        results[attr] = obj.data
                return results
            else:
                return {"error": f"Unknown query_type: {query_type}"}


class CalculationTool(Tool):
    """Performs deterministic computations (health scores, budgets, severity)."""

    name = "calculation"
    description = "Perform deterministic calculations like health scores, budget projections, and severity ratings"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        calc_type: str = kwargs.get("calc_type", "")
        inputs: dict[str, Any] = kwargs.get("inputs", {})

        if calc_type == "threat_severity":
            impact = inputs.get("impact", 1)
            probability = inputs.get("probability", 1)
            return {"severity": impact * probability}

        elif calc_type == "health_indicators":
            return self._calculate_health_indicators(inputs)

        elif calc_type == "budget_runway":
            monthly_burn = inputs.get("monthly_burn_usd", 0)
            available_capital = inputs.get("available_capital_usd", 0)
            if monthly_burn <= 0:
                return {"runway_months": 0, "error": "monthly_burn_usd must be > 0"}
            runway = available_capital / monthly_burn
            return {"runway_months": round(runway, 1)}

        else:
            return {"error": f"Unknown calc_type: {calc_type}"}

    def _calculate_health_indicators(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Compute startup health indicators from predecessor stage data."""
        dna = inputs.get("dna", {})
        features = inputs.get("features", {})
        roadmap = inputs.get("roadmap", {})
        swot = inputs.get("swot", {})
        cost = inputs.get("cost", {})

        scores = dna.get("scores", {})
        scalability = scores.get("scalability", 50)
        innovation = scores.get("innovation", 50)

        feature_count = len(features.get("features", []))
        task_count = sum(
            len(phase.get("tasks", []))
            for phase in roadmap.get("phases", [])
        )
        execution_readiness = min(100, (task_count / max(feature_count, 1)) * 25)

        funding = cost.get("funding_requirements", {})
        runway_months = funding.get("runway_months", 12)
        funding_readiness = min(100, (runway_months / 18) * 100)

        threats = swot.get("threats", [])
        mitigations = swot.get("mitigations", [])
        risk_exposure = (len(mitigations) / max(len(threats), 1)) * 100 if threats else 50

        growth_readiness = scalability
        strategic_strength = (innovation + scalability) / 2

        composite = (
            execution_readiness * 0.25
            + funding_readiness * 0.25
            + growth_readiness * 0.15
            + risk_exposure * 0.15
            + strategic_strength * 0.20
        )

        return {
            "execution_readiness": round(execution_readiness, 1),
            "funding_readiness": round(funding_readiness, 1),
            "growth_readiness": round(growth_readiness, 1),
            "risk_exposure": round(risk_exposure, 1),
            "strategic_strength": round(strategic_strength, 1),
            "composite_score": round(composite, 1),
        }


# ── Tool Registry ────────────────────────────────────────────────

class ToolRegistry:
    """Central registry of available tools for agents."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


# Singleton registry
tool_registry = ToolRegistry()
tool_registry.register(WebSearchTool())
tool_registry.register(DatabaseTool())
tool_registry.register(CalculationTool())
