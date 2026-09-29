from typing import Any
from backend.models.project import Project
from backend.core.logging import logger
from backend.utils.checksum import compute_stage_checksum


# Maps result relationship attribute names to their stage keys
_RESULT_ATTR_MAP = {
    "dna": "dna_result",
    "features": "feature_result",
    "roadmap": "roadmap_result",
    "team": "team_result",
    "swot": "swot_result",
    "cost": "cost_result",
    "legal_compliance": "legal_compliance_result",
}


class ContextManager:
    """Manages active compilation contexts and token payload compression strategies.

    Now includes checksum computation: each time a context is assembled for a stage,
    the manager computes the deterministic input hash so the orchestrator can compare
    it against the stored hash of the existing result.
    """

    def assemble_context(self, project: Project) -> dict[str, Any]:
        """Gathers database results from all completed stages into a prompt variable context."""
        context: dict[str, Any] = {
            "startup_idea": project.title,
            "industry": project.industry,
            "description": project.description
        }

        # Mount DNA Context if present
        if project.dna_result and project.dna_result.data:
            context["dna"] = self._sanitize_module_data(project.dna_result.data)

        # Mount Feature Context if present
        if project.feature_result and project.feature_result.data:
            context["features"] = self._sanitize_module_data(project.feature_result.data)

        # Mount Roadmap Context if present
        if project.roadmap_result and project.roadmap_result.data:
            context["roadmap"] = self._sanitize_module_data(project.roadmap_result.data)

        # Mount Team Context if present
        if project.team_result and project.team_result.data:
            context["team"] = self._sanitize_module_data(project.team_result.data)

        # Mount SWOT Context if present
        if project.swot_result and project.swot_result.data:
            context["swot"] = self._sanitize_module_data(project.swot_result.data)

        # Mount Cost Context if present
        if project.cost_result and project.cost_result.data:
            context["cost"] = self._sanitize_module_data(project.cost_result.data)

        # Mount Legal & Compliance Context if present
        if project.legal_compliance_result and project.legal_compliance_result.data:
            context["legal_compliance"] = self._sanitize_module_data(project.legal_compliance_result.data)

        return context

    def compute_input_checksum(
        self,
        stage_name: str,
        project: Project,
        context: dict[str, Any],
    ) -> str:
        """Compute the deterministic input checksum for a specific stage.

        This is the hash that the orchestrator compares against the stored
        hash_checksum of the existing result to determine cache hit/miss.
        """
        return compute_stage_checksum(
            stage_name=stage_name,
            project_title=project.title,
            project_industry=project.industry,
            project_description=project.description,
            context=context,
        )

    def get_stored_checksum(self, project: Project, stage_name: str) -> str | None:
        """Retrieve the stored hash_checksum for a stage's existing result.

        Returns None if no result exists for this stage.
        """
        result_attr = _RESULT_ATTR_MAP.get(stage_name)
        if not result_attr:
            return None

        result_obj = getattr(project, result_attr, None)
        if result_obj and hasattr(result_obj, "hash_checksum"):
            return result_obj.hash_checksum
        return None

    def compress_context_payload(
        self,
        context: dict[str, Any],
        max_items_list: int = 25,
    ) -> dict[str, Any]:
        """Preserve full structured data between stages — only compress when absolutely necessary.

        Previous version destroyed critical context (descriptions, dependencies, responsibilities).
        This version only compresses when lists exceed realistic token budgets.

        Compression strategy:
        - DNA: preserve scores, competitors, key risks (foundation for all downstream)
        - Features: preserve descriptions, user_stories, dependencies (roadmap needs them)
        - Roadmap: preserve task details, acceptance_criteria (team/cost need them)
        - Team: preserve responsibilities, skills, salary (cost/blueprint need them)
        - SWOT: preserve mitigations with severity (blueprint needs them)
        - Cost: preserve breakdowns (blueprint needs them)
        - Only truncate text fields > 3000 chars (not 500)
        """
        compressed = context.copy()

        # Only truncate extremely long narrative descriptions
        if "description" in compressed and isinstance(compressed["description"], str):
            if len(compressed["description"]) > 3000:
                compressed["description"] = compressed["description"][:3000] + "... [Truncated]"

        # Features: keep all fields, only cap at 25 features max
        if "features" in compressed and isinstance(compressed.get("features"), dict):
            feats = compressed["features"].get("features", [])
            if isinstance(feats, list) and len(feats) > max_items_list:
                compressed["features"]["features"] = feats[:max_items_list]

        # Roadmap: keep all task fields, only cap phases at 8
        if "roadmap" in compressed and isinstance(compressed["roadmap"], dict):
            phases = compressed["roadmap"].get("phases", [])
            if isinstance(phases, list) and len(phases) > 8:
                compressed["roadmap"]["phases"] = phases[:8]

        # Team: keep all role fields, only cap at 15 roles
        if "team" in compressed and isinstance(compressed["team"], dict):
            org = compressed["team"].get("org_chart", [])
            if isinstance(org, list) and len(org) > 15:
                compressed["team"]["org_chart"] = org[:15]

        # SWOT: keep all data, only cap lists at 10
        if "swot" in compressed and isinstance(compressed["swot"], dict):
            for key in ("strengths", "weaknesses", "opportunities", "threats"):
                val = compressed["swot"].get(key, [])
                if isinstance(val, list) and len(val) > 10:
                    compressed["swot"][key] = val[:10]

        # Cost: keep all data, only cap operational costs at 15
        if "cost" in compressed and isinstance(compressed["cost"], dict):
            ops = compressed["cost"].get("operational_costs", [])
            if isinstance(ops, list) and len(ops) > 15:
                compressed["cost"]["operational_costs"] = ops[:15]

        return compressed

    def _sanitize_module_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove metadata properties that are irrelevant for prompt contexts."""
        sanitized = data.copy()
        # Strip internal search fields or export layout ASTs to save tokens
        sanitized.pop("search_metadata", None)
        sanitized.pop("export_metadata", None)
        return sanitized


context_manager = ContextManager()
