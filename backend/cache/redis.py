from typing import Any
import redis.asyncio as aioredis
from backend.core.config import settings
from backend.core.logging import logger


class RedisManager:
    """Manages active connection pools and commands for Redis caching & Pub/Sub."""
    
    def __init__(self) -> None:
        self.client: aioredis.Redis | None = None

    def initialize(self) -> None:
        """Initialize connection pool client."""
        logger.info("Initializing Redis async connection pool...", extra_data={"url": settings.REDIS_URL})
        self.client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50  # Connection capacity settings
        )

    async def close(self) -> None:
        """Close connection pool pool."""
        if self.client:
            logger.info("Closing Redis connection pool...")
            await self.client.close()

    async def is_healthy(self) -> bool:
        """Check Redis connectivity."""
        if not self.client:
            return False
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error("Redis health check failed", extra_data={"error": str(e)})
            return False

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        if not self.client:
            raise RuntimeError("Redis Client not initialized")
        return await self.client.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """Set value in cache with optional TTL expiration."""
        if not self.client:
            raise RuntimeError("Redis Client not initialized")
        return await self.client.set(key, str(value), ex=ex)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        if not self.client:
            raise RuntimeError("Redis Client not initialized")
        return await self.client.delete(key)

    async def publish(self, channel: str, message: str) -> int:
        """Publish event message to a channel."""
        if not self.client:
            raise RuntimeError("Redis Client not initialized")
        return await self.client.publish(channel, message)


redis_manager = RedisManager()
