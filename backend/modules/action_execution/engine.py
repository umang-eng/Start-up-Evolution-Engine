"""Action Execution Engine — converts discussions into executable work.

Generates GitHub Issues, Jira Tasks, Sprint Tasks, Roadmap Updates,
Calendar Reminders, and Documentation Updates.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class TaskPlatform(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"
    INTERNAL = "internal"
    CALENDAR = "calendar"
    DOCUMENTATION = "documentation"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GeneratedTask(BaseModel):
    """A task generated from meeting discussions."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    platform: TaskPlatform
    owner: str = Field(description="Who is responsible")
    priority: TaskPriority
    deadline: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    estimated_effort: str = Field(default="", description="e.g., '2 hours', '3 days'")
    related_meeting_id: str
    category: str = Field(default="general")
    labels: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: Literal["created", "in_progress", "completed", "cancelled"] = "created"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionExtractionResult(BaseModel):
    """Result of extracting action items from a meeting."""
    tasks: list[GeneratedTask]
    total_tasks: int
    by_platform: dict[str, int]
    by_priority: dict[str, int]
    by_owner: dict[str, int]
    summary: str


ACTION_EXTRACTION_PROMPT = """You are an Action Item Extraction Expert. Extract ALL action items from this meeting.

## Meeting
- Title: {title}
- Date: {date}
- Participants: {participants}

## Transcript
{transcript}

## Extract EVERY action item as:

For EACH action:
1. title: clear, actionable title
2. description: detailed description of what needs to be done
3. platform: github/jira/linear/internal/calendar/documentation (where should this be created)
4. owner: who is responsible (use participant names)
5. priority: critical/high/medium/low
6. deadline: when it's due (if mentioned)
7. dependencies: what needs to happen first
8. estimated_effort: time estimate
9. category: features/infrastructure/marketing/finance/legal/hiring/operations/strategy
10. labels: relevant tags
11. acceptance_criteria: how to know it's done

## Rules:
- Extract EVERY action item, even small ones
- Assign specific owners (not "team" or "someone")
- Include realistic deadlines based on discussion
- Break down large items into specific tasks
- Include acceptance criteria for each task

Return valid ActionExtractionResult JSON."""


class ActionExecutionEngine:
    """Extracts and manages action items from meetings."""

    def __init__(self):
        self.all_tasks: list[GeneratedTask] = []

    async def extract_actions(
        self,
        meeting_id: str,
        title: str,
        date: str,
        participants: list[str],
        transcript: str,
    ) -> ActionExtractionResult:
        """Extract action items from a meeting transcript."""
        prompt = ACTION_EXTRACTION_PROMPT.format(
            title=title,
            date=date,
            participants=", ".join(participants),
            transcript=transcript[:6000],
        )

        try:
            result = await __import__("backend.ai.gemini", fromlist=["gemini_adapter"]).gemini_adapter.generate(
                prompt=prompt,
                schema=ActionExtractionResult,
                system_instruction="You extract actionable tasks from meeting transcripts.",
            )

            if isinstance(result, ActionExtractionResult):
                for task in result.tasks:
                    task.related_meeting_id = meeting_id
                self.all_tasks.extend(result.tasks)
                return result

        except Exception as e:
            pass

        return ActionExtractionResult(
            tasks=[],
            total_tasks=0,
            by_platform={},
            by_priority={},
            by_owner={},
            summary="Action extraction unavailable",
        )

    def get_by_platform(self, platform: TaskPlatform) -> list[GeneratedTask]:
        """Get tasks by platform."""
        return [t for t in self.all_tasks if t.platform == platform]

    def get_by_owner(self, owner: str) -> list[GeneratedTask]:
        """Get tasks by owner."""
        return [t for t in self.all_tasks if t.owner.lower() == owner.lower()]

    def get_by_priority(self, priority: TaskPriority) -> list[GeneratedTask]:
        """Get tasks by priority."""
        return [t for t in self.all_tasks if t.priority == priority]

    def get_overdue(self) -> list[GeneratedTask]:
        """Get tasks past their deadline."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            t for t in self.all_tasks
            if t.deadline and t.deadline < now and t.status != "completed"
        ]

    def get_pending(self) -> list[GeneratedTask]:
        """Get tasks not yet completed."""
        return [t for t in self.all_tasks if t.status in ("created", "in_progress")]

    def to_github_issue(self, task: GeneratedTask) -> dict[str, Any]:
        """Convert task to GitHub Issue format."""
        return {
            "title": task.title,
            "body": f"{task.description}\n\n**Owner:** {task.owner}\n**Deadline:** {task.deadline}\n**Effort:** {task.estimated_effort}",
            "labels": task.labels + [task.priority.value],
            "assignees": [task.owner],
        }

    def to_jira_task(self, task: GeneratedTask) -> dict[str, Any]:
        """Convert task to Jira format."""
        return {
            "fields": {
                "summary": task.title,
                "description": task.description,
                "issuetype": {"name": "Task"},
                "priority": {"name": task.priority.value.upper()},
                "assignee": {"displayName": task.owner},
                "labels": task.labels,
                "duedate": task.deadline,
            }
        }

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all tasks."""
        by_platform: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        by_owner: dict[str, int] = {}
        by_status: dict[str, int] = {}

        for task in self.all_tasks:
            by_platform[task.platform.value] = by_platform.get(task.platform.value, 0) + 1
            by_priority[task.priority.value] = by_priority.get(task.priority.value, 0) + 1
            by_owner[task.owner] = by_owner.get(task.owner, 0) + 1
            by_status[task.status] = by_status.get(task.status, 0) + 1

        return {
            "total": len(self.all_tasks),
            "by_platform": by_platform,
            "by_priority": by_priority,
            "by_owner": by_owner,
            "by_status": by_status,
            "pending": len(self.get_pending()),
            "overdue": len(self.get_overdue()),
        }
