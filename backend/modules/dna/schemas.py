from pydantic import BaseModel, Field, field_validator


class DNAPayload(BaseModel):
    """Input payload to trigger the Startup DNA Analyzer."""
    startup_idea: str = Field(min_length=20, max_length=1000)
    industry_hint: str | None = Field(default=None, max_length=100)
    target_audience_hint: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)

    @field_validator("startup_idea")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Strip markdown and excessive white spaces."""
        import re
        cleaned = re.sub(r"[*_#`~]", "", v)
        return " ".join(cleaned.split())


class DNAScores(BaseModel):
    """Structured scoring metrics for core startup viability vectors."""
    innovation: int = Field(ge=0, le=100)
    scalability: int = Field(ge=0, le=100)
    complexity: int = Field(ge=0, le=100)
    market_opportunity: int = Field(ge=0, le=100)
    risk_factor: int = Field(ge=0, le=100)
    competition: int = Field(ge=0, le=100)


class CompetitorItem(BaseModel):
    """A identified competitor in the market landscape."""
    name: str = Field(description="Company or product name")
    type: str = Field(description="Direct, indirect, or substitute competitor")
    strength: str = Field(max_length=200, description="Key competitive strength")
    threat_level: str = Field(description="HIGH, MEDIUM, or LOW threat to this startup")


class DNAOutput(BaseModel):
    """Structured output returned by the Gemini AI Engine."""
    category: str = Field(description="Startup category, e.g., B2B SaaS, Marketplace, Hardware, DeepTech, B2C App")
    customer_type: str = Field(description="Customer type segment, e.g., B2B, B2C, B2B2C, B2G")
    market_type: str = Field(description="Market structure, e.g., Existing niche, New/Disruptive market, Clone market")
    business_model: str = Field(description="Core monetization strategy details")
    revenue_streams: list[str] = Field(description="Array of primary revenue capture methods")
    value_proposition: str = Field(description="Elevator value proposition statement")
    usp: str = Field(description="Unique Selling Proposition distinguishing the startup")
    target_segments: list[str] = Field(description="Demographic and customer group segments list")
    scores: DNAScores
    executive_summary: str = Field(description="Detailed narrative diagnostic summary paragraph")
    strategic_recommendations: list[str] = Field(description="Actionable next steps list for the management team")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Reliability score metric")
    confidence_rationale: str = Field(description="Rationale behind context match quality score")
    market_size_estimate: str = Field(
        default="",
        description="Estimated TAM/SAM/SOM, e.g., 'TAM ~$50B, SAM ~$5B, SOM ~$500M'"
    )
    competitor_landscape: list[CompetitorItem] = Field(
        default_factory=list,
        description="Top 3-5 identified competitors with threat assessment"
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Top 3-5 risks with brief rationale for each"
    )
    market_evidence: str = Field(
        default="",
        description="Summary of real-time market data used for scoring, if available"
    )
