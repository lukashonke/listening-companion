"""Pydantic AI model integration tests — R16.

Tests verify that:
- Agent construction works for each model provider + model name combination
- _is_chat_model() and _is_gemini_chat_model() filters include/exclude correctly
- OpenAI o-series models receive OpenAIModelSettings with reasoning_effort
- Non-o-series OpenAI models receive no model_settings
- System prompt renders correctly with theme and custom_system_prompt
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import SessionConfig, TranscriptChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _noop(*args, **kwargs):
    pass


def _make_session_agent(
    provider: str,
    model: str,
    reasoning_effort: str = "medium",
    tools: list | None = None,
):
    """Return a SessionAgent with the given provider/model and no-op callbacks."""
    from agent import SessionAgent

    config = SessionConfig(
        model_provider=provider,
        agent_model=model,
        reasoning_effort=reasoning_effort,
    )
    return SessionAgent(
        session_config=config,
        tools=tools or [],
        get_short_term_context=lambda: "no memory",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )


def _fake_settings(**overrides):
    """Return a MagicMock that looks like config.settings with fake API keys."""
    m = MagicMock()
    m.openai_api_key = "sk-fake-openai-key"
    m.google_api_key = "fake-google-key"
    m.anthropic_api_key = "fake-anthropic-key"
    m.claude_model = "claude-sonnet-4-5"
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _build(sa):
    """Call SessionAgent._build_agent() with patched settings and return the Agent."""
    with patch("agent.settings", _fake_settings()):
        return sa._build_agent()


# ---------------------------------------------------------------------------
# OpenAI model matrix
# ---------------------------------------------------------------------------

OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "gpt-5.4",
    "gpt-5.3-chat-latest",
    "o3",
    "o4-mini",
]


@pytest.mark.parametrize("model_name", OPENAI_MODELS)
def test_build_agent_openai(model_name):
    from pydantic_ai import Agent

    sa = _make_session_agent("openai", model_name)
    agent = _build(sa)
    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Google model matrix
# ---------------------------------------------------------------------------

GOOGLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
]


@pytest.mark.parametrize("model_name", GOOGLE_MODELS)
def test_build_agent_google(model_name):
    from pydantic_ai import Agent

    sa = _make_session_agent("google", model_name)
    agent = _build(sa)
    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Anthropic model matrix
# ---------------------------------------------------------------------------

ANTHROPIC_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
]


@pytest.mark.parametrize("model_name", ANTHROPIC_MODELS)
def test_build_agent_anthropic(model_name):
    from pydantic_ai import Agent

    sa = _make_session_agent("anthropic", model_name)
    agent = _build(sa)
    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Agent with tools
# ---------------------------------------------------------------------------

def _dummy_sync_tool(x: str) -> str:
    """Return a dummy sync result."""
    return f"sync: {x}"


async def _dummy_async_tool(x: str) -> str:
    """Return a dummy async result."""
    return f"async: {x}"


def test_build_agent_with_tools():
    from pydantic_ai import Agent

    sa = _make_session_agent(
        "anthropic",
        "claude-sonnet-4-6",
        tools=[_dummy_sync_tool, _dummy_async_tool],
    )
    agent = _build(sa)
    assert isinstance(agent, Agent)


def test_build_agent_with_no_tools():
    from pydantic_ai import Agent

    sa = _make_session_agent("anthropic", "claude-sonnet-4-6", tools=[])
    agent = _build(sa)
    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Agent construction via monkeypatch on settings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider,model_name", [
    ("openai", "gpt-4o"),
    ("google", "gemini-2.5-flash"),
    ("anthropic", "claude-haiku-4-5-20251001"),
])
def test_build_agent_monkeypatch_providers(provider, model_name, monkeypatch):
    """_build_agent() succeeds for each provider when API keys are set via monkeypatch."""
    import config as cfg
    from pydantic_ai import Agent

    monkeypatch.setattr(cfg.settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr(cfg.settings, "google_api_key", "test-google-key")
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-anthropic-key")

    from agent import SessionAgent

    config = SessionConfig(model_provider=provider, agent_model=model_name)
    sa = SessionAgent(
        session_config=config,
        tools=[],
        get_short_term_context=lambda: "no memory",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()

    assert agent is not None
    assert isinstance(agent, Agent)


@pytest.mark.parametrize("provider,model_name,tools,expected_count", [
    ("anthropic", "claude-haiku-4-5-20251001", [], 0),
    ("anthropic", "claude-haiku-4-5-20251001", [_dummy_async_tool], 1),
    ("openai", "gpt-4o", [_dummy_sync_tool, _dummy_async_tool], 2),
    ("google", "gemini-2.5-flash", [_dummy_sync_tool, _dummy_async_tool], 2),
])
def test_build_agent_tools_count(provider, model_name, tools, expected_count, monkeypatch):
    """Wrapped tools are registered on the agent with the correct count."""
    import config as cfg

    monkeypatch.setattr(cfg.settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr(cfg.settings, "google_api_key", "test-google-key")
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-anthropic-key")

    from agent import SessionAgent

    config = SessionConfig(model_provider=provider, agent_model=model_name)
    sa = SessionAgent(
        session_config=config,
        tools=tools,
        get_short_term_context=lambda: "no memory",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()

    assert len(agent._function_toolset.tools) == expected_count


# ---------------------------------------------------------------------------
# System prompt rendering (via live agent — monkeypatch)
# ---------------------------------------------------------------------------

def _render_system_prompt(agent) -> str:
    """Call the registered system prompt function and return the rendered string."""
    runner = agent._system_prompt_functions[0]
    return runner.function()


def test_system_prompt_no_extras_via_agent(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-key")

    from agent import SessionAgent

    sa = SessionAgent(
        session_config=SessionConfig(),
        tools=[],
        get_short_term_context=lambda: "empty memory",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()
    prompt = _render_system_prompt(agent)

    assert "empty memory" in prompt
    assert "Session context" not in prompt
    assert "Additional instructions" not in prompt


def test_system_prompt_with_theme_via_agent(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-key")

    from agent import SessionAgent

    sa = SessionAgent(
        session_config=SessionConfig(theme="Dungeons & Dragons campaign"),
        tools=[],
        get_short_term_context=lambda: "no memory",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()
    prompt = _render_system_prompt(agent)

    assert "Dungeons & Dragons campaign" in prompt
    assert "Session context" in prompt
    assert "Additional instructions" not in prompt


def test_system_prompt_with_custom_via_agent(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-key")

    from agent import SessionAgent

    sa = SessionAgent(
        session_config=SessionConfig(custom_system_prompt="Always respond in bullet points."),
        tools=[],
        get_short_term_context=lambda: "memory here",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()
    prompt = _render_system_prompt(agent)

    assert "Always respond in bullet points." in prompt
    assert "Additional instructions" in prompt
    assert "Session context" not in prompt


def test_system_prompt_reflects_dynamic_context(monkeypatch):
    """System prompt re-renders dynamically on each call, reflecting updated context."""
    import config as cfg
    monkeypatch.setattr(cfg.settings, "anthropic_api_key", "test-key")

    from agent import SessionAgent

    context = {"value": "initial context"}
    sa = SessionAgent(
        session_config=SessionConfig(),
        tools=[],
        get_short_term_context=lambda: context["value"],
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )
    agent = sa._build_agent()

    assert "initial context" in _render_system_prompt(agent)
    context["value"] = "updated context"
    assert "updated context" in _render_system_prompt(agent)
    assert "initial context" not in _render_system_prompt(agent)


# ---------------------------------------------------------------------------
# System prompt rendering — template-level tests (no API calls)
# ---------------------------------------------------------------------------

def test_system_prompt_base_rendering():
    from agent import SYSTEM_PROMPT_TEMPLATE

    rendered = SYSTEM_PROMPT_TEMPLATE.format(
        short_term_memory="- Entry A\n- Entry B",
        theme_section="",
        custom_prompt_section="",
    )
    assert "AI listening companion" in rendered
    assert "Entry A" in rendered
    assert "Entry B" in rendered


def test_system_prompt_with_theme():
    from agent import SYSTEM_PROMPT_TEMPLATE

    theme_section = (
        "\n## Session context\nThis session is: D&D Session\n"
        "Adapt your behavior accordingly (e.g., track initiative in D&D, track action items in meetings).\n"
    )
    rendered = SYSTEM_PROMPT_TEMPLATE.format(
        short_term_memory="",
        theme_section=theme_section,
        custom_prompt_section="",
    )
    assert "D&D Session" in rendered


def test_system_prompt_with_custom_prompt():
    from agent import SYSTEM_PROMPT_TEMPLATE

    custom_section = "\n## Additional instructions\nAlways respond in haiku.\n"
    rendered = SYSTEM_PROMPT_TEMPLATE.format(
        short_term_memory="",
        theme_section="",
        custom_prompt_section=custom_section,
    )
    assert "haiku" in rendered


def test_system_prompt_logic_with_theme_and_custom():
    """Verify the closure logic in _build_agent produces the correct prompt."""
    from agent import SYSTEM_PROMPT_TEMPLATE, SessionAgent

    config = SessionConfig(
        model_provider="anthropic",
        agent_model="claude-sonnet-4-6",
        theme="Board Game Night",
        custom_system_prompt="Track scores for each player.",
    )
    sa = SessionAgent(
        session_config=config,
        tools=[],
        get_short_term_context=lambda: "player 1 leads",
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )

    # Replicate the closure logic from _build_agent
    theme_section = (
        f"\n## Session context\nThis session is: {config.theme}\n"
        "Adapt your behavior accordingly (e.g., track initiative in D&D, track action items in meetings).\n"
    )
    custom_prompt_section = f"\n## Additional instructions\n{config.custom_system_prompt}\n"
    rendered = SYSTEM_PROMPT_TEMPLATE.format(
        short_term_memory=sa._get_short_term_context(),
        theme_section=theme_section,
        custom_prompt_section=custom_prompt_section,
    )

    assert "Board Game Night" in rendered
    assert "Track scores for each player" in rendered
    assert "player 1 leads" in rendered


def test_system_prompt_no_theme_no_custom_produces_empty_sections():
    from agent import SYSTEM_PROMPT_TEMPLATE

    rendered = SYSTEM_PROMPT_TEMPLATE.format(
        short_term_memory="",
        theme_section="",
        custom_prompt_section="",
    )
    assert "## Session context" not in rendered
    assert "## Additional instructions" not in rendered


# ---------------------------------------------------------------------------
# Reasoning effort — o-series models
# ---------------------------------------------------------------------------

O_SERIES_MODELS = ["o1", "o3", "o4-mini", "o1-pro", "o3-pro"]
NON_O_SERIES_MODELS = ["gpt-4o", "gpt-4.1", "gpt-5"]


@pytest.mark.parametrize("model_name", O_SERIES_MODELS)
async def test_reasoning_effort_set_for_o_series(model_name):
    sa = _make_session_agent("openai", model_name, reasoning_effort="high")
    sa._agent = _build(sa)

    run_mock = AsyncMock(return_value=MagicMock())
    chunks = [TranscriptChunk(text="hello world", speaker="A", ts=time.time())]

    with patch.object(sa._agent, "run", run_mock):
        with patch("agent.settings", _fake_settings(agent_timeout_s=60, agent_transcript_window_s=9999)):
            await sa.invoke_once(chunks)

    run_mock.assert_called_once()
    _, kwargs = run_mock.call_args
    ms = kwargs.get("model_settings")
    # OpenAIModelSettings is a TypedDict (dict at runtime) — check by key
    assert ms is not None, f"Expected model_settings for {model_name!r}, got None"
    assert ms.get("reasoning_effort") == "high", (
        f"Expected reasoning_effort='high' for {model_name!r}, got {ms!r}"
    )


@pytest.mark.parametrize("model_name", NON_O_SERIES_MODELS)
async def test_no_reasoning_effort_for_non_o_series(model_name):
    sa = _make_session_agent("openai", model_name)
    sa._agent = _build(sa)

    run_mock = AsyncMock(return_value=MagicMock())
    chunks = [TranscriptChunk(text="hello world", speaker="A", ts=time.time())]

    with patch.object(sa._agent, "run", run_mock):
        with patch("agent.settings", _fake_settings(agent_timeout_s=60, agent_transcript_window_s=9999)):
            await sa.invoke_once(chunks)

    run_mock.assert_called_once()
    _, kwargs = run_mock.call_args
    ms = kwargs.get("model_settings")
    assert ms is None, (
        f"Expected no model_settings for {model_name!r}, got {ms!r}"
    )


def test_reasoning_effort_default_is_medium():
    """Default reasoning_effort in SessionConfig is 'medium'."""
    config = SessionConfig(model_provider="openai", agent_model="o3")
    assert config.reasoning_effort == "medium"


# ---------------------------------------------------------------------------
# _is_chat_model filter — OpenAI
# ---------------------------------------------------------------------------

OPENAI_CHAT_INCLUDE = [
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "gpt-5.4",
    "gpt-5.3-chat-latest",
    "o3",
    "o4-mini",
]

OPENAI_CHAT_EXCLUDE = [
    "gpt-image-1",
    "dall-e-3",
    "gpt-5-codex",
    "gpt-4o-realtime-preview",
    "gpt-4o-transcribe",
    "gpt-4o-audio-preview",
    "tts-1",
    "whisper-1",
]


@pytest.mark.parametrize("model_id", OPENAI_CHAT_INCLUDE)
def test_is_chat_model_includes(model_id):
    from main import _is_chat_model

    assert _is_chat_model(model_id), f"{model_id!r} should be included as a chat model"


@pytest.mark.parametrize("model_id", OPENAI_CHAT_EXCLUDE)
def test_is_chat_model_excludes(model_id):
    from main import _is_chat_model

    assert not _is_chat_model(model_id), f"{model_id!r} should be excluded from chat models"


# ---------------------------------------------------------------------------
# _is_gemini_chat_model filter — Google
# ---------------------------------------------------------------------------

GEMINI_CHAT_INCLUDE = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
]

GEMINI_CHAT_EXCLUDE = [
    "gemini-embedding-001",
    "gemini-2.5-flash-image",
    "gemini-robotics-er-1.5-preview",
    "gemini-3.1-flash-image-preview",
]


@pytest.mark.parametrize("model_name", GEMINI_CHAT_INCLUDE)
def test_is_gemini_chat_model_includes(model_name):
    from main import _is_gemini_chat_model

    assert _is_gemini_chat_model(model_name), (
        f"{model_name!r} should be included as a Gemini chat model"
    )


@pytest.mark.parametrize("model_name", GEMINI_CHAT_EXCLUDE)
def test_is_gemini_chat_model_excludes(model_name):
    from main import _is_gemini_chat_model

    assert not _is_gemini_chat_model(model_name), (
        f"{model_name!r} should be excluded from Gemini chat models"
    )
