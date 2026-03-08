"""Tests for session auto-naming: trigger logic, name_source tracking, user rename blocks auto-naming."""
import time

import pytest
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock

from database import SCHEMA
from models import SessionConfig, WsSessionNameUpdate


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
async def db_with_session(db):
    """Database with one test session."""
    await db.execute(
        "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
        ("sess_test1", "New Session", "default", time.time(), "{}"),
    )
    await db.commit()
    return db


class TestNameSourceColumn:
    """Test that name_source column exists and works correctly."""

    async def test_name_source_default_value(self, db):
        """New sessions get name_source='default'."""
        await db.execute(
            "INSERT INTO sessions (id, name, created_at, config) VALUES (?, ?, ?, ?)",
            ("sess_1", "Test", time.time(), "{}"),
        )
        await db.commit()
        async with db.execute(
            "SELECT name_source FROM sessions WHERE id = ?", ("sess_1",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "default"

    async def test_name_source_can_be_set(self, db):
        """name_source can be set to 'auto' or 'user'."""
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            ("sess_auto", "Auto Name", "auto", time.time(), "{}"),
        )
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            ("sess_user", "User Name", "user", time.time(), "{}"),
        )
        await db.commit()

        async with db.execute(
            "SELECT name_source FROM sessions WHERE id = ?", ("sess_auto",)
        ) as cur:
            assert (await cur.fetchone())[0] == "auto"

        async with db.execute(
            "SELECT name_source FROM sessions WHERE id = ?", ("sess_user",)
        ) as cur:
            assert (await cur.fetchone())[0] == "user"

    async def test_name_source_update_on_rename(self, db_with_session):
        """PATCH /api/sessions/{id} sets name_source='user'."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/sessions/sess_test1",
                    json={"name": "My Custom Name"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Custom Name"
        assert data["name_source"] == "user"

        # Verify in DB
        async with db_with_session.execute(
            "SELECT name_source FROM sessions WHERE id = ?", ("sess_test1",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "user"


class TestNameSourceInApi:
    """Test that API endpoints return name_source."""

    async def test_list_sessions_includes_name_source(self, db_with_session):
        """GET /api/sessions includes name_source field."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions")

        data = resp.json()
        assert len(data["sessions"]) == 1
        assert "name_source" in data["sessions"][0]
        assert data["sessions"][0]["name_source"] == "default"

    async def test_get_session_includes_name_source(self, db_with_session):
        """GET /api/sessions/{id} includes name_source field."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_test1")

        data = resp.json()
        assert "name_source" in data
        assert data["name_source"] == "default"


class TestAutoNamingTriggerLogic:
    """Test auto-naming trigger conditions without actual LLM calls."""

    async def test_first_trigger_at_configured_count(self, db):
        """Auto-naming triggers at exactly the first_trigger chunk count."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_naming_enabled=True,
            auto_naming_first_trigger=5,
            auto_naming_repeat_interval=10,
        )
        session = ActiveSession(ws_mock, config, name="New Session")
        session._db = db
        # Insert session in DB
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        # Add transcript chunks and track when auto-naming would trigger
        infer_mock = AsyncMock(return_value="Test Topic Discussion")
        session._infer_session_name = infer_mock

        for i in range(4):
            session.transcript_chunk_count = i + 1
            session.transcript.append(MagicMock(text=f"chunk {i}", speaker="A"))
            await session._auto_name_task()
        # Should not have triggered yet (count = 1..4)
        infer_mock.assert_not_called()

        # At count = 5, should trigger
        session.transcript_chunk_count = 5
        session.transcript.append(MagicMock(text="chunk 5", speaker="A"))
        await session._auto_name_task()
        infer_mock.assert_called_once()

    async def test_repeat_trigger_at_interval(self, db):
        """Auto-naming re-triggers at repeat intervals after first trigger."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_naming_enabled=True,
            auto_naming_first_trigger=5,
            auto_naming_repeat_interval=10,
        )
        session = ActiveSession(ws_mock, config, name="Auto Named")
        session.name_source = "auto"
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        infer_mock = AsyncMock(return_value="Updated Topic")
        session._infer_session_name = infer_mock

        # At 15 (5 + 10), should trigger
        session.transcript_chunk_count = 15
        for i in range(15):
            session.transcript.append(MagicMock(text=f"chunk {i}", speaker="A"))
        await session._auto_name_task()
        assert infer_mock.call_count == 1

        # Reset for next check
        infer_mock.reset_mock()
        session._auto_naming_in_progress = False

        # At 16, should NOT trigger
        session.transcript_chunk_count = 16
        session.transcript.append(MagicMock(text="chunk 16", speaker="A"))
        await session._auto_name_task()
        infer_mock.assert_not_called()

        # At 25 (5 + 20), should trigger again
        session.transcript_chunk_count = 25
        for i in range(25 - len(session.transcript)):
            session.transcript.append(MagicMock(text=f"chunk", speaker="A"))
        await session._auto_name_task()
        assert infer_mock.call_count == 1

    async def test_disabled_auto_naming_never_triggers(self, db):
        """When auto_naming_enabled=False, auto-naming never triggers."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_naming_enabled=False, auto_naming_first_trigger=5)
        session = ActiveSession(ws_mock, config, name="New Session")
        session._db = db

        infer_mock = AsyncMock(return_value="Some Name")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 5
        session.transcript.append(MagicMock(text="test", speaker="A"))
        await session._auto_name_task()
        infer_mock.assert_not_called()

    async def test_user_rename_blocks_auto_naming(self, db):
        """When name_source='user', auto-naming is permanently skipped."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_naming_enabled=True, auto_naming_first_trigger=5)
        session = ActiveSession(ws_mock, config, name="My Session", name_source="user")
        session._db = db

        infer_mock = AsyncMock(return_value="Auto Name")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 5
        session.transcript.append(MagicMock(text="test", speaker="A"))
        await session._auto_name_task()
        infer_mock.assert_not_called()

    async def test_name_update_emits_ws_event(self, db):
        """When auto-naming produces a new name, a session_name_update WS event is emitted."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_naming_enabled=True, auto_naming_first_trigger=5)
        session = ActiveSession(ws_mock, config, name="New Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        infer_mock = AsyncMock(return_value="Meeting Notes")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 5
        session.transcript.append(MagicMock(text="discussing meeting agenda", speaker="A"))
        await session._auto_name_task()

        # Check that WS event was emitted
        ws_mock.send_text.assert_called()
        import json
        calls = ws_mock.send_text.call_args_list
        events = [json.loads(c.args[0]) for c in calls]
        name_events = [e for e in events if e.get("type") == "session_name_update"]
        assert len(name_events) == 1
        assert name_events[0]["name"] == "Meeting Notes"
        assert name_events[0]["name_source"] == "auto"

    async def test_name_update_persisted_to_db(self, db):
        """Auto-naming updates the name and name_source in the database."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_naming_enabled=True, auto_naming_first_trigger=5)
        session = ActiveSession(ws_mock, config, name="New Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        infer_mock = AsyncMock(return_value="Project Planning")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 5
        session.transcript.append(MagicMock(text="project planning", speaker="A"))
        await session._auto_name_task()

        # Check DB
        async with db.execute(
            "SELECT name, name_source FROM sessions WHERE id = ?", (session.id,)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "Project Planning"
        assert row[1] == "auto"

    async def test_same_name_does_not_trigger_update(self, db):
        """If LLM returns the same name, no update event is emitted."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_naming_enabled=True, auto_naming_first_trigger=5)
        session = ActiveSession(ws_mock, config, name="Existing Name")
        session.name_source = "auto"
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        infer_mock = AsyncMock(return_value="Existing Name")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 15
        for i in range(15):
            session.transcript.append(MagicMock(text=f"chunk {i}", speaker="A"))
        await session._auto_name_task()

        # Should NOT have emitted any event since name didn't change
        ws_mock.send_text.assert_not_called()


class TestSessionStartNameSource:
    """Test that session_start handles name_source correctly."""

    async def test_non_empty_name_sets_user_source(self):
        """When client provides a non-default name, name_source should be 'user'."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        config = SessionConfig()
        # Simulate what websocket_handler does
        name = "My Custom Session"
        name_source = "user" if name and name != "New Session" else "default"
        session = ActiveSession(ws_mock, config, name=name, name_source=name_source)
        assert session.name_source == "user"

    async def test_empty_name_sets_default_source(self):
        """When client provides empty name, name_source should be 'default'."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        config = SessionConfig()
        name = ""
        name_source = "user" if name and name != "New Session" else "default"
        session = ActiveSession(ws_mock, config, name=name, name_source=name_source)
        assert session.name_source == "default"

    async def test_new_session_default_name_allows_auto_naming(self):
        """'New Session' name keeps name_source='default', allowing auto-naming."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        config = SessionConfig()
        name = "New Session"
        name_source = "user" if name and name != "New Session" else "default"
        session = ActiveSession(ws_mock, config, name=name, name_source=name_source)
        assert session.name_source == "default"


class TestAutoNamingReEvaluation:
    """Test that re-evaluation passes the old name to LLM."""

    async def test_re_eval_passes_current_name(self, db):
        """Re-evaluation passes the current auto-generated name to LLM."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_naming_enabled=True,
            auto_naming_first_trigger=5,
            auto_naming_repeat_interval=10,
        )
        session = ActiveSession(ws_mock, config, name="First Auto Name")
        session.name_source = "auto"
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, time.time(), "{}"),
        )
        await db.commit()

        infer_mock = AsyncMock(return_value="Better Name")
        session._infer_session_name = infer_mock

        session.transcript_chunk_count = 15
        for i in range(15):
            session.transcript.append(MagicMock(text=f"chunk {i}", speaker="A"))
        await session._auto_name_task()

        # Check that _infer_session_name was called with the current name
        infer_mock.assert_called_once()
        call_args = infer_mock.call_args
        # Second arg should be the current name (re-evaluation)
        assert call_args[0][1] == "First Auto Name"
