"""
Web Search Provider — Real-Time Grounding for Pipeline Modules

Provides a unified async interface to query real-world market data, funding
schemes, regulatory requirements, and competitive intelligence. Used by
pipeline modules to inject live facts into LLM prompts.

Primary: Tavily Search API (optimized for AI agents, clean structured output)
Fallback: Google Custom Search JSON API (broad coverage, 100 free queries/day)

Usage:
    from backend.utils.search import search_provider

    results = await search_provider.search(
        query="Startup India seed fund scheme 2026 eligibility",
        region="IN",
        max_results=5,
    )

    # Format results for LLM context injection
    context_block = search_provider.format_for_llm(results)
"""

import asyncio
import time
from dataclasses import dataclass, field

import httpx

from backend.core.config import settings
from backend.core.logging import logger


# ── Search Result Data Structures ─────────────────────────────────

@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single clean search result returned by any provider."""
    title: str
    snippet: str
    url: str
    source: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
        }


@dataclass(slots=True)
class SearchResponse:
    """Aggregated response from a search query."""
    query: str
    region: str
    results: list[SearchResult] = field(default_factory=list)
    provider: str = ""
    latency_ms: int = 0
    raw_count: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.results) > 0


# ── Provider Implementations ──────────────────────────────────────

async def _tavily_search(
    query: str,
    region: str,
    max_results: int,
    api_key: str,
) -> SearchResponse:
    """Execute search via Tavily Search API.

    Tavily is purpose-built for AI agents: returns clean titles + snippets
    with no HTML parsing required. Supports region filtering via include_domains.
    """
    start = time.monotonic()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    latency = int((time.monotonic() - start) * 1000)

    results = []
    for item in data.get("results", []):
        results.append(SearchResult(
            title=item.get("title", ""),
            snippet=item.get("content", "")[:500],
            url=item.get("url", ""),
            source="tavily",
            relevance_score=item.get("score", 0.0),
        ))

    return SearchResponse(
        query=query,
        region=region,
        results=results,
        provider="tavily",
        latency_ms=latency,
        raw_count=data.get("results", []),
    )


async def _google_search(
    query: str,
    region: str,
    max_results: int,
    api_key: str,
    cse_id: str,
) -> SearchResponse:
    """Execute search via Google Custom Search JSON API.

    Falls back here if Tavily is unavailable or rate-limited.
    Google CSE returns up to 10 results per call (free tier limit).
    """
    start = time.monotonic()

    region_map = {
        "IN": "in",
        "US": "us",
        "GB": "uk",
        "DE": "de",
        "JP": "jp",
        "BR": "br",
        "AU": "au",
        "CA": "ca",
    }
    gl_param = region_map.get(region.upper(), "us")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cse_id,
                "q": query,
                "num": min(max_results, 10),
                "gl": gl_param,
                "safe": "active",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    latency = int((time.monotonic() - start) * 1000)

    results = []
    for item in data.get("items", []):
        results.append(SearchResult(
            title=item.get("title", ""),
            snippet=item.get("snippet", "")[:500],
            url=item.get("link", ""),
            source="google_cse",
            relevance_score=0.5,
        ))

    return SearchResponse(
        query=query,
        region=region,
        results=results,
        provider="google_cse",
        latency_ms=latency,
        raw_count=len(results),
    )


# ── Search Provider Facade ────────────────────────────────────────

class SearchProvider:
    """Unified search facade that tries providers in priority order.

    Provider priority:
    1. Tavily (if TAVILY_API_KEY is configured)
    2. Google Custom Search (if GOOGLE_SEARCH_API_KEY + GOOGLE_CSE_ID configured)
    3. Graceful degradation: returns empty response with error logged

    All methods are async and use httpx for non-blocking HTTP.
    """

    MAX_QUERY_LENGTH = 500
    SNIPPET_MAX_CHARS = 500

    def __init__(self) -> None:
        self._tavily_key = settings.TAVILY_API_KEY
        self._google_key = settings.GOOGLE_SEARCH_API_KEY
        self._google_cse = settings.GOOGLE_CSE_ID
        self._configured = bool(self._tavily_key or (self._google_key and self._google_cse))

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _build_regional_query(self, base_query: str, region: str, industry: str | None = None) -> str:
        """Construct a region-qualified search query.

        Appends region and industry context to improve result relevance.
        """
        parts = [base_query]

        # Append region qualifier
        region_names = {
            "IN": "India", "US": "United States", "GB": "United Kingdom",
            "DE": "Germany", "JP": "Japan", "BR": "Brazil",
            "AU": "Australia", "CA": "Canada",
        }
        region_name = region_names.get(region.upper(), region)
        if region_name.lower() not in base_query.lower():
            parts.append(region_name)

        # Append industry context
        if industry and industry.lower() not in base_query.lower():
            parts.append(industry)

        query = " ".join(parts)
        return query[: self.MAX_QUERY_LENGTH]

    async def search(
        self,
        query: str,
        region: str = "US",
        industry: str | None = None,
        max_results: int = 5,
    ) -> SearchResponse:
        """Execute a real-time web search with automatic provider fallback.

        Args:
            query: Raw search query (will be enriched with region/industry)
            region: ISO 3166-1 alpha-2 country code (e.g. "IN", "US")
            industry: Optional industry sector to refine results
            max_results: Maximum results to return (1-10)

        Returns:
            SearchResponse with results or error details
        """
        if not self._configured:
            return SearchResponse(
                query=query,
                region=region,
                error="No search provider configured. Set TAVILY_API_KEY or GOOGLE_SEARCH_API_KEY.",
            )

        enriched_query = self._build_regional_query(query, region, industry)
        max_results = max(1, min(max_results, 10))

        logger.info(
            f"[Search] provider=priority_queue query=\"{enriched_query[:80]}…\" "
            f"region={region} max_results={max_results}"
        )

        # Try Tavily first (best for AI consumption)
        if self._tavily_key:
            try:
                response = await _tavily_search(enriched_query, region, max_results, self._tavily_key)
                if response.success:
                    logger.info(
                        f"[Search] Tavily returned {len(response.results)} results "
                        f"in {response.latency_ms}ms"
                    )
                    return response
                logger.warning(f"[Search] Tavily failed: {response.error} — falling back to Google")
            except Exception as e:
                logger.warning(f"[Search] Tavily error: {e} — falling back to Google")

        # Fallback to Google Custom Search
        if self._google_key and self._google_cse:
            try:
                response = await _google_search(
                    enriched_query, region, max_results, self._google_key, self._google_cse
                )
                if response.success:
                    logger.info(
                        f"[Search] Google CSE returned {len(response.results)} results "
                        f"in {response.latency_ms}ms"
                    )
                    return response
                logger.warning(f"[Search] Google CSE failed: {response.error}")
                return response
            except Exception as e:
                logger.error(f"[Search] Google CSE error: {e}")
                return SearchResponse(query=query, region=region, error=str(e))

        return SearchResponse(
            query=query,
            region=region,
            error="No search provider available.",
        )

    async def search_multi(
        self,
        queries: list[str],
        region: str = "US",
        industry: str | None = None,
        max_results_per_query: int = 5,
    ) -> list[SearchResponse]:
        """Execute multiple search queries concurrently.

        Uses asyncio.gather for parallel execution within rate limits.
        """
        tasks = [
            self.search(q, region, industry, max_results_per_query)
            for q in queries
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    @staticmethod
    def format_for_llm(responses: list[SearchResponse] | SearchResponse) -> str:
        """Format search results as a labeled context block for LLM prompt injection.

        Produces a structured string that can be directly appended to the prompt
        context window. Each result block is clearly delineated with metadata.

        Output format:
            [REAL-TIME_MARKET_DATA]
            Source: https://example.com
            Title: Scheme Name
            Snippet: Description text...
            ---
            ...
            [/REAL-TIME_MARKET_DATA]
        """
        if isinstance(responses, SearchResponse):
            responses = [responses]

        lines: list[str] = ["[REAL-TIME_MARKET_DATA]"]

        total_results = 0
        for resp in responses:
            if not resp.success:
                continue

            for result in resp.results:
                total_results += 1
                lines.append(f"Source: {result.url}")
                lines.append(f"Title: {result.title}")
                lines.append(f"Snippet: {result.snippet}")
                lines.append("---")

        if total_results == 0:
            lines.append("No real-time data available for this query.")

        lines.append("[/REAL-TIME_MARKET_DATA]")
        return "\n".join(lines)

    @staticmethod
    def format_grants(results: list[SearchResponse] | SearchResponse) -> str:
        """Format funding/grant search results for prompt injection."""
        if isinstance(results, SearchResponse):
            results = [results]

        lines: list[str] = ["[REAL-TIME_FUNDING_DATA]"]

        for resp in results:
            if not resp.success:
                continue
            for result in resp.results:
                lines.append(f"Grant/Scheme: {result.title}")
                lines.append(f"Details: {result.snippet}")
                lines.append(f"URL: {result.url}")
                lines.append("---")

        lines.append("[/REAL-TIME_FUNDING_DATA]")
        return "\n".join(lines)

    @staticmethod
    def format_compliance(results: list[SearchResponse] | SearchResponse) -> str:
        """Format legal/compliance search results for prompt injection."""
        if isinstance(results, SearchResponse):
            results = [results]

        lines: list[str] = ["[REAL-TIME_COMPLIANCE_DATA]"]

        for resp in results:
            if not resp.success:
                continue
            for result in resp.results:
                lines.append(f"Requirement: {result.title}")
                lines.append(f"Details: {result.snippet}")
                lines.append(f"Source URL: {result.url}")
                lines.append("---")

        lines.append("[/REAL-TIME_COMPLIANCE_DATA]")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────

search_provider = SearchProvider()
