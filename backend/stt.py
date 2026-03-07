"""ElevenLabs Scribe STT — WebSocket streaming bridge.

Forwards raw PCM audio from the browser to ElevenLabs Scribe and delivers
transcript chunks via a callback.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Callable, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

from config import settings

logger = logging.getLogger(__name__)

SCRIBE_WS_URL = "wss://api.elevenlabs.io/v1/speech-to-text/stream"


class ScribeSTT:
    """
    Maintains a WebSocket connection to ElevenLabs Scribe.
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
        params = f"?model_id={settings.elevenlabs_stt_model}&language_code=en"
        if self._speaker_diarization:
            params += "&diarize=true"
        url = SCRIBE_WS_URL + params
        headers = {"xi-api-key": settings.elevenlabs_api_key}

        try:
            self._ws = await websockets.connect(url, additional_headers=headers)
            # Send session init with audio format
            await self._ws.send(json.dumps({
                "type": "session.start",
                "audio_format": {
                    "encoding": "pcm_s16le",
                    "sample_rate": 16000,
                    "channels": 1,
                },
            }))
            self._receiver_task = asyncio.create_task(self._receive_loop())
            self._sender_task = asyncio.create_task(self._send_loop())
            self._reconnect_attempts = 0
            logger.info("Scribe STT connected")
        except Exception as exc:
            logger.error("Scribe STT connection failed: %s", exc)
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _send_loop(self) -> None:
        while self._running:
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=5.0)
                if chunk is None:
                    break
                if self._ws and not self._ws.closed:
                    await self._ws.send(chunk)
            except asyncio.TimeoutError:
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
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
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
        msg_type = msg.get("type", "")
        # Handle various transcript message formats ElevenLabs may send
        if msg_type in ("transcript.word", "transcript.text", "speech.final",
                        "transcript", "transcription"):
            text = (msg.get("text") or msg.get("transcript") or "").strip()
            speaker = "A"
            if self._speaker_diarization:
                speaker = str(msg.get("speaker_id") or msg.get("speaker") or "A")
            if text:
                await self._on_transcript(text, speaker)
        elif msg_type == "error":
            logger.error("Scribe error message: %s", msg)

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
        await asyncio.sleep(min(2 ** self._reconnect_attempts, 30))
        if self._running:
            logger.info("Reconnecting to Scribe STT (attempt %d)...", self._reconnect_attempts)
            await self._connect()
