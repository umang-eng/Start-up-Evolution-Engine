"""Unit tests for backend.agents.tools — Tool system.

Tests use mocked external dependencies (no live web search, no live DB).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents.tools import (
    Tool, WebSearchTool, DatabaseTool, CalculationTool,
    ToolRegistry, tool_registry,
)
from backend.agents.types import ToolCallResult


# ── Tool base class ──────────────────────────────────────────────

class TestToolBase:
    def test_registry_has_all_tools(self):
        assert "web_search" in tool_registry.list_tools()
        assert "database" in tool_registry.list_tools()
        assert "calculation" in tool_registry.list_tools()

    def test_registry_get(self):
        tool = tool_registry.get("web_search")
        assert tool is not None
        assert isinstance(tool, WebSearchTool)

    def test_registry_get_unknown(self):
        assert tool_registry.get("nonexistent") is None


# ── WebSearchTool ────────────────────────────────────────────────

class TestWebSearchTool:
    @pytest.mark.asyncio
    async def test_search_not_configured(self):
        tool = WebSearchTool()
        with patch("backend.utils.search.search_provider") as mock_sp:
            mock_sp.is_configured = False
            result = await tool.safe_execute(queries=["test query"])
            assert result.ok is True
            assert "formatted_market" in result.data

    @pytest.mark.asyncio
    async def test_search_configured(self):
        tool = WebSearchTool()
        with patch("backend.utils.search.search_provider") as mock_sp:
            mock_sp.is_configured = True
            mock_sp.search_multi = AsyncMock(return_value=[])
            mock_sp.format_for_llm = MagicMock(return_value="[DATA]test[/DATA]")
            mock_sp.format_grants = MagicMock(return_value="[GRANTS]test[/GRANTS]")

            result = await tool.safe_execute(
                queries=["query1"],
                region="US",
                industry="tech",
            )
            assert result.ok is True
            assert result.data["formatted_market"] == "[DATA]test[/DATA]"

    @pytest.mark.asyncio
    async def test_search_exception_returns_error(self):
        tool = WebSearchTool()
        with patch("backend.utils.search.search_provider") as mock_sp:
            mock_sp.is_configured = True
            mock_sp.search_multi = AsyncMock(side_effect=Exception("API down"))

            result = await tool.safe_execute(queries=["query1"])
            assert result.ok is False
            assert "API down" in result.error


# ── DatabaseTool ─────────────────────────────────────────────────

class TestDatabaseTool:
    @pytest.mark.asyncio
    async def test_missing_project_id(self):
        tool = DatabaseTool()
        result = await tool.safe_execute()
        assert result.ok is True
        assert "error" in result.data

    @pytest.mark.asyncio
    async def test_project_not_found(self):
        tool = DatabaseTool()
        with patch("backend.database.session.AsyncSessionLocal") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await tool.safe_execute(project_id="test-id")
            assert result.ok is True
            assert "not found" in result.data.get("error", "").lower()


# ── CalculationTool ──────────────────────────────────────────────

class TestCalculationTool:
    @pytest.mark.asyncio
    async def test_threat_severity(self):
        tool = CalculationTool()
        result = await tool.safe_execute(
            calc_type="threat_severity",
            inputs={"impact": 3, "probability": 2},
        )
        assert result.ok is True
        assert result.data["severity"] == 6

    @pytest.mark.asyncio
    async def test_budget_runway(self):
        tool = CalculationTool()
        result = await tool.safe_execute(
            calc_type="budget_runway",
            inputs={"monthly_burn_usd": 10000, "available_capital_usd": 120000},
        )
        assert result.ok is True
        assert result.data["runway_months"] == 12.0

    @pytest.mark.asyncio
    async def test_budget_runway_zero_burn(self):
        tool = CalculationTool()
        result = await tool.safe_execute(
            calc_type="budget_runway",
            inputs={"monthly_burn_usd": 0, "available_capital_usd": 100000},
        )
        assert result.ok is True
        assert "error" in result.data

    @pytest.mark.asyncio
    async def test_health_indicators(self):
        tool = CalculationTool()
        result = await tool.safe_execute(
            calc_type="health_indicators",
            inputs={
                "dna": {"scores": {"scalability": 80, "innovation": 70}},
                "features": {"features": [{"id": 1}, {"id": 2}]},
                "roadmap": {"phases": [{"tasks": [{"id": 1}, {"id": 2}, {"id": 3}]}]},
                "swot": {"threats": ["t1", "t2"], "mitigations": [{"m": 1}]},
                "cost": {"funding_requirements": {"runway_months": 18}},
            },
        )
        assert result.ok is True
        assert "composite_score" in result.data
        assert 0 <= result.data["composite_score"] <= 100

    @pytest.mark.asyncio
    async def test_unknown_calc_type(self):
        tool = CalculationTool()
        result = await tool.safe_execute(calc_type="nonexistent")
        assert result.ok is True
        assert "error" in result.data


# ── Tool.safe_execute error wrapping ─────────────────────────────

class TestToolSafeExecute:
    @pytest.mark.asyncio
    async def test_exception_caught(self):
        class BrokenTool(Tool):
            name = "broken"
            async def execute(self, **kwargs):
                raise RuntimeError("boom")

        tool = BrokenTool()
        result = await tool.safe_execute()
        assert result.ok is False
        assert "boom" in result.error
        assert result.tool_name == "broken"
        assert result.latency_ms >= 0
