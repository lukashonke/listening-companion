"""Tests for full_system_prompt feature (R20).

Verifies:
- Custom full system prompt used when provided
- Fallback to built-in when empty
- Variable substitution works in custom prompt
- GET /api/default-system-prompt returns the built-in template
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from models import SessionConfig


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


def _make_session_agent(config: SessionConfig, context: str = "no memory"):
    from agent import SessionAgent

    return SessionAgent(
        session_config=config,
        tools=[],
        get_short_term_context=lambda: context,
        emit_agent_start=_noop,
        emit_agent_done=_noop,
        emit_tool_call=_noop,
    )


def _render_system_prompt(agent) -> str:
    runner = agent._system_prompt_functions[0]
    return runner.function()


def _build(sa):
    with patch("agent.settings", _fake_settings()):
        return sa._build_agent()


# ---------------------------------------------------------------------------
# Test: fallback to built-in when full_system_prompt is empty
# ---------------------------------------------------------------------------

class TestFullSystemPromptFallback:
    def test_empty_full_prompt_uses_builtin(self):
        """When full_system_prompt is empty, the built-in SYSTEM_PROMPT_TEMPLATE is used."""
        config = SessionConfig(full_system_prompt="")
        sa = _make_session_agent(config, context="test memory")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "AI listening companion" in prompt
        assert "test memory" in prompt

    def test_default_config_uses_builtin(self):
        """Default SessionConfig (no full_system_prompt set) uses built-in prompt."""
        config = SessionConfig()
        sa = _make_session_agent(config, context="default mem")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "AI listening companion" in prompt
        assert "default mem" in prompt


# ---------------------------------------------------------------------------
# Test: custom full system prompt used when provided
# ---------------------------------------------------------------------------

class TestFullSystemPromptCustom:
    def test_custom_prompt_replaces_builtin(self):
        """When full_system_prompt is set, it replaces the built-in template entirely."""
        custom = "You are a pirate captain. Memory: {short_term_memory}"
        config = SessionConfig(full_system_prompt=custom)
        sa = _make_session_agent(config, context="treasure map")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "pirate captain" in prompt
        assert "treasure map" in prompt
        # Built-in content should NOT be present
        assert "AI listening companion" not in prompt

    def test_custom_prompt_variable_substitution_theme(self):
        """Variable {theme_section} is substituted in custom prompt."""
        custom = "Custom agent. Theme: {theme_section}Memory: {short_term_memory}"
        config = SessionConfig(
            full_system_prompt=custom,
            theme="D&D Campaign",
        )
        sa = _make_session_agent(config, context="elves spotted")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "D&D Campaign" in prompt
        assert "elves spotted" in prompt

    def test_custom_prompt_variable_substitution_all(self):
        """All standard variables are available for substitution."""
        custom = (
            "Agent v2.\n"
            "Memory: {short_term_memory}\n"
            "{theme_section}"
            "{custom_prompt_section}"
            "{image_style_section}"
        )
        config = SessionConfig(
            full_system_prompt=custom,
            theme="Meeting",
            custom_system_prompt="Be formal",
            image_prompt_theme="corporate style",
        )
        sa = _make_session_agent(config, context="action items")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "Agent v2" in prompt
        assert "action items" in prompt
        assert "Meeting" in prompt
        assert "Be formal" in prompt
        assert "corporate style" in prompt

    def test_custom_prompt_without_variables(self):
        """Custom prompt without any template variables is used as-is."""
        custom = "You are a simple bot. No variables here."
        config = SessionConfig(full_system_prompt=custom)
        sa = _make_session_agent(config, context="some memory")
        agent = _build(sa)
        prompt = _render_system_prompt(agent)

        assert "simple bot" in prompt
        # Since no {short_term_memory} variable, memory won't appear
        assert "some memory" not in prompt


# ---------------------------------------------------------------------------
# Test: GET /api/default-system-prompt endpoint
# ---------------------------------------------------------------------------

class TestDefaultSystemPromptEndpoint:
    @pytest.fixture
    def app(self):
        from main import app
        return app

    async def test_returns_template(self, app):
        """GET /api/default-system-prompt returns the built-in template string."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/default-system-prompt")

        assert resp.status_code == 200
        data = resp.json()
        assert "template" in data
        assert "AI listening companion" in data["template"]
        assert "{short_term_memory}" in data["template"]

    async def test_template_contains_variables(self, app):
        """The returned template contains all substitution variables."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/default-system-prompt")

        template = resp.json()["template"]
        assert "{short_term_memory}" in template
        assert "{theme_section}" in template
        assert "{custom_prompt_section}" in template
        assert "{image_style_section}" in template


# ---------------------------------------------------------------------------
# Test: full_system_prompt field in SessionConfig
# ---------------------------------------------------------------------------

class TestSessionConfigField:
    def test_default_is_empty_string(self):
        config = SessionConfig()
        assert config.full_system_prompt == ""

    def test_can_set_custom_prompt(self):
        config = SessionConfig(full_system_prompt="Custom prompt here")
        assert config.full_system_prompt == "Custom prompt here"
