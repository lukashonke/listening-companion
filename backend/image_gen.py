"""Image generation — placeholder implementation.
Extend with a real provider (fal.ai, OpenAI, Vertex AI Imagen) when needed.
"""
from __future__ import annotations
import logging
from urllib.parse import quote

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

    raise NotImplementedError(f"Image provider '{provider}' not implemented yet")
