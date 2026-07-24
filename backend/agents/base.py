"""Agent Mesh — Base agent abstraction and lifecycle.

All agents inherit from BaseAgent. The agent's run() method is called
by workflows; the agent must respect budgets (timeout, tool call limits).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, AgentBudget, Observation, ToolCallResult
from backend.core.logging import logger


class BaseAgent(ABC):
    """Abstract base for all pipeline agents.

    Subclasses must define:
        - role: AgentRole
        - tools: list of tool names from the registry (or empty list)
    """

    role: AgentRole
    tools: list[str] = []

    def __init__(self, budget: AgentBudget | None = None) -> None:
        self.budget = budget or AgentBudget()
        self._tool_call_count = 0

    @abstractmethod
    async def run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> Any:
        """Execute the agent's work. Returns agent-specific output.

        Must NOT raise exceptions — handle errors internally and return
        a result that includes error information if needed.
        """
        pass

    async def safe_run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> tuple[Any, list[ToolCallResult]]:
        """Run the agent with budget enforcement and timing.

        Returns:
            (result, tool_call_results) — tool results are collected for metadata
        """
        start = time.monotonic()
        tool_results: list[ToolCallResult] = []

        logger.info(
            f"[Agent] Starting {self.role.value} | "
            f"budget=timeout={self.budget.timeout_s}s,tools={self.budget.max_tool_calls}"
        )

        try:
            result = await self.run(context, bus)
        except Exception as e:
            logger.error(f"[Agent] {self.role.value} crashed: {e}")
            raise

        elapsed = time.monotonic() - start
        logger.info(
            f"[Agent] Completed {self.role.value} | "
            f"elapsed={elapsed:.1f}s,tool_calls={self._tool_call_count}"
        )

        return result, tool_results

    async def use_tool(
        self,
        tool_name: str,
        bus: AgentContextBus,
        **kwargs: Any,
    ) -> ToolCallResult:
        """Use a tool with budget enforcement. Returns ToolCallResult (never raises)."""
        from backend.agents.tools import tool_registry

        if self._tool_call_count >= self.budget.max_tool_calls:
            result = ToolCallResult(
                tool_name=tool_name,
                ok=False,
                error=f"Budget exceeded: {self._tool_call_count}/{self.budget.max_tool_calls} tool calls used",
            )
            logger.warning(
                f"[Agent] {self.role.value} budget exceeded for tool {tool_name}"
            )
            return result

        tool = tool_registry.get(tool_name)
        if not tool:
            result = ToolCallResult(
                tool_name=tool_name,
                ok=False,
                error=f"Tool '{tool_name}' not found in registry",
            )
            return result

        self._tool_call_count += 1
        return await tool.safe_execute(**kwargs)

    async def publish_observation(
        self,
        bus: AgentContextBus,
        topic: str,
        data: Any,
    ) -> None:
        """Publish an observation to the context bus."""
        obs = Observation(
            topic=topic,
            producer=self.role,
            data=data,
        )
        await bus.publish(self.role, obs)

    async def wait_for_observation(
        self,
        bus: AgentContextBus,
        topic: str,
        timeout_s: float = 30.0,
    ) -> Observation:
        """Wait for an observation from another agent."""
        return await bus.subscribe(self.role, topic, timeout_s=timeout_s)
