from typing import Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class ThreatMitigation(BaseModel):
    """Pydantic model mapping strategic threats to active mitigation tasks."""
    threat_description: str = Field(max_length=300)
    impact: int = Field(ge=1, le=3, description="Scale: 1=Low, 2=Medium, 3=High")
    probability: int = Field(ge=1, le=3, description="Scale: 1=Low, 2=Medium, 3=High")
    severity: int = Field(ge=1, le=9, description="Computed: impact * probability")
    mitigation_strategy: str = Field(max_length=300)
    action_item_id: str = Field(description="Action item ID links, e.g. task_auth_setup")
    affected_area: Literal["MARKET", "TECHNICAL", "FINANCIAL", "REGULATORY", "COMPETITIVE"] = Field(
        default="MARKET",
        description="Which area of the business this threat affects"
    )

    @model_validator(mode="before")
    @classmethod
    def compute_severity(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Automatically compute severity from impact * probability."""
        impact = values.get("impact", 1)
        probability = values.get("probability", 1)
        values["severity"] = impact * probability
        return values


class FounderAction(BaseModel):
    """Pydantic model representing strategic actions for the execution horizons."""
    horizon: Literal[
        "IMMEDIATE_30_DAYS",
        "SHORT_TERM_60_DAYS",
        "MEDIUM_TERM_90_DAYS",
        "LONG_TERM_BEYOND"
    ] = Field(description="Target execution timeline windows")
    action: str = Field(max_length=300)
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Priority rankings")


class SWOTOutput(BaseModel):
    """Structured output returned by the SWOT Generator Module."""
    strengths: list[str] = Field(description="List of internal core capabilities")
    weaknesses: list[str] = Field(description="List of internal operational gaps or vulnerabilities")
    opportunities: list[str] = Field(description="List of external market windows or scaling vectors")
    threats: list[str] = Field(description="List of external competitive or regulation risks")
    mitigations: list[ThreatMitigation] = Field(
        description="Mitigation rules mapped for every threat with severity >= 6"
    )
    founder_actions: list[FounderAction] = Field(
        description="Horizon roadmap actions list for the founders team"
    )
    competitor_positioning: str = Field(
        default="",
        max_length=500,
        description="Where this startup stands relative to competitors — advantages and gaps"
    )
    market_validation_required: list[str] = Field(
        default_factory=list,
        description="Specific assumptions the founder must validate before proceeding"
    )
    biggest_assumption: str = Field(
        default="",
        max_length=300,
        description="The single riskiest assumption the business depends on"
    )
