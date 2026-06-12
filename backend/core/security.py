from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.core.config import settings

# CryptContext using argon2 for Argon2id hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenError(Exception):
    """Base exception for Token validation errors."""
    pass


class TokenExpiredError(TokenError):
    """Exception raised when token is expired."""
    pass


class TokenInvalidError(TokenError):
    """Exception raised when token is invalid."""
    pass


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_jwt_token(
    claims: dict[str, Any], 
    expires_delta: timedelta, 
    token_type: str = "access"
) -> str:
    """Generate JWT payload containing target scopes."""
    to_encode = claims.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({
        "exp": expire,
        "type": token_type,
        "iat": datetime.now(timezone.utc)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_access_token(claims: dict[str, Any]) -> str:
    """Create a short-lived access token."""
    return create_jwt_token(
        claims=claims, 
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access"
    )


def create_refresh_token(claims: dict[str, Any]) -> str:
    """Create a long-lived refresh token."""
    return create_jwt_token(
        claims=claims, 
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh"
    )


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate claims of a JWT."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != expected_type:
            raise TokenInvalidError("Invalid token type scope")
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except JWTError as e:
        raise TokenInvalidError(f"Could not validate token: {str(e)}")
