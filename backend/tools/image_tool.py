"""Image generation tool factory."""
from __future__ import annotations
from typing import Callable


def build_image_tool(provider: str, emit_image_generated: Callable) -> Callable:
    async def generate_image(prompt: str, style: str = "realistic") -> str:
        """
        Generate an image based on something described in the conversation.
        Use when the conversation references something visual that would benefit from illustration.
        Returns the URL of the generated image.
        """
        import image_gen as ig
        try:
            url = await ig.generate_image(prompt, style=style, provider=provider)
            await emit_image_generated(url, prompt)
            return f"Image generated: {url}"
        except Exception as exc:
            return f"Image generation failed: {exc}"

    return generate_image
