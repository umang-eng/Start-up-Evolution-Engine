"""ResearcherAgent — Gathers real-time data via web search and database queries.

This agent uses WebSearchTool and DatabaseTool to collect market intelligence,
competitive data, and project context for downstream agents.
"""

from __future__ import annotations

from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, ResearchFindings


class ResearcherAgent(BaseAgent):
    """Gathers real-time data from web search and project database."""

    role = AgentRole.RESEARCHER
    tools = ["web_search", "database"]

    SYSTEM_INSTRUCTION = (
        "You are a senior research analyst specializing in startup market intelligence. "
        "Gather comprehensive, factual data from available sources."
    )

    async def run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> ResearchFindings:
        """Gather research data from web search and project database."""
        project_id = context.get("project_id", "")
        industry = context.get("industry", context.get("dna", {}).get("category", "technology"))
        startup_idea = context.get("startup_idea", context.get("title", ""))

        market_data: dict[str, Any] = {}
        project_data: dict[str, Any] = {}
        sources: list[str] = []
        tool_errors = []

        # Search for market data if enabled
        if context.get("enable_web_research", True):
            queries = [
                f"{industry} market trends 2026 opportunities startups",
                f"{industry} competitive landscape emerging players 2026",
            ]

            search_result = await self.use_tool(
                "web_search",
                bus,
                queries=queries,
                region=context.get("region", "US"),
                industry=industry,
                max_results_per_query=3,
            )

            if search_result.ok and search_result.data:
                market_data = search_result.data
                sources = [
                    r.get("url", "")
                    for r in search_result.data.get("responses", [])
                    if isinstance(r, dict)
                ]
            elif not search_result.ok:
                tool_errors.append(search_result)

        # Get project data from database
        if project_id:
            db_result = await self.use_tool(
                "database",
                bus,
                query_type="project_overview",
                project_id=project_id,
            )
            if db_result.ok and db_result.data:
                project_data = db_result.data
            elif not db_result.ok:
                tool_errors.append(db_result)

        return ResearchFindings(
            market_data=market_data,
            project_data=project_data,
            sources=sources,
            tool_errors=tool_errors,
        )
