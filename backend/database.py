import aiosqlite
import asyncio
from pathlib import Path
from config import settings

_db: aiosqlite.Connection | None = None
_lock = asyncio.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    ended_at    REAL,
    config      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS short_term_memory (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS long_term_memory (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    embedding   BLOB NOT NULL,
    created_at  REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS images (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    filename    TEXT NOT NULL,
    prompt      TEXT NOT NULL DEFAULT '',
    style       TEXT NOT NULL DEFAULT '',
    provider    TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    async with _lock:
        if _db is None:
            db_path = Path(settings.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _db = await aiosqlite.connect(db_path)
            _db.row_factory = aiosqlite.Row
            await _db.executescript(SCHEMA)
            await _db.commit()
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
