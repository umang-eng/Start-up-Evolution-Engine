"""Financial Analyst Agent — assesses financial viability, unit economics, and projections."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class FinancialAnalystAgent(SpecializedAgent):
    role = "Financial Analyst"
    expertise = "Financial modeling, unit economics, valuation, fundraising"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        stage = context.get("stage", "pre-seed")
        cost = context.get("cost_output", {})
        target = context.get("target_market", "")

        fin_evidence = await search_evidence(
            f"{industry} {stage} startup financial benchmarks metrics 2025", max_results=4
        )
        evidence.extend(fin_evidence)

        viability = self._score_financial_viability(context, evidence)
        unit_econ = self._score_unit_economics(context, evidence)
        fundraise = self._score_fundraise_ability(context, evidence)

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, viability, unit_econ, fundraise),
            scores=[viability, unit_econ, fundraise],
            key_findings=[
                f"Financial viability: {viability.value:.0f}/100",
                f"Unit economics: {unit_econ.value:.0f}/100",
                f"Fundraising ability: {fundraise.value:.0f}/100",
            ],
            risks_identified=self._risks(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                (viability.confidence.score + unit_econ.confidence.score) / 2,
                evidence,
                missing=["Detailed financial projections", "Actual financial data"],
                assumptions=["Industry benchmarks applicable", "Standard SaaS metrics"]
            ),
        )

    def _score_financial_viability(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        fin_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["revenue", "profit", "margin", "financial"])]
        val = 55 + min(len(fin_signals) * 5, 25) if fin_signals else 45
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Financial Viability",
            confidence=self._build_confidence(val, fin_signals),
            explanation=f"{len(fin_signals)} financial data points found."
        )

    def _score_unit_economics(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        unit_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["cac", "ltv", "unit economics", "payback"])]
        val = 55 + min(len(unit_signals) * 7, 25) if unit_signals else 48
        return EvidenceBackedScore(
            value=min(val, 90),
            label="Unit Economics Health",
            confidence=self._build_confidence(val, unit_signals),
            explanation=f"{len(unit_signals)} unit economics indicators found."
        )

    def _score_fundraise_ability(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        fund_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["funding", "investor", "venture", "raise"])]
        val = 55 + min(len(fund_signals) * 5, 25) if fund_signals else 50
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Fundraising Readiness",
            confidence=self._build_confidence(val, fund_signals),
            explanation=f"{len(fund_signals)} funding ecosystem signals found."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        return (
            f"Financial analysis: Viability {scores[0].value:.0f}/100, "
            f"Unit Economics {scores[1].value:.0f}/100, Fundraising {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources."
        )

    def _risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        cost = ctx.get("cost_output", {})
        if not cost:
            risks.append("No cost analysis provided — financial projections may be unreliable")
        burn = cost.get("total_monthly_payroll_usd", 0)
        if burn > 50000:
            risks.append(f"High monthly burn (${burn:,.0f}) relative to early stage")
        return risks[:3]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Build detailed financial model with best/base/worst case scenarios",
            "Target LTV:CAC ratio of 3:1 or higher",
            "Maintain 18+ months runway at all times",
        ]
