import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Payload to register a new user account."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Payload to authenticate user credentials."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User profile data returned to client."""
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT response payload."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT claims payload model."""
    sub: str | None = None
    role: str = "USER"
    exp: int | None = None
