"""Agent Mesh — Workflow patterns for orchestrating agent teams.

The Workflow implementations are the orchestrator (no separate CoordinatorAgent).
Each workflow takes a list of agents, a context dict, and a shared bus,
and returns the final stage output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus, ObservationTimeoutError
from backend.agents.types import AgentRole, ReviewCritique
from backend.core.logging import logger


class Workflow(ABC):
    """Abstract workflow that orchestrates a team of agents."""

    @abstractmethod
    async def execute(
        self,
        agents: list[BaseAgent],
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> dict[str, Any]:
        """Execute the workflow. Returns the final stage output as a dict."""
        pass


class SequentialWorkflow(Workflow):
    """Agents run in order: agent_0 → agent_1 → → agent_n.

    Each agent's output is published to the bus under its role name.
    The last agent's output is returned as the stage result.
    """

    async def execute(
        self,
        agents: list[BaseAgent],
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> dict[str, Any]:
        if not agents:
            raise ValueError("SequentialWorkflow requires at least one agent")

        result = None
        for agent in agents:
            logger.info(
                f"[Workflow:Sequential] Running {agent.role.value} "
                f"({agents.index(agent) + 1}/{len(agents)})"
            )
            result, _ = await agent.safe_run(context, bus)

            # Publish result to bus for downstream agents
            if hasattr(result, "model_dump"):
                await agent.publish_observation(
                    bus, f"{agent.role.value}_output", result
                )
            elif isinstance(result, dict):
                from pydantic import BaseModel

                class DictOutput(BaseModel):
                    data: dict[str, Any]

                await agent.publish_observation(
                    bus, f"{agent.role.value}_output", DictOutput(data=result)
                )

        # Return last agent's result as dict
        if hasattr(result, "model_dump"):
            return result.model_dump()
        elif isinstance(result, dict):
            return result
        else:
            return {"output": result}


class ParallelWorkflow(Workflow):
    """Multiple agents run concurrently. Results are namespaced by role.

    merge_strategy="namespace": each agent's output is under its role key.
    merge_strategy="override": later agents overwrite earlier ones on conflict.
    """

    def __init__(self, merge_strategy: str = "namespace") -> None:
        self.merge_strategy = merge_strategy

    async def execute(
        self,
        agents: list[BaseAgent],
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> dict[str, Any]:
        if not agents:
            raise ValueError("ParallelWorkflow requires at least one agent")

        async def run_agent(agent: BaseAgent) -> tuple[str, Any]:
            result, _ = await agent.safe_run(context, bus)
            return agent.role.value, result

        # Run all agents concurrently
        tasks = [run_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        merged: dict[str, Any] = {}
        errors: list[str] = []

        for item in results:
            if isinstance(item, Exception):
                errors.append(str(item))
                continue

            role_name, result = item
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"output": result}

            if self.merge_strategy == "namespace":
                merged[role_name] = result_dict
            else:
                merged.update(result_dict)

        if errors:
            logger.warning(
                f"[Workflow:Parallel] {len(errors)} agent(s) failed: {errors}"
            )

        return merged


class DebateWorkflow(Workflow):
    """Synthesizer proposes, Reviewer critiques, Synthesizer revises.

    Runs up to max_debate_rounds iterations. If the Reviewer never approves,
    returns the last synthesis plus the outstanding ReviewCritique in metadata.
    """

    def __init__(self, max_rounds: int = 2) -> None:
        self.max_rounds = max_rounds

    async def execute(
        self,
        agents: list[BaseAgent],
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> dict[str, Any]:
        if len(agents) < 2:
            raise ValueError(
                "DebateWorkflow requires at least a Synthesizer and Reviewer"
            )

        # Find synthesizer and reviewer by role
        synthesizer = None
        reviewer = None
        other_agents: list[BaseAgent] = []

        for agent in agents:
            if agent.role == AgentRole.SYNTHESIZER:
                synthesizer = agent
            elif agent.role == AgentRole.REVIEWER:
                reviewer = agent
            else:
                other_agents.append(agent)

        if not synthesizer or not reviewer:
            raise ValueError(
                "DebateWorkflow requires both a SYNTHESIZER and REVIEWER agent"
            )

        # Run any non-debate agents first (e.g., Researcher)
        for agent in other_agents:
            logger.info(f"[Workflow:Debate] Running pre-debate agent: {agent.role.value}")
            result, _ = await agent.safe_run(context, bus)
            if hasattr(result, "model_dump"):
                await agent.publish_observation(
                    bus, f"{agent.role.value}_output", result
                )

        # Debate loop
        last_synthesis = None
        last_critique = None
        approved = False

        for round_num in range(1, self.max_rounds + 1):
            logger.info(
                f"[Workflow:Debate] Round {round_num}/{self.max_rounds}"
            )

            # Synthesizer proposes/revises
            synth_result, _ = await synthesizer.safe_run(context, bus)
            if hasattr(synth_result, "model_dump"):
                last_synthesis = synth_result.model_dump()
            elif isinstance(synth_result, dict):
                last_synthesis = synth_result
            else:
                last_synthesis = {"output": synth_result}

            # Publish synthesis for reviewer
            from pydantic import BaseModel

            class SynthOutput(BaseModel):
                data: dict[str, Any]

            await synthesizer.publish_observation(
                bus, "synthesis_complete", SynthOutput(data=last_synthesis)
            )

            # Reviewer critiques
            review_result, _ = await reviewer.safe_run(context, bus)
            if isinstance(review_result, ReviewCritique):
                last_critique = review_result
            elif isinstance(review_result, dict):
                last_critique = ReviewCritique(**review_result)
            else:
                last_critique = ReviewCritique(
                    approved=False,
                    issues=["Reviewer returned unexpected output"],
                    severity="blocking",
                )

            # Publish critique
            await reviewer.publish_observation(
                bus, "review_complete", last_critique
            )

            if last_critique.approved:
                approved = True
                logger.info(
                    f"[Workflow:Debate] Approved in round {round_num}"
                )
                break
            else:
                logger.info(
                    f"[Workflow:Debate] Round {round_num} not approved: "
                    f"{last_critique.issues}"
                )
                # Inject critique into context for revision
                context["review_critique"] = {
                    "issues": last_critique.issues,
                    "revision_notes": last_critique.revision_notes,
                }

        if not approved:
            logger.warning(
                f"[Workflow:Debate] Non-convergence after {self.max_rounds} rounds. "
                f"Returning last synthesis with unresolved review."
            )

        # Attach metadata about debate outcome
        if last_synthesis is None:
            last_synthesis = {}

        last_synthesis["_debate_metadata"] = {
            "approved": approved,
            "rounds": self.max_rounds,
            "unresolved_issues": last_critique.issues if last_critique and not approved else [],
        }

        return last_synthesis


# Needed for ParallelWorkflow
import asyncio
