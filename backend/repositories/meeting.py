from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.meeting import Meeting, Transcript, MeetingReport
from backend.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    """Repository managing meeting session transactions."""

    def __init__(self) -> None:
        super().__init__(Meeting)

    async def get_with_relations(self, db: AsyncSession, meeting_id) -> Meeting | None:
        """Fetch meeting with transcript and report eagerly loaded."""
        stmt = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(
                selectinload(Meeting.transcript),
                selectinload(Meeting.report),
                selectinload(Meeting.segments),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_user_meetings(
        self, db: AsyncSession, *, user_id, offset: int = 0, limit: int = 50
    ) -> list[Meeting]:
        """Fetch all meetings for a user, newest first."""
        stmt = (
            select(Meeting)
            .where(Meeting.user_id == user_id)
            .order_by(Meeting.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_by_meeting_and_user(
        self, db: AsyncSession, meeting_id, user_id
    ) -> Meeting | None:
        """Fetch a meeting ensuring user ownership."""
        stmt = (
            select(Meeting)
            .where(Meeting.id == meeting_id, Meeting.user_id == user_id)
            .options(
                selectinload(Meeting.transcript),
                selectinload(Meeting.report),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()


class TranscriptRepository(BaseRepository[Transcript]):
    """Repository managing transcript transactions."""

    def __init__(self) -> None:
        super().__init__(Transcript)

    async def get_by_meeting(self, db: AsyncSession, meeting_id) -> Transcript | None:
        stmt = select(Transcript).where(Transcript.meeting_id == meeting_id)
        return (await db.execute(stmt)).scalar_one_or_none()


class MeetingReportRepository(BaseRepository[MeetingReport]):
    """Repository managing meeting report transactions."""

    def __init__(self) -> None:
        super().__init__(MeetingReport)

    async def get_by_meeting(self, db: AsyncSession, meeting_id) -> MeetingReport | None:
        stmt = select(MeetingReport).where(MeetingReport.meeting_id == meeting_id)
        return (await db.execute(stmt)).scalar_one_or_none()


meeting_repository = MeetingRepository()
transcript_repository = TranscriptRepository()
meeting_report_repository = MeetingReportRepository()
