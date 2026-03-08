"""Cross-area integration tests: verify features work together correctly.

Tests verify:
- Auto-named sessions appear correctly in paginated sessions list
- Config settings (auto-summarization interval) are accepted by backend
- Images persist and appear in session detail after session ends
- Session detail returns summary for past sessions
- Name source flows through the full API lifecycle
"""
import time

import pytest
import aiosqlite
from unittest.mock import patch

from database import SCHEMA
from models import SessionConfig


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
async def db_with_mixed_sessions(db):
    """Database with sessions having different name_source values and summaries."""
    base_time = 1700000000.0
    sessions = [
        ("sess_default", "New Session", "default", "", base_time),
        ("sess_auto1", "Music Theory Discussion", "auto", "Summary of music theory chat.", base_time + 100),
        ("sess_auto2", "Project Planning", "auto", "Team discussed project milestones.", base_time + 200),
        ("sess_user", "My Important Meeting", "user", "", base_time + 300),
        ("sess_auto3", "Code Review Session", "auto", "Reviewed PR #42 with the team.", base_time + 400),
    ]
    for sid, name, ns, summary, ts in sessions:
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, ended_at, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, name, ns, summary, ts, ts + 3600, "{}"),
        )
    await db.commit()
    return db


@pytest.fixture
async def db_with_images(db):
    """Database with a session that has images."""
    ts = time.time()
    await db.execute(
        "INSERT INTO sessions (id, name, name_source, summary, created_at, ended_at, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("sess_img", "Image Session", "auto", "Session with generated images.", ts, ts + 3600, "{}"),
    )
    await db.execute(
        "INSERT INTO images (id, session_id, filename, prompt, style, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("img_001", "sess_img", "abc123.png", "A beautiful sunset", "realistic", "gemini", ts + 60),
    )
    await db.execute(
        "INSERT INTO images (id, session_id, filename, prompt, style, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("img_002", "sess_img", "def456.png", "A mountain landscape", "watercolor", "gemini", ts + 120),
    )
    await db.commit()
    return db


class TestAutoNamedSessionsInPaginatedList:
    """Verify auto-generated names appear correctly in the paginated sessions list."""

    async def test_auto_named_sessions_have_names_in_list(self, db_with_mixed_sessions):
        """GET /api/sessions returns auto-generated names correctly."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions?offset=0&limit=20")

        data = resp.json()
        assert data["total"] == 5

        # All sessions should have names
        sessions_by_id = {s["id"]: s for s in data["sessions"]}

        # Auto-named sessions should have their inferred names
        assert sessions_by_id["sess_auto1"]["name"] == "Music Theory Discussion"
        assert sessions_by_id["sess_auto2"]["name"] == "Project Planning"
        assert sessions_by_id["sess_auto3"]["name"] == "Code Review Session"

        # Name source should be preserved
        assert sessions_by_id["sess_auto1"]["name_source"] == "auto"
        assert sessions_by_id["sess_user"]["name_source"] == "user"
        assert sessions_by_id["sess_default"]["name_source"] == "default"

    async def test_pagination_preserves_auto_names(self, db_with_mixed_sessions):
        """Pagination does not lose auto-generated names across pages."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp1 = await client.get("/api/sessions?offset=0&limit=2")
                resp2 = await client.get("/api/sessions?offset=2&limit=2")
                resp3 = await client.get("/api/sessions?offset=4&limit=2")

        page1 = resp1.json()
        page2 = resp2.json()
        page3 = resp3.json()

        # All pages should report correct total
        assert page1["total"] == 5
        assert page2["total"] == 5
        assert page3["total"] == 5

        # Collect all sessions across pages
        all_sessions = page1["sessions"] + page2["sessions"] + page3["sessions"]
        assert len(all_sessions) == 5

        # All auto-named sessions should have their names intact
        auto_sessions = [s for s in all_sessions if s["name_source"] == "auto"]
        assert len(auto_sessions) == 3
        auto_names = {s["name"] for s in auto_sessions}
        assert auto_names == {"Music Theory Discussion", "Project Planning", "Code Review Session"}


