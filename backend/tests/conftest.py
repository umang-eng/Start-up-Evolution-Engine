from typing import Any
import asyncio
from collections.abc import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from backend.app.main import app
from backend.cache.redis import redis_manager
from backend.database.session import get_db
from backend.database.base import Base

# Compile PostgreSQL JSONB type to SQLite JSON type during unit tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

# Async SQLite engine for database-related unit testing in-memory
TEST_SQLITE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_SQLITE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class MockPubSub:
    """Mock Redis PubSub instance."""
    async def subscribe(self, *args, **kwargs) -> None:
        pass

    async def get_message(self, *args, **kwargs) -> dict | None:
        await asyncio.sleep(0.05)
        return None

    async def unsubscribe(self, *args, **kwargs) -> None:
        pass

    async def close(self) -> None:
        pass


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
        return 1

    def pubsub(self) -> MockPubSub:
        return MockPubSub()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Overrides pytest event loop to use session scope lifecycle."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Initializes tables in in-memory test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
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


@pytest.fixture(autouse=True)
def mock_gemini_adapter() -> Generator[None, None, None]:
    """Mocks the LLM adapter methods to avoid external API dependencies in tests."""
    from unittest.mock import AsyncMock, patch
    
    with patch("backend.ai.gemini.gemini_adapter.generate_text", new_callable=AsyncMock) as mock_text, \
         patch("backend.ai.gemini.gemini_adapter.generate", new_callable=AsyncMock) as mock_structured:
        
        # Default mock responses
        mock_text.return_value = (
            "Fitness app targeting busy professionals with personalized workouts "
            "and a premium monthly subscription model."
        )
        yield


