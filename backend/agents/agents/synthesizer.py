"""SynthesizerAgent — Generates structured output using existing stage schemas.

This agent calls the LLM with the stage-specific Pydantic schema to produce
the final structured output. It does NOT define its own output model —
it binds to the existing per-stage schema (e.g. DNAOutput for the DNA stage).
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole


class SynthesizerAgent(BaseAgent):
    """Generates structured output by calling the LLM with the stage schema.

    The output_schema must be set before running (by AgentModule).
    The prompt_template and system_instruction are set per stage.
    """

    role = AgentRole.SYNTHESIZER
    tools = []

    def __init__(
        self,
        output_schema: Type[BaseModel] | None = None,
        system_instruction: str = "",
        prompt_template: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.output_schema = output_schema
        self.system_instruction = system_instruction
        self.prompt_template = prompt_template

    async def run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> BaseModel:
        """Call the LLM to generate structured output matching the stage schema.

        Collects context from research and analysis agents via the bus,
        then calls gemini_adapter.generate() with the stage-specific schema.
        """
        from backend.ai.gemini import gemini_adapter
        from jinja2 import Template

        # Gather context from upstream agents
        research_data = {}
        analysis_data = {}
        review_critique = context.get("review_critique")

        try:
            obs = await self.wait_for_observation(bus, "researcher_output", timeout_s=5.0)
            if hasattr(obs.data, "model_dump"):
                research_data = obs.data.model_dump()
            elif hasattr(obs.data, "data"):
                research_data = obs.data.data if isinstance(obs.data.data, dict) else {}
        except Exception:
            pass

        try:
            obs = await self.wait_for_observation(bus, "analyst_output", timeout_s=5.0)
            if hasattr(obs.data, "model_dump"):
                analysis_data = obs.data.model_dump()
            elif hasattr(obs.data, "data"):
                analysis_data = obs.data.data if isinstance(obs.data.data, dict) else {}
        except Exception:
            pass

        # Build template variables from full context
        variables = {
            "startup_idea": context.get("startup_idea", context.get("title", "")),
            "industry": context.get("industry", "Unspecified"),
            "target_audience": context.get("target_audience", context.get("description", "Unspecified")),
            "notes": context.get("notes", "None"),
            "dna": context.get("dna", {}),
            "features": context.get("features", {}),
            "roadmap": context.get("roadmap", {}),
            "team": context.get("team", {}),
            "swot": context.get("swot", {}),
            "cost": context.get("cost", {}),
            "research": research_data,
            "analysis": analysis_data,
        }

        # Add market/funding blocks if available from research
        if research_data:
            variables["market_data_block"] = research_data.get(
                "formatted_market",
                "[REAL-TIME_MARKET_DATA] No real-time data available[/REAL-TIME_MARKET_DATA]",
            )
            variables["funding_data_block"] = research_data.get(
                "formatted_funding",
                "[REAL-TIME_FUNDING_DATA] No real-time data available[/REAL-TIME_FUNDING_DATA]",
            )

        # Inject review critique for revision rounds
        if review_critique:
            variables["review_critique"] = review_critique
            variables["revision_notes"] = review_critique.get("revision_notes", "")

        # Render prompt
        if self.prompt_template:
            rendered_prompt = Template(self.prompt_template).render(**variables)
        else:
            rendered_prompt = str(variables)

        system_instruction = self.system_instruction

        # Call LLM with schema-constrained generation
        if self.output_schema:
            result = await gemini_adapter.generate(
                prompt=rendered_prompt,
                schema=self.output_schema,
                system_instruction=system_instruction,
            )
            return result
        else:
            # Fallback: return context as-is (for testing)
            return context
