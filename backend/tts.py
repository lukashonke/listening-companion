"""ElevenLabs TTS v3 — streams audio as base64 chunks via EU endpoint."""
from __future__ import annotations
import base64
import logging
from typing import Callable, Awaitable

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def synthesize_tts_chunks(
    text: str,
    voice_id: str,
    on_chunk: Callable[[str, str], Awaitable[None]],
    language_code: str = "cs",
) -> None:
    """
    Fetch TTS audio from ElevenLabs EU endpoint and emit a single on_chunk call
    with the complete MP3 once fully downloaded.
    """
    url = f"{settings.elevenlabs_eu_endpoint}/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model,
        "output_format": "mp3_44100_128",
        "language_code": language_code,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                # Accumulate the full MP3 before sending — partial MP3 chunks
                # cannot be decoded independently by the browser's WebAudio API.
                audio_bytes = b""
                async for raw_chunk in resp.aiter_bytes(chunk_size=4096):
                    audio_bytes += raw_chunk
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode()
                    await on_chunk(audio_b64, text)
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise
