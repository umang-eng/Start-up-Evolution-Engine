from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.exceptions import AuthenticationError, ConflictError
from backend.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from backend.models.user import User
from backend.repositories.user import user_repository, UserRepository
from backend.schemas.user import UserCreate, UserLogin, Token
from backend.services.base import BaseService


class UserService(BaseService[User, UserRepository]):
    """Service layer managing user registrations, token lifecycle, and authentication."""

    def __init__(self) -> None:
        super().__init__(user_repository)

    async def register_user(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Register a new user, ensuring email uniqueness."""
        existing = await self.repository.get_by_email(db, email=obj_in.email)
        if existing:
            raise ConflictError("An account with this email address already exists")
        return await self.repository.create_user(db, obj_in=obj_in)

    async def authenticate_user(self, db: AsyncSession, *, obj_in: UserLogin) -> User:
        """Authenticate credentials and return the active User entity."""
        user = await self.repository.get_by_email(db, email=obj_in.email)
        if not user:
            raise AuthenticationError("Incorrect email or password")
        
        if not verify_password(obj_in.password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")

        if not user.is_active:
            raise AuthenticationError("Your user account has been disabled")

        return user

    def generate_user_tokens(self, user: User) -> Token:
        """Issue access and refresh token pair for a user."""
        claims = {"sub": str(user.id), "role": user.role}
        access = create_access_token(claims)
        refresh = create_refresh_token(claims)
        return Token(access_token=access, refresh_token=refresh)

    async def refresh_user_session(self, db: AsyncSession, *, refresh_token: str) -> Token:
        """Validate refresh token and issue a new token pair."""
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token subject payload")
        except Exception as e:
            raise AuthenticationError(f"Session expired or token is invalid: {str(e)}")

        user = await self.repository.get(db, id=user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User session is invalid or inactive")

        return self.generate_user_tokens(user)


user_service = UserService()
