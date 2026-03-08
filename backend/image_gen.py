"""Image generation — supports placeholder and Google Gemini."""
from __future__ import annotations
import base64
import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


async def generate_image(
    prompt: str,
    style: str = "realistic",
    provider: str = "placeholder",
) -> str:
    """Returns a URL to the generated image, or raises on failure."""
    if provider == "placeholder":
        logger.info("Image generation placeholder — prompt: %s", prompt[:60])
        encoded = quote(prompt[:50])
        return f"https://placehold.co/512x512/1a1a2e/ffffff?text={encoded}"

    if provider == "gemini":
        return await _generate_gemini(prompt)

    raise NotImplementedError(f"Image provider '{provider}' not implemented yet")


async def _generate_gemini(prompt: str) -> str:
    """Generate an image using Gemini's native image generation."""
    from config import settings

    api_key = settings.google_api_key
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured")

    model = "gemini-2.0-flash-preview-image-generation"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, params={"key": api_key})
        resp.raise_for_status()
        data = resp.json()

    # Extract the first image part from the response
    candidates = data.get("candidates", [])
    for candidate in candidates:
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData", {})
            if inline.get("mimeType", "").startswith("image/"):
                mime = inline["mimeType"]
                b64 = inline["data"]
                logger.info("Gemini image generated for prompt: %s", prompt[:60])
                return f"data:{mime};base64,{b64}"

    raise RuntimeError(f"Gemini returned no image. Response: {data}")
