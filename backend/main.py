"""FastAPI application — entry point."""
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from database import get_db, close_db
from ws_handler import websocket_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    logger.info("Database ready")
    yield
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(title="Listening Companion API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Password-gate /api/* and /ws routes when APP_PASSWORD is set."""
    if settings.app_password:
        path = request.url.path
        if path.startswith("/api/") or path == "/ws":
            auth_header = request.headers.get("Authorization", "")
            token_param = request.query_params.get("token", "")
            authorized = (
                auth_header == f"Bearer {settings.app_password}"
                or token_param == settings.app_password
            )
            if not authorized:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await websocket_handler(ws)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# OpenAI models cache
# ---------------------------------------------------------------------------
_openai_models_cache: list[str] | None = None
_openai_models_cache_at: float = 0.0
_OPENAI_MODELS_CACHE_TTL = 3600  # 1 hour

_OPENAI_EXCLUDE_KEYWORDS = [
    "embedding", "whisper", "dall-e", "moderation",
    "audio", "search", "similarity", "instruct",
    "babbage", "davinci", "ada", "curie",
    "realtime", "transcribe", "image", "codex", "tts",
]


def _is_chat_model(model_id: str) -> bool:
    lower = model_id.lower()
    if lower.startswith("tts"):
        return False
    return not any(kw in lower for kw in _OPENAI_EXCLUDE_KEYWORDS)


@app.get("/api/models/openai")
async def list_openai_models():
    global _openai_models_cache, _openai_models_cache_at
    now = time.time()
    if _openai_models_cache is not None and now - _openai_models_cache_at < _OPENAI_MODELS_CACHE_TTL:
        return {"models": _openai_models_cache}
    if not settings.openai_api_key:
        return {"models": []}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch OpenAI models: %s", exc)
        return JSONResponse({"error": "Failed to fetch models from OpenAI"}, status_code=502)
    models = sorted(m["id"] for m in data.get("data", []) if _is_chat_model(m["id"]))
    _openai_models_cache = models
    _openai_models_cache_at = now
    return {"models": models}


# ---------------------------------------------------------------------------
# Gemini models cache
# ---------------------------------------------------------------------------
_gemini_models_cache: list[str] | None = None
_gemini_models_cache_at: float = 0.0
_GEMINI_MODELS_CACHE_TTL = 3600  # 1 hour

_GEMINI_EXCLUDE_KEYWORDS = [
    "embedding", "imagen", "veo", "gemma", "aqa", "robotics", "tts", "audio",
    "text-embedding", "image-generation", "image", "computer-use", "customtools",
]

_GEMINI_INCLUDE_PREFIX = "gemini-"


def _is_gemini_chat_model(model_name: str) -> bool:
    lower = model_name.lower()
    if not lower.startswith(_GEMINI_INCLUDE_PREFIX):
        return False
    # Exclude models used for image gen, embedding, tts, etc.
    if any(kw in lower for kw in _GEMINI_EXCLUDE_KEYWORDS):
        return False
    return True


@app.get("/api/models/gemini")
async def list_gemini_models():
    global _gemini_models_cache, _gemini_models_cache_at
    now = time.time()
    if _gemini_models_cache is not None and now - _gemini_models_cache_at < _GEMINI_MODELS_CACHE_TTL:
        return {"models": _gemini_models_cache}
    if not settings.google_api_key:
        return {"models": []}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": settings.google_api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch Gemini models: %s", exc)
        return JSONResponse({"error": "Failed to fetch models from Google"}, status_code=502)
    models = sorted(
        m["name"].replace("models/", "")
        for m in data.get("models", [])
        if _is_gemini_chat_model(m.get("name", "").replace("models/", ""))
    )
    _gemini_models_cache = models
    _gemini_models_cache_at = now
    return {"models": models}


# ---------------------------------------------------------------------------
# Image models endpoints
# ---------------------------------------------------------------------------

