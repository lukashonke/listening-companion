"""Tests for sessions pagination: offset/limit params, total count, edge cases."""
import time

import pytest
import aiosqlite
from unittest.mock import patch

from database import SCHEMA
from config import Settings


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh SQLite database for each test."""
    db_path = tmp_path / "test.db"
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture
async def db_with_sessions(db):
    """Database with 5 test sessions inserted (newest first by created_at)."""
    base_time = 1700000000.0
    for i in range(5):
        await db.execute(
            "INSERT INTO sessions (id, name, created_at, config) VALUES (?, ?, ?, ?)",
            (f"sess_{i}", f"Session {i}", base_time + i * 100, "{}"),
        )
    await db.commit()
    return db


class TestSessionsPagination:
    """Test GET /api/sessions with offset/limit pagination."""

    async def test_default_pagination(self, db_with_sessions):
        """Default call returns {sessions: [...], total: N} with all sessions (under limit)."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions")

        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["sessions"]) == 5

    async def test_pagination_with_limit(self, db_with_sessions):
        """Limit restricts the number of returned sessions."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?limit=2")

        data = resp.json()
        assert len(data["sessions"]) == 2
        assert data["total"] == 5

    async def test_pagination_with_offset(self, db_with_sessions):
        """Offset skips sessions."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?offset=3&limit=10")

        data = resp.json()
        assert len(data["sessions"]) == 2  # 5 total, skip 3 => 2 remaining
        assert data["total"] == 5

    async def test_pagination_offset_and_limit(self, db_with_sessions):
        """Offset + limit work together; different pages have different sessions."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp1 = await client.get("/api/sessions?offset=0&limit=2")
                resp2 = await client.get("/api/sessions?offset=2&limit=2")

        page1 = resp1.json()
        page2 = resp2.json()
        assert len(page1["sessions"]) == 2
        assert len(page2["sessions"]) == 2
        # Pages should have different sessions
        ids1 = {s["id"] for s in page1["sessions"]}
        ids2 = {s["id"] for s in page2["sessions"]}
        assert ids1.isdisjoint(ids2)

    async def test_pagination_out_of_range_offset(self, db_with_sessions):
        """Offset beyond total returns empty sessions array but correct total."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?offset=100&limit=20")

        data = resp.json()
        assert len(data["sessions"]) == 0
        assert data["total"] == 5

    async def test_pagination_zero_offset(self, db_with_sessions):
        """Explicit offset=0 returns the first page."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?offset=0&limit=20")

        data = resp.json()
        assert data["total"] == 5
        assert len(data["sessions"]) == 5

    async def test_pagination_empty_database(self, db):
        """No sessions at all returns empty list and total 0."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions")

        data = resp.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    async def test_sessions_ordered_by_created_at_desc(self, db_with_sessions):
        """Sessions are ordered newest first (DESC by created_at)."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?offset=0&limit=5")

        data = resp.json()
        timestamps = [s["created_at"] for s in data["sessions"]]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_total_count_independent_of_limit(self, db_with_sessions):
        """Total reflects actual count regardless of limit."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?limit=1")

        data = resp.json()
        assert len(data["sessions"]) == 1
        assert data["total"] == 5
