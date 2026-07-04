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
        max_items_list: int = 15
    ) -> dict[str, Any]:
        """Compresses payload lists and narratives to fit token limits."""
        compressed = context.copy()
        
        # Compress narrative descriptions if present
        if "description" in compressed and isinstance(compressed["description"], str):
            if len(compressed["description"]) > 1000:
                logger.debug("Compressing project description context payload.")
                compressed["description"] = compressed["description"][:1000] + "... [Truncated]"

        # Compress feature lists if present
        if "features" in compressed and "features" in compressed["features"]:
            feats = compressed["features"]["features"]
            if isinstance(feats, list) and len(feats) > max_items_list:
                logger.debug(f"Compressing features list size from {len(feats)} to {max_items_list}.")
                compressed["features"]["features"] = feats[:max_items_list]

        return compressed

    def _sanitize_module_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove metadata properties that are irrelevant for prompt contexts."""
        sanitized = data.copy()
        # Strip internal search fields or export layout ASTs to save tokens
        sanitized.pop("search_metadata", None)
        sanitized.pop("export_metadata", None)
        return sanitized


context_manager = ContextManager()
