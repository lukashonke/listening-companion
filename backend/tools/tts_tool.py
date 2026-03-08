"""TTS tool factory."""
from __future__ import annotations
from typing import Callable, Awaitable


def build_tts_tool(voice_id: str, emit_tts_chunk: Callable, tts_language: str = "cs") -> Callable:
    async def answer_tts(text: str) -> str:
        """
        Speak a response aloud to the user via ElevenLabs TTS.
        Use when the conversation requires a direct spoken answer or clarification.
        Keep responses concise (1-2 sentences).
        """
        import tts as tts_module

        async def on_chunk(audio_b64: str, chunk_text: str) -> None:
            await emit_tts_chunk(audio_b64, chunk_text)

        try:
            await tts_module.synthesize_tts_chunks(text, voice_id, on_chunk, language_code=tts_language)
        except Exception as exc:
            return f"TTS failed: {exc}"
        return f"Spoke: {text[:80]}..."

    return answer_tts
