"""Tests for agent context window improvements (R18).

Tests that invoke_once builds context with full transcript history,
includes properly formatted tool call history, and trims context
when it exceeds size limits.
"""
from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent import SessionAgent, format_tool_call_history, build_transcript_context
from models import SessionConfig, TranscriptChunk


def _make_chunks(texts: list[str], speaker: str = "A", start_ts: float | None = None) -> list[TranscriptChunk]:
    """Helper to create transcript chunks with incrementing timestamps."""
    base = start_ts or time.time()
    return [
        TranscriptChunk(text=t, speaker=speaker, ts=base + i)
        for i, t in enumerate(texts)
    ]


def _make_agent(config: SessionConfig | None = None) -> SessionAgent:
    """Create a SessionAgent with mocked dependencies."""
    cfg = config or SessionConfig()
    return SessionAgent(
        session_config=cfg,
        tools=[],
        get_short_term_context=lambda: "(no memory)",
        emit_agent_start=AsyncMock(),
        emit_agent_done=AsyncMock(),
        emit_tool_call=AsyncMock(),
    )


# ── Tests for format_tool_call_history ──────────────────────────────────────


class TestFormatToolCallHistory:
    """Test compact tool call history formatting."""

    def test_empty_log(self):
        result = format_tool_call_history([])
        assert result == ""

    def test_image_gen_includes_full_params(self):
        """Image generation tools should include full parameters."""
        log = [
            {"tool": "generate_image", "args": {"prompt": "medieval castle at sunset", "style": "fantasy"}, "ts": 1000.0},
        ]
        result = format_tool_call_history(log)
        assert "generate_image" in result
        assert "medieval castle at sunset" in result
        assert "fantasy" in result

    def test_tts_includes_full_text(self):
        """TTS (speak) tools should include the full text that was spoken."""
        log = [
            {"tool": "answer_tts", "args": {"text": "Here is a beautiful castle scene I created for you."}, "ts": 1001.0},
        ]
        result = format_tool_call_history(log)
        assert "answer_tts" in result
        assert "Here is a beautiful castle scene I created for you." in result

    def test_memory_tools_brief_mention(self):
        """Memory edit tools should only mention they were called."""
        log = [
            {"tool": "save_short_term_memory", "args": {"content": "Very long content that should not appear in full"}, "ts": 1002.0},
        ]
        result = format_tool_call_history(log)
        assert "save_short_term_memory" in result
        # The full content should NOT be in the output (memory tools are brief)
        assert "Very long content that should not appear in full" not in result

    def test_update_memory_brief(self):
        """update_short_term_memory should be mentioned briefly."""
        log = [
            {"tool": "update_short_term_memory", "args": {"entry_id": "mem_123", "content": "updated content here"}, "ts": 1003.0},
        ]
        result = format_tool_call_history(log)
        assert "update_short_term_memory" in result
        assert "updated content here" not in result

    def test_remove_memory_brief(self):
        """remove_short_term_memory should be mentioned briefly."""
        log = [
            {"tool": "remove_short_term_memory", "args": {"entry_id": "mem_abc"}, "ts": 1004.0},
        ]
        result = format_tool_call_history(log)
        assert "remove_short_term_memory" in result

    def test_save_long_term_memory_brief(self):
        """save_long_term_memory should be mentioned briefly."""
        log = [
            {"tool": "save_long_term_memory", "args": {"content": "some archived content"}, "ts": 1005.0},
        ]
        result = format_tool_call_history(log)
        assert "save_long_term_memory" in result
        assert "some archived content" not in result

    def test_search_long_term_memory_brief(self):
        """search_long_term_memory should be mentioned briefly."""
        log = [
            {"tool": "search_long_term_memory", "args": {"query": "previous meetings"}, "ts": 1006.0},
        ]
        result = format_tool_call_history(log)
        assert "search_long_term_memory" in result

    def test_mixed_tools_formatting(self):
        """Multiple tool types in order should be formatted compactly."""
        log = [
            {"tool": "generate_image", "args": {"prompt": "dragon flying", "style": "watercolor"}, "ts": 1000.0},
            {"tool": "answer_tts", "args": {"text": "I created a dragon image for you."}, "ts": 1001.0},
            {"tool": "save_short_term_memory", "args": {"content": "User likes dragons"}, "ts": 1002.0},
        ]
        result = format_tool_call_history(log)
        lines = [l for l in result.strip().split("\n") if l.strip().startswith("-")]
        assert len(lines) == 3
        # Image gen has full params
        assert "dragon flying" in lines[0]
        # TTS has full text
        assert "I created a dragon image for you." in lines[1]
        # Memory is brief
        assert "User likes dragons" not in lines[2]

    def test_format_includes_header(self):
        """Non-empty tool history should have a header."""
        log = [
            {"tool": "answer_tts", "args": {"text": "Hello"}, "ts": 1000.0},
        ]
        result = format_tool_call_history(log)
        assert "[Tool calls]" in result or "Tool calls" in result


