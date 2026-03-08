"""Image persistence — save generated images to disk and record metadata."""
from __future__ import annotations

import base64
import logging
import re
import uuid
from pathlib import Path

import aiosqlite
import httpx

from models import new_id, now

logger = logging.getLogger(__name__)

# Data URI pattern: data:<mime>;base64,<data>
_DATA_URI_RE = re.compile(r"^data:(image/\w+);base64,(.+)$", re.DOTALL)

# Map MIME types to file extensions
_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _ext_from_mime(mime: str) -> str:
    """Get file extension from MIME type."""
    return _MIME_TO_EXT.get(mime.lower(), ".png")


def _ext_from_content_type(content_type: str) -> str:
    """Get file extension from Content-Type header."""
    mime = content_type.split(";")[0].strip().lower()
    return _ext_from_mime(mime)


async def save_image_to_disk(
    *,
    image_data: str,
    session_id: str,
    prompt: str,
    style: str,
    provider: str,
    db: aiosqlite.Connection,
    storage_path: str,
) -> str:
    """Save an image (data URI or URL) to disk and record in the database.

    Returns the persistent URL path (/api/images/{filename}).
    For placeholder URLs, returns the URL unchanged.
    """
    # Placeholder URLs don't need saving
    if "placehold.co" in image_data:
        # Still record in DB for session image listing, but no local file
        await _insert_image_record(
            db=db,
            session_id=session_id,
            filename="",
            prompt=prompt,
            style=style,
            provider=provider,
        )
        return image_data

    storage_dir = Path(storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Check if it's a data URI
    match = _DATA_URI_RE.match(image_data)
    if match:
        mime_type = match.group(1)
        b64_data = match.group(2)
        image_bytes = base64.b64decode(b64_data)
        ext = _ext_from_mime(mime_type)
    elif image_data.startswith("http://") or image_data.startswith("https://"):
        # External URL — download it
        image_bytes, ext = await _download_image(image_data)
    else:
        raise ValueError(f"Unsupported image data format: {image_data[:50]}...")

    # Generate unique filename
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = storage_dir / filename

    # Write to disk
    file_path.write_bytes(image_bytes)
    logger.info("Saved image to %s (%d bytes)", file_path, len(image_bytes))

    # Record in database
    await _insert_image_record(
        db=db,
        session_id=session_id,
        filename=filename,
        prompt=prompt,
        style=style,
        provider=provider,
    )

    return f"/api/images/{filename}"


async def _download_image(url: str) -> tuple[bytes, str]:
    """Download an image from a URL and return (bytes, extension)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        ext = _ext_from_content_type(content_type)
        return resp.content, ext


async def _insert_image_record(
    *,
    db: aiosqlite.Connection,
    session_id: str,
    filename: str,
    prompt: str,
    style: str,
    provider: str,
) -> str:
    """Insert a row into the images table."""
    image_id = new_id("img_")
    await db.execute(
        "INSERT INTO images (id, session_id, filename, prompt, style, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (image_id, session_id, filename, prompt, style, provider, now()),
    )
    await db.commit()
    return image_id
