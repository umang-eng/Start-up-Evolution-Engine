from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_token_payload
from backend.database.session import get_db
from backend.repositories.user import user_repository
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.schemas.user import UserCreate, UserLogin, UserResponse, Token
from backend.services.user import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate, 
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Register a new user account profile."""
    user = await user_service.register_user(db, obj_in=payload)
    return {
        "success": True,
        "data": UserResponse.model_validate(user),
        "metadata": APIResponseMetadata()
    }


@router.post("/login", response_model=BaseResponse[Token])
async def login(
    payload: UserLogin, 
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Authenticate credentials and issue JWT tokens."""
    user = await user_service.authenticate_user(db, obj_in=payload)
    tokens = user_service.generate_user_tokens(user)
    return {
        "success": True,
        "data": tokens,
        "metadata": APIResponseMetadata()
    }


@router.post("/refresh", response_model=BaseResponse[Token])
async def refresh_session(
    refresh_token: str, 
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Refresh active session and return a new JWT pair."""
    tokens = await user_service.refresh_user_session(db, refresh_token=refresh_token)
    return {
        "success": True,
        "data": tokens,
        "metadata": APIResponseMetadata()
    }


@router.get("/me", response_model=BaseResponse[UserResponse])
async def get_my_profile(
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve profile metadata for the authenticated user session."""
    user_id = claims.get("sub")
    user = await user_repository.get(db, id=user_id)
    return {
        "success": True,
        "data": UserResponse.model_validate(user),
        "metadata": APIResponseMetadata()
    }
