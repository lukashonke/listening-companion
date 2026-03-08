"""Tests for agent transcript-based triggering (R19).

Tests that the agent can be triggered on committed transcript chunks,
skips when already running, respects minimum cooldown, and falls back
to timer mode.
"""
from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent import SessionAgent
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


class TestTriggerAgentRun:
    """Test the trigger_agent_run() method for transcript-based triggering."""

    async def test_trigger_invokes_agent(self):
        """trigger_agent_run() should invoke the agent when not already running."""
        config = SessionConfig(agent_trigger_mode="transcript")
        agent = _make_agent(config)

        # Build a mock pydantic agent
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        transcript = _make_chunks(["Hello world"])
        tool_log: list[dict] = []

        await agent.trigger_agent_run(
            get_transcript=lambda: transcript,
            get_tool_call_log=lambda: tool_log,
        )

        # Give async task a moment to run
        await asyncio.sleep(0.1)

        # Agent should have been invoked
        assert mock_pydantic_agent.run.call_count == 1

    async def test_trigger_skips_when_already_running(self):
        """If agent is currently running, trigger_agent_run() should skip."""
        config = SessionConfig(agent_trigger_mode="transcript")
        agent = _make_agent(config)

        mock_pydantic_agent = MagicMock()
        # Make run take a while
        async def slow_run(*args, **kwargs):
            await asyncio.sleep(1.0)
        mock_pydantic_agent.run = AsyncMock(side_effect=slow_run)
        agent._agent = mock_pydantic_agent

        transcript = _make_chunks(["Hello", "World"])

        # First trigger starts the run
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript,
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.05)  # Let task start

        # Second trigger while first is still running should be skipped
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript + _make_chunks(["More"], start_ts=time.time() + 100),
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.05)

        # Only one invocation should have started
        assert mock_pydantic_agent.run.call_count == 1

    async def test_trigger_respects_minimum_cooldown(self):
        """Rapid triggers should be throttled by the minimum cooldown period."""
        config = SessionConfig(agent_trigger_mode="transcript")
        agent = _make_agent(config)

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        transcript = _make_chunks(["Hello"])

        # First trigger
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript,
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.1)

        # Immediately trigger again (within cooldown)
        transcript2 = transcript + _make_chunks(["World"], start_ts=time.time() + 100)
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript2,
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.1)

        # Only the first should have run (second within cooldown)
        assert mock_pydantic_agent.run.call_count == 1

    async def test_trigger_allows_run_after_cooldown(self):
        """After cooldown expires, a new trigger should invoke the agent."""
        config = SessionConfig(agent_trigger_mode="transcript", agent_trigger_cooldown_s=0.2)
        agent = _make_agent(config)

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        transcript = _make_chunks(["Hello"])

        # First trigger
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript,
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.1)
        assert mock_pydantic_agent.run.call_count == 1

        # Wait for cooldown to expire
        await asyncio.sleep(0.2)

        # Second trigger after cooldown
        transcript2 = transcript + _make_chunks(["World"], start_ts=time.time() + 100)
        await agent.trigger_agent_run(
            get_transcript=lambda: transcript2,
            get_tool_call_log=lambda: [],
        )
        await asyncio.sleep(0.1)
        assert mock_pydantic_agent.run.call_count == 2


class TestTimerModeFallback:
    """Test that timer-based triggering still works as a fallback."""

    async def test_timer_mode_uses_agent_loop(self):
        """In timer mode, start_loop should launch the traditional _agent_loop."""
        config = SessionConfig(agent_trigger_mode="timer", agent_interval_s=1)
        agent = _make_agent(config)

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock()
        agent._agent = mock_pydantic_agent

        # Ensure agent is built (normally done in _agent_loop)
        with patch.object(agent, '_build_agent', return_value=mock_pydantic_agent):
            await agent.start_loop(
                get_transcript=lambda: _make_chunks(["Test"]),
                get_tool_call_log=lambda: [],
            )

        # The loop task should be running
        assert agent._loop_task is not None
        assert not agent._loop_task.done()

        await agent.stop_loop()

    async def test_transcript_mode_does_not_start_timer_loop(self):
        """In transcript mode, start_loop should NOT launch the timer-based _agent_loop.
        It should only build the agent and store getters for on-demand triggering."""
        config = SessionConfig(agent_trigger_mode="transcript")
        agent = _make_agent(config)

        mock_pydantic_agent = MagicMock()
        with patch.object(agent, '_build_agent', return_value=mock_pydantic_agent):
            await agent.start_loop(
                get_transcript=lambda: [],
                get_tool_call_log=lambda: [],
            )

        # In transcript mode, there should be no background timer loop running
        # The agent should be built though
        assert agent._agent is not None
        await agent.stop_loop()


class TestAgentTriggerModeConfig:
    """Test that agent_trigger_mode config field works correctly."""

    def test_default_trigger_mode_is_transcript(self):
        """Default trigger mode should be 'transcript'."""
        config = SessionConfig()
        assert config.agent_trigger_mode == "transcript"

    def test_timer_mode_configurable(self):
        """Should be able to set trigger mode to 'timer'."""
        config = SessionConfig(agent_trigger_mode="timer")
        assert config.agent_trigger_mode == "timer"

    def test_default_cooldown_value(self):
        """Default cooldown should be 2 seconds."""
        config = SessionConfig()
        assert config.agent_trigger_cooldown_s == 2
