import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import EntityNotFoundError, AuthorizationError
from backend.models.project import Project
from backend.repositories.project import project_repository, ProjectRepository
from backend.schemas.project import ProjectCreate
from backend.services.base import BaseService


class ProjectService(BaseService[Project, ProjectRepository]):
    """Service layer managing workspace project lifecycles and tenancy validations."""

    def __init__(self) -> None:
        super().__init__(project_repository)

    async def create_user_project(
        self, db: AsyncSession, *, user_id: uuid.UUID, obj_in: ProjectCreate
    ) -> Project:
        """Create a new project workspace mapped to the owner user ID."""
        data = obj_in.model_dump()
        data["user_id"] = user_id
        return await self.repository.create(db, obj_in=data)

    async def get_user_project(
        self, db: AsyncSession, *, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> Project:
        """Retrieve a specific project workspace, validating ownership."""
        project = await self.repository.get(db, project_id)
        if not project:
            raise EntityNotFoundError("Project workspace not found")
        
        # Verify tenant scope isolation
        if project.user_id != user_id:
            raise AuthorizationError("Access denied. You do not own this project workspace.")

        return project

    async def list_user_projects(
        self, db: AsyncSession, *, user_id: uuid.UUID, offset: int = 0, limit: int = 100
    ) -> list[Project]:
        """List project workspaces belonging to the active user."""
        return await self.repository.get_multi_by_user(db, user_id=user_id, offset=offset, limit=limit)

    async def delete_user_project(
        self, db: AsyncSession, *, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> Project:
        """Delete a project workspace after validating user permissions."""
        project = await self.get_user_project(db, project_id=project_id, user_id=user_id)
        return await self.repository.remove(db, id=project.id)


project_service = ProjectService()
