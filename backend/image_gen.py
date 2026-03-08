"""Image generation — supports placeholder, OpenAI, and Google Gemini."""
from __future__ import annotations
import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# ── Default models per provider ──────────────────────────────────────────────
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-1"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

# Models that use the legacy OpenAI API (response_format instead of output_format)
_LEGACY_OPENAI_MODELS = {"dall-e-2", "dall-e-3"}


async def generate_image(
    prompt: str,
    style: str = "realistic",
    provider: str = "placeholder",
    model: str = "",
) -> str:
    """Returns a URL (or data URI) to the generated image, or raises on failure."""
    if provider == "placeholder":
        logger.info("Image generation placeholder — prompt: %s", prompt[:60])
        encoded = quote(prompt[:50])
        return f"https://placehold.co/512x512/1a1a2e/ffffff?text={encoded}"

    if provider == "gemini":
        return await _generate_gemini(prompt, model=model or DEFAULT_GEMINI_IMAGE_MODEL)

    if provider == "openai":
        return await _generate_openai(prompt, model=model or DEFAULT_OPENAI_IMAGE_MODEL)

    raise NotImplementedError(f"Image provider '{provider}' not implemented yet")


async def _generate_gemini(prompt: str, model: str = DEFAULT_GEMINI_IMAGE_MODEL) -> str:
    """Generate an image using Gemini's native image generation."""
    from config import settings

    api_key = settings.google_api_key
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured")

    # Imagen models use a different API endpoint
    if model.startswith("imagen-"):
        return await _generate_imagen(prompt, model=model, api_key=api_key)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
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
                logger.info("Gemini image generated (model=%s) for prompt: %s", model, prompt[:60])
                return f"data:{mime};base64,{b64}"

    raise RuntimeError(f"Gemini ({model}) returned no image. Response keys: {list(data.keys())}")


async def _generate_imagen(prompt: str, model: str, api_key: str) -> str:
    """Generate an image using Google Imagen models."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
        },
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(url, json=payload, params={"key": api_key})
        resp.raise_for_status()
        data = resp.json()

    predictions = data.get("predictions", [])
    if predictions:
        b64 = predictions[0].get("bytesBase64Encoded", "")
        mime = predictions[0].get("mimeType", "image/png")
        if b64:
            logger.info("Imagen image generated (model=%s) for prompt: %s", model, prompt[:60])
            return f"data:{mime};base64,{b64}"

    raise RuntimeError(f"Imagen ({model}) returned no image. Response keys: {list(data.keys())}")


async def _generate_openai(prompt: str, model: str = DEFAULT_OPENAI_IMAGE_MODEL) -> str:
    """Generate an image using OpenAI image models and return as a data URI."""
    from config import settings

    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    is_legacy = model in _LEGACY_OPENAI_MODELS

    if is_legacy:
        # dall-e-2/3 use the old API format
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        }
    else:
        # gpt-image-1 and newer models — no response_format param
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()

    item = data["data"][0]
    b64 = item.get("b64_json", "")
    if b64:
        logger.info("OpenAI image generated (model=%s) for prompt: %s", model, prompt[:60])
        return f"data:image/png;base64,{b64}"

    # Some models may return a URL instead
    url = item.get("url", "")
    if url:
        logger.info("OpenAI image generated (model=%s, url) for prompt: %s", model, prompt[:60])
        return url

    raise RuntimeError(f"OpenAI ({model}) returned no image data. Keys: {list(item.keys())}")
