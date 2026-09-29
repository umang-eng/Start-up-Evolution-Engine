from typing import Literal
from pydantic import BaseModel, Field


class FundingSource(BaseModel):
    """An active grant, subsidy, or funding scheme relevant to the startup."""
    scheme_name: str = Field(description="Official name of the scheme or grant")
    scheme_type: Literal["GRANT", "SUBSIDY", "SEED_FUND", "VC_PROGRAM", "GOVERNMENT_SCHEME", "TAX_INCENTIVE"]
    description: str = Field(max_length=500, description="What the scheme offers")
    eligibility: str = Field(max_length=500, description="Who qualifies and key criteria")
    amount_range: str = Field(max_length=200, description="Funding range or benefit amount (e.g. 'Up to ₹25 Lakhs')")
    application_url: str = Field(default="", description="Official application or information URL")
    deadline: str = Field(default="", description="Application deadline if known")
    relevance_score: float = Field(ge=0.0, le=1.0, description="How relevant this scheme is to the startup")


class RegistrationRequirement(BaseModel):
    """A mandatory business registration, license, or filing requirement."""
    requirement_name: str = Field(description="Name of the registration or filing")
    authority: str = Field(description="Issuing government body or agency")
    category: Literal["BUSINESS_REGISTRATION", "TAX_REGISTRATION", "INDUSTRY_LICENSE", "LABOR_COMPLIANCE", "ENVIRONMENTAL", "DATA_PROTECTION", "IP_FILING"]
    description: str = Field(max_length=500, description="What this registration entails")
    estimated_cost: str = Field(default="", description="Government fee or estimated cost")
    timeline: str = Field(default="", description="Processing time (e.g. '7-15 business days')")
    is_mandatory: bool = Field(description="Whether this is legally required before operations")
    reference_url: str = Field(default="", description="Official government portal URL")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(description="Execution priority")


class ComplianceDirectory(BaseModel):
    """A directory entry for a local regulatory agency or compliance body."""
    agency_name: str = Field(description="Name of the regulatory body")
    jurisdiction: str = Field(description="Geographic scope (e.g. 'Gujarat, India' or 'Delaware, US')")
    contact_url: str = Field(default="", description="Official website URL")
    relevant_for: list[str] = Field(description="Which compliance areas this agency covers")


class LegalComplianceOutput(BaseModel):
    """Structured output from the Legal & Compliance Doc Generator Module.

    Contains real-time research results on funding opportunities, registration
    requirements, and compliance directories for the startup's target region.
    """
    funding_sources: list[FundingSource] = Field(
        min_length=3,
        max_length=8,
        description="Active funding schemes, grants, and subsidies relevant to the startup"
    )
    registration_requirements: list[RegistrationRequirement] = Field(
        min_length=2,
        max_length=10,
        description="Mandatory business registrations, licenses, and filings"
    )
    compliance_directories: list[ComplianceDirectory] = Field(
        min_length=1,
        max_length=5,
        description="Local regulatory agencies and compliance bodies"
    )
    industry_specific_licenses: list[RegistrationRequirement] = Field(
        default_factory=list,
        description="Industry-specific permits (e.g. FSSAI, SEBI, Drug License)"
    )
    data_protection_requirements: list[str] = Field(
        default_factory=list,
        description="Applicable data protection and privacy compliance requirements"
    )
    summary: str = Field(
        max_length=1500,
        description="Executive summary of the legal and compliance landscape for this startup in its target region"
    )
    estimated_compliance_budget_usd: float = Field(
        ge=0.0,
        description="Total estimated cost for all mandatory registrations and initial compliance setup"
    )
