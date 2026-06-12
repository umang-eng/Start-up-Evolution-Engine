import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.project import Project
from backend.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository managing project workspace database transactions."""

    def __init__(self) -> None:
        super().__init__(Project)

    async def get_multi_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, offset: int = 0, limit: int = 100
    ) -> list[Project]:
        """Fetch multiple projects belonging to the target owner ID."""
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


project_repository = ProjectRepository()
