"""FastAPI application — entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

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
