"""FastAPI application — entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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
        "SELECT id, name, created_at, ended_at FROM sessions ORDER BY created_at DESC LIMIT 50"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# Serve frontend static files (production mode)
_dist = Path(settings.frontend_dist)
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
    logger.info("Serving frontend from %s", _dist)
else:
    logger.info("Frontend dist not found at %s — running in API-only mode", _dist)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