_OPENAI_IMAGE_MODELS = [
    "gpt-image-1",
    "gpt-image-1-mini",
    "gpt-image-1.5",
    "chatgpt-image-latest",
    "dall-e-3",
    "dall-e-2",
]

_GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "nano-banana-pro-preview",
    "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001",
    "imagen-4.0-ultra-generate-001",
]


@app.get("/api/models/openai-image")
async def list_openai_image_models():
    return {"models": _OPENAI_IMAGE_MODELS}


@app.get("/api/models/gemini-image")
async def list_gemini_image_models():
    return {"models": _GEMINI_IMAGE_MODELS}


# ---------------------------------------------------------------------------
# ElevenLabs voices cache
# ---------------------------------------------------------------------------
_elevenlabs_voices_cache: list[dict] | None = None
_elevenlabs_voices_cache_at: float = 0.0
_ELEVENLABS_VOICES_CACHE_TTL = 3600  # 1 hour


@app.get("/api/voices/elevenlabs")
async def list_elevenlabs_voices():
    global _elevenlabs_voices_cache, _elevenlabs_voices_cache_at
    now = time.time()
    if _elevenlabs_voices_cache is not None and now - _elevenlabs_voices_cache_at < _ELEVENLABS_VOICES_CACHE_TTL:
        return {"voices": _elevenlabs_voices_cache}
    if not settings.elevenlabs_api_key:
        return {"voices": []}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.elevenlabs_eu_endpoint}/v1/voices",
                headers={"xi-api-key": settings.elevenlabs_api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch ElevenLabs voices: %s", exc)
        return JSONResponse({"error": "Failed to fetch voices from ElevenLabs"}, status_code=502)
    voices = sorted(
        {"id": v["voice_id"], "name": v["name"], "category": v.get("category", "")},
        key=lambda v: v["name"],
    )
    _elevenlabs_voices_cache = voices
    _elevenlabs_voices_cache_at = now
    return {"voices": voices}


@app.get("/api/sessions")
async def list_sessions():
    db = await get_db()
    async with db.execute(
        "SELECT id, name, created_at, ended_at, config FROM sessions ORDER BY created_at DESC LIMIT 50"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    db = await get_db()
    async with db.execute(
        "SELECT id, name, created_at, ended_at, config FROM sessions WHERE id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    session = dict(row)
    async with db.execute(
        "SELECT id, content, tags, created_at, updated_at FROM short_term_memory WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ) as cursor:
        mem_rows = await cursor.fetchall()
    import json as _json
    session["memory"] = [
        {**dict(r), "tags": _json.loads(r["tags"])} for r in mem_rows
    ]
    return session


class RenameSessionRequest(BaseModel):
    name: str


@app.patch("/api/sessions/{session_id}")
async def rename_session(session_id: str, body: RenameSessionRequest):
    db = await get_db()
    async with db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    await db.execute("UPDATE sessions SET name = ? WHERE id = ?", (body.name.strip(), session_id))
    await db.commit()
    return {"id": session_id, "name": body.name.strip()}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    db = await get_db()
    async with db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    await db.execute("DELETE FROM short_term_memory WHERE session_id = ?", (session_id,))
    await db.execute("DELETE FROM long_term_memory WHERE session_id = ?", (session_id,))
    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()
    return {"deleted": session_id}


# Serve frontend static files (production mode)
_dist = Path(settings.frontend_dist)
if _dist.exists():
    # Serve hashed assets from /assets directly
    _assets = _dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")
    logger.info("Serving frontend from %s", _dist)
else:
    logger.info("Frontend dist not found at %s — running in API-only mode", _dist)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """SPA catch-all: serve index.html for any non-API, non-WS path."""
    if _dist.exists():
        # Resolve to prevent path traversal
        resolved = (_dist / full_path).resolve()
        if resolved.is_relative_to(_dist.resolve()) and resolved.is_file():
            return FileResponse(str(resolved))
        index = _dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
    return JSONResponse({"error": "Frontend not available"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
