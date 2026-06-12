from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.security import hash_password
from backend.models.user import User
from backend.repositories.base import BaseRepository
from backend.schemas.user import UserCreate


class UserRepository(BaseRepository[User]):
    """Repository managing user account table transactions."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Fetch user by unique email address."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a user with an Argon2id hashed password."""
        hashed = hash_password(obj_in.password)
        db_obj = User(
            email=obj_in.email,
            hashed_password=hashed,
            role="USER",
            is_active=True
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


user_repository = UserRepository()
