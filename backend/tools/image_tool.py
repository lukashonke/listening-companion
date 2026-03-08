"""Image generation tool factory."""
from __future__ import annotations
import logging
from typing import Callable

import aiosqlite

logger = logging.getLogger(__name__)


def build_image_tool(
    provider: str,
    emit_image_generated: Callable,
    model: str = "",
    session_id: str = "",
    db: aiosqlite.Connection | None = None,
    storage_path: str = "",
) -> Callable:
    async def generate_image(prompt: str, style: str = "realistic") -> str:
        """
        Generate an image based on something described in the conversation.
        Use when the conversation references something visual that would benefit from illustration.
        Returns the URL of the generated image.
        """
        logger.info("generate_image tool called — provider=%s model=%s prompt=%s style=%s", provider, model, prompt[:80], style)
        import image_gen as ig
        try:
            raw_url = await ig.generate_image(prompt, style=style, provider=provider, model=model)
            logger.info("generate_image tool raw result — url_prefix=%s", raw_url[:60])

            # Persist image to disk if storage is configured
            url = raw_url
            if db is not None and storage_path and session_id:
                try:
                    from image_storage import save_image_to_disk
                    url = await save_image_to_disk(
                        image_data=raw_url,
                        session_id=session_id,
                        prompt=prompt,
                        style=style,
                        provider=provider,
                        db=db,
                        storage_path=storage_path,
                    )
                    logger.info("Image persisted — url=%s", url)
                except Exception as save_exc:
                    logger.error("Failed to persist image, using raw URL: %s", save_exc)
                    url = raw_url

            await emit_image_generated(url, prompt)
            return f"Image generated: {url}"
        except Exception as exc:
            logger.error("generate_image tool failed — provider=%s model=%s error=%s", provider, model, exc)
            return f"Image generation failed: {exc}"

    return generate_image
