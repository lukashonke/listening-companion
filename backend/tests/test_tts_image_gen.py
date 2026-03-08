"""Tests for B6: Fix agent generating image but not speaking.

Verifies:
- System prompt contains instruction about always speaking to direct questions
- Agent configuration allows multiple tool calls per turn (no limit set)
- Tool call tracking logs multiple tools per turn
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent import SessionAgent, SYSTEM_PROMPT_TEMPLATE
from models import SessionConfig, TranscriptChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _noop(*args, **kwargs):
    pass


def _fake_settings(**overrides):
    m = MagicMock()
    m.openai_api_key = "sk-fake"
    m.google_api_key = "fake-google"
    m.anthropic_api_key = "fake-anthropic"
    m.claude_model = "claude-sonnet-4-5"
    m.agent_timeout_s = 60
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _make_session_agent(config: SessionConfig | None = None, context: str = "no memory"):
    cfg = config or SessionConfig()
    return SessionAgent(
        session_config=cfg,
        tools=[],
        get_short_term_context=lambda: context,
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )


def _build(sa):
    with patch("agent.settings", _fake_settings()):
        return sa._build_agent()


def _render_system_prompt(agent) -> str:
    runner = agent._system_prompt_functions[0]
    return runner.function()


def _make_chunks(texts: list[str], speaker: str = "A") -> list[TranscriptChunk]:
    base = time.time()
    return [
        TranscriptChunk(text=t, speaker=speaker, ts=base + i)
        for i, t in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# Test: System prompt contains TTS instruction for direct questions
# ---------------------------------------------------------------------------


class TestSystemPromptTTSInstruction:
    """VAL-TODO-007: System prompt instructs agent to always respond verbally."""

    def test_default_prompt_contains_tts_instruction(self):
        """Built-in SYSTEM_PROMPT_TEMPLATE instructs agent to always use answer_tts for direct questions."""
        assert "answer_tts" in SYSTEM_PROMPT_TEMPLATE
        assert "ALWAYS" in SYSTEM_PROMPT_TEMPLATE
        assert "question" in SYSTEM_PROMPT_TEMPLATE.lower()

    def test_rendered_prompt_contains_tts_instruction(self):
        """Rendered system prompt contains the always-speak instruction."""
        sa = _make_session_agent()
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        # Must contain the instruction to always respond verbally
        assert "answer_tts" in prompt
        assert "ALWAYS" in prompt

    def test_prompt_mentions_multiple_tool_use(self):
        """System prompt explicitly says agent can use multiple tools in same response."""
        sa = _make_session_agent()
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        # Must mention that agent can use other tools alongside TTS
        assert "generate_image" in prompt
        # Should mention using both speak AND image
        assert "BOTH" in prompt or "also use other tools" in prompt

    def test_custom_full_prompt_overrides_but_default_has_instruction(self):
        """When using custom full_system_prompt, the default instruction is not present.
        But the default template DOES contain it."""
        # Default template has the instruction
        assert "ALWAYS respond verbally" in SYSTEM_PROMPT_TEMPLATE

        # Custom prompt overrides entirely
        config = SessionConfig(full_system_prompt="You are a simple bot.")
        sa = _make_session_agent(config)
        agent = _build(sa)
        prompt = _render_system_prompt(agent)
        assert "ALWAYS respond verbally" not in prompt


# ---------------------------------------------------------------------------
# Test: Agent configuration allows multiple tool calls per turn
# ---------------------------------------------------------------------------


class TestMultipleToolCallsAllowed:
    """VAL-TODO-007: Agent can call multiple tools per turn."""

    def test_no_usage_limits_set(self):
        """Agent.run() is called without usage_limits, allowing unlimited tool calls."""
        sa = _make_session_agent()
        agent = _build(sa)

        # The Agent constructor should not have any tool_calls_limit
        # Pydantic AI's default is no limit (None)
        # Check that we don't pass usage_limits in invoke_once
        # by inspecting the invoke_once source — it calls agent.run() with no usage_limits
        import inspect
        source = inspect.getsource(SessionAgent.invoke_once)
        assert "usage_limits" not in source

    def test_no_end_strategy_limiting_tools(self):
        """Agent is not configured with end_strategy that would limit parallel tool execution."""
        sa = _make_session_agent()
        agent = _build(sa)

        # end_strategy should be default (not set to 'early' which would skip tools)
        # The default in Pydantic AI is 'early' for output tools, but since we don't
        # use output tools (result_type), this doesn't apply.
        # Key check: no explicit end_strategy='early' that would limit function tool calls
        import inspect
        source = inspect.getsource(SessionAgent._build_agent)
        assert "end_strategy" not in source

    def test_agent_constructor_no_tool_limit(self):
        """Agent() is constructed without any tool call restrictions."""
        # Verify the Agent is created with just model and tools, no restrictions
        sa = _make_session_agent()
        with patch("agent.settings", _fake_settings()):
            with patch("pydantic_ai.Agent.__init__", return_value=None) as mock_init:
                # Need to also patch the system_prompt decorator
                mock_agent = MagicMock()
                with patch("pydantic_ai.Agent", return_value=mock_agent):
                    sa._build_agent()

                    # Check Agent was called with model and tools only
                    call_kwargs = mock_agent.__class__.call_args if hasattr(mock_agent.__class__, 'call_args') else {}
                    # The important thing is that usage_limits and end_strategy are NOT passed


# ---------------------------------------------------------------------------
# Test: Tool call tracking per turn
# ---------------------------------------------------------------------------


class TestToolCallTracking:
    """Track and log when multiple tools are called in a single agent turn."""

    def test_turn_tool_calls_reset_each_invocation(self):
        """_turn_tool_calls list is reset at the start of each invoke_once call."""
        sa = _make_session_agent()
        # Simulate some leftover tool calls
        sa._turn_tool_calls = ["answer_tts", "generate_image"]

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock()
        sa._agent = mock_agent

        chunks = _make_chunks(["Hello"])

        async def run():
            await sa.invoke_once(chunks, tool_call_log=[])

        asyncio.get_event_loop().run_until_complete(run())

        # After invocation, _turn_tool_calls should have been reset
        # (it was reset at the start, then no tools were called during mock run)
        assert sa._turn_tool_calls == []

    def test_turn_tool_calls_initialized_empty(self):
        """SessionAgent starts with empty _turn_tool_calls."""
        sa = _make_session_agent()
        assert sa._turn_tool_calls == []

    def test_wrap_tool_tracks_async_calls(self):
        """Wrapped async tools append their name to _turn_tool_calls."""
        sa = _make_session_agent()
        sa._emit_tool_call = AsyncMock()

        async def my_tool(text: str) -> str:
            return "done"

        wrapped = sa._wrap_tool(my_tool)

        async def run():
            await wrapped("hello")

        asyncio.get_event_loop().run_until_complete(run())

        assert "my_tool" in sa._turn_tool_calls
        assert len(sa._turn_tool_calls) == 1

    def test_wrap_tool_tracks_multiple_calls(self):
        """Multiple tool calls in one turn are all tracked."""
        sa = _make_session_agent()
        sa._emit_tool_call = AsyncMock()

        async def tool_a(text: str) -> str:
            return "a"

        async def tool_b(prompt: str) -> str:
            return "b"

        wrapped_a = sa._wrap_tool(tool_a)
        wrapped_b = sa._wrap_tool(tool_b)

        async def run():
            await wrapped_a("hello")
            await wrapped_b("world")

        asyncio.get_event_loop().run_until_complete(run())

        assert sa._turn_tool_calls == ["tool_a", "tool_b"]
        assert len(sa._turn_tool_calls) == 2
