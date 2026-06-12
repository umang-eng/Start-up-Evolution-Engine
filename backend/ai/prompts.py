import os
from typing import Any
import yaml
from jinja2 import Template

from backend.core.config import settings
from backend.core.logging import logger

# Default embedded templates in case YAML files are missing on disk
FALLBACK_PROMPTS = {
    "dna_analyzer": {
        "system_instruction": "You are a senior venture architect and McKinsey business analyst. Evaluate the following startup idea.",
        "template": "Analyze the business idea: {{ startup_idea }}.\nIndustry context: {{ industry }}.\nAudience segments: {{ target_audience }}."
    },
    "feature_extractor": {
        "system_instruction": "You are a senior product manager and software architect. Convert the business intelligence profile into a product feature catalog.",
        "template": "Review the startup idea: {{ startup_idea }}.\nDNA Value Proposition: {{ dna.value_proposition }}.\nExtract all core, advanced, future, and competitive features."
    },
    "roadmap_generator": {
        "system_instruction": "You are a lead project manager and tech coordinator. Schedule development deliverables for product release phases.",
        "template": "Startup Concept: {{ startup_idea }}.\nFeature Catalog: {{ features }}.\nGenerate execution phases and milestones."
    },
    "team_structure": {
        "system_instruction": "You are a Head of Talent and startup advisor. Propose an engineering organization chart and salary projections.",
        "template": "Feature catalog scope: {{ features }}.\nRoadmap launch deliverables: {{ roadmap }}.\nPropose hiring timelines and role descriptions."
    },
    "swot_generator": {
        "system_instruction": "You are a startup accelerator director and risk analyst. Conduct a thorough SWOT analysis and map threats to specific roadmap tasks.",
        "template": "Startup idea: {{ startup_idea }}.\nFeature scope: {{ features }}.\nRoadmap schedule: {{ roadmap }}.\nDraft strategic SWOT opportunities and risk mitigations."
    },
    "cost_estimator": {
        "system_instruction": "You are a startup CFO and venture analyst. Build financial operational expense calculations.",
        "template": "Startup Model: {{ dna.business_model }}.\nRequired org hires: {{ team }}.\nIdentify operational tool budgets, salaries, and cash runway targets."
    },
    "blueprint_composer": {
        "system_instruction": "You are a principal systems architect. Consolidate strategic modules into a single, cohesive narrative overview.",
        "template": "Verify all compiled modules:\nDNA: {{ dna }}\nFeatures: {{ features }}\nRoadmap: {{ roadmap }}\nTeam: {{ team }}\nSWOT: {{ swot }}\nCost: {{ cost }}\nDraft the executive summaries."
    }
}


class PromptManager:
    """Manages prompt template loading, versioning, and variable interpolation."""

    def __init__(self) -> None:
        self.prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)

    def load_prompt_definition(self, module_name: str) -> dict[str, str]:
        """Load prompt configuration from disk or fall back to default values."""
        file_path = os.path.join(self.prompts_dir, f"{module_name}.yaml")
        if not os.path.exists(file_path):
            logger.debug(f"Prompt YAML file not found for {module_name}, loading default fallback configuration.")
            return FALLBACK_PROMPTS.get(module_name, {
                "system_instruction": "You are a startup consultant.",
                "template": "Analyze the context: {{ context }}"
            })

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return {
                    "system_instruction": config.get("system_instruction", ""),
                    "template": config.get("template", "")
                }
        except Exception as e:
            logger.error(f"Failed to read prompt template file {file_path}", exc_info=e)
            return FALLBACK_PROMPTS.get(module_name, {})

    def render_prompt(self, module_name: str, variables: dict[str, Any]) -> tuple[str, str]:
        """Interpolates variables into the loaded instructions and template."""
        config = self.load_prompt_definition(module_name)
        system_instruction = config.get("system_instruction", "")
        template_text = config.get("template", "")

        # Render templates using Jinja2
        system_rendered = Template(system_instruction).render(**variables)
        user_rendered = Template(template_text).render(**variables)

        return system_rendered, user_rendered


prompt_manager = PromptManager()
