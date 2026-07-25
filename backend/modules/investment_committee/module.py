"""Investment Committee Simulation Module — realistic VC review process.

Simulates a real investment committee meeting with multiple partners,
deliberation, voting, and term sheet generation.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.investment_committee.schemas import (
    InvestmentCommitteeOutput, CommitteeMember
)
from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, InvestorRecommendation
)
from backend.modules.evidence.collector import search_evidence
from backend.modules.evidence.pipeline import run_decision_pipeline


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

## Committee Members (generate 5 realistic VC partners)
Each member must have a distinct personality:
1. **Market-focused partner**: Cares about market size and timing
2. **Technical partner**: Cares about technology moat and team capability
3. **Financial partner**: Cares about unit economics and path to profitability
4. **Growth partner**: Cares about scalability and GTM strategy
5. **Risk-averse partner**: Cares about downside protection and exit

For EACH member provide:
- Name and firm (realistic VC names)
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

## Term Sheet
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
        ic_evidence = await search_evidence(
            f"{industry} startup valuation multiples funding rounds 2025", max_results=4
        )
        evidence.extend(ic_evidence)

        # Run multi-agent pipeline for IC context
        decision_context = {**context, "stage": "investment_committee"}
        decision_result = await run_decision_pipeline(decision_context, evidence)

        # Generate IC simulation
        output = await self._generate_ic(context, evidence, decision_result)
        return output.model_dump()

    async def _generate_ic(
        self, context: dict[str, Any], evidence: list[EvidenceSource],
        decision_result: dict[str, Any]
    ) -> InvestmentCommitteeOutput:
        """Generate investment committee simulation."""
        features = context.get("features_output", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: {f.get('description', '')[:60]}"
            for f in feature_list[:8] if isinstance(f, dict)
        )

        team = context.get("team_output", {})
        roles = team.get("roles", [])
        team_summary = ", ".join(
            r.get("title", "Role") for r in roles[:6] if isinstance(r, dict)
        ) or "Not specified"

        cost = context.get("cost_output", {})
        monthly_burn = cost.get("total_monthly_payroll_usd", 15000)

        competitors = context.get("dna_output", {}).get("competitor_landscape", [])
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

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=InvestmentCommitteeOutput,
            system_instruction="You are simulating a Venture Capital Investment Committee meeting with multiple partners.",
        )

        if isinstance(result, InvestmentCommitteeOutput):
            result.evidence = evidence[:15]
            return result

        return self._fallback_output(evidence, monthly_burn)

    def _fallback_output(self, evidence: list[EvidenceSource], monthly_burn: float) -> InvestmentCommitteeOutput:
        """Fallback IC simulation."""
        fallback_member = CommitteeMember(
            name="Sarah Chen",
            firm="Horizon Ventures",
            thesis="Early-stage SaaS in emerging markets with strong team fundamentals.",
            vote="CONDITIONAL",
            confidence=55.0,
            key_concern="Limited market data for validation",
            key_excitement="Strong technical team and clear product vision",
            suggested_terms="$1.5M pre-seed at $6M pre-money",
        )

        return InvestmentCommitteeOutput(
            recommendation=InvestorRecommendation(
                recommendation="CONDITIONAL_INVEST",
                investment_thesis="Promising early-stage opportunity with strong team but unvalidated market assumptions.",
                reasons_to_invest=[
                    "Strong technical founding team",
                    "Large addressable market",
                    "Clear product vision",
                ],
                reasons_not_to_invest=[
                    "Market size unvalidated",
                    "Competitive landscape uncertain",
                    "Revenue model not proven",
                ],
                fatal_risks=["No proven demand", "Competitive response unknown"],
                biggest_unknowns=["Actual customer willingness to pay", "True market size"],
                competitive_advantages=["Technical expertise", "First-mover timing"],
                exit_opportunities=["Strategic acquisition", "Series A and growth"],
                expected_roi="3-5x over 5-7 years",
                confidence=ConfidenceScore(score=55.0, evidence=evidence[:5]),
                due_diligence_checklist=[
                    "Customer interviews (10+)", "Market size validation",
                    "Competitor deep dive", "Financial model review",
                ],
            ),
            committee_members=[fallback_member],
            vote_tally={"INVEST": 1, "PASS": 1, "CONDITIONAL": 3},
            deliberation_notes=[
                "Committee sees potential but requires more validation",
                "Market timing is a key concern",
                "Team strength is a key asset",
            ],
            term_sheet={
                "pre_money_valuation": 6000000,
                "investment_amount": 1500000,
                "equity_offered": 20.0,
                "board_seats": 1,
                "liquidation_preference": "1x non-participating",
            },
            due_diligence_status={
                "Customer references": "PENDING",
                "Market analysis": "IN_PROGRESS",
                "Financial audit": "PENDING",
                "Technical review": "COMPLETE",
            },
            evidence=evidence[:10],
            confidence=ConfidenceScore(score=55.0, evidence=evidence[:5]),
            explanation="Conditional investment recommendation — strong team needs market validation before full commitment.",
        )
