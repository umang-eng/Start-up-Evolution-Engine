from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from backend.core.config import settings
from backend.core.logging import logger

# Compile PostgreSQL JSONB type to SQLite JSON type during fallback
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

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


async def verify_db_connectivity() -> None:
    """Verifies database connectivity at startup, falling back to SQLite if PostgreSQL is unreachable."""
    global engine, AsyncSessionLocal
    
    logger.info("Verifying database connectivity...")
    try:
        # Try running a select 1 check on active connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully (PostgreSQL).")
    except Exception as e:
        logger.warning(
            "PostgreSQL database connection check failed! Falling back to local SQLite database: dev_fallback.db",
            exc_info=e
        )
        # Recreate engine and configure sessionmaker with local SQLite file
        sqlite_url = "sqlite+aiosqlite:///dev_fallback.db"
        engine = create_async_engine(
            sqlite_url,
            echo=False
        )
        AsyncSessionLocal.configure(bind=engine)
        
        # Initialize tables in fallback SQLite database automatically
        from backend.database.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite fallback database initialized and verified successfully.")


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
