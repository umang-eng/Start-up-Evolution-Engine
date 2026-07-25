"""Meeting Timeline — interactive company timeline from meeting discussions.

Includes major decisions, pivots, releases, hires, funding, pricing changes,
customer discoveries, roadmap updates, all linked to originating meetings.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):
    DECISION = "decision"
    PIVOT = "pivot"
    RELEASE = "release"
    HIRE = "hire"
    FUNDING = "funding"
    PRICING_CHANGE = "pricing_change"
    CUSTOMER_DISCOVERY = "customer_discovery"
    ROADMAP_UPDATE = "roadmap_update"
    PARTNERSHIP = "partnership"
    RISK_IDENTIFIED = "risk_identified"
    GOAL_SET = "goal_set"
    MILESTONE_REACHED = "milestone_reached"
    STRATEGY_CHANGE = "strategy_change"
    TEAM_CHANGE = "team_change"
    PRODUCT_UPDATE = "product_update"


class TimelineEvent(BaseModel):
    """A single event on the company timeline."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    event_type: TimelineEventType
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    date: str = Field(description="When this happened")
    meeting_id: str = Field(description="Which meeting this came from")
    meeting_title: str = Field(default="")
    importance: Literal["critical", "high", "medium", "low"] = Field(default="medium")
    affected_areas: list[str] = Field(default_factory=list)
    related_events: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CompanyTimeline(BaseModel):
    """Complete company timeline."""
    project_id: str
    events: list[TimelineEvent] = Field(default_factory=list)
    total_events: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


TIMELINE_EXTRACTION_PROMPT = """You are a Timeline Event Extractor. Extract all timeline-worthy events from this meeting.

## Meeting
- Title: {title}
- Date: {date}
- Participants: {participants}

## Previous Timeline Events
{previous_events}

## Transcript
{transcript}

## Extract events:

For EACH significant event:
1. event_type: decision/pivot/release/hire/funding/pricing_change/customer_discovery/roadmap_update/partnership/risk_identified/goal_set/milestone_reached/strategy_change/team_change/product_update
2. title: concise event title
3. description: what happened
4. date: when (from transcript context)
5. importance: critical/high/medium/low
6. affected_areas: which parts of the business

## Rules:
- Only extract events that matter for the company's history
- Include all decisions and pivots
- Include all hires and team changes
- Include all funding-related events
- Include all product milestones
- Link related events

Return as JSON array of TimelineEvent objects."""


class TimelineEngine:
    """Builds and manages the company timeline."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.timeline = CompanyTimeline(project_id=project_id)

    async def extract_events(
        self,
        meeting_id: str,
        title: str,
        date: str,
        participants: list[str],
        transcript: str,
    ) -> list[TimelineEvent]:
        """Extract timeline events from a meeting."""
        previous = self._format_previous_events()

        prompt = TIMELINE_EXTRACTION_PROMPT.format(
            title=title,
            date=date,
            participants=", ".join(participants),
            previous_events=previous,
            transcript=transcript[:6000],
        )

        try:
            result = await __import__("backend.ai.gemini", fromlist=["gemini_adapter"]).gemini_adapter.generate(
                prompt=prompt,
                schema=list[dict[str, Any]],
                system_instruction="You extract timeline-worthy events from meeting transcripts.",
            )

            events = []
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        event = TimelineEvent(
                            event_type=TimelineEventType(item.get("event_type", "decision")),
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            date=item.get("date", date),
                            meeting_id=meeting_id,
                            meeting_title=title,
                            importance=item.get("importance", "medium"),
                            affected_areas=item.get("affected_areas", []),
                        )
                        events.append(event)

            self.timeline.events.extend(events)
            self.timeline.total_events = len(self.timeline.events)
            self.timeline.last_updated = datetime.now(timezone.utc).isoformat()

            return events

        except Exception:
            return []

    def _format_previous_events(self) -> str:
        """Format previous events for context."""
        if not self.timeline.events:
            return "No previous events."

        recent = sorted(self.timeline.events, key=lambda e: e.date, reverse=True)[:10]
        parts = []
        for e in recent:
            parts.append(f"- [{e.date}] [{e.event_type.value}] {e.title}")
        return "\n".join(parts)

    def get_by_type(self, event_type: TimelineEventType) -> list[TimelineEvent]:
        """Get events by type."""
        return [e for e in self.timeline.events if e.event_type == event_type]

    def get_by_importance(self, importance: str) -> list[TimelineEvent]:
        """Get events by importance."""
        return [e for e in self.timeline.events if e.importance == importance]

    def get_range(self, start_date: str, end_date: str) -> list[TimelineEvent]:
        """Get events in a date range."""
        return [
            e for e in self.timeline.events
            if start_date <= e.date <= end_date
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get timeline summary."""
        by_type: dict[str, int] = {}
        for e in self.timeline.events:
            by_type[e.event_type.value] = by_type.get(e.event_type.value, 0) + 1

        return {
            "total_events": self.timeline.total_events,
            "by_type": by_type,
            "latest_event": self.timeline.events[-1].title if self.timeline.events else None,
            "date_range": {
                "first": self.timeline.events[0].date if self.timeline.events else None,
                "last": self.timeline.events[-1].date if self.timeline.events else None,
            },
        }
