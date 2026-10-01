import pytest
import uuid
import io
from types import SimpleNamespace
from typing import Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from pypdf import PdfReader

from backend.schemas.user import UserCreate
from backend.services.user import user_service
from backend.models.project import Project
from backend.models.blueprint import Blueprint
from backend.api.v1.exports import prepare_blueprint_export_data
from backend.exports.export import ExportCompiler

pytestmark = pytest.mark.asyncio


async def test_export_repairs_stale_and_unverified_blueprint_sections() -> None:
    project = SimpleNamespace(
        title="Industrial Predictive Maintenance",
        description="Predictive maintenance software for industrial machinery",
        industry="industrial software",
        region="US",
    )
    task = {
        "id": "task_validation",
        "title": "Validate data",
        "duration_weeks": 4,
        "is_critical_path": False,
    }
    persisted = {
        "product_architecture": {
            "features": [{
                "id": "FEAT-001",
                "name": "Failure prediction",
                "priority": "MUST_HAVE",
                "category": "CORE",
                "effort_estimate": "M",
            }]
        },
        "execution_roadmap": {
            "total_estimated_weeks": 24,
            "critical_path": ["task_validation"],
            "phases": [
                {"name": name, "duration_months": months, "tasks": [dict(task)]}
                for name, months in (("Discovery", 3), ("MVP", 6), ("Launch", 6))
            ],
        },
        "team_structure": {
            "total_monthly_payroll_usd": 0,
            "org_chart": [{"title": "Software Engineer", "estimated_salary_usd": 120_000}],
        },
        "financial_plan": {
            "operational_costs": [{"category": "SALARIES", "monthly_usd": 0}],
            "budget_scenarios": [],
            "funding_requirements": {
                "minimum_target_usd": 0,
                "optimal_target_usd": 0,
                "runway_months": 1,
            },
            "mvp_cost_estimate": 0,
            "year_1_cost_estimate": 0,
        },
        "swot_analysis": {"strengths": ["Engineering expertise"], "weaknesses": ["No pilot data"]},
        "legal_compliance": {
            "funding_sources": [
                {"scheme_name": "State of California Seed Fund Program", "scheme_type": "SEED_FUND"},
                {"scheme_name": "Y Combinator Startup Program", "scheme_type": "GRANT"},
            ],
            "registration_requirements": [
                {"requirement_name": "HIPAA compliance", "category": "DATA_PROTECTION", "authority": "HHS"},
                {"requirement_name": "State Business License", "category": "BUSINESS_REGISTRATION", "authority": "California"},
            ],
            "compliance_directories": [{"agency_name": "HHS", "jurisdiction": "US"}],
            "data_protection_requirements": ["HIPAA is mandatory for industrial software."],
            "summary": "California and HIPAA requirements apply.",
            "estimated_compliance_budget_usd": 0,
        },
    }
    intelligence = {
        "product_execution": {
            "prd_summary": "Execution plan requires detailed feature specifications for full generation.",
            "technical_architecture": {"system_overview": "Architecture to be defined based on specific requirements."},
            "user_stories": [],
            "sprints": [],
        },
        "financial_intelligence": {
            "explanation": "Fallback values require actual financial data.",
            "key_assumptions": ["Fallback values"],
            "metrics": {"assumptions": ["Fallback values"]},
        },
        "global_expansion": {
            "explanation": "Fallback expansion plan.",
            "recommended_first_market": "United Kingdom",
            "waves": [{"countries": [{"local_competitors": ["Local Corp", "UK Tech Ltd"]}]}],
        },
        "investment_committee": {
            "committee_members": [{
                "name": "Sarah Chen",
                "firm": "Horizon Ventures",
                "suggested_terms": "$1.5M at $6M pre-money",
                "vote": "CONDITIONAL",
            }],
            "recommendation": {"expected_roi": "3-5x over 5-7 years"},
            "term_sheet": {"investment_amount": 1_500_000, "pre_money_valuation": 6_000_000},
        },
        "competitive_moat": {
            "moat_dimensions": [{
                "explanation": "Fallback assessment — insufficient evidence",
            }]
        },
    }
    blueprint = {
        "executive_summary": {
            "business_summary": "The startup tackles the growing need for predictive maintenance..."
        },
        "financial_plan": {"mvp_cost_estimate": 0},
        "execution_risks": [],
    }
    records = {
        key: SimpleNamespace(data=value)
        for key, value in persisted.items()
    }

    result = await prepare_blueprint_export_data(blueprint, project, records, intelligence)

    assert result["_project_title"] == project.title
    assert result["financial_plan"]["total_monthly_payroll_usd"] == 10_000
    assert result["financial_plan"]["mvp_cost_estimate"] > 0
    assert result["financial_plan"]["funding_requirements"]["minimum_target_usd"] > 0
    assert result["execution_roadmap"]["total_estimated_weeks"] == 60
    assert result["execution_roadmap"]["phases"][0]["tasks"][0]["is_critical_path"] is True
    assert result["swot_analysis"]["opportunities"]
    assert result["swot_analysis"]["threats"]
    assert result["product_execution"]["sprints"]
    assert "requires detailed feature specifications" not in result["product_execution"]["prd_summary"]
    assert result["financial_intelligence"]["metrics"]["arr"] == 0
    assert result["financial_intelligence"]["scenarios"][0]["year1_revenue"] == 0
    assert result["legal_compliance"]["funding_sources"] == []
    assert result["legal_compliance"]["registration_requirements"] == []
    assert "hipaa" not in str(result["legal_compliance"]).casefold()
    assert result["investment_committee"]["committee_members"][0]["name"].startswith("Simulated ")
    assert "Sarah Chen" not in str(result["investment_committee"])
    assert result["investment_committee"]["term_sheet"]["investment_amount"] is None
    assert result["global_expansion"]["total_markets_assessed"] == 0
    assert result["global_expansion"]["expected_global_arr"] == 0
    assert result["competitive_moat"]["moat_dimensions"][0]["cost_to_copy_usd"] == 0
    assert result["execution_risks"]

    pdf = ExportCompiler().compile_blueprint_to_pdf(result)
    cover_text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert project.title in cover_text
    assert "The startup tackles the growing need" not in cover_text


