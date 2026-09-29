"""Startup Memory Engine — extracts, stores, and retrieves startup knowledge.

Maintains persistent memory across all meetings. Detects contradictions,
repeated discussions, forgotten decisions, and changed priorities.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from backend.modules.memory.types import (
    MemoryEntry, MemoryType, StartupMemory, MemoryCluster, MemoryDiff,
    AffectedComponent,
)
from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


MEMORY_EXTRACTION_PROMPT = """You are a Startup Memory Engineer. Extract ALL important information from this meeting transcript.

## Meeting Context
- Meeting ID: {meeting_id}
- Title: {title}
- Date: {date}
- Participants: {participants}

## Previous Startup Memory
{previous_memory_summary}

## Transcript
{transcript}

## Extract the following (output as JSON array):

For EACH important item, extract:
1. memory_type: one of [decision, assumption, hypothesis, rejected_idea, pivot, priority, deadline, assigned_owner, unresolved_question, risk, opportunity, fact, commitment, concern, idea, lesson]
2. content: clear description of the item
3. category: business area (pricing, features, hiring, roadmap, funding, marketing, technical, legal, operations, strategy)
4. confidence: 0.0-1.0 based on how clearly it was stated
5. source_transcript_refs: specific quotes or timestamps that support this
6. affected_modules: which pipeline stages this affects (dna, features, roadmap, team, swot, cost, blueprint, competitive_moat, stress_test, financial_intelligence, investment_committee, product_execution, global_expansion)
7. related_topics: other topics this relates to

## Important Rules:
- Extract EVERY decision, even minor ones
- Capture ALL rejected ideas (what was considered and dismissed)
- Note ALL assumptions (things taken as true without proof)
- Capture ALL action items and commitments
- Note ANY contradictions with previous memory
- Capture ALL risks and concerns mentioned
- Note ANY pivots or direction changes

Return as JSON array of memory entry objects."""

CONTRADICTION_DETECTION_PROMPT = """You are a Contradiction Detector for startup knowledge.

## New Memory Entries
{new_entries}

## Existing Memory
{existing_entries}

## Detect:
1. Direct contradictions (A says X, B says not-X)
2. Changed assumptions (previously assumed Y, now assuming Z)
3. Forgotten decisions (decided X before, now discussing X again as if new)
4. Repeated discussions (same topic discussed multiple times without resolution)
5. Changed priorities (priority X was high, now mentioned as low)
6. Abandoned features (feature was planned, now dropped without explicit decision)

For each detected issue:
- type: contradiction/forgotten_decision/repeated_discussion/changed_priority/abandoned_feature
- description: what was detected
- old_entry_id: the original memory entry ID
- new_entry_id: the new conflicting entry ID (if applicable)
- severity: low/medium/high
- recommendation: what to do about it

Return as JSON array."""

MEMORY_SUMMARY_PROMPT = """Summarize the current startup memory state:

## All Memory Entries
{all_entries}

## Group into clusters by topic and provide:
1. Topic name
2. Key decisions made
3. Current status (active/resolved/superseded/abandoned)
4. Any contradictions or unresolved items
5. Most recent update

