"""Evidence collection service — searches for real data before analysis.

Provides functions to gather market data, competitors, pricing, funding,
regulations, and trends from multiple sources.
"""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import EvidenceSource
from backend.utils.search import search_provider


async def search_evidence(query: str, max_results: int = 5) -> list[EvidenceSource]:
    """Search the web for evidence and return structured sources."""
    evidence: list[EvidenceSource] = []
    try:
        if not search_provider.is_configured:
            return evidence
        
        response = await search_provider.search(
            query=query,
            region="US",
            max_results=max_results,
        )
        for result in response.results:
            evidence.append(EvidenceSource(
                source_name=result.title,
                source_url=result.url,
                source_type="WEB_SEARCH",
                snippet=result.snippet[:500] if result.snippet else "",
                relevance_score=result.relevance_score or 0.7,
            ))
    except Exception:
        pass
    return evidence


async def gather_market_evidence(industry: str, product_description: str) -> dict[str, list[EvidenceSource]]:
    """Gather comprehensive market evidence from multiple sources."""
    queries = [
        f"{industry} market size 2024 2025 2026 growth rate",
        f"{industry} competitors market share landscape",
        f"{industry} funding rounds venture capital 2024 2025",
        f"{industry} regulations compliance requirements",
        f"{product_description} pricing trends customers",
        f"{industry} technology trends emerging 2025 2026",
    ]
    results: dict[str, list[EvidenceSource]] = {}
    for q in queries:
        results[q] = await search_evidence(q, max_results=5)
    return results


async def gather_competitor_evidence(competitors: list[str]) -> dict[str, list[EvidenceSource]]:
    """Gather evidence on specific competitors."""
    results: dict[str, list[EvidenceSource]] = {}
    for comp in competitors:
        queries = [
            f"{comp} company funding valuation revenue",
            f"{comp} product features pricing reviews",
            f"{comp} recent news developments 2025",
        ]
        comp_evidence: list[EvidenceSource] = []
        for q in queries:
            comp_evidence.extend(await search_evidence(q, max_results=3))
        results[comp] = comp_evidence
    return results


async def gather_financial_evidence(industry: str, stage: str) -> list[EvidenceSource]:
    """Gather financial benchmark evidence for the industry and stage."""
    queries = [
        f"{industry} {stage} startup SaaS benchmarks metrics 2025",
        f"{industry} average customer acquisition cost LTV",
        f"{industry} gross margin benchmarks startup",
        f"{stage} company burn rate runway benchmarks",
    ]
    evidence: list[EvidenceSource] = []
    for q in queries:
        evidence.extend(await search_evidence(q, max_results=3))
    return evidence


async def gather_regulatory_evidence(industry: str, countries: list[str]) -> dict[str, list[EvidenceSource]]:
    """Gather regulatory evidence for specific countries."""
    results: dict[str, list[EvidenceSource]] = {}
    for country in countries:
        queries = [
            f"{industry} regulations {country} compliance 2025",
            f"{country} data protection privacy laws",
            f"{country} startup regulations foreign company",
        ]
        country_evidence: list[EvidenceSource] = []
        for q in queries:
            country_evidence.extend(await search_evidence(q, max_results=3))
        results[country] = country_evidence
    return results


def merge_evidence(evidence_lists: list[list[EvidenceSource]], max_per_source: int = 3) -> list[EvidenceSource]:
    """Merge evidence from multiple sources, deduplicating by URL."""
    seen_urls: set[str] = set()
    merged: list[EvidenceSource] = []
    for evidence_list in evidence_lists:
        count = 0
        for e in evidence_list:
            if e.source_url not in seen_urls and count < max_per_source:
                seen_urls.add(e.source_url)
                merged.append(e)
                count += 1
    return merged


def evidence_summary(evidence: list[EvidenceSource]) -> str:
    """Create a human-readable summary of evidence."""
    if not evidence:
        return "No evidence gathered."
    by_type: dict[str, int] = {}
    for e in evidence:
        by_type[e.source_type] = by_type.get(e.source_type, 0) + 1
    parts = [f"{count} {src}" for src, count in by_type.items()]
    return f"{len(evidence)} sources gathered: {', '.join(parts)}"
