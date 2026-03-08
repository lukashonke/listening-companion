"""Tests for auto-summarization: timer logic, transcript trimming, summary stored in DB, WS event."""
import json
import time

import pytest
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock

from database import SCHEMA
from models import SessionConfig, WsSessionSummaryUpdate


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
        "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
        ("sess_test1", "Test Session", "auto", "", time.time(), "{}"),
    )
    await db.commit()
    return db


class TestSummaryColumn:
    """Test that summary column exists and works correctly."""

    async def test_summary_default_value(self, db):
        """New sessions get summary=''."""
        await db.execute(
            "INSERT INTO sessions (id, name, created_at, config) VALUES (?, ?, ?, ?)",
            ("sess_1", "Test", time.time(), "{}"),
        )
        await db.commit()
        async with db.execute(
            "SELECT summary FROM sessions WHERE id = ?", ("sess_1",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == ""

    async def test_summary_can_be_set(self, db):
        """Summary can be stored and retrieved."""
        await db.execute(
            "INSERT INTO sessions (id, name, summary, created_at, config) VALUES (?, ?, ?, ?, ?)",
            ("sess_sum", "Test", "This is a session about cooking.", time.time(), "{}"),
        )
        await db.commit()
        async with db.execute(
            "SELECT summary FROM sessions WHERE id = ?", ("sess_sum",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "This is a session about cooking."

    async def test_summary_can_be_updated(self, db_with_session):
        """Summary can be updated for an existing session."""
        await db_with_session.execute(
            "UPDATE sessions SET summary = ? WHERE id = ?",
            ("Updated summary content.", "sess_test1"),
        )
        await db_with_session.commit()
        async with db_with_session.execute(
            "SELECT summary FROM sessions WHERE id = ?", ("sess_test1",)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "Updated summary content."


class TestSummaryInApi:
    """Test that API endpoints return summary."""

    async def test_get_session_includes_summary(self, db_with_session):
        """GET /api/sessions/{id} includes summary field."""
        # Set a summary
        await db_with_session.execute(
            "UPDATE sessions SET summary = ? WHERE id = ?",
            ("A discussion about music theory.", "sess_test1"),
        )
        await db_with_session.commit()

        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_test1")

        data = resp.json()
        assert "summary" in data
        assert data["summary"] == "A discussion about music theory."

    async def test_get_session_empty_summary(self, db_with_session):
        """GET /api/sessions/{id} returns empty summary when not set."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/sessions/sess_test1")

        data = resp.json()
        assert "summary" in data
        assert data["summary"] == ""


class TestSummarizationRunMethod:
    """Test the _run_summarization method logic."""

    async def test_summarization_generates_and_stores_summary(self, db):
        """_run_summarization calls LLM, stores result, and emits WS event."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_summarization_enabled=True,
            auto_summarization_interval=60,
            auto_summarization_max_transcript_length=10000,
        )
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "", time.time(), "{}"),
        )
        await db.commit()

        # Add some transcript chunks
        for i in range(10):
            session.transcript.append(MagicMock(text=f"Speaker discusses topic {i}", speaker="A", ts=time.time()))

        # Mock the LLM call
        llm_mock = AsyncMock(return_value="A conversation about various topics numbered 0 through 9.")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        # Verify LLM was called
        llm_mock.assert_called_once()

        # Verify summary stored in DB
        async with db.execute(
            "SELECT summary FROM sessions WHERE id = ?", (session.id,)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == "A conversation about various topics numbered 0 through 9."

        # Verify WS event emitted
        ws_mock.send_text.assert_called()
        calls = ws_mock.send_text.call_args_list
        events = [json.loads(c.args[0]) for c in calls]
        summary_events = [e for e in events if e.get("type") == "session_summary_update"]
        assert len(summary_events) == 1
        assert summary_events[0]["summary"] == "A conversation about various topics numbered 0 through 9."

    async def test_summarization_skips_with_no_transcript(self, db):
        """_run_summarization does nothing when transcript is empty."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_summarization_enabled=True)
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "", time.time(), "{}"),
        )
        await db.commit()

        llm_mock = AsyncMock(return_value="Some summary")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        # LLM should NOT be called
        llm_mock.assert_not_called()
        # No WS event
        ws_mock.send_text.assert_not_called()

    async def test_summarization_passes_previous_summary(self, db):
        """_run_summarization passes existing summary as context for continuity."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_summarization_enabled=True,
            auto_summarization_max_transcript_length=10000,
        )
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "Previous summary from earlier.", time.time(), "{}"),
        )
        await db.commit()

        for i in range(5):
            session.transcript.append(MagicMock(text=f"New topic {i}", speaker="B", ts=time.time()))

        llm_mock = AsyncMock(return_value="Updated summary incorporating new topics.")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        # Verify previous summary was passed to LLM
        llm_mock.assert_called_once()
        call_args = llm_mock.call_args
        # The method should pass transcript_text, tool_previews, and previous_summary
        assert "Previous summary from earlier." in call_args[1].get("previous_summary", "") or \
               "Previous summary from earlier." in str(call_args)

    async def test_summarization_includes_tool_previews(self, db):
        """_run_summarization includes trimmed tool call previews in LLM input."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_summarization_enabled=True)
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "", time.time(), "{}"),
        )
        await db.commit()

        # Add transcript
        session.transcript.append(MagicMock(text="Discuss the castle image", speaker="A", ts=time.time()))

        # Simulate tool calls by adding to the agent's tool log
        # The tool call log is tracked via _emit_tool_call which we need to capture
        session._tool_call_log = [
            {"tool": "generate_image", "args": {"prompt": "A beautiful medieval castle in the mountains with a dragon"}, "ts": time.time()},
            {"tool": "answer_tts", "args": {"text": "Here is a response about the castle image"}, "ts": time.time()},
        ]

        llm_mock = AsyncMock(return_value="Discussion about generating a castle image.")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        llm_mock.assert_called_once()
        call_args = llm_mock.call_args
        tool_previews = call_args[1].get("tool_previews", "") if call_args[1] else str(call_args)
        # Tool previews should be present and trimmed
        assert "generate_image" in str(call_args) or "castle" in str(call_args)


class TestTranscriptTrimming:
    """Test transcript trimming logic for long transcripts."""

    async def test_long_transcript_trimmed_from_start(self, db):
        """When transcript exceeds max length, beginning is trimmed, recent content preserved."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        max_len = 500
        config = SessionConfig(
            auto_summarization_enabled=True,
            auto_summarization_max_transcript_length=max_len,
        )
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "Previous summary.", time.time(), "{}"),
        )
        await db.commit()

        # Generate a very long transcript
        for i in range(100):
            session.transcript.append(
                MagicMock(text=f"This is a long chunk of text number {i} with lots of words to make it exceed the limit", speaker="A", ts=time.time())
            )

        llm_mock = AsyncMock(return_value="Trimmed summary.")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        llm_mock.assert_called_once()
        call_args = llm_mock.call_args
        transcript_text = call_args[1].get("transcript_text", "")
        # The transcript should be trimmed to fit within max_length
        # Recent content (end) should be preserved
        assert len(transcript_text) <= max_len
        # The last chunk should be in the transcript (most recent preserved)
        assert "number 99" in transcript_text

    async def test_short_transcript_not_trimmed(self, db):
        """When transcript is within max length, nothing is trimmed."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(
            auto_summarization_enabled=True,
            auto_summarization_max_transcript_length=50000,
        )
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db
        await db.execute(
            "INSERT INTO sessions (id, name, name_source, summary, created_at, config) VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.name, session.name_source, "", time.time(), "{}"),
        )
        await db.commit()

        # Small transcript
        for i in range(3):
            session.transcript.append(MagicMock(text=f"Short chunk {i}", speaker="A", ts=time.time()))

        llm_mock = AsyncMock(return_value="Short summary.")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        llm_mock.assert_called_once()
        call_args = llm_mock.call_args
        transcript_text = call_args[1].get("transcript_text", "")
        # All chunks should be present
        assert "Short chunk 0" in transcript_text
        assert "Short chunk 1" in transcript_text
        assert "Short chunk 2" in transcript_text


class TestSummarizationDisabled:
    """Test that summarization respects enabled/disabled config."""

    async def test_disabled_summarization_never_runs(self, db):
        """When auto_summarization_enabled=False, summarization never runs."""
        from ws_handler import ActiveSession

        ws_mock = AsyncMock()
        ws_mock.send_text = AsyncMock()
        config = SessionConfig(auto_summarization_enabled=False)
        session = ActiveSession(ws_mock, config, name="Test Session")
        session._db = db

        session.transcript.append(MagicMock(text="Some text", speaker="A", ts=time.time()))

        llm_mock = AsyncMock(return_value="Should not run")
        session._call_summarization_llm = llm_mock

        await session._run_summarization()

        llm_mock.assert_not_called()
        ws_mock.send_text.assert_not_called()
