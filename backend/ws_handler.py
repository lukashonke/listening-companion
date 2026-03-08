"""WebSocket handler — session lifecycle and audio pipeline orchestration."""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from database import get_db
from models import (
    SessionConfig,
    TranscriptChunk,
    WsTranscriptChunk,
    WsAgentStart,
    WsAgentDone,
    WsToolCall,
    WsMemoryUpdate,
    WsImageGenerated,
    WsTtsChunk,
    WsError,
    WsSessionStatus,
    WsLog,
    WsSessionNameUpdate,
    WsSessionSummaryUpdate,
)
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from stt import ScribeSTT
from agent import SessionAgent
from tools.memory_ops import build_memory_tools
from tools.tts_tool import build_tts_tool
from tools.image_tool import build_image_tool
from tools import get_plugin_tools

logger = logging.getLogger(__name__)


class WebSocketLogHandler(logging.Handler):
    """Forwards log records to the active WebSocket session as WsLog events."""

    def __init__(self, session: "ActiveSession") -> None:
        super().__init__()
        self._session = session
        self._loop = asyncio.get_event_loop()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            level = record.levelname  # DEBUG / INFO / WARNING / ERROR / CRITICAL
            event = WsLog(level=level, message=msg)  # type: ignore[arg-type]
            asyncio.run_coroutine_threadsafe(
                self._session._emit(event), self._loop
            )
        except Exception:
            self.handleError(record)


