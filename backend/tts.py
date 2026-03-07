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
) -> None:
    """
    Stream TTS audio from ElevenLabs EU endpoint.
    Calls on_chunk(audio_b64, text) for each audio chunk received.
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
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                first = True
                buffer = b""
                async for raw_chunk in resp.aiter_bytes(chunk_size=4096):
                    buffer += raw_chunk
                    if len(buffer) >= 4096:
                        audio_b64 = base64.b64encode(buffer).decode()
                        await on_chunk(audio_b64, text if first else "")
                        buffer = b""
                        first = False
                if buffer:
                    audio_b64 = base64.b64encode(buffer).decode()
                    await on_chunk(audio_b64, text if first else "")
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise
