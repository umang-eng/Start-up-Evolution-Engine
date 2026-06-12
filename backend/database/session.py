from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.core.config import settings
from backend.core.logging import logger

# Async DB Engine with optimized connection pooling parameters
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Prevent stale connections
    pool_size=20,         # Minimum persistent pool connections
    max_overflow=10       # Maximum temporary burst connections
)

# Async Session Maker instance
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding async transactional database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database transaction rolled back due to error", extra_data={"error": str(e)})
            await session.rollback()
            raise
        finally:
            await session.close()
