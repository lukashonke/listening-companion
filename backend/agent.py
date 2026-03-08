"""Pydantic AI agent builder and invocation loop."""
from __future__ import annotations
import asyncio
import functools
import inspect
import logging
import time
from typing import Callable, Awaitable

from config import settings
from models import TranscriptChunk, SessionConfig

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """\
You are an AI listening companion. You listen to ongoing conversations and help \
the user by maintaining context, tracking important information, and responding when helpful.

## Current short-term memory
{short_term_memory}

## Your capabilities
You have tools to:
- Manage short-term memory (save, update, remove entries by ID)
- Archive to long-term memory and search past conversations
- Speak responses aloud (answer_tts) — use sparingly, only when genuinely helpful
- Generate images when the conversation references something visual
- Track entities, action items, quotes (if those tools are enabled)

## Guidelines
- Be concise and act on what is NEW in the transcript
- Don't repeat actions you have already taken in this session
- If nothing meaningful happened, do nothing — it is fine to call no tools
- Reference memory entries by their ID when updating or removing them
{theme_section}{custom_prompt_section}"""


class SessionAgent:
    """Manages the Pydantic AI agent lifecycle for one session."""

    def __init__(
        self,
        session_config: SessionConfig,
        tools: list[Callable],
        get_short_term_context: Callable[[], str],
        emit_agent_start: Callable[[], Awaitable[None]],
        emit_agent_done: Callable[[], Awaitable[None]],
        emit_tool_call: Callable[[str, dict, object, str | None], Awaitable[None]],
    ):
        self._config = session_config
        self._tools = tools
        self._get_short_term_context = get_short_term_context
        self._emit_agent_start = emit_agent_start
        self._emit_agent_done = emit_agent_done
        self._emit_tool_call = emit_tool_call
        self._agent = None  # built lazily in start_loop
        self._loop_task: asyncio.Task | None = None
        self._running = False
        self._last_transcript_count = 0

    def _build_agent(self):
        from pydantic_ai import Agent

        provider = self._config.model_provider or "anthropic"

        if provider == "openai":
            from pydantic_ai.models.openai import OpenAIModel
            from pydantic_ai.providers.openai import OpenAIProvider
            model_name = self._config.agent_model or "gpt-4o"
            model = OpenAIModel(
                model_name,
                provider=OpenAIProvider(api_key=settings.openai_api_key),
            )
        elif provider == "google":
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider
            model_name = self._config.agent_model or "gemini-2.5-flash"
            model = GoogleModel(
                model_name,
                provider=GoogleProvider(api_key=settings.google_api_key),
            )
        else:
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider
            model_name = self._config.agent_model or settings.claude_model
            model = AnthropicModel(
                model_name,
                provider=AnthropicProvider(api_key=settings.anthropic_api_key),
            )

        wrapped = [self._wrap_tool(t) for t in self._tools]

        agent = Agent(model=model, tools=wrapped)

        # Use the @agent.system_prompt decorator so it is evaluated dynamically
        # on each run, reflecting the current short-term memory state.
        get_context = self._get_short_term_context
        config = self._config

        @agent.system_prompt
        def dynamic_system_prompt() -> str:
            theme_section = ""
            if config.theme:
                theme_section = f"\n## Session context\nThis session is: {config.theme}\nAdapt your behavior accordingly (e.g., track initiative in D&D, track action items in meetings).\n"
            custom_prompt_section = ""
            if config.custom_system_prompt:
                custom_prompt_section = f"\n## Additional instructions\n{config.custom_system_prompt}\n"
            return SYSTEM_PROMPT_TEMPLATE.format(
                short_term_memory=get_context(),
                theme_section=theme_section,
                custom_prompt_section=custom_prompt_section,
            )

        return agent

    def _wrap_tool(self, fn: Callable) -> Callable:
        """Wrap a tool to emit tool_call WS events on each invocation."""
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                tool_args = {param_names[i]: v for i, v in enumerate(args) if i < len(param_names)}
                tool_args.update(kwargs)
                logger.info("Tool invoked: %s args=%s", fn.__name__, list(tool_args.keys()))
                result = error = None
                try:
                    result = await fn(*args, **kwargs)
                except Exception as exc:
                    error = str(exc)
                    result = f"Tool error: {exc}"
                    logger.error("Tool %s raised: %s", fn.__name__, exc)
                logger.info("Tool %s completed — emitting tool_call event", fn.__name__)
                await self._emit_tool_call(fn.__name__, tool_args, result, error)
                return result
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                tool_args = {param_names[i]: v for i, v in enumerate(args) if i < len(param_names)}
                tool_args.update(kwargs)
                result = error = None
                try:
                    result = fn(*args, **kwargs)
                except Exception as exc:
                    error = str(exc)
                    result = f"Tool error: {exc}"
                asyncio.create_task(self._emit_tool_call(fn.__name__, tool_args, result, error))
                return result
            return sync_wrapper

    async def start_loop(
        self, get_transcript: Callable[[], list[TranscriptChunk]]
    ) -> None:
        self._running = True
        self._loop_task = asyncio.create_task(
            self._agent_loop(get_transcript)
        )

    async def stop_loop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _agent_loop(
        self, get_transcript: Callable[[], list[TranscriptChunk]]
    ) -> None:
        # Build the agent lazily inside the loop task so that start_loop() never
        # raises — this ensures session_status:listening is always emitted even
        # when the Anthropic API key is absent.
        try:
            self._agent = self._build_agent()
        except Exception as exc:
            logger.error("Agent build failed — loop will not run: %s", exc)
            return

        while self._running:
            await asyncio.sleep(self._config.agent_interval_s)
            if not self._running:
                break
            try:
                await self.invoke_once(get_transcript())
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Agent loop error (skipping cycle): %s", exc)

    async def invoke_once(self, transcript: list[TranscriptChunk]) -> None:
        """Run one agent invocation with current transcript."""
        if self._agent is None:
            logger.debug("Agent not yet built — skipping invocation")
            return
        new_chunks = transcript[self._last_transcript_count:]
        if not new_chunks:
            logger.debug("Agent skipping — no new transcript")
            return

        self._last_transcript_count = len(transcript)

        cutoff = time.time() - settings.agent_transcript_window_s
        window = [c for c in new_chunks if c.ts >= cutoff]
        if not window:
            return

        transcript_text = "\n".join(
            f"[{c.speaker} {c.ts:.0f}] {c.text}" for c in window
        )
        user_prompt = f"New transcript:\n{transcript_text}"

        await self._emit_agent_start()
        try:
            async with asyncio.timeout(settings.agent_timeout_s):
                model_settings = None
                # Pass reasoning_effort for OpenAI o-series reasoning models
                if self._config.model_provider == "openai":
                    model_name = self._config.agent_model or ""
                    if any(model_name.startswith(p) for p in ("o1", "o3", "o4")):
                        from pydantic_ai.models.openai import OpenAIModelSettings
                        model_settings = OpenAIModelSettings(
                            reasoning_effort=self._config.reasoning_effort or "medium"
                        )
                await self._agent.run(user_prompt, model_settings=model_settings)
        except asyncio.TimeoutError:
            logger.warning("Agent timed out after %ds", settings.agent_timeout_s)
        except Exception as exc:
            logger.error("Agent invocation failed: %s", exc)
        finally:
            await self._emit_agent_done()