class ActiveSession:
    """One active listening session, tied to a single WebSocket connection."""

    def __init__(self, ws: WebSocket, config: SessionConfig, name: str = "", resume_session_id: str | None = None, name_source: str = "default"):
        self.id = resume_session_id if resume_session_id else f"sess_{uuid.uuid4().hex[:12]}"
        self.ws = ws
        self.config = config
        self.name = name
        self.name_source = name_source
        self._resume = resume_session_id is not None
        self.transcript: list[TranscriptChunk] = []
        self.transcript_chunk_count: int = 0
        self._auto_naming_in_progress: bool = False
        self._tool_call_log: list[dict] = []
        self._summarization_timer: asyncio.Task | None = None
        self._summarization_in_progress: bool = False
        self._db = None
        self._short_term: ShortTermMemory | None = None
        self._long_term: LongTermMemory | None = None
        self._stt: ScribeSTT | None = None
        self._agent: SessionAgent | None = None
        self._log_handler: WebSocketLogHandler | None = None

    async def setup(self) -> None:
        """Initialize all session components."""
        # Attach WS log handler so all backend logs stream to the browser
        self._log_handler = WebSocketLogHandler(self)
        self._log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logging.getLogger().addHandler(self._log_handler)

        self._db = await get_db()

        if self._resume:
            # Re-open existing session: clear ended_at and update name/config
            await self._db.execute(
                "UPDATE sessions SET ended_at = NULL, name = ?, config = ? WHERE id = ?",
                (self.name, self.config.model_dump_json(), self.id),
            )
            # Load existing name_source from DB if resuming
            async with self._db.execute(
                "SELECT name_source FROM sessions WHERE id = ?", (self.id,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    self.name_source = row[0] or "default"
            logger.info("Resuming session %s", self.id)
        else:
            # Persist new session row
            await self._db.execute(
                "INSERT OR IGNORE INTO sessions (id, name, name_source, created_at, config) VALUES (?, ?, ?, ?, ?)",
                (self.id, self.name, self.name_source, time.time(), self.config.model_dump_json()),
            )
        await self._db.commit()

        # Memory
        self._short_term = ShortTermMemory(self.id, self._db)
        self._long_term = LongTermMemory(self.id, self._db)
        await self._short_term.load()

        # Build session-bound tools (closures over this session's memory + emit fns)
        memory_tools = build_memory_tools(
            self._short_term,
            self._long_term,
            self._emit_memory_update,
        )
        tts_tool = build_tts_tool(self.config.voice_id, self._emit_tts_chunk, tts_language=self.config.tts_language)
        image_tool = build_image_tool(
            self.config.image_provider,
            self._emit_image_generated,
            model=self.config.image_model,
            session_id=self.id,
            db=self._db,
            storage_path=settings.image_storage_path,
        )
        plugin_tools = get_plugin_tools(self.config.tools)

        all_tools = memory_tools + [tts_tool, image_tool] + plugin_tools

        # Agent
        self._agent = SessionAgent(
            session_config=self.config,
            tools=all_tools,
            get_short_term_context=self._short_term.as_context_str,
            emit_agent_start=self._emit_agent_start,
            emit_agent_done=self._emit_agent_done,
            emit_tool_call=self._emit_tool_call,
        )

        # STT
        self._stt = ScribeSTT(
            on_transcript=self._on_transcript,
            speaker_diarization=self.config.speaker_diarization,
        )
        await self._stt.start()

        # Start agent loop (pass tool call log so agent has full context)
        await self._agent.start_loop(
            get_transcript=lambda: self.transcript,
            get_tool_call_log=lambda: self._tool_call_log,
        )

        # Start auto-summarization timer if enabled
        if self.config.auto_summarization_enabled:
            self._summarization_timer = asyncio.create_task(self._summarization_loop())

        await self._emit(WsSessionStatus(state="listening"))
        # If resuming, push existing memory to the frontend immediately
        if self._resume and self._short_term:
            await self._emit_memory_update()
        logger.info("Session %s started (tools: %s)", self.id, self.config.tools)

    async def teardown(self) -> None:
        """Gracefully shut down all session components."""
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None
        # Cancel summarization timer
        if self._summarization_timer and not self._summarization_timer.done():
            self._summarization_timer.cancel()
            try:
                await self._summarization_timer
            except asyncio.CancelledError:
                pass
            self._summarization_timer = None
        if self._agent:
            await self._agent.stop_loop()
        if self._stt:
            await self._stt.stop()
        if self._db:
            try:
                await self._db.execute(
                    "UPDATE sessions SET ended_at = ? WHERE id = ?",
                    (time.time(), self.id),
                )
                await self._db.commit()
            except Exception as exc:
                logger.warning("Session teardown DB error: %s", exc)
        await self._emit(WsSessionStatus(state="idle"))
        logger.info("Session %s ended", self.id)

    async def handle_audio(self, data: bytes) -> None:
        """Forward raw PCM audio bytes to the Scribe STT bridge."""
        if self._stt:
            await self._stt.send_audio(data)

    async def handle_config_update(self, config_patch: dict) -> None:
        """Apply partial config overrides, validated through Pydantic."""
        try:
            self.config = self.config.model_copy(update=config_patch)
        except Exception as exc:
            logger.warning("Invalid config_update ignored: %s", exc)

    # ── Internal callbacks ─────────────────────────────────────────────────────

    async def _on_transcript(self, text: str, speaker: str) -> None:
        chunk = TranscriptChunk(text=text, speaker=speaker)
        self.transcript.append(chunk)
        self.transcript_chunk_count += 1
        await self._emit(WsTranscriptChunk(text=text, speaker=speaker, ts=chunk.ts))
        # Trigger auto-naming check (fire and forget)
        asyncio.create_task(self._auto_name_task())

    # ── Auto-naming ──────────────────────────────────────────────────────────

    async def _auto_name_task(self) -> None:
        """Check if auto-naming should trigger and call LLM if so."""
        if not self.config.auto_naming_enabled:
            return
        if self.name_source == "user":
            return
        if self._auto_naming_in_progress:
            return

        first_trigger = self.config.auto_naming_first_trigger
        repeat_interval = self.config.auto_naming_repeat_interval
        count = self.transcript_chunk_count

        should_trigger = False
        if count == first_trigger:
            should_trigger = True
        elif count > first_trigger and repeat_interval > 0:
            chunks_after_first = count - first_trigger
            if chunks_after_first % repeat_interval == 0:
                should_trigger = True

        if not should_trigger:
            return

        self._auto_naming_in_progress = True
        try:
            # Gather recent transcript text (last ~20 chunks)
            recent = self.transcript[-20:]
            transcript_text = "\n".join(
                f"[{c.speaker}] {c.text}" for c in recent
            )

            is_re_eval = self.name_source == "auto"
            current_name = self.name if is_re_eval else None

            new_name = await self._infer_session_name(transcript_text, current_name)
            if new_name and new_name != self.name:
                self.name = new_name
                self.name_source = "auto"
                # Persist to DB
                if self._db:
                    await self._db.execute(
                        "UPDATE sessions SET name = ?, name_source = 'auto' WHERE id = ?",
                        (new_name, self.id),
                    )
                    await self._db.commit()
                # Emit WS event
                await self._emit(WsSessionNameUpdate(name=new_name, name_source="auto"))
                logger.info("Auto-named session %s: %s", self.id, new_name)
        except Exception as exc:
            logger.warning("Auto-naming failed: %s", exc)
        finally:
            self._auto_naming_in_progress = False

    async def _infer_session_name(self, transcript_text: str, current_name: str | None = None) -> str | None:
        """Make a simple LLM call to infer a session name from transcript content."""
        if current_name:
            prompt = (
                f"You are naming a conversation session. The current auto-generated name is: \"{current_name}\"\n\n"
                f"Here is the recent transcript:\n{transcript_text}\n\n"
                "Based on the transcript, is the current name still accurate? "
                "If yes, respond with the same name. If not, suggest a better name.\n"
                "Rules: 2-5 words, concise, descriptive of the main topic. "
                "Respond with ONLY the name, nothing else."
            )
        else:
            prompt = (
                f"You are naming a conversation session. Here is the transcript so far:\n{transcript_text}\n\n"
                "Suggest a concise, descriptive name for this session (2-5 words). "
                "The name should capture the main topic or theme of the conversation.\n"
                "Respond with ONLY the name, nothing else."
            )

        try:
            from pydantic_ai import Agent

            provider = self.config.model_provider or "anthropic"
            if provider == "openai":
                from pydantic_ai.models.openai import OpenAIModel
                from pydantic_ai.providers.openai import OpenAIProvider
                model_name = self.config.agent_model or "gpt-4o"
                model = OpenAIModel(
                    model_name,
                    provider=OpenAIProvider(api_key=settings.openai_api_key),
                )
            elif provider == "google":
                from pydantic_ai.models.google import GoogleModel
                from pydantic_ai.providers.google import GoogleProvider
                model_name = self.config.agent_model or "gemini-2.5-flash"
                model = GoogleModel(
                    model_name,
                    provider=GoogleProvider(api_key=settings.google_api_key),
                )
            else:
                from pydantic_ai.models.anthropic import AnthropicModel
                from pydantic_ai.providers.anthropic import AnthropicProvider
                model_name = self.config.agent_model or settings.claude_model
                model = AnthropicModel(
                    model_name,
                    provider=AnthropicProvider(api_key=settings.anthropic_api_key),
                )

            agent = Agent(model=model)
            result = await agent.run(prompt)
            name = result.output.strip().strip('"').strip("'")
            # Limit to reasonable length
            if len(name) > 100:
                name = name[:100]
            return name if name else None
        except Exception as exc:
            logger.warning("LLM call for auto-naming failed: %s", exc)
            return None

    # ── Auto-summarization ──────────────────────────────────────────────────

    async def _summarization_loop(self) -> None:
        """Background loop that triggers summarization at configured intervals."""
        try:
            while True:
                await asyncio.sleep(self.config.auto_summarization_interval)
                await self._run_summarization()
        except asyncio.CancelledError:
            pass

    async def _run_summarization(self) -> None:
        """Run a single summarization cycle."""
        if not self.config.auto_summarization_enabled:
            return
        if not self.transcript:
            return
        if self._summarization_in_progress:
            return

        self._summarization_in_progress = True
        try:
            # Gather transcript text
            transcript_text = "\n".join(
                f"[{c.speaker}] {c.text}" for c in self.transcript
            )

            # Gather tool call previews (~50 chars each)
            tool_previews = ""
            if self._tool_call_log:
                previews = []
                for tc in self._tool_call_log:
                    tool_name = tc.get("tool", "unknown")
                    args_str = str(tc.get("args", {}))
                    preview = f"{tool_name}: {args_str}"
                    if len(preview) > 50:
                        preview = preview[:47] + "..."
                    previews.append(preview)
                tool_previews = "\n".join(previews)

            # Get previous summary from DB
            previous_summary = ""
            if self._db:
                async with self._db.execute(
                    "SELECT summary FROM sessions WHERE id = ?", (self.id,)
                ) as cur:
                    row = await cur.fetchone()
                    if row and row[0]:
                        previous_summary = row[0]

            # Trim transcript if too long
            max_len = self.config.auto_summarization_max_transcript_length
            if len(transcript_text) > max_len:
                # Keep recent content (trim from the start)
                transcript_text = transcript_text[-max_len:]
                # Try to start at a clean line boundary
                newline_pos = transcript_text.find("\n")
                if newline_pos > 0 and newline_pos < 200:
                    transcript_text = transcript_text[newline_pos + 1:]

            # Call LLM for summarization
            summary = await self._call_summarization_llm(
                transcript_text=transcript_text,
                tool_previews=tool_previews,
                previous_summary=previous_summary,
            )

            if summary:
                # Store summary in DB
                if self._db:
                    await self._db.execute(
                        "UPDATE sessions SET summary = ? WHERE id = ?",
                        (summary, self.id),
                    )
                    await self._db.commit()

                # Emit WS event
                await self._emit(WsSessionSummaryUpdate(summary=summary))
                logger.info("Auto-summarization updated for session %s", self.id)

        except Exception as exc:
            logger.warning("Auto-summarization failed: %s", exc)
        finally:
            self._summarization_in_progress = False

    async def _call_summarization_llm(
        self,
        transcript_text: str,
        tool_previews: str,
        previous_summary: str,
    ) -> str | None:
        """Make a simple LLM call to generate a session summary."""
        parts = []
        parts.append(
            "Given the following conversation transcript and previous summary, "
            "provide an updated comprehensive summary."
        )
        if previous_summary:
            parts.append(f"\nPrevious summary: {previous_summary}")
        if tool_previews:
            parts.append(f"\nTool activity: {tool_previews}")
        parts.append(f"\nRecent transcript: {transcript_text}")
        parts.append("\nProvide a concise but thorough summary.")

        prompt = "\n".join(parts)

        try:
            from pydantic_ai import Agent

            provider = self.config.model_provider or "anthropic"
            if provider == "openai":
                from pydantic_ai.models.openai import OpenAIModel
                from pydantic_ai.providers.openai import OpenAIProvider
                model_name = self.config.agent_model or "gpt-4o"
                model = OpenAIModel(
                    model_name,
                    provider=OpenAIProvider(api_key=settings.openai_api_key),
                )
            elif provider == "google":
                from pydantic_ai.models.google import GoogleModel
                from pydantic_ai.providers.google import GoogleProvider
                model_name = self.config.agent_model or "gemini-2.5-flash"
                model = GoogleModel(
                    model_name,
                    provider=GoogleProvider(api_key=settings.google_api_key),
                )
            else:
                from pydantic_ai.models.anthropic import AnthropicModel
                from pydantic_ai.providers.anthropic import AnthropicProvider
                model_name = self.config.agent_model or settings.claude_model
                model = AnthropicModel(
                    model_name,
                    provider=AnthropicProvider(api_key=settings.anthropic_api_key),
                )

            agent = Agent(model=model)
            result = await agent.run(prompt)
            summary = result.output.strip()
            return summary if summary else None
        except Exception as exc:
            logger.warning("LLM call for auto-summarization failed: %s", exc)
            return None

    # ── Emit helpers ───────────────────────────────────────────────────────────

    async def _emit(self, event) -> None:
        try:
            await self.ws.send_text(event.model_dump_json())
        except Exception as exc:
            logger.debug("WS emit failed: %s", exc)

    async def _emit_agent_start(self) -> None:
        await self._emit(WsAgentStart())

    async def _emit_agent_done(self) -> None:
        await self._emit(WsAgentDone())

    async def _emit_tool_call(
        self, tool: str, args: dict, result: object, error: str | None
    ) -> None:
        result_val = result if not isinstance(result, Exception) else str(result)
        await self._emit(WsToolCall(tool=tool, args=args, result=result_val, error=error))
        # Track tool calls for summarization context
        self._tool_call_log.append({"tool": tool, "args": args, "ts": time.time()})

    async def _emit_memory_update(self) -> None:
        if self._short_term:
            await self._emit(WsMemoryUpdate(short_term=self._short_term.all()))

    async def _emit_tts_chunk(self, audio_b64: str, text: str) -> None:
        await self._emit(WsTtsChunk(audio_b64=audio_b64, text=text))

    async def _emit_image_generated(self, url: str, prompt: str) -> None:
        await self._emit(WsImageGenerated(url=url, prompt=prompt))

    async def emit_error(self, code: str, message: str, fatal: bool = False) -> None:
        await self._emit(WsError(code=code, message=message, fatal=fatal))


async def websocket_handler(ws: WebSocket) -> None:
    """Main WebSocket endpoint — drives the full session lifecycle."""
    await ws.accept()
    client = getattr(ws, "client", None)
    client_info = f"{client.host}:{client.port}" if client else "unknown"
    logger.info("WebSocket client connected: %s", client_info)
    session: ActiveSession | None = None

    try:
        while True:
            msg = await ws.receive()

            if msg["type"] == "websocket.disconnect":
                break

            if msg["type"] != "websocket.receive":
                continue

            # Binary frame → raw PCM audio
            if msg.get("bytes"):
                if session:
                    logger.info("Audio chunk received: %d bytes", len(msg["bytes"]))
                    await session.handle_audio(msg["bytes"])
                continue

            # Text frame → JSON control message
            raw_text = msg.get("text", "")
            if not raw_text:
                continue

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.debug("Ignoring non-JSON WS frame")
                continue

            msg_type = data.get("type")

            if msg_type == "session_start":
                # Tear down existing session if any
                if session:
                    await session.teardown()
                config = SessionConfig(**data.get("config", {}))
                name = str(data.get("name", "")).strip()
                resume_id = str(data.get("session_id", "")).strip() or None
                # If client provides a non-empty, non-default name, mark as user-set
                name_source = "user" if name and name != "New Session" else "default"
                session = ActiveSession(ws, config, name=name, resume_session_id=resume_id, name_source=name_source)
                action = "resume" if resume_id else "new session"
                logger.info("session_start received (%s will be: %s)", action, session.id)
                try:
                    await session.setup()
                except Exception as exc:
                    logger.error("Session setup failed: %s", exc)
                    session = None
                    err = WsError(
                        code="session_init_failed",
                        message=str(exc),
                        fatal=True,
                    )
                    await ws.send_text(err.model_dump_json())

            elif msg_type == "session_end":
                if session:
                    logger.info("session_end received (session: %s)", session.id)
                    await session.teardown()
                    session = None

            elif msg_type == "config_update":
                if session:
                    logger.info("config_update applied to session %s", session.id)
                    await session.handle_config_update(data.get("config", {}))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("Unhandled WebSocket error: %s", exc)
    finally:
        if session:
            await session.teardown()
