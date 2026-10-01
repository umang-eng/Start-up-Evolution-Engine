"""Investment Committee Simulation Module — realistic VC review process.

Simulates a real investment committee meeting with multiple partners,
deliberation, voting, and term sheet generation.
"""

from __future__ import annotations

from typing import Any

from backend.ai.ollama import ollama_adapter
from backend.modules.investment_committee.schemas import (
    InvestmentCommitteeOutput, CommitteeMember
)
from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, InvestorRecommendation
)
from backend.modules.evidence.collector import search_evidence
from backend.modules.evidence.pipeline import run_decision_pipeline
from backend.core.config import settings


IC_PROMPT = """You are simulating a Venture Capital Investment Committee meeting.

## Startup Under Review
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}
- Features: {features_summary}
- Team: {team_summary}
- Monthly Burn: ${monthly_burn:,.0f}
- Key Competitors: {competitors_text}

## Evidence Package
{evidence_text}

## Hypothetical Committee Simulation
This is an analytical simulation, not an actual investment committee, investor interest, or offer.
Never use real people or real venture-fund names. Label members as simulated roles and every
term-sheet number as illustrative; if evidence is insufficient, state that terms are undetermined.
Do not imply that real investors reviewed, approved, offered, or negotiated anything for this company.

## Committee Members (simulate 5 partner roles; do not invent identities)
Each member must have a distinct personality:
1. **Market-focused partner**: Cares about market size and timing
2. **Technical partner**: Cares about technology moat and team capability
3. **Financial partner**: Cares about unit economics and path to profitability
4. **Growth partner**: Cares about scalability and GTM strategy
5. **Risk-averse partner**: Cares about downside protection and exit

For EACH member provide:
- A role-based name (for example, "Simulated Market Partner") and firm "Illustrative simulation"
- Their investment thesis (2-3 sentences)
- Their vote: INVEST / PASS / CONDITIONAL
- Their confidence level (0-100)
- Their biggest concern
- What excites them most
- Suggested deal terms

## Voting Rules
- Majority INVEST = deal goes through
- 2+ PASS = deal fails
- Mix = conditional terms

## Final Recommendation Must Include:
- Investment Thesis (2-3 sentences)
- 3 Reasons to Invest
- 3 Reasons Not to Invest
- Fatal Risks (if any)
- Biggest Unknowns
- Competitive Advantages
- Exit Opportunities (IPO, acquisition, etc.)
- Expected ROI range
- Funding recommendation (amount, stage, terms)
- Due diligence checklist (8-12 items)

## Illustrative Term-Sheet Scenario (not an offer)
- Pre-money valuation
- Investment amount
- Equity offered
- Board seats
- Protective provisions
- Liquidation preference
- Anti-dilution

## Due Diligence Items
List 8-12 items with status: PENDING/IN_PROGRESS/COMPLETE

Return valid InvestmentCommitteeOutput JSON."""


