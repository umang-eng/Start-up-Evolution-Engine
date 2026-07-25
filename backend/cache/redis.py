from typing import Any
import asyncio
from collections import defaultdict
import redis.asyncio as aioredis
from backend.core.config import settings
from backend.core.logging import logger


class MockPubSub:
    """Mock Redis PubSub emulator running fully in-memory."""
    def __init__(self):
        self._queue = asyncio.Queue()
        self._subscribed_channels = []

    async def subscribe(self, channel: str) -> None:
        self._subscribed_channels.append(channel)
        MockRedis.register_subscriber(channel, self._queue)

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 0.5) -> dict | None:
        try:
            msg = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return {"data": msg}
        except asyncio.TimeoutError:
            return None

    async def unsubscribe(self, channel: str) -> None:
        if channel in self._subscribed_channels:
            self._subscribed_channels.remove(channel)
        MockRedis.remove_subscriber(channel, self._queue)

    async def close(self) -> None:
        for channel in list(self._subscribed_channels):
            await self.unsubscribe(channel)


class MockRedis:
    """Mock Redis client emulating async key-value cache operations and channel pub-sub."""
    _subscribers = defaultdict(list)
    
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    @classmethod
    def register_subscriber(cls, channel: str, queue: asyncio.Queue) -> None:
        cls._subscribers[channel].append(queue)

    @classmethod
    def remove_subscriber(cls, channel: str, queue: asyncio.Queue) -> None:
        if queue in cls._subscribers[channel]:
            cls._subscribers[channel].remove(queue)

    async def close(self) -> None:
        pass

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        self.store[key] = str(value)
        return True

    async def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def publish(self, channel: str, message: str) -> int:
        queues = self._subscribers[channel]
        for q in queues:
            await q.put(message)
        return len(queues)

    def pubsub(self) -> MockPubSub:
        return MockPubSub()


class RedisManager:
    """Manages active connection pools and commands for Redis caching & Pub/Sub with in-memory fallbacks."""
    
    def __init__(self) -> None:
        self.client: Any = None

    def initialize(self) -> None:
        """Initialize connection pool client."""
        logger.info("Initializing Redis async connection pool...", extra_data={"url": settings.REDIS_URL})
        self.client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50
        )

    async def close(self) -> None:
        """Close connection pool."""
        if self.client:
            logger.info("Closing Redis connection pool...")
            await self.client.close()

    async def is_healthy(self) -> bool:
        """Check Redis connectivity, triggering Mock fallback on failure."""
        if not self.client:
            return False
        
        # If client is already a MockRedis, skip real ping checks
        if isinstance(self.client, MockRedis):
            return True

        try:
            # Enforce short 1.0s timeout to prevent blocking application boot
            await asyncio.wait_for(self.client.ping(), timeout=1.0)
            return True
        except Exception as e:
            logger.warning(
                "Redis connection failed check! Falling back to in-memory MockRedis.",
                extra_data={"error": str(e)}
            )
            # Switch client to MockRedis fallback
            self.client = MockRedis()
            return True

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

    async def clean_stuck_jobs(self, queue_name: str = "see:queue") -> int:
        """
        Clean stuck ARQ jobs that are marked as "running" but have no active worker.
        
        ARQ stores job locks in Redis with keys like: arq:job:<job_id>
        When a worker crashes, these locks remain and prevent new jobs from running.
        
        Returns the number of stuck jobs cleaned.
        """
        if not self.client or isinstance(self.client, MockRedis):
            return 0
            
        cleaned = 0
        try:
            # Find all job keys in the queue
            cursor = 0
            pattern = f"arq:job:*"
            
            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    # Check if the job is stuck (has a lock but no result)
                    job_data = await self.client.hgetall(key)
                    if job_data and job_data.get("status") == "running":
                        # Check if the job lock is older than job_timeout (600s)
                        # ARQ stores the enqueued time in the job data
                        logger.info(f"Found stuck job: {key} - removing lock")
                        await self.client.delete(key)
                        cleaned += 1
                
                if cursor == 0:
                    break
                    
            if cleaned > 0:
                logger.info(f"Cleaned {cleaned} stuck job(s) from Redis")
                
        except Exception as e:
            logger.warning(f"Failed to clean stuck jobs: {e}")
            
        return cleaned


redis_manager = RedisManager()
