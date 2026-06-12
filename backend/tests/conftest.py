import asyncio
from collections.abc import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.main import app
from backend.cache.redis import redis_manager
from backend.database.session import get_db
from backend.models.base import Base

# Async SQLite engine for database-related unit testing in-memory
TEST_SQLITE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_SQLITE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class MockRedis:
    """Mock Redis client simulating Redis connection manager functions."""
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def is_healthy(self) -> bool:
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
        return 1
from typing import Any


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Overrides pytest event loop to use session scope lifecycle."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Initializes tables in in-memory test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields clean transaction-scoped database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(autouse=True)
def override_redis() -> Generator[None, None, None]:
    """Replaces global Redis client connection with local memory mock."""
    mock_redis = MockRedis()
    original_redis = redis_manager.client
    redis_manager.client = mock_redis  # type: ignore
    yield
    redis_manager.client = original_redis


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Injects client sessions with database overrides."""
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    
    # Use HTTPX ASGITransport to test app routes locally
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
        
    app.dependency_overrides.clear()
