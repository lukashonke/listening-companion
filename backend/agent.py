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
"""


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
        self._agent = self._build_agent()
        self._loop_task: asyncio.Task | None = None
        self._running = False
        self._last_transcript_count = 0

    def _build_agent(self):
        from pydantic_ai import Agent
        from pydantic_ai.models.anthropic import AnthropicModel

        model = AnthropicModel(
            settings.claude_model,
            api_key=settings.anthropic_api_key,
        )

        wrapped = [self._wrap_tool(t) for t in self._tools]

        # system_prompt is a callable so it is evaluated dynamically on each run,
        # reflecting the current short-term memory state.
        def dynamic_system_prompt() -> str:
            return SYSTEM_PROMPT_TEMPLATE.format(
                short_term_memory=self._get_short_term_context()
            )

        return Agent(model=model, tools=wrapped, system_prompt=dynamic_system_prompt)

    def _wrap_tool(self, fn: Callable) -> Callable:
        """Wrap a tool to emit tool_call WS events on each invocation."""
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                tool_args = {param_names[i]: v for i, v in enumerate(args) if i < len(param_names)}
                tool_args.update(kwargs)
                result = error = None
                try:
                    result = await fn(*args, **kwargs)
                except Exception as exc:
                    error = str(exc)
                    result = f"Tool error: {exc}"
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
                await self._agent.run(user_prompt)
        except asyncio.TimeoutError:
            logger.warning("Agent timed out after %ds", settings.agent_timeout_s)
        except Exception as exc:
            logger.error("Agent invocation failed: %s", exc)
        finally:
            await self._emit_agent_done()
