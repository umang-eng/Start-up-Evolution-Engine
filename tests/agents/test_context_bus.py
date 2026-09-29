"""Unit tests for backend.agents.context_bus — Inter-agent communication.

Tests verify publish/subscribe, timeouts, and the ObservationTimeoutError contract.
"""

import pytest
import asyncio

from backend.agents.context_bus import AgentContextBus, ObservationTimeoutError
from backend.agents.types import AgentRole, Observation, ResearchFindings


# ── Publish / Subscribe ──────────────────────────────────────────

class TestContextBus:
    @pytest.mark.asyncio
    async def test_publish_subscribe_immediate(self):
        bus = AgentContextBus()
        findings = ResearchFindings(market_data={"tam": "50B"})
        obs = Observation(
            topic="research_complete",
            producer=AgentRole.RESEARCHER,
            data=findings,
        )
        await bus.publish(AgentRole.RESEARCHER, obs)

        # Subscribe should return immediately
        received = await bus.subscribe(
            AgentRole.SYNTHESIZER, "research_complete", timeout_s=1.0
        )
        assert received.topic == "research_complete"
        assert received.data.market_data == {"tam": "50B"}

    @pytest.mark.asyncio
    async def test_subscribe_waits_for_publish(self):
        bus = AgentContextBus()
        received = None

        async def delayed_publish():
            await asyncio.sleep(0.1)
            obs = Observation(
                topic="analysis_done",
                producer=AgentRole.ANALYST,
                data=ResearchFindings(),
            )
            await bus.publish(AgentRole.ANALYST, obs)

        # Start subscriber and publisher concurrently
        publish_task = asyncio.create_task(delayed_publish())
        received = await bus.subscribe(
            AgentRole.SYNTHESIZER, "analysis_done", timeout_s=5.0
        )
        await publish_task

        assert received is not None
        assert received.topic == "analysis_done"

    @pytest.mark.asyncio
    async def test_subscribe_timeout_raises(self):
        bus = AgentContextBus()
        with pytest.raises(ObservationTimeoutError) as exc_info:
            await bus.subscribe(
                AgentRole.REVIEWER, "nonexistent_topic", timeout_s=0.1
            )
        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_returns_latest(self):
        bus = AgentContextBus()
        for i in range(3):
            obs = Observation(
                topic="multiple",
                producer=AgentRole.RESEARCHER,
                data=ResearchFindings(market_data={"iter": i}),
            )
            await bus.publish(AgentRole.RESEARCHER, obs)

        received = await bus.subscribe(
            AgentRole.ANALYST, "multiple", timeout_s=1.0
        )
        assert received.data.market_data["iter"] == 2

    @pytest.mark.asyncio
    async def test_get_all_observations(self):
        bus = AgentContextBus()
        for topic in ["a", "b", "a"]:
            obs = Observation(
                topic=topic,
                producer=AgentRole.RESEARCHER,
                data=ResearchFindings(),
            )
            await bus.publish(AgentRole.RESEARCHER, obs)

        all_obs = bus.get_all_observations()
        assert "a" in all_obs
        assert "b" in all_obs
        assert len(all_obs["a"]) == 2

    @pytest.mark.asyncio
    async def test_clear(self):
        bus = AgentContextBus()
        obs = Observation(
            topic="test",
            producer=AgentRole.RESEARCHER,
            data=ResearchFindings(),
        )
        await bus.publish(AgentRole.RESEARCHER, obs)
        assert len(bus.get_all_observations()) == 1

        bus.clear()
        assert len(bus.get_all_observations()) == 0
