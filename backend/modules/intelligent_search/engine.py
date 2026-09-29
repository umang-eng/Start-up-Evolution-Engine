"""Intelligent Search — natural language search across all startup knowledge.

Searches structured knowledge rather than keyword matching.
Allows semantic retrieval of decisions, meetings, actions, and more.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from backend.modules.memory.engine import MemoryEngine
from backend.modules.decisions.engine import DecisionIntelligence
from backend.modules.knowledge_graph.engine import KnowledgeGraphEngine, NodeType
from backend.modules.action_execution.engine import ActionExecutionEngine
from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class SearchResult(BaseModel):
    """A single search result."""
    result_type: str = Field(description="Type of result (decision, memory, action, node, event)")
    title: str
    content: str
    source_meeting_id: str = ""
    source_meeting_title: str = ""
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Complete search response."""
    query: str
    results: list[SearchResult]
    total_results: int
    summary: str
    related_queries: list[str] = Field(default_factory=list)


SEARCH_PROMPT = """You are a Startup Knowledge Search Engine. Answer this natural language query about the startup.

## Query
{query}

## Available Knowledge

### Recent Decisions
{decisions}

### Recent Memory Entries
{memories}

### Action Items
{actions}

### Knowledge Graph Entities
{entities}

## Task:
1. Find all relevant information that answers this query
2. Rank by relevance
3. Provide context from source meetings
4. Suggest related queries the user might want to explore

Return as JSON with:
- results: list of {result_type, title, content, source_meeting_id, relevance_score}
- summary: 2-3 sentence answer to the query
- related_queries: 3-5 related search suggestions"""


class IntelligentSearchEngine:
    """Natural language search across all startup knowledge."""

    def __init__(
        self,
        memory_engine: MemoryEngine,
        decision_engine: DecisionIntelligence,
        knowledge_engine: KnowledgeGraphEngine,
        action_engine: ActionExecutionEngine,
    ):
        self.memory = memory_engine
        self.decisions = decision_engine
        self.knowledge = knowledge_engine
        self.actions = action_engine

    async def search(self, query: str) -> SearchResponse:
        """Search all startup knowledge with natural language."""
        decisions = self._format_decisions()
        memories = self._format_memories()
        actions = self._format_actions()
        entities = self._format_entities()

        prompt = SEARCH_PROMPT.format(
            query=query,
            decisions=decisions,
            memories=memories,
            actions=actions,
            entities=entities,
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=SearchResponse,
                system_instruction="You search startup knowledge and provide relevant results.",
            )

            if isinstance(result, SearchResponse):
                result.query = query
                return result

        except Exception as e:
            logger.warning(f"Intelligent search failed: {e}")

        # Fallback to keyword search
        return self._fallback_search(query)

    def _format_decisions(self) -> str:
        """Format recent decisions for search context."""
        recent = self.decisions.get_recent(15)
        if not recent:
            return "No decisions recorded."
        parts = []
        for d in recent:
            parts.append(f"- [{d.category}] {d.decision[:100]} (confidence: {d.confidence:.0%})")
        return "\n".join(parts)

    def _format_memories(self) -> str:
        """Format recent memories for search context."""
        recent = self.memory.get_recent(15)
        if not recent:
            return "No memories recorded."
        parts = []
        for m in recent:
            parts.append(f"- [{m.memory_type.value}] [{m.category}] {m.content[:100]}")
        return "\n".join(parts)

    def _format_actions(self) -> str:
        """Format pending actions for search context."""
        pending = self.actions.get_pending()[:10]
        if not pending:
            return "No pending actions."
        parts = []
        for a in pending:
            parts.append(f"- [{a.priority.value}] {a.title} (owner: {a.owner})")
        return "\n".join(parts)

    def _format_entities(self) -> str:
        """Format knowledge graph entities for search context."""
        entities = []
        for node_type in [NodeType.PERSON, NodeType.FEATURE, NodeType.COMPETITOR, NodeType.DECISION]:
            nodes = self.knowledge.get_by_type(node_type)
            for n in nodes[:5]:
                entities.append(f"- [{node_type.value}] {n.name}")
        return "\n".join(entities) if entities else "No entities in knowledge graph."

    def _fallback_search(self, query: str) -> SearchResponse:
        """Fallback keyword search when LLM search fails."""
        results = []

        # Search decisions
        for d in self.decisions.search(query):
            results.append(SearchResult(
                result_type="decision",
                title=d.decision[:100],
                content=f"{d.decision} — {d.reason}",
                source_meeting_id=d.source_meeting_id,
                relevance_score=0.7,
            ))

        # Search memories
        for m in self.memory.search(query):
            results.append(SearchResult(
                result_type="memory",
                title=m.content[:100],
                content=m.content,
                source_meeting_id=m.source_meeting_id,
                relevance_score=0.6,
            ))

        # Search knowledge graph
        for n in self.knowledge.search(query):
            results.append(SearchResult(
                result_type="entity",
                title=n.name,
                content=n.description or n.name,
                relevance_score=0.5,
            ))

        return SearchResponse(
            query=query,
            results=results[:10],
            total_results=len(results),
            summary=f"Found {len(results)} results for '{query}'",
        )
