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

# Default max characters for transcript context before trimming.
DEFAULT_MAX_TRANSCRIPT_CHARS = 30000

# Memory-related tool names that get only a brief mention in context.
_MEMORY_TOOLS = frozenset({
    "save_short_term_memory",
    "update_short_term_memory",
    "remove_short_term_memory",
    "save_long_term_memory",
    "search_long_term_memory",
})

# Tools whose full args should be included in context.
_IMAGE_TOOLS = frozenset({"generate_image"})
_TTS_TOOLS = frozenset({"answer_tts"})


def format_tool_call_history(tool_log: list[dict]) -> str:
    """Format tool call history compactly for agent context.

    Different detail levels per tool type:
    - Image generation: include full parameters (prompt, style, provider, model)
    - TTS (speak): include the full spoken text so agent doesn't repeat
    - Memory tools: brief mention only (agent can see current memory directly)
    """
    if not tool_log:
        return ""

    lines = ["[Tool calls]"]
    for entry in tool_log:
        tool_name = entry.get("tool", "unknown")
        args = entry.get("args", {})

        if tool_name in _MEMORY_TOOLS:
            # Brief mention — agent can see current memory state directly
            lines.append(f"- {tool_name}() -> done")
        elif tool_name in _IMAGE_TOOLS:
            # Include full parameters for image generation
            params = ", ".join(f"{k}='{v}'" for k, v in args.items() if v)
            lines.append(f"- {tool_name}({params}) -> image saved")
        elif tool_name in _TTS_TOOLS:
            # Include full text that was spoken
            text = args.get("text", "")
            lines.append(f"- {tool_name}(text='{text}')")
        else:
            # Other tools: include args compactly
            params = ", ".join(f"{k}='{v}'" for k, v in args.items() if v)
            lines.append(f"- {tool_name}({params})")

    return "\n".join(lines)


