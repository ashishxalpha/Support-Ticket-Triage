"""
Database initialization script for development.

Creates all tables and runs seed data.
Run with: python -m app.init_db
"""

import asyncio
from app.core.database import init_db, engine, Base
import app.models  # noqa: F401 — load all models for metadata


async def setup():
    """Create pgvector extension and all tables."""
    await init_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    asyncio.run(setup())
