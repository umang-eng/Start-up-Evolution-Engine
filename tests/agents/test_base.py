"""Unit tests for backend.agents.base — BaseAgent abstraction.

Tests verify budget enforcement, tool usage limits, and observation publishing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, AgentBudget, ResearchFindings, ToolCallResult


# ── Test agent implementation ────────────────────────────────────

class StubAgent(BaseAgent):
    """Minimal agent for testing BaseAgent behavior."""

    role = AgentRole.ANALYST
    tools = ["calculation"]

    async def run(self, context, bus):
        return {"result": "stub_output"}


class ToolUserAgent(BaseAgent):
    """Agent that uses tools in its run method."""

    role = AgentRole.RESEARCHER
    tools = ["web_search"]

    async def run(self, context, bus):
        result = await self.use_tool("web_search", bus, queries=["test"])
        return {"search_ok": result.ok}


class FailingAgent(BaseAgent):
    """Agent that raises an exception in run()."""

    role = AgentRole.REVIEWER

    async def run(self, context, bus):
        raise RuntimeError("Agent intentionally failed")


# ── BaseAgent tests ──────────────────────────────────────────────

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_safe_run_returns_result(self):
        agent = StubAgent()
        bus = AgentContextBus()
        result, tool_results = await agent.safe_run({}, bus)
        assert result == {"result": "stub_output"}
        assert isinstance(tool_results, list)

    @pytest.mark.asyncio
    async def test_safe_run_crash_raises(self):
        agent = FailingAgent()
        bus = AgentContextBus()
        with pytest.raises(RuntimeError, match="intentionally failed"):
            await agent.safe_run({}, bus)

    @pytest.mark.asyncio
    async def test_tool_budget_enforcement(self):
        budget = AgentBudget(max_tool_calls=2)
        agent = StubAgent(budget=budget)
        bus = AgentContextBus()

        # First two calls should succeed
        r1 = await agent.use_tool("calculation", bus, calc_type="threat_severity", inputs={"impact": 1, "probability": 1})
        assert r1.ok is True

        r2 = await agent.use_tool("calculation", bus, calc_type="threat_severity", inputs={"impact": 1, "probability": 1})
        assert r2.ok is True

        # Third call should be budget-exceeded
        r3 = await agent.use_tool("calculation", bus, calc_type="threat_severity", inputs={})
        assert r3.ok is False
        assert "Budget exceeded" in r3.error

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        agent = StubAgent()
        bus = AgentContextBus()
        result = await agent.use_tool("nonexistent_tool", bus)
        assert result.ok is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_publish_and_wait_observation(self):
        bus = AgentContextBus()

        async def publisher():
            findings = ResearchFindings(market_data={"key": "value"})
            await publisher_agent.publish_observation(bus, "my_topic", findings)

        publisher_agent = StubAgent()
        receiver_agent = StubAgent()

        pub_task = asyncio.create_task(publisher())
        obs = await receiver_agent.wait_for_observation(bus, "my_topic", timeout_s=5.0)
        await pub_task

        assert obs.topic == "my_topic"
        assert obs.data.market_data["key"] == "value"

    def test_default_budget(self):
        agent = StubAgent()
        assert agent.budget.max_tokens == 4000
        assert agent.budget.timeout_s == 30.0
        assert agent.budget.max_tool_calls == 3
