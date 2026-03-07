import asyncio
import pytest
import aiosqlite


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh in-memory (tmp) SQLite database for each test."""
    db_path = tmp_path / "test.db"
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    from database import SCHEMA
    await conn.executescript(SCHEMA)
    await conn.commit()
    yield conn
    await conn.close()
