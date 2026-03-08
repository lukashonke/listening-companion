"""Tests for image persistence: saving to disk, serving via API, session images endpoint."""
import base64
import os
import time

import pytest
import aiosqlite
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# We need to patch settings before importing modules that use them
from config import Settings


@pytest.fixture
def image_storage_dir(tmp_path):
    """Create a temporary directory for image storage."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    return img_dir


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh SQLite database for each test."""
    db_path = tmp_path / "test.db"
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    from database import SCHEMA
    await conn.executescript(SCHEMA)
    # Also create the images table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            filename    TEXT NOT NULL,
            prompt      TEXT NOT NULL DEFAULT '',
            style       TEXT NOT NULL DEFAULT '',
            provider    TEXT NOT NULL DEFAULT '',
            created_at  REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture
async def db_with_session(db):
    """Database with a test session already inserted."""
    await db.execute(
        "INSERT INTO sessions (id, name, created_at, config) VALUES (?, ?, ?, ?)",
        ("sess_test123", "Test Session", time.time(), "{}"),
    )
    await db.commit()
    return db


# ── Test: save_image_to_disk ─────────────────────────────────────────────────

class TestSaveImageToDisk:
    async def test_save_base64_data_uri_png(self, image_storage_dir, db_with_session):
        """Save a base64 data URI (PNG) to disk and return persistent URL."""
        from image_storage import save_image_to_disk

        # Create a minimal 1x1 red PNG
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        data_uri = f"data:image/png;base64,{png_b64}"

        url = await save_image_to_disk(
            image_data=data_uri,
            session_id="sess_test123",
            prompt="A red pixel",
            style="realistic",
            provider="openai",
            db=db_with_session,
            storage_path=str(image_storage_dir),
        )

        # URL should be /api/images/{filename}
        assert url.startswith("/api/images/")
        filename = url.split("/api/images/")[1]
        assert filename.endswith(".png")

        # File should exist on disk
        file_path = image_storage_dir / filename
        assert file_path.exists()
        assert file_path.stat().st_size > 0

        # Database row should exist
        async with db_with_session.execute(
            "SELECT * FROM images WHERE session_id = ?", ("sess_test123",)
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        assert row["filename"] == filename
        assert row["prompt"] == "A red pixel"
        assert row["provider"] == "openai"

    async def test_save_base64_data_uri_jpeg(self, image_storage_dir, db_with_session):
        """Save a base64 data URI (JPEG) to disk."""
        from image_storage import save_image_to_disk

        # Minimal JPEG-like data (just testing the path, not a real JPEG)
        fake_b64 = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 100).decode()
        data_uri = f"data:image/jpeg;base64,{fake_b64}"

        url = await save_image_to_disk(
            image_data=data_uri,
            session_id="sess_test123",
            prompt="A jpeg test",
            style="",
            provider="gemini",
            db=db_with_session,
            storage_path=str(image_storage_dir),
        )

        filename = url.split("/api/images/")[1]
        assert filename.endswith(".jpg")
        assert (image_storage_dir / filename).exists()

    async def test_save_external_url(self, image_storage_dir, db_with_session):
        """Save an external URL — downloads and saves to disk."""
        from image_storage import save_image_to_disk

        # Mock httpx download
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )

        mock_response = MagicMock()
        mock_response.content = png_bytes
        mock_response.headers = {"content-type": "image/png"}
        mock_response.raise_for_status = MagicMock()

        with patch("image_storage.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            url = await save_image_to_disk(
                image_data="https://example.com/image.png",
                session_id="sess_test123",
                prompt="Downloaded image",
                style="",
                provider="placeholder",
                db=db_with_session,
                storage_path=str(image_storage_dir),
            )

        assert url.startswith("/api/images/")
        filename = url.split("/api/images/")[1]
        assert (image_storage_dir / filename).exists()

    async def test_save_placeholder_url(self, image_storage_dir, db_with_session):
        """Placeholder URLs (placehold.co) are stored as-is (no download)."""
        from image_storage import save_image_to_disk

        placeholder_url = "https://placehold.co/512x512/1a1a2e/ffffff?text=test"

        url = await save_image_to_disk(
            image_data=placeholder_url,
            session_id="sess_test123",
            prompt="Placeholder test",
            style="",
            provider="placeholder",
            db=db_with_session,
            storage_path=str(image_storage_dir),
        )

        # Placeholder URLs should be returned as-is
        assert url == placeholder_url

    async def test_multiple_images_per_session(self, image_storage_dir, db_with_session):
        """Multiple images in the same session get unique filenames."""
        from image_storage import save_image_to_disk

        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        data_uri = f"data:image/png;base64,{png_b64}"

        url1 = await save_image_to_disk(
            image_data=data_uri,
            session_id="sess_test123",
            prompt="Image 1",
            style="",
            provider="openai",
            db=db_with_session,
            storage_path=str(image_storage_dir),
        )
        url2 = await save_image_to_disk(
            image_data=data_uri,
            session_id="sess_test123",
            prompt="Image 2",
            style="",
            provider="openai",
            db=db_with_session,
            storage_path=str(image_storage_dir),
        )

        # URLs should be different
        assert url1 != url2

        # Both files should exist
        f1 = url1.split("/api/images/")[1]
        f2 = url2.split("/api/images/")[1]
        assert (image_storage_dir / f1).exists()
        assert (image_storage_dir / f2).exists()

        # Both rows should be in the database
        async with db_with_session.execute(
            "SELECT COUNT(*) as cnt FROM images WHERE session_id = ?", ("sess_test123",)
        ) as cursor:
            row = await cursor.fetchone()
        assert row["cnt"] == 2


# ── Test: API endpoints ──────────────────────────────────────────────────────

class TestImageApiEndpoints:
    """Test the FastAPI endpoints for serving images and listing session images."""

    @pytest.fixture
    def app_client(self, tmp_path, image_storage_dir):
        """Create a test client with mocked settings."""
        # We need to import and set up the FastAPI app with test settings
        # This is done by patching the settings and database
        pass

    async def test_serve_image_file(self, image_storage_dir):
        """GET /api/images/{filename} serves the file with correct content-type."""
        # Create a test image file
        test_filename = "test_image.png"
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        (image_storage_dir / test_filename).write_bytes(png_data)

        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.settings", Settings(
            image_storage_path=str(image_storage_dir),
            elevenlabs_api_key="test",
            openai_api_key="test",
            anthropic_api_key="test",
        )):
            # We need to re-import to pick up the new settings
            # Instead, let's directly test via the route logic
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/images/{test_filename}")

        assert resp.status_code == 200
        assert "image/png" in resp.headers.get("content-type", "")

    async def test_serve_image_not_found(self, image_storage_dir):
        """GET /api/images/{filename} returns 404 for nonexistent file."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.settings", Settings(
            image_storage_path=str(image_storage_dir),
            elevenlabs_api_key="test",
            openai_api_key="test",
            anthropic_api_key="test",
        )):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/images/nonexistent.png")

        assert resp.status_code == 404

    async def test_serve_image_path_traversal(self, image_storage_dir):
        """GET /api/images/../../etc/passwd should be blocked."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.settings", Settings(
            image_storage_path=str(image_storage_dir),
            elevenlabs_api_key="test",
            openai_api_key="test",
            anthropic_api_key="test",
        )):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/images/..%2F..%2Fetc%2Fpasswd")

        assert resp.status_code in (400, 404)

    async def test_session_images_endpoint(self, image_storage_dir, db_with_session):
        """GET /api/sessions/{id}/images returns image metadata list."""
        # Insert test image records
        await db_with_session.execute(
            "INSERT INTO images (id, session_id, filename, prompt, style, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("img_001", "sess_test123", "abc.png", "A cat", "realistic", "openai", time.time()),
        )
        await db_with_session.execute(
            "INSERT INTO images (id, session_id, filename, prompt, style, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("img_002", "sess_test123", "def.png", "A dog", "cartoon", "gemini", time.time()),
        )
        await db_with_session.commit()

        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            with patch("database.get_db", return_value=db_with_session):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/sessions/sess_test123/images")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Check metadata fields
        assert data[0]["prompt"] in ("A cat", "A dog")
        assert "url" in data[0]
        assert data[0]["url"].startswith("/api/images/")

    async def test_session_images_empty(self, db_with_session):
        """GET /api/sessions/{id}/images returns empty list for session with no images."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        with patch("main.get_db", return_value=db_with_session):
            with patch("database.get_db", return_value=db_with_session):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/sessions/sess_test123/images")

        assert resp.status_code == 200
        data = resp.json()
        assert data == []