# ── Tests for build_transcript_context ──────────────────────────────────────


class TestBuildTranscriptContext:
    """Test building full transcript context with optional trimming."""

    def test_full_history_included(self):
        """All transcript chunks should be included (no delta-only behavior)."""
        chunks = _make_chunks(["Hello", "How are you?", "I'm fine", "Great!"])
        result = build_transcript_context(chunks)
        assert "Hello" in result
        assert "How are you?" in result
        assert "I'm fine" in result
        assert "Great!" in result

    def test_empty_transcript(self):
        result = build_transcript_context([])
        assert result == ""

    def test_speaker_labels_included(self):
        """Speaker labels should be in the formatted output."""
        chunks = [
            TranscriptChunk(text="Hi there", speaker="A", ts=1000.0),
            TranscriptChunk(text="Hey!", speaker="B", ts=1001.0),
        ]
        result = build_transcript_context(chunks)
        assert "[A" in result
        assert "[B" in result

    def test_trimming_when_too_long(self):
        """Old entries should be trimmed when total exceeds max chars."""
        # Create many chunks that exceed the limit
        texts = [f"This is chunk number {i} with some filler content to make it longer." for i in range(200)]
        chunks = _make_chunks(texts)
        max_chars = 500
        result = build_transcript_context(chunks, max_chars=max_chars)
        # Result should be trimmed
        assert len(result) <= max_chars + 200  # Some tolerance for line boundaries
        # Most recent chunks should be present
        assert "chunk number 199" in result
        # Oldest chunks should be trimmed
        assert "chunk number 0" not in result

    def test_trimming_preserves_recent(self):
        """Trimming should keep the most recent transcript entries."""
        texts = [f"Chunk {i}" for i in range(100)]
        chunks = _make_chunks(texts)
        result = build_transcript_context(chunks, max_chars=200)
        # Latest chunks should survive
        assert "Chunk 99" in result

    def test_no_trimming_when_within_limit(self):
        """When transcript is within limits, all entries are included."""
        chunks = _make_chunks(["Hello", "World"])
        result = build_transcript_context(chunks, max_chars=10000)
        assert "Hello" in result
        assert "World" in result


# ── Tests for invoke_once context building ──────────────────────────────────


