from typing import Literal
from pydantic import BaseModel, Field, field_validator


class FeatureItem(BaseModel):
    """Pydantic model representing a single product feature."""
    id: str = Field(description="Deterministic unique slug, e.g. feat_auth_core")
    name: str = Field(max_length=100)
    category: Literal["CORE", "ADVANCED", "FUTURE", "COMPETITIVE", "GROWTH"] = Field(
        description="Feature category classification"
    )
    description: str = Field(max_length=500)
    priority: Literal["MUST_HAVE", "SHOULD_HAVE", "COULD_HAVE", "WONT_HAVE"] = Field(
        description="MoSCoW priority score"
    )
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Development complexity estimate"
    )
    effort_estimate: Literal["XS", "S", "M", "L", "XL"] = Field(
        default="M",
        description="Engineering effort: XS(<1wk), S(1-2wk), M(2-4wk), L(1-2mo), XL(2+mo)"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of parent feature IDs this feature depends on"
    )
    user_stories: list[str] = Field(
        default_factory=list,
        description="As a [user], I want [X] so that [Y]"
    )
    business_value: str = Field(
        default="",
        max_length=300,
        description="Why this feature matters to the business"
    )
    success_metrics: list[str] = Field(
        default_factory=list,
        description="How to measure this feature works post-launch"
    )


class FeatureExtractorOutput(BaseModel):
    """Structured output schema returned by the Feature Extraction Module."""
    features: list[FeatureItem] = Field(
        min_length=5,
        max_length=20,
        description="Dynamic feature list scaled by startup complexity (5-20 features)"
    )
    mvp_scope_rationale: str = Field(max_length=1000)
    core_stack: list[str] = Field(description="Recommended technology choices")
    blockers: list[str] = Field(description="Identified technical risk factors or integration blockers")
    nfr_requirements: list[str] = Field(
        default_factory=list,
        description="Non-functional requirements: performance, security, scalability, accessibility"
    )
    technical_risks: list[str] = Field(
        default_factory=list,
        description="Known implementation risks and mitigation approaches"
    )

    @field_validator("features")
    @classmethod
    def check_circular_dependencies(cls, v: list[FeatureItem]) -> list[FeatureItem]:
        """Runs a DFS cycle-detection check on the feature dependency map."""
        adj: dict[str, list[str]] = {f.id: f.dependencies for f in v}
        visited: dict[str, int] = {f.id: 0 for f in v}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node: str) -> bool:
            if visited[node] == 1:
                return True  # Cycle detected
            if visited[node] == 2:
                return False

            visited[node] = 1
            for neighbor in adj.get(node, []):
                if neighbor in visited:  # Ignore external system refs
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for f in v:
            if visited[f.id] == 0:
                if dfs(f.id):
                    # Clean dependency path to resolve the cycle (reset parent dependencies)
                    f.dependencies = []

        return v