class TestConfigAffectsLiveBehavior:
    """Verify that config settings are accepted and stored correctly."""

    async def test_session_config_accepts_auto_summarization_interval(self):
        """SessionConfig model accepts custom auto_summarization_interval."""
        config = SessionConfig(auto_summarization_interval=60)
        assert config.auto_summarization_interval == 60

    async def test_session_config_accepts_all_background_settings(self):
        """SessionConfig model accepts all background AI feature settings."""
        config = SessionConfig(
            auto_naming_enabled=False,
            auto_naming_first_trigger=10,
            auto_naming_repeat_interval=20,
            auto_summarization_enabled=True,
            auto_summarization_interval=120,
            auto_summarization_max_transcript_length=25000,
        )
        assert config.auto_naming_enabled is False
        assert config.auto_naming_first_trigger == 10
        assert config.auto_naming_repeat_interval == 20
        assert config.auto_summarization_enabled is True
        assert config.auto_summarization_interval == 120
        assert config.auto_summarization_max_transcript_length == 25000

    async def test_session_config_stored_in_session(self, db):
        """When a session is created, its config is stored in the database."""
        config = SessionConfig(auto_summarization_interval=60)
        config_json = config.model_dump_json()

        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            ("sess_cfg", "Test Session", "default", time.time(), config_json),
        )
        await db.commit()

        async with db.execute("SELECT config FROM sessions WHERE id = ?", ("sess_cfg",)) as cur:
            row = await cur.fetchone()

        import json
        stored_config = json.loads(row[0])
        assert stored_config["auto_summarization_interval"] == 60


class TestEndToEndImagePersistence:
    """Verify images persist and are accessible in session detail (VAL-CROSS-001)."""

    async def test_session_detail_includes_images(self, db_with_images):
        """GET /api/sessions/{id}/images returns persisted images."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_images):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_img/images")

        assert resp.status_code == 200
        images = resp.json()
        assert len(images) == 2

        # Images should have persistent URLs
        assert images[0]["url"] == "/api/images/abc123.png"
        assert images[1]["url"] == "/api/images/def456.png"

        # Images should have metadata
        assert images[0]["prompt"] == "A beautiful sunset"
        assert images[1]["prompt"] == "A mountain landscape"

    async def test_session_detail_with_summary_and_images(self, db_with_images):
        """GET /api/sessions/{id} returns session with summary. Images are separate endpoint."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_images):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_img")

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Image Session"
        assert data["summary"] == "Session with generated images."
        assert data["name_source"] == "auto"


class TestSummaryInPastSessionDetail:
    """Verify summary is visible for past sessions (VAL-CROSS-003)."""

    async def test_past_session_with_summary(self, db_with_mixed_sessions):
        """GET /api/sessions/{id} returns summary for sessions that have one."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_auto1")

        data = resp.json()
        assert data["summary"] == "Summary of music theory chat."

    async def test_past_session_without_summary(self, db_with_mixed_sessions):
        """GET /api/sessions/{id} returns empty summary for sessions without one."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_default")

        data = resp.json()
        assert data["summary"] == ""


class TestNameSourceLifecycle:
    """Verify name_source flows through the full API lifecycle."""

    async def test_rename_changes_source_to_user(self, db_with_mixed_sessions):
        """PATCH rename changes name_source from 'auto' to 'user'."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Rename an auto-named session
                resp = await client.patch(
                    "/api/sessions/sess_auto1",
                    json={"name": "Renamed by User"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed by User"
        assert data["name_source"] == "user"

        # Verify in DB
        async with db_with_mixed_sessions.execute(
            "SELECT name, name_source FROM sessions WHERE id = ?", ("sess_auto1",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "Renamed by User"
        assert row[1] == "user"

    async def test_renamed_session_shows_in_list(self, db_with_mixed_sessions):
        """After rename, the session list shows the new name and source."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_mixed_sessions):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Rename
                await client.patch(
                    "/api/sessions/sess_auto1",
                    json={"name": "User Chosen Name"},
                )
                # List
                resp = await client.get("/api/sessions?offset=0&limit=20")

        data = resp.json()
        session = next(s for s in data["sessions"] if s["id"] == "sess_auto1")
        assert session["name"] == "User Chosen Name"
        assert session["name_source"] == "user"