async def test_exports_and_sharing_workflow(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Setup User and Project
    user_payload = UserCreate(email="exporter@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    project = Project(
        user_id=user.id,
        title="EcoDrive",
        description="Electric vehicle planning",
        industry="CleanTech"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 2. Add Blueprint record for project
    blueprint_data = {
        "executive_summary": {
            "startup_name": "EcoDrive",
            "vision": "Green mobility for everyone",
            "summary": "Building electric vehicle route compilers."
        },
        "dna": {
            "value_proposition": {
                "core_usp": "Route compile optimization saving 15% battery life."
            },
            "revenue_model": {
                "revenue_streams": ["SaaS Subscription", "API Access"]
            }
        },
        "team": {
            "roles": [
                {
                    "role_title": "Lead Venture Architect",
                    "department": "Engineering",
                    "salary_range_usd_min": 120000,
                    "salary_range_usd_max": 150000,
                    "key_responsibilities": ["Lead development", "Architect systems"]
                }
            ]
        }
    }
    blueprint = Blueprint(
        project_id=project.id,
        data=blueprint_data,
        health_score=85.0
    )
    db_session.add(blueprint)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Test that the package is a real PDF and includes generated blueprint sections.
    response = await client.post(
        f"/api/v1/exports/pdf/{project.id}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "content-disposition" in response.headers
    assert f"blueprint-{project.id}.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    assert b"EcoDrive" in response.content
    assert b"Startup DNA" in response.content
    assert b"Team & Organization" in response.content

    # 4. Test Pitch Deck Slide export (falls back to structured JSON if python-pptx not installed)
    response_deck = await client.post(
        f"/api/v1/exports/deck/{project.id}",
        headers=headers
    )
    assert response_deck.status_code == 200
    assert "Content-Type" in response_deck.headers

    # 5. Test Share Link Generation
    response_share = await client.post(
        f"/api/v1/exports/share-link/{project.id}?scope=investor:read",
        headers=headers
    )
    assert response_share.status_code == 200
    share_payload = response_share.json()
    assert share_payload["success"] is True
    share_token = share_payload["data"]["share_token"]
    share_url = share_payload["data"]["share_url"]
    assert "shared" in share_url

    # 6. Test Shared Blueprint Retrieval & Obfuscation (public route, no login auth header)
    response_shared_blueprint = await client.get(
        share_url
    )
    assert response_shared_blueprint.status_code == 200
    shared_data = response_shared_blueprint.json()
    assert shared_data["success"] is True
    
    # Assert sensitive data is obfuscated as CONFIDENTIAL for investor:read scope
    roles = shared_data["data"]["team"]["roles"]
    assert roles[0]["salary_range_usd_min"] == "CONFIDENTIAL"
    assert roles[0]["salary_range_usd_max"] == "CONFIDENTIAL"
    assert roles[0]["role_title"] == "Lead Venture Architect"  # Non-sensitive field intact