Return as JSON array of cluster objects with fields: topic, summary, status, entry_ids, contradictions_count"""


class MemoryEngine:
    """Extracts, stores, and manages startup memory across all meetings."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.memory = StartupMemory(project_id=project_id)

    async def process_meeting(
        self,
        meeting_id: str,
        title: str,
        date: str,
        participants: list[str],
        transcript: str,
        previous_memory: StartupMemory | None = None,
    ) -> MemoryDiff:
        """Process a meeting transcript and extract startup memory."""
        previous_memory = previous_memory or self.memory

        # Extract memory entries from transcript
        new_entries = await self._extract_memory(
            meeting_id, title, date, participants, transcript, previous_memory
        )

        # Detect contradictions and issues
        issues = await self._detect_issues(new_entries, previous_memory)

        # Apply changes to memory
        diff = self._apply_changes(new_entries, issues, meeting_id)

        # Update clusters
        self.memory.entries.extend(new_entries)
        self.memory.total_meetings_processed += 1
        self.memory.last_meeting_id = meeting_id
        self.memory.last_updated = datetime.now(timezone.utc).isoformat()

        # Mark superseded entries
        for entry in new_entries:
            if entry.superseded_by:
                for existing in self.memory.entries:
                    if existing.id == entry.superseded_by:
                        existing.is_active = False
                        existing.superseded_by = entry.id

        return diff

    async def _extract_memory(
        self,
        meeting_id: str,
        title: str,
        date: str,
        participants: list[str],
        transcript: str,
        previous_memory: StartupMemory,
    ) -> list[MemoryEntry]:
        """Extract memory entries from transcript using LLM."""
        previous_summary = self._summarize_previous_memory(previous_memory)

        prompt = MEMORY_EXTRACTION_PROMPT.format(
            meeting_id=meeting_id,
            title=title,
            date=date,
            participants=", ".join(participants),
            previous_memory_summary=previous_summary,
            transcript=transcript[:8000],  # Limit for token budget
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=list[dict[str, Any]],
                system_instruction="You extract structured startup knowledge from meeting transcripts.",
            )
            entries = []
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        entries.append(MemoryEntry(
                            memory_type=MemoryType(item.get("memory_type", "fact")),
                            content=item.get("content", ""),
                            category=item.get("category", "general"),
                            confidence=float(item.get("confidence", 0.8)),
                            source_meeting_id=meeting_id,
                            source_transcript_refs=item.get("source_transcript_refs", []),
                            affected_modules=item.get("affected_modules", []),
                            related_entries=item.get("related_entry_ids", []),
                        ))
            return entries
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []

    async def _detect_issues(
        self,
        new_entries: list[MemoryEntry],
        previous_memory: StartupMemory,
    ) -> list[dict[str, Any]]:
        """Detect contradictions, repeated discussions, and other issues."""
        if not previous_memory.entries:
            return []

        new_entries_text = "\n".join(
            f"- [{e.memory_type.value}] {e.content}" for e in new_entries[:20]
        )
        existing_text = "\n".join(
            f"- [{e.id}] [{e.memory_type.value}] {e.content[:100]}"
            for e in previous_memory.entries[-30:]
        )

        prompt = CONTRADICTION_DETECTION_PROMPT.format(
            new_entries=new_entries_text,
            existing_entries=existing_text,
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=list[dict[str, Any]],
                system_instruction="You detect contradictions and issues in startup knowledge.",
            )
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def _apply_changes(
        self,
        new_entries: list[MemoryEntry],
        issues: list[dict[str, Any]],
        meeting_id: str,
    ) -> MemoryDiff:
        """Apply extracted entries and issues to memory, return diff."""
        affected_modules: set[str] = set()
        contradictions: list[str] = []
        repeated: list[str] = []
        forgotten: list[str] = []
        changed: list[str] = []

        for issue in issues:
            issue_type = issue.get("type", "")
            desc = issue.get("description", "")
            if issue_type == "contradiction":
                contradictions.append(desc)
            elif issue_type == "repeated_discussion":
                repeated.append(desc)
            elif issue_type == "forgotten_decision":
                forgotten.append(desc)
            elif issue_type == "changed_priority":
                changed.append(desc)

        for entry in new_entries:
            for mod in entry.affected_modules:
                affected_modules.add(mod)

        return MemoryDiff(
            new_entries=new_entries,
            contradictions=contradictions,
            repeated_discussions=repeated,
            forgotten_decisions=forgotten,
            changed_priorities=changed,
            affected_modules=list(affected_modules),
            summary=f"Extracted {len(new_entries)} memories, detected {len(contradictions)} contradictions, {len(repeated)} repeated discussions",
        )

    def _summarize_previous_memory(self, memory: StartupMemory) -> str:
        """Create a summary of existing memory for context."""
        if not memory.entries:
            return "No previous memory."

        by_type: dict[str, list[str]] = {}
        for entry in memory.entries[-50:]:  # Last 50 entries
            t = entry.memory_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(f"  - {entry.content[:80]}")

        parts = []
        for t, items in by_type.items():
            parts.append(f"\n{t.upper()} ({len(items)}):")
            parts.extend(items[:5])

        return "\n".join(parts)

    def get_active_entries(self, memory_type: MemoryType | None = None) -> list[MemoryEntry]:
        """Get all active memory entries, optionally filtered by type."""
        entries = [e for e in self.memory.entries if e.is_active]
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        return entries

    def get_entries_by_category(self, category: str) -> list[MemoryEntry]:
        """Get all active entries for a category."""
        return [e for e in self.memory.entries if e.is_active and e.category == category]

    def get_recent_entries(self, limit: int = 20) -> list[MemoryEntry]:
        """Get the most recent memory entries."""
        return sorted(
            [e for e in self.memory.entries if e.is_active],
            key=lambda e: e.timestamp,
            reverse=True,
        )[:limit]

    def search(self, query: str) -> list[MemoryEntry]:
        """Simple keyword search across memory entries."""
        query_lower = query.lower()
        return [
            e for e in self.memory.entries
            if e.is_active and query_lower in e.content.lower()
        ]

    def get_contradictions(self) -> list[dict[str, Any]]:
        """Get all detected contradictions."""
        return [
            {"id": e.id, "content": e.content, "contradicts": e.contradictions}
            for e in self.memory.entries
            if e.is_active and e.contradictions
        ]
