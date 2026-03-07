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


class ActiveSession:
    """One active listening session, tied to a single WebSocket connection."""

    def __init__(self, ws: WebSocket, config: SessionConfig):
        self.id = f"sess_{uuid.uuid4().hex[:12]}"
        self.ws = ws
        self.config = config
        self.transcript: list[TranscriptChunk] = []
        self._db = None
        self._short_term: ShortTermMemory | None = None
        self._long_term: LongTermMemory | None = None
        self._stt: ScribeSTT | None = None
        self._agent: SessionAgent | None = None

    async def setup(self) -> None:
        """Initialize all session components."""
        self._db = await get_db()

        # Persist session row
        await self._db.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at, config) VALUES (?, ?, ?)",
            (self.id, time.time(), self.config.model_dump_json()),
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
        tts_tool = build_tts_tool(self.config.voice_id, self._emit_tts_chunk)
        image_tool = build_image_tool(self.config.image_provider, self._emit_image_generated)
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

        # Start agent loop
        await self._agent.start_loop(
            get_transcript=lambda: self.transcript,
            interval_s=self.config.agent_interval_s,
        )

        await self._emit(WsSessionStatus(state="listening"))
        logger.info("Session %s started (tools: %s)", self.id, self.config.tools)

    async def teardown(self) -> None:
        """Gracefully shut down all session components."""
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
        """Apply partial config overrides received from the browser."""
        for key, value in config_patch.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    # ── Internal callbacks ─────────────────────────────────────────────────────

    async def _on_transcript(self, text: str, speaker: str) -> None:
        chunk = TranscriptChunk(text=text, speaker=speaker)
        self.transcript.append(chunk)
        await self._emit(WsTranscriptChunk(text=text, speaker=speaker, ts=chunk.ts))

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
                session = ActiveSession(ws, config)
                try:
                    await session.setup()
                except Exception as exc:
                    logger.error("Session setup failed: %s", exc)
                    err = WsError(
                        code="session_init_failed",
                        message=str(exc),
                        fatal=True,
                    )
                    await ws.send_text(err.model_dump_json())

            elif msg_type == "session_end":
                if session:
                    await session.teardown()
                    session = None

            elif msg_type == "config_update":
                if session:
                    await session.handle_config_update(data.get("config", {}))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("Unhandled WebSocket error: %s", exc)
    finally:
        if session:
            await session.teardown()
