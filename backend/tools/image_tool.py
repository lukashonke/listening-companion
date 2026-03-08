"""Image generation tool factory."""
from __future__ import annotations
import logging
from typing import Callable

logger = logging.getLogger(__name__)


def build_image_tool(provider: str, emit_image_generated: Callable, model: str = "") -> Callable:
    async def generate_image(prompt: str, style: str = "realistic") -> str:
        """
        Generate an image based on something described in the conversation.
        Use when the conversation references something visual that would benefit from illustration.
        Returns the URL of the generated image.
        """
        logger.info("generate_image tool called — provider=%s model=%s prompt=%s style=%s", provider, model, prompt[:80], style)
        import image_gen as ig
        try:
            url = await ig.generate_image(prompt, style=style, provider=provider, model=model)
            logger.info("generate_image tool succeeded — url_prefix=%s", url[:60])
            await emit_image_generated(url, prompt)
            return f"Image generated: {url}"
        except Exception as exc:
            logger.error("generate_image tool failed — provider=%s model=%s error=%s", provider, model, exc)
            return f"Image generation failed: {exc}"

    return generate_image
