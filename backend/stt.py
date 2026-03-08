"""ElevenLabs Scribe Realtime STT — WebSocket streaming bridge.

Forwards raw PCM audio from the browser to ElevenLabs Scribe Realtime and
delivers transcript chunks via a callback.

Protocol (ElevenLabs Scribe Realtime API):
  - Endpoint: /v1/speech-to-text/realtime
  - Config via URL params: model_id, audio_format, commit_strategy, language_code
  - Audio: JSON {"message_type": "input_audio_chunk", "audio_base_64": "<b64>",
                 "commit": false, "sample_rate": 16000}
  - Server events use "message_type" field (not "type"):
      session_started, partial_transcript, committed_transcript, auth_error, etc.
"""
from __future__ import annotations
import asyncio
import base64
import json
import logging
from typing import Callable, Awaitable

from websockets.asyncio.client import connect as ws_connect
from websockets.connection import State
from websockets.exceptions import ConnectionClosed

from config import settings

logger = logging.getLogger(__name__)

SCRIBE_WS_PATH = "/v1/speech-to-text/realtime"


class ScribeSTT:
    """
    Maintains a WebSocket connection to ElevenLabs Scribe Realtime.
    Call send_audio(chunk) with raw PCM bytes from the browser.
    Transcript chunks are delivered to on_transcript(text, speaker).
    """

    def __init__(
        self,
        on_transcript: Callable[[str, str], Awaitable[None]],
        speaker_diarization: bool = False,
    ):
        self._on_transcript = on_transcript
        self._speaker_diarization = speaker_diarization
        self._ws = None
        self._receiver_task: asyncio.Task | None = None
        self._sender_task: asyncio.Task | None = None
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._running = False
        self._reconnect_attempts = 0

    async def start(self) -> None:
        self._running = True
        await self._connect()

    async def _connect(self) -> None:
        api_key = settings.elevenlabs_api_key
        params = [
            f"model_id={settings.elevenlabs_stt_model}",
            "audio_format=pcm_16000",
            "commit_strategy=vad",
            "language_code=en",
            # Pass API key in URL so it survives proxy/load-balancer header stripping
            f"xi_api_key={api_key}",
        ]
        if self._speaker_diarization:
            params.append("diarize=true")
        url = settings.elevenlabs_stt_endpoint + SCRIBE_WS_PATH + "?" + "&".join(params)
        # Also send as header (redundant but harmless; some infra passes headers through)
        headers = {"xi-api-key": api_key}

        logger.info(
            "Connecting to Scribe STT: %s (api_key present: %s)",
            url.split("?")[0],
            bool(api_key),
        )

        try:
            # Cancel old tasks before creating new ones (prevents zombie tasks on reconnect)
            for task in (self._receiver_task, self._sender_task):
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
            self._receiver_task = None
            self._sender_task = None

            # All config goes in URL params — no init message needed for the realtime API
            self._ws = await ws_connect(url, additional_headers=headers)
            self._receiver_task = asyncio.create_task(self._receive_loop())
            self._sender_task = asyncio.create_task(self._send_loop())
            self._reconnect_attempts = 0
            logger.info("Scribe STT connected")
        except Exception as exc:
            logger.error(
                "Scribe STT connection failed: %s | endpoint: %s | api_key present: %s",
                exc,
                url.split("?")[0],
                bool(api_key),
            )
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _send_loop(self) -> None:
        chunks_sent = 0
        bytes_sent = 0
        while self._running:
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=5.0)
                if chunk is None:
                    break
                if self._ws and self._ws.state is State.OPEN:
                    # Scribe Realtime expects base64-encoded audio in a JSON message
                    audio_b64 = base64.b64encode(chunk).decode()
                    msg = json.dumps({
                        "message_type": "input_audio_chunk",
                        "audio_base_64": audio_b64,
                        "commit": False,
                        "sample_rate": 16000,
                    })
                    await self._ws.send(msg)
                    chunks_sent += 1
                    bytes_sent += len(chunk)
                    if chunks_sent % 20 == 0:
                        logger.info(
                            "Scribe STT: forwarded %d audio chunks to Scribe (%d bytes total, ~%.1fs of audio)",
                            chunks_sent, bytes_sent, chunks_sent * 0.2,
                        )
            except asyncio.TimeoutError:
                # Queue was empty for 5s — send an explicit commit to flush VAD
                if self._ws and self._ws.state is State.OPEN and chunks_sent > 0:
                    try:
                        commit_msg = json.dumps({"message_type": "commit"})
                        await self._ws.send(commit_msg)
                        logger.info(
                            "Scribe STT: sent explicit commit after 5s silence (chunks_sent=%d)",
                            chunks_sent,
                        )
                    except Exception as exc:
                        logger.debug("STT commit send error: %s", exc)
                continue
            except Exception as exc:
                logger.debug("STT send error: %s", exc)
                break

    async def _receive_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    logger.info("Scribe raw binary frame received (%d bytes)", len(raw))
                    continue
                logger.info("Scribe raw message: %s", raw[:300])
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Scribe non-JSON message: %r", raw[:200])
                    continue
                await self._handle_message(msg)
        except ConnectionClosed:
            logger.warning("Scribe STT connection closed")
            if self._running:
                asyncio.create_task(self._reconnect())
        except Exception as exc:
            logger.error("STT receive error: %s", exc)
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _handle_message(self, msg: dict) -> None:
        # Scribe Realtime uses "message_type" (not "type")
        msg_type = msg.get("message_type", "")

        if msg_type == "session_started":
            logger.info("Scribe session started: %s", msg)

        elif msg_type == "partial_transcript":
            text = (msg.get("transcript") or "").strip()
            logger.info("Scribe partial transcript: %r", text[:80])

        elif msg_type == "committed_transcript":
            # Final committed transcript — pass to agent and frontend
            text = (msg.get("transcript") or "").strip()
            speaker = "A"
            if self._speaker_diarization:
                speaker = str(msg.get("speaker_id") or msg.get("speaker") or "A")
            if text:
                logger.info("Committed transcript: %s", text[:80])
                await self._on_transcript(text, speaker)

        elif msg_type in (
            "auth_error", "quota_exceeded", "transcriber_error",
            "unaccepted_terms_error", "rate_limited", "input_error",
            "queue_overflow", "resource_exhausted", "session_time_limit_exceeded",
            "chunk_size_exceeded", "insufficient_audio_activity",
        ):
            logger.error("Scribe error [%s]: %s", msg_type, msg)

        else:
            logger.info("Scribe unknown message_type=%r: %s", msg_type, msg)

    async def send_audio(self, chunk: bytes) -> None:
        """Queue a raw PCM audio chunk to be forwarded to Scribe."""
        if self._running:
            self._audio_queue.put_nowait(chunk)

    async def stop(self) -> None:
        self._running = False
        self._audio_queue.put_nowait(None)
        tasks = []
        if self._receiver_task:
            self._receiver_task.cancel()
            tasks.append(self._receiver_task)
        if self._sender_task:
            self._sender_task.cancel()
            tasks.append(self._sender_task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        logger.info("Scribe STT stopped")

    async def _reconnect(self) -> None:
        self._reconnect_attempts += 1
        if self._reconnect_attempts > 10:
            logger.error("Scribe STT: max reconnect attempts reached, giving up")
            return
        delay = min(2 ** self._reconnect_attempts, 30)
        logger.info(
            "Reconnecting to Scribe STT in %ds (attempt %d)...",
            delay, self._reconnect_attempts,
        )
        await asyncio.sleep(delay)
        if self._running:
            await self._connect()