class TestInvokeOnceContextBuilding:
    """Test that invoke_once uses full transcript history."""

    @pytest.fixture
    def agent(self):
        return _make_agent()

    async def test_invoke_uses_full_history(self, agent):
        """invoke_once should include full transcript, not just delta."""
        # Build a mock agent
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        chunks1 = _make_chunks(["First batch chunk 1", "First batch chunk 2"])
        # First invocation
        await agent.invoke_once(chunks1, tool_call_log=[])

        # Capture what was passed
        call1_prompt = mock_pydantic_agent.run.call_args[0][0]
        assert "First batch chunk 1" in call1_prompt
        assert "First batch chunk 2" in call1_prompt

        # Second invocation with more chunks - should include ALL
        chunks2 = chunks1 + _make_chunks(["Second batch chunk 1"], start_ts=time.time() + 10)
        await agent.invoke_once(chunks2, tool_call_log=[])

        call2_prompt = mock_pydantic_agent.run.call_args[0][0]
        # Full history included
        assert "First batch chunk 1" in call2_prompt
        assert "First batch chunk 2" in call2_prompt
        assert "Second batch chunk 1" in call2_prompt

    async def test_invoke_includes_tool_history(self, agent):
        """invoke_once should include tool call history in the prompt."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        chunks = _make_chunks(["Something happened"])
        tool_log = [
            {"tool": "answer_tts", "args": {"text": "I spoke this."}, "ts": 1000.0},
            {"tool": "generate_image", "args": {"prompt": "sunset"}, "ts": 1001.0},
        ]

        await agent.invoke_once(chunks, tool_call_log=tool_log)

        prompt = mock_pydantic_agent.run.call_args[0][0]
        assert "Tool calls" in prompt
        assert "I spoke this." in prompt
        assert "sunset" in prompt

    async def test_invoke_no_tool_history_when_empty(self, agent):
        """When tool log is empty, no tool call section in prompt."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        chunks = _make_chunks(["Something"])
        await agent.invoke_once(chunks, tool_call_log=[])

        prompt = mock_pydantic_agent.run.call_args[0][0]
        assert "[Tool calls]" not in prompt

    async def test_invoke_skips_empty_transcript(self, agent):
        """invoke_once with no transcript should skip."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        await agent.invoke_once([], tool_call_log=[])
        mock_pydantic_agent.run.assert_not_called()

    async def test_invoke_context_trimming(self, agent):
        """Very long transcripts should be trimmed to keep context manageable."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        # Create a very large transcript
        texts = [f"Long conversation chunk {i}: " + "x" * 100 for i in range(500)]
        chunks = _make_chunks(texts)

        await agent.invoke_once(chunks, tool_call_log=[])

        prompt = mock_pydantic_agent.run.call_args[0][0]
        # The prompt should have been trimmed (not contain all 500 chunks)
        assert "Long conversation chunk 499" in prompt  # Recent should be present
        # Prompt length should be reasonable (not 50k+ chars)
        assert len(prompt) < 60000

    async def test_invoke_with_new_chunks_still_includes_full_history(self, agent):
        """Even after multiple calls, all available transcript is included."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        base_ts = time.time()
        # Call 1
        chunks_v1 = _make_chunks(["Alpha", "Beta"], start_ts=base_ts)
        await agent.invoke_once(chunks_v1, tool_call_log=[])

        # Call 2 - transcript grew
        chunks_v2 = chunks_v1 + _make_chunks(["Gamma"], start_ts=base_ts + 100)
        await agent.invoke_once(chunks_v2, tool_call_log=[])

        prompt = mock_pydantic_agent.run.call_args[0][0]
        assert "Alpha" in prompt
        assert "Beta" in prompt
        assert "Gamma" in prompt

    async def test_invoke_detects_new_content(self, agent):
        """invoke_once should still track last count so it can skip when no new content."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        chunks = _make_chunks(["Hello"])
        await agent.invoke_once(chunks, tool_call_log=[])
        assert mock_pydantic_agent.run.call_count == 1

        # Same chunks again — no new content
        await agent.invoke_once(chunks, tool_call_log=[])
        assert mock_pydantic_agent.run.call_count == 1  # Should not have been called again

        # Add new chunk
        chunks2 = chunks + _make_chunks(["World"], start_ts=time.time() + 10)
        await agent.invoke_once(chunks2, tool_call_log=[])
        assert mock_pydantic_agent.run.call_count == 2
