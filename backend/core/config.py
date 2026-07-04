from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Start-up Evolution Engine"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    SERVICE_ROLE: Literal["api-gateway", "worker-engine"] = "api-gateway"

    # CORS — tighten in production via ALLOWED_ORIGINS env var
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Security — MUST be overridden in production via environment variable
    SECRET_KEY: str = "39fca85521b7c191a0c4f8263152d24269e8ef81d11ff31ff215443210ef8abc"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "startup_evolution"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # AI Configuration
    GEMINI_API_KEY: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "nemotron-3-super:cloud"

    # Real-Time Search (at least one provider required for live market grounding)
    TAVILY_API_KEY: str = ""
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure the secret key meets minimum entropy for production deployments."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        password_prefix = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_prefix}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def cors_origins(self) -> list[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