class InvestmentCommitteeModule:
    """Simulates a realistic VC investment committee meeting."""

    stage_name = "investment_committee"
    input_stages = ["dna", "features", "roadmap", "team", "cost", "blueprint",
                    "competitive_moat", "financial_intelligence"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []
        industry = context.get("industry", "technology")

        # Gather IC-specific evidence
        if not settings.PIPELINE_FAST_MODE:
            ic_evidence = await search_evidence(
                f"{industry} startup valuation multiples funding rounds 2025", max_results=4
            )
            evidence.extend(ic_evidence)

        # Run multi-agent pipeline for IC context
        decision_result = {}
        if not settings.PIPELINE_FAST_MODE:
            decision_result = await run_decision_pipeline(
                {**context, "stage": "investment_committee"}, evidence
            )

        # Generate IC simulation
        output = await self._generate_ic(context, evidence, decision_result)
        return output.model_dump()

    async def _generate_ic(
        self, context: dict[str, Any], evidence: list[EvidenceSource],
        decision_result: dict[str, Any]
    ) -> InvestmentCommitteeOutput:
        """Generate investment committee simulation."""
        features = context.get("features_output") or context.get("features", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: {f.get('description', '')[:60]}"
            for f in feature_list[:8] if isinstance(f, dict)
        )

        team = context.get("team_output") or context.get("team", {})
        roles = team.get("org_chart") or team.get("roles", [])
        team_summary = ", ".join(
            r.get("title", "Role") for r in roles[:6] if isinstance(r, dict)
        ) or "Not specified"

        cost = context.get("cost_output") or context.get("cost", {})
        monthly_burn = float(cost.get("monthly_burn_usd", 0) or cost.get("total_monthly_payroll_usd", 0) or 0)

        dna = context.get("dna_output") or context.get("dna", {})
        competitors = dna.get("competitor_landscape", [])
        competitors_text = ", ".join(
            c.get("name", "Unknown") for c in competitors[:4] if isinstance(c, dict)
        ) or "None identified"

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:120]}"
            for e in evidence[:20]
        )

        prompt = IC_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            features_summary=features_summary,
            team_summary=team_summary,
            monthly_burn=monthly_burn,
            competitors_text=competitors_text,
            evidence_text=evidence_text,
        )

        result = await ollama_adapter.generate(
            prompt=prompt,
            schema=InvestmentCommitteeOutput,
            system_instruction="You are simulating a Venture Capital Investment Committee meeting with multiple partners.",
        )

        if isinstance(result, InvestmentCommitteeOutput):
            result.evidence = evidence[:15]
            return InvestmentCommitteeOutput.model_validate(self.sanitize_output(result.model_dump()))

        return self._fallback_output(evidence, monthly_burn)

    @staticmethod
    def sanitize_output(data: dict[str, Any]) -> dict[str, Any]:
        """Keep simulated committee output from implying real investors or an actual offer."""
        result = dict(data)
        members = []
        roles = (
            "Market-focused", "Technical", "Financial", "Growth",
            "Risk-focused", "Product-focused", "Operations-focused",
        )
        for index, raw_member in enumerate(result.get("committee_members", [])):
            if not isinstance(raw_member, dict):
                continue
            member = dict(raw_member)
            role = roles[min(index, len(roles) - 1)]
            member["name"] = f"Simulated {role} Partner"
            member["firm"] = "Illustrative simulation — not an actual investor"
            member["suggested_terms"] = (
                "No offer or financing terms; any future terms require diligence and direct investor negotiation."
            )
            members.append(member)
        result["committee_members"] = members

        recommendation = dict(result.get("recommendation") or {})
        recommendation["expected_roi"] = "Not estimable from supplied evidence"
        result["recommendation"] = recommendation

        term_sheet = dict(result.get("term_sheet") or {})
        term_sheet.update({
            "status": "Illustrative simulation only — no investor has made an offer.",
            "pre_money_valuation": None,
            "investment_amount": None,
            "equity_offered": None,
            "board_seats": None,
            "protective_provisions": None,
            "liquidation_preference": None,
            "anti_dilution": None,
        })
        result["term_sheet"] = term_sheet
        result["explanation"] = (
            "Simulated analytical review only; no real investor reviewed this startup or made an offer."
        )
        return result

    def _fallback_output(self, evidence: list[EvidenceSource], monthly_burn: float) -> InvestmentCommitteeOutput:
        """Fallback IC simulation."""
        fallback_member = CommitteeMember(
            name="Simulated Analyst",
            firm="Illustrative simulation — not an actual investor",
            thesis="A recommendation cannot be made until customer demand, pricing, and financial assumptions are validated.",
            vote="PASS",
            confidence=5.0,
            key_concern="No verified customer or financial evidence is available.",
            key_excitement="The project brief describes a problem worth validating.",
            suggested_terms="No offer or financing terms; valuation requires diligence and investor negotiation.",
        )

        return InvestmentCommitteeOutput(
            recommendation=InvestorRecommendation(
                recommendation="PASS",
                investment_thesis="This simulated review cannot recommend investment without validated customer demand and financial evidence.",
                reasons_to_invest=[
                    "The project brief identifies a specific problem and target customer.",
                ],
                reasons_not_to_invest=[
                    "Market size, pricing, and revenue model are unvalidated.",
                ],
                fatal_risks=["No verified customer demand or financial evidence was supplied."],
                biggest_unknowns=["Actual customer willingness to pay", "True market size"],
                competitive_advantages=[],
                exit_opportunities=["Strategic acquisition", "Series A and growth"],
                expected_roi="Not estimable from supplied evidence",
                confidence=ConfidenceScore(score=5.0, evidence=evidence[:5]),
                due_diligence_checklist=[
                    "Customer interviews (10+)", "Market size validation",
                    "Competitor deep dive", "Financial model review",
                ],
            ),
            committee_members=[fallback_member],
            vote_tally={"INVEST": 0, "PASS": 1, "CONDITIONAL": 0},
            deliberation_notes=[
                "Simulation only; no real investor reviewed this startup.",
                "Validate customer demand, pricing, and the competitive landscape.",
            ],
            term_sheet={
                "status": "Illustrative simulation only — no investor has made an offer.",
                "pre_money_valuation": None,
                "investment_amount": None,
                "equity_offered": None,
            },
            due_diligence_status={
                "Customer references": "PENDING",
                "Market analysis": "IN_PROGRESS",
                "Financial audit": "PENDING",
                "Technical review": "COMPLETE",
            },
            evidence=evidence[:10],
            confidence=ConfidenceScore(
                score=5.0,
                evidence=evidence[:5],
                missing_information=["Verified customers", "Pricing and unit economics", "Independent market sizing"],
            ),
            explanation="Fallback simulation only; it does not represent an actual investment decision or offer.",
        )