def build_transcript_context(
    transcript: list[TranscriptChunk],
    max_chars: int = DEFAULT_MAX_TRANSCRIPT_CHARS,
) -> str:
    """Build full transcript context, trimming oldest entries if too long.

    Returns the conversation formatted as speaker-labeled lines. When the
    total exceeds *max_chars*, the oldest entries are dropped and a note is
    prepended indicating some history was trimmed.
    """
    if not transcript:
        return ""

    # Format all chunks
    formatted = [
        f"[{c.speaker} {c.ts:.0f}] {c.text}" for c in transcript
    ]

    full_text = "\n".join(formatted)

    if len(full_text) <= max_chars:
        return full_text

    # Trim from the start — keep the most recent entries
    trimmed_lines: list[str] = []
    current_len = 0
    for line in reversed(formatted):
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_chars:
            break
        trimmed_lines.append(line)
        current_len += line_len

    trimmed_lines.reverse()
    return "(earlier transcript trimmed)\n" + "\n".join(trimmed_lines)


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
- Generate images when the conversation references something visual{image_style_section}
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
        # Transcript trigger state
        self._invoke_running = False  # True while an agent invocation is in progress
        self._last_invoke_time: float = 0.0  # monotonic time of last invocation start
        self._get_transcript: Callable[[], list[TranscriptChunk]] | None = None
        self._get_tool_call_log: Callable[[], list[dict]] | None = None

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
            image_style_section = ""
            if config.image_prompt_theme:
                image_style_section = f"\n  - When generating images, always incorporate this style/theme: {config.image_prompt_theme}"

            # R20: Use full_system_prompt as complete override when non-empty
            template = config.full_system_prompt if config.full_system_prompt else SYSTEM_PROMPT_TEMPLATE

            # Apply variable substitution — unknown variables are left as-is
            # to avoid KeyError for user prompts that don't use all variables.
            substitutions = {
                "short_term_memory": get_context(),
                "theme_section": theme_section,
                "custom_prompt_section": custom_prompt_section,
                "image_style_section": image_style_section,
            }
            try:
                return template.format(**substitutions)
            except KeyError:
                # If the custom template has unknown placeholders, do partial substitution
                result = template
                for key, value in substitutions.items():
                    result = result.replace("{" + key + "}", value)
                return result

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
        self,
        get_transcript: Callable[[], list[TranscriptChunk]],
        get_tool_call_log: Callable[[], list[dict]] | None = None,
    ) -> None:
        self._running = True
        self._get_transcript = get_transcript
        self._get_tool_call_log = get_tool_call_log

        if self._config.agent_trigger_mode == "timer":
            # Legacy timer-based mode
            self._loop_task = asyncio.create_task(
                self._agent_loop(get_transcript, get_tool_call_log)
            )
        else:
            # Transcript-trigger mode: build agent eagerly, no timer loop
            try:
                self._agent = self._build_agent()
            except Exception as exc:
                logger.error("Agent build failed: %s", exc)
                return

    async def stop_loop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def trigger_agent_run(
        self,
        get_transcript: Callable[[], list[TranscriptChunk]] | None = None,
        get_tool_call_log: Callable[[], list[dict]] | None = None,
    ) -> None:
        """Trigger an agent invocation if one isn't already running.

        Used in transcript trigger mode. Respects a minimum cooldown between
        runs to avoid excessive LLM calls for rapid transcripts. If the agent
        IS already running, the trigger is silently skipped (no queuing).
        """
        if self._invoke_running:
            logger.debug("Agent trigger skipped — already running")
            return

        # Check cooldown
        now = time.monotonic()
        cooldown = self._config.agent_trigger_cooldown_s
        elapsed = now - self._last_invoke_time
        if elapsed < cooldown:
            logger.debug(
                "Agent trigger skipped — cooldown (%.1fs < %.1fs)",
                elapsed, cooldown,
            )
            return

        # Use provided getters or fall back to stored ones
        transcript_fn = get_transcript or self._get_transcript
        tool_log_fn = get_tool_call_log or self._get_tool_call_log

        if not transcript_fn:
            logger.debug("Agent trigger skipped — no transcript getter")
            return

        # Fire and forget the invocation in a task
        asyncio.create_task(self._run_triggered_invocation(transcript_fn, tool_log_fn))

    async def _run_triggered_invocation(
        self,
        get_transcript: Callable[[], list[TranscriptChunk]],
        get_tool_call_log: Callable[[], list[dict]] | None = None,
    ) -> None:
        """Execute a single agent invocation as a triggered task."""
        self._invoke_running = True
        self._last_invoke_time = time.monotonic()
        try:
            tool_log = get_tool_call_log() if get_tool_call_log else []
            await self.invoke_once(get_transcript(), tool_call_log=tool_log)
        except Exception as exc:
            logger.error("Triggered agent invocation failed: %s", exc)
        finally:
            self._invoke_running = False

    async def _agent_loop(
        self,
        get_transcript: Callable[[], list[TranscriptChunk]],
        get_tool_call_log: Callable[[], list[dict]] | None = None,
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
                tool_log = get_tool_call_log() if get_tool_call_log else []
                await self.invoke_once(get_transcript(), tool_call_log=tool_log)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Agent loop error (skipping cycle): %s", exc)

    async def invoke_once(
        self,
        transcript: list[TranscriptChunk],
        tool_call_log: list[dict] | None = None,
    ) -> None:
        """Run one agent invocation with full conversation context.

        Provides the agent with:
        - Full transcript history (or a trimmed rolling window if too long)
        - Compact tool call history with detail levels per tool type
        """
        if self._agent is None:
            logger.debug("Agent not yet built — skipping invocation")
            return

        # Detect whether there are new chunks since last invocation
        if len(transcript) <= self._last_transcript_count:
            logger.debug("Agent skipping — no new transcript")
            return

        self._last_transcript_count = len(transcript)

        # Build full transcript context (with trimming if too long)
        transcript_text = build_transcript_context(transcript)
        if not transcript_text:
            return

        # Build the user prompt with full conversation context
        parts: list[str] = []
        parts.append("## Conversation transcript")
        parts.append(transcript_text)

        # Include tool call history if available
        if tool_call_log:
            tool_history = format_tool_call_history(tool_call_log)
            if tool_history:
                parts.append("")
                parts.append("## Previous tool calls this session")
                parts.append(tool_history)

        user_prompt = "\n".join(parts)

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
