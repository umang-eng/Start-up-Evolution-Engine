import asyncio
from backend.database.session import async_session
from sqlalchemy import text
async def main():
    async with async_session() as db:
        result = await db.execute(text("SELECT id FROM projects LIMIT 1"))
        print(result.scalar())
asyncio.run(main())
