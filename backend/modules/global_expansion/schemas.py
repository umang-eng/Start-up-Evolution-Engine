"""Global Expansion Engine — multi-country expansion analysis with evidence."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.modules.evidence.types import ConfidenceScore, EvidenceSource


class CountryExpansion(BaseModel):
    """Expansion analysis for a single country."""
    country: str = Field(description="Country name")
    country_code: str = Field(description="ISO country code")
    priority: Literal["TIER_1", "TIER_2", "TIER_3"] = Field(description="Expansion priority tier")
    market_size_usd: float = Field(ge=0.0, description="Estimated market size in USD")
    local_competitors: list[str] = Field(description="Key local competitors")
    regulatory_requirements: list[str] = Field(description="Key regulations to comply with")
    localization_needs: list[str] = Field(description="Localization requirements")
    hiring_costs_monthly: float = Field(ge=0.0, description="Average monthly hiring cost")
    pricing_adjustment_percent: float = Field(description="Price adjustment vs US market")
    tax_considerations: list[str] = Field(description="Key tax factors")
    gtm_strategy: str = Field(max_length=500, description="Go-to-market for this country")
    risks: list[str] = Field(description="Country-specific risks")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(description="Confidence in this assessment")


class ExpansionWave(BaseModel):
    """A wave of country expansions."""
    wave_number: int
    wave_name: str
    countries: list[CountryExpansion]
    timeline_months: int = Field(ge=0, description="Months for this wave")
    total_investment_usd: float = Field(ge=0.0)
    expected_arr_contribution: float = Field(ge=0.0)


class GlobalExpansionOutput(BaseModel):
    """Complete global expansion analysis."""
    waves: list[ExpansionWave] = Field(min_length=1, description="Expansion waves")
    total_markets_assessed: int = Field(ge=0)
    recommended_first_market: str = Field(description="First market to enter")
    total_expansion_investment: float = Field(ge=0.0)
    expected_global_arr: float = Field(ge=0.0)
    expansion_timeline_months: int = Field(ge=0)
    key_risks: list[str] = Field(description="Global expansion risks")
    recommendations: list[str] = Field(description="Expansion recommendations")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(description="Confidence in expansion plan")
    explanation: str = Field(max_length=2000)
