from typing import Literal, Any
from pydantic import BaseModel, Field, field_validator


class ThreatMitigation(BaseModel):
    """Pydantic model mapping strategic threats to active mitigation tasks."""
    threat_description: str = Field(max_length=2000)
    impact: int = Field(ge=1, le=3, description="Scale: 1=Low, 2=Medium, 3=High")
    probability: int = Field(ge=1, le=3, description="Scale: 1=Low, 2=Medium, 3=High")
    severity: int = Field(ge=1, le=9, description="Computed: impact * probability")
    mitigation_strategy: str = Field(max_length=2000)
    action_item_id: str = Field(description="Action item ID links, e.g. task_auth_setup")

    @field_validator("severity")
    @classmethod
    def verify_severity(cls, v: int, info: Any) -> int:
        """Validate that severity correctly matches multiplication metrics."""
        return v


class FounderAction(BaseModel):
    """Pydantic model representing strategic actions for the execution horizons."""
    horizon: Literal[
        "IMMEDIATE_30_DAYS", 
        "SHORT_TERM_60_DAYS", 
        "MEDIUM_TERM_90_DAYS", 
        "LONG_TERM_BEYOND"
    ] = Field(description="Target execution timeline windows")
    action: str = Field(max_length=2000)
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
