# Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python FastAPI backend with WebSocket audio streaming, ElevenLabs STT/TTS, Pydantic AI agent loop, and SQLite memory — matching the protocol in ARCHITECTURE.md.

**Architecture:** Single FastAPI app with one WebSocket endpoint per session. Audio binary frames from the browser are forwarded to ElevenLabs Scribe (via websockets library). A background asyncio task calls the Pydantic AI agent every N seconds with the latest transcript and short-term memory. Tools are plain Python closures over the session object, registered with a simple decorator.

**Tech Stack:** Python 3.12+, uv, FastAPI, Pydantic AI (anthropic provider), aiosqlite, elevenlabs SDK, sentence-transformers, numpy, websockets

---

## Task 1: Project scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/config.py`

**Step 1: Create backend/.python-version**

```
3.12
```

**Step 2: Create backend/pyproject.toml**

```toml
[project]
name = "listening-companion-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic-ai[anthropic]>=0.0.14",
    "pydantic-settings>=2.6",
    "aiosqlite>=0.20",
    "elevenlabs>=1.50",
    "sentence-transformers>=3.3",
    "numpy>=1.26",
    "websockets>=13",
    "httpx>=0.27",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pytest-mock>=3.14",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["."]
```

**Step 3: Run uv sync**

```bash
cd backend && uv sync --extra dev
```

Expected: resolves and installs all packages.

**Step 4: Create backend/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_tts_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_tts_model: str = "eleven_v3"
    elevenlabs_eu_endpoint: str = "https://api.eu.elevenlabs.io"
    elevenlabs_stt_model: str = "scribe_v1"

    # Anthropic / Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"

    # Agent
    agent_interval_s: int = 30
    agent_timeout_s: int = 60
    agent_transcript_window_s: int = 120  # feed last N seconds to agent

    # Memory
    short_term_memory_max: int = 50
    long_term_embedding_dim: int = 384

    # Database
    database_path: str = "listening_companion.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_dist: str = "../frontend/dist"


settings = Settings()
```

**Step 5: Commit**

```bash
cd backend && git add pyproject.toml .python-version config.py
git commit -m "feat(backend): project scaffold, config"
```

---

## Task 2: Database layer

**Files:**
- Create: `backend/database.py`

**Step 1: Create backend/database.py**

```python
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
```

**Step 2: Commit**

```bash
git add backend/database.py
git commit -m "feat(backend): database layer, SQLite schema"
```

---

## Task 3: Pydantic models

**Files:**
- Create: `backend/models.py`

**Step 1: Create backend/models.py**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
import time
import uuid


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def now() -> float:
    return time.time()


# ── Session ──────────────────────────────────────────────────────────────────

class SessionConfig(BaseModel):
    tools: list[str] = []
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    agent_interval_s: int = 30
    image_provider: str = "placeholder"
    speaker_diarization: bool = False


class Session(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sess_"))
    name: str = ""
    created_at: float = Field(default_factory=now)
    ended_at: float | None = None
    config: SessionConfig = Field(default_factory=SessionConfig)


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem_"))
    content: str
    tags: list[str] = []
    created_at: float = Field(default_factory=now)
    updated_at: float = Field(default_factory=now)


class LongTermEntry(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ltm_"))
    session_id: str
    content: str
    tags: list[str] = []
    created_at: float = Field(default_factory=now)


# ── Transcript ────────────────────────────────────────────────────────────────

class TranscriptChunk(BaseModel):
    text: str
    speaker: str = "A"
    ts: float = Field(default_factory=now)


# ── WebSocket event types ─────────────────────────────────────────────────────

class WsTranscriptChunk(BaseModel):
    type: Literal["transcript_chunk"] = "transcript_chunk"
    text: str
    speaker: str
    ts: float


class WsAgentStart(BaseModel):
    type: Literal["agent_start"] = "agent_start"
    ts: float = Field(default_factory=now)


class WsAgentDone(BaseModel):
    type: Literal["agent_done"] = "agent_done"
    ts: float = Field(default_factory=now)


class WsToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict
    result: dict | str | None = None
    error: str | None = None
    ts: float = Field(default_factory=now)


class WsMemoryUpdate(BaseModel):
    type: Literal["memory_update"] = "memory_update"
    short_term: list[MemoryEntry]


class WsImageGenerated(BaseModel):
    type: Literal["image_generated"] = "image_generated"
    url: str
    prompt: str
    ts: float = Field(default_factory=now)


class WsTtsChunk(BaseModel):
    type: Literal["tts_chunk"] = "tts_chunk"
    audio_b64: str
    text: str


class WsError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    fatal: bool = False


class WsSessionStatus(BaseModel):
    type: Literal["session_status"] = "session_status"
    state: Literal["listening", "processing", "idle"]


# ── Client → Server frames ────────────────────────────────────────────────────

class WsSessionStart(BaseModel):
    type: Literal["session_start"]
    config: SessionConfig = Field(default_factory=SessionConfig)


class WsSessionEnd(BaseModel):
    type: Literal["session_end"]


class WsConfigUpdate(BaseModel):
    type: Literal["config_update"]
    config: dict
```

**Step 2: Commit**

```bash
git add backend/models.py
git commit -m "feat(backend): Pydantic models for sessions, memory, WS events"
```

---

## Task 4: Short-term memory module

**Files:**
- Create: `backend/memory/__init__.py`
- Create: `backend/memory/short_term.py`

**Step 1: Create backend/memory/__init__.py** (empty)

**Step 2: Create backend/memory/short_term.py**

```python
from __future__ import annotations
import asyncio
import json
import logging
import time

import aiosqlite

from models import MemoryEntry, new_id, now
from config import settings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """In-memory dict backed by SQLite for crash recovery."""

    def __init__(self, session_id: str, db: aiosqlite.Connection):
        self._session_id = session_id
        self._db = db
        self._entries: dict[str, MemoryEntry] = {}
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Load existing entries from SQLite on session resume."""
        async with self._db.execute(
            "SELECT id, content, tags, created_at, updated_at FROM short_term_memory WHERE session_id = ?",
            (self._session_id,),
        ) as cursor:
            async for row in cursor:
                entry = MemoryEntry(
                    id=row["id"],
                    content=row["content"],
                    tags=json.loads(row["tags"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                self._entries[entry.id] = entry

    async def save(self, content: str, tags: list[str]) -> MemoryEntry:
        async with self._lock:
            entry = MemoryEntry(content=content, tags=tags)
            self._entries[entry.id] = entry
            await self._persist(entry)
            await self._prune_if_needed()
            return entry

    async def update(self, entry_id: str, content: str) -> MemoryEntry | None:
        async with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return None
            entry.content = content
            entry.updated_at = now()
            await self._persist(entry)
            return entry

    async def remove(self, entry_id: str) -> bool:
        async with self._lock:
            if entry_id not in self._entries:
                return False
            del self._entries[entry_id]
            await self._db.execute(
                "DELETE FROM short_term_memory WHERE id = ? AND session_id = ?",
                (entry_id, self._session_id),
            )
            await self._db.commit()
            return True

    def all(self) -> list[MemoryEntry]:
        return list(self._entries.values())

    def as_context_str(self) -> str:
        entries = self.all()
        if not entries:
            return "(empty)"
        lines = [f"[{e.id}] {e.content}" + (f" #{' #'.join(e.tags)}" if e.tags else "") for e in entries]
        return "\n".join(lines)

    async def _persist(self, entry: MemoryEntry) -> None:
        try:
            await self._db.execute(
                """INSERT OR REPLACE INTO short_term_memory
                   (id, session_id, content, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entry.id, self._session_id, entry.content, json.dumps(entry.tags),
                 entry.created_at, entry.updated_at),
            )
            await self._db.commit()
        except Exception as exc:
            logger.warning("SQLite write failed (in-memory state preserved): %s", exc)

    async def _prune_if_needed(self) -> None:
        if len(self._entries) <= settings.short_term_memory_max:
            return
        untagged = sorted(
            [e for e in self._entries.values() if not e.tags],
            key=lambda e: e.created_at,
        )
        to_remove = untagged[: len(self._entries) - settings.short_term_memory_max]
        for entry in to_remove:
            del self._entries[entry.id]
            await self._db.execute(
                "DELETE FROM short_term_memory WHERE id = ?", (entry.id,)
            )
        if to_remove:
            await self._db.commit()
```

**Step 3: Commit**

```bash
git add backend/memory/
git commit -m "feat(backend): short-term memory (in-memory + SQLite backup)"
```

---

## Task 5: Long-term memory module

**Files:**
- Create: `backend/memory/long_term.py`

**Step 1: Create backend/memory/long_term.py**

```python
from __future__ import annotations
import json
import logging
import struct

import aiosqlite
import numpy as np

from models import LongTermEntry, new_id, now

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid slow import at startup
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _embed(text: str) -> np.ndarray:
    return _get_embedder().encode(text, normalize_embeddings=True)


def _vec_to_blob(v: np.ndarray) -> bytes:
    return struct.pack(f"{len(v)}f", *v.tolist())


def _blob_to_vec(b: bytes) -> np.ndarray:
    n = len(b) // 4
    return np.array(struct.unpack(f"{n}f", b), dtype=np.float32)


class LongTermMemory:
    def __init__(self, session_id: str, db: aiosqlite.Connection):
        self._session_id = session_id
        self._db = db

    async def save(self, content: str, tags: list[str]) -> LongTermEntry:
        entry = LongTermEntry(session_id=self._session_id, content=content, tags=tags)
        embedding = await asyncio.get_event_loop().run_in_executor(None, _embed, content)
        try:
            await self._db.execute(
                """INSERT INTO long_term_memory (id, session_id, content, tags, embedding, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entry.id, entry.session_id, entry.content,
                 json.dumps(entry.tags), _vec_to_blob(embedding), entry.created_at),
            )
            await self._db.commit()
        except Exception as exc:
            logger.warning("Long-term memory save failed: %s", exc)
        return entry

    async def search(self, query: str, top_k: int = 5) -> list[LongTermEntry]:
        query_vec = await asyncio.get_event_loop().run_in_executor(None, _embed, query)

        rows = []
        async with self._db.execute(
            "SELECT id, content, tags, embedding, created_at FROM long_term_memory WHERE session_id = ?",
            (self._session_id,),
        ) as cursor:
            async for row in cursor:
                rows.append(row)

        if not rows:
            return []

        scores = []
        for row in rows:
            vec = _blob_to_vec(row["embedding"])
            score = float(np.dot(query_vec, vec))
            scores.append((score, row))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for _, row in scores[:top_k]:
            results.append(LongTermEntry(
                id=row["id"],
                session_id=self._session_id,
                content=row["content"],
                tags=json.loads(row["tags"]),
                created_at=row["created_at"],
            ))
        return results


import asyncio  # noqa: E402 — needed for run_in_executor
```

**Step 2: Commit**

```bash
git add backend/memory/long_term.py
git commit -m "feat(backend): long-term memory with numpy cosine similarity"
```

---

## Task 6: Tool registry + memory tools

**Files:**
- Create: `backend/tools/__init__.py`
- Create: `backend/tools/memory_ops.py`

**Step 1: Create backend/tools/__init__.py**

```python
"""Tool registry: @tool decorator + auto-discovery."""
from __future__ import annotations
import importlib
import pkgutil
import pathlib
from typing import Callable

_TOOL_REGISTRY: dict[str, Callable] = {}

CORE_TOOLS = [
    "save_short_term_memory",
    "remove_short_term_memory",
    "update_short_term_memory",
    "save_long_term_memory",
    "search_long_term_memory",
    "answer_tts",
    "generate_image",
]


def tool(fn: Callable | None = None, *, tags: list[str] | None = None):
    """Register a function in the global tool registry."""
    def decorator(f: Callable) -> Callable:
        _TOOL_REGISTRY[f.__name__] = f
        f._tool_tags = tags or []
        return f
    return decorator(fn) if fn is not None else decorator


def discover_tools() -> dict[str, Callable]:
    tools_dir = pathlib.Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(tools_dir)]):
        if module_name != "__init__":
            importlib.import_module(f"tools.{module_name}")
    return _TOOL_REGISTRY


def get_active_tools(session_tool_names: list[str]) -> list[Callable]:
    """Return core tools + requested plugin tools (functions from registry)."""
    discover_tools()
    wanted = list(dict.fromkeys(CORE_TOOLS + session_tool_names))  # dedup, preserve order
    active = []
    for name in wanted:
        if name in _TOOL_REGISTRY:
            active.append(_TOOL_REGISTRY[name])
        else:
            import logging
            logging.getLogger(__name__).warning("Unknown tool requested: %s", name)
    return active
```

**Step 2: Create backend/tools/memory_ops.py**

This file registers tool stubs. Actual tools are built as closures per session in agent.py — these stubs are only used for documentation/type hints. The registry stores the session-bound versions.

Actually, the right pattern is: tool functions in `tools/` are session-unaware stubs. The agent.py builds session-specific closures and passes them directly to the Pydantic AI agent. But discovery still happens via the registry for validation (checking tool names).

**Revised approach**: `memory_ops.py` defines the *session-bound builder* functions that return callable tools. They're not registered as tools themselves — they're factories. The tool registry holds the plugin tools only. Core tools are always built fresh per session.

Revise `backend/tools/__init__.py`:

```python
"""Tool registry: @tool decorator for plugin tools + auto-discovery."""
from __future__ import annotations
import importlib
import pkgutil
import pathlib
from typing import Callable

_PLUGIN_REGISTRY: dict[str, Callable] = {}

CORE_TOOL_NAMES = [
    "save_short_term_memory",
    "remove_short_term_memory",
    "update_short_term_memory",
    "save_long_term_memory",
    "search_long_term_memory",
    "answer_tts",
    "generate_image",
]


def tool(fn: Callable | None = None, *, tags: list[str] | None = None):
    """Register a plugin tool in the global registry."""
    def decorator(f: Callable) -> Callable:
        _PLUGIN_REGISTRY[f.__name__] = f
        f._tool_tags = tags or []
        return f
    return decorator(fn) if fn is not None else decorator


def discover_plugins() -> None:
    tools_dir = pathlib.Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(tools_dir)]):
        if module_name not in ("__init__", "memory_ops", "tts_tool", "image_tool"):
            importlib.import_module(f"tools.{module_name}")


def get_plugin_tools(names: list[str]) -> list[Callable]:
    """Return registered plugin tools by name."""
    import logging
    log = logging.getLogger(__name__)
    discover_plugins()
    result = []
    for name in names:
        if name in _PLUGIN_REGISTRY:
            result.append(_PLUGIN_REGISTRY[name])
        elif name not in CORE_TOOL_NAMES:
            log.warning("Unknown plugin tool: %s", name)
    return result
```

**Step 3: Create backend/tools/memory_ops.py**

These are factory functions called by agent.py to build session-bound tool callables:

```python
"""Core memory tool factories — called by agent.py to build session-bound tools."""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from memory.short_term import ShortTermMemory
    from memory.long_term import LongTermMemory


def build_memory_tools(
    short_term: "ShortTermMemory",
    long_term: "LongTermMemory",
    emit_memory_update: Callable,
) -> list[Callable]:
    """Return the 5 memory tools bound to this session's memory objects."""

    async def save_short_term_memory(content: str, tags: list[str] = []) -> str:
        """Save important information to short-term memory. Returns the entry ID."""
        entry = await short_term.save(content, tags)
        await emit_memory_update()
        return entry.id

    async def update_short_term_memory(id: str, content: str) -> str:
        """Update an existing short-term memory entry by ID."""
        entry = await short_term.update(id, content)
        if entry is None:
            return f"Entry {id} not found"
        await emit_memory_update()
        return f"Updated {id}"

    async def remove_short_term_memory(id: str) -> str:
        """Remove a short-term memory entry by ID."""
        removed = await short_term.remove(id)
        if removed:
            await emit_memory_update()
            return f"Removed {id}"
        return f"Entry {id} not found"

    async def save_long_term_memory(content: str, tags: list[str] = []) -> str:
        """Archive important information to long-term memory for future retrieval."""
        entry = await long_term.save(content, tags)
        return f"Saved to long-term memory: {entry.id}"

    async def search_long_term_memory(query: str) -> str:
        """Search long-term memory for relevant past information."""
        results = await long_term.search(query)
        if not results:
            return "No relevant long-term memories found."
        return "\n".join(f"[{e.id}] {e.content}" for e in results)

    return [
        save_short_term_memory,
        update_short_term_memory,
        remove_short_term_memory,
        save_long_term_memory,
        search_long_term_memory,
    ]
```

**Step 4: Commit**

```bash
git add backend/tools/
git commit -m "feat(backend): tool registry and memory tool factories"
```

---

## Task 7: TTS module + tool

**Files:**
- Create: `backend/tts.py`
- Create: `backend/tools/tts_tool.py`

**Step 1: Create backend/tts.py**

```python
"""ElevenLabs TTS v3 — streams audio as base64 chunks."""
from __future__ import annotations
import asyncio
import base64
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def synthesize_tts_chunks(
    text: str,
    voice_id: str,
    on_chunk: "Callable[[str, str], Awaitable[None]]",
) -> None:
    """
    Stream TTS audio from ElevenLabs. Calls on_chunk(audio_b64, text_fragment) for each chunk.
    Uses EU endpoint as specified in ARCHITECTURE.md.
    """
    url = f"{settings.elevenlabs_eu_endpoint}/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model,
        "output_format": "mp3_44100_128",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                chunk_text = text  # send full text on first chunk, empty after
                first = True
                buffer = b""
                async for raw_chunk in resp.aiter_bytes(chunk_size=4096):
                    buffer += raw_chunk
                    if len(buffer) >= 4096 or not first:
                        audio_b64 = base64.b64encode(buffer).decode()
                        await on_chunk(audio_b64, chunk_text if first else "")
                        buffer = b""
                        first = False
                if buffer:
                    audio_b64 = base64.b64encode(buffer).decode()
                    await on_chunk(audio_b64, "")
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        raise


from typing import Callable, Awaitable  # noqa: E402
```

**Step 2: Create backend/tools/tts_tool.py**

```python
"""TTS tool factory."""
from __future__ import annotations
from typing import Callable, Awaitable


def build_tts_tool(voice_id: str, emit_tts_chunk: Callable) -> Callable:
    async def answer_tts(text: str) -> str:
        """
        Speak a response aloud to the user via ElevenLabs TTS.
        Use when the conversation requires a direct spoken answer.
        """
        import tts as tts_module

        async def on_chunk(audio_b64: str, chunk_text: str) -> None:
            await emit_tts_chunk(audio_b64, chunk_text)

        try:
            await tts_module.synthesize_tts_chunks(text, voice_id, on_chunk)
        except Exception as exc:
            return f"TTS failed: {exc}"
        return f"Spoke: {text[:60]}..."

    return answer_tts
```

**Step 3: Commit**

```bash
git add backend/tts.py backend/tools/tts_tool.py
git commit -m "feat(backend): ElevenLabs TTS streaming module and tool"
```

---

## Task 8: Image generation (placeholder)

**Files:**
- Create: `backend/image_gen.py`
- Create: `backend/tools/image_tool.py`

**Step 1: Create backend/image_gen.py**

```python
"""Image generation — placeholder implementation.
Extend with real provider (fal.ai, OpenAI, etc.) as needed.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def generate_image(prompt: str, style: str = "realistic", provider: str = "placeholder") -> str:
    """Returns a URL to the generated image, or raises on failure."""
    if provider == "placeholder":
        logger.info("Image generation placeholder — prompt: %s", prompt)
        # Return a placeholder image URL
        encoded = prompt[:40].replace(" ", "+")
        return f"https://placehold.co/512x512?text={encoded}"

    raise NotImplementedError(f"Image provider '{provider}' not implemented")
```

**Step 2: Create backend/tools/image_tool.py**

```python
"""Image generation tool factory."""
from __future__ import annotations
from typing import Callable


def build_image_tool(provider: str, emit_image_generated: Callable) -> Callable:
    async def generate_image(prompt: str, style: str = "realistic") -> str:
        """
        Generate an image based on a description from the conversation.
        Use when the conversation describes something visual worth showing.
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
```

**Step 3: Commit**

```bash
git add backend/image_gen.py backend/tools/image_tool.py
git commit -m "feat(backend): image generation placeholder + tool"
```

---

## Task 9: Plugin tools (entity tracker example)

**Files:**
- Create: `backend/tools/entity_tracker.py`

**Step 1: Create backend/tools/entity_tracker.py**

```python
"""Entity tracker plugin — tracks named entities mentioned in conversation."""
from tools import tool


@tool(tags=["plugin"])
async def track_entity(name: str, entity_type: str, description: str) -> str:
    """
    Track a named entity mentioned in the conversation: person, place, item, or concept.
    Call whenever a significant new entity is introduced that should be remembered.
    entity_type should be one of: person, place, item, concept, organization
    """
    return f"Tracking {entity_type}: {name} — {description}"
```

**Step 2: Commit**

```bash
git add backend/tools/entity_tracker.py
git commit -m "feat(backend): entity_tracker plugin tool example"
```

---

## Task 10: STT module (ElevenLabs Scribe)

**Files:**
- Create: `backend/stt.py`

**Step 1: Create backend/stt.py**

```python
"""ElevenLabs Scribe STT — WebSocket streaming bridge.

Forwards raw PCM audio from the browser WebSocket to ElevenLabs Scribe
and delivers transcript chunks via a callback.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Callable, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

from config import settings

logger = logging.getLogger(__name__)

SCRIBE_WS_URL = "wss://api.elevenlabs.io/v1/speech-to-text/stream"


class ScribeSTT:
    """
    Maintains a WebSocket connection to ElevenLabs Scribe.
    Call `send_audio(chunk)` with raw PCM bytes.
    Transcript chunks are delivered to `on_transcript(text, speaker)`.
    """

    def __init__(
        self,
        on_transcript: Callable[[str, str], Awaitable[None]],
        speaker_diarization: bool = False,
    ):
        self._on_transcript = on_transcript
        self._speaker_diarization = speaker_diarization
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._receiver_task: asyncio.Task | None = None
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._sender_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        await self._connect()

    async def _connect(self) -> None:
        url = (
            f"{SCRIBE_WS_URL}"
            f"?model_id={settings.elevenlabs_stt_model}"
            f"&language_code=en"
            + ("&diarize=true" if self._speaker_diarization else "")
        )
        headers = {"xi-api-key": settings.elevenlabs_api_key}
        try:
            self._ws = await websockets.connect(url, additional_headers=headers)
            # Send session init
            await self._ws.send(json.dumps({
                "type": "session.start",
                "audio_format": {
                    "encoding": "pcm_s16le",
                    "sample_rate": 16000,
                    "channels": 1,
                }
            }))
            self._receiver_task = asyncio.create_task(self._receive_loop())
            self._sender_task = asyncio.create_task(self._send_loop())
            logger.info("Scribe STT connected")
        except Exception as exc:
            logger.error("Scribe STT connection failed: %s", exc)
            asyncio.create_task(self._reconnect())

    async def _send_loop(self) -> None:
        while self._running:
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=5.0)
                if chunk is None:
                    break
                if self._ws and not self._ws.closed:
                    await self._ws.send(chunk)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.debug("STT send error: %s", exc)
                break

    async def _receive_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    continue  # ignore binary frames from server
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_message(msg)
        except ConnectionClosed:
            logger.warning("Scribe STT connection closed")
            if self._running:
                asyncio.create_task(self._reconnect())
        except Exception as exc:
            logger.error("STT receive error: %s", exc)
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type", "")
        if msg_type in ("transcript.word", "transcript.text", "speech.final"):
            text = msg.get("text", "") or msg.get("transcript", "")
            speaker = "A"
            if self._speaker_diarization:
                speaker = msg.get("speaker_id", "A") or "A"
            if text.strip():
                await self._on_transcript(text.strip(), speaker)
        elif msg_type == "error":
            logger.error("Scribe error: %s", msg)

    async def send_audio(self, chunk: bytes) -> None:
        if self._running:
            await self._audio_queue.put(chunk)

    async def stop(self) -> None:
        self._running = False
        await self._audio_queue.put(None)  # signal sender to exit
        if self._receiver_task:
            self._receiver_task.cancel()
        if self._sender_task:
            await asyncio.wait_for(self._sender_task, timeout=2.0)
        if self._ws:
            await self._ws.close()
        logger.info("Scribe STT stopped")

    async def _reconnect(self) -> None:
        await asyncio.sleep(2)
        if self._running:
            logger.info("Reconnecting to Scribe STT...")
            await self._connect()
```

**Step 2: Commit**

```bash
git add backend/stt.py
git commit -m "feat(backend): ElevenLabs Scribe STT WebSocket bridge"
```

---

## Task 11: Pydantic AI agent

**Files:**
- Create: `backend/agent.py`

**Step 1: Create backend/agent.py**

```python
"""Pydantic AI agent builder and invocation logic."""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Callable, Awaitable

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from config import settings
from models import TranscriptChunk, SessionConfig

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """You are an AI listening companion. You listen to ongoing conversations
and help the user by maintaining context, tracking important information, and responding when helpful.

Current short-term memory (use IDs to update/remove entries):
{short_term_memory}

You have access to tools to:
- Manage short-term memory (save, update, remove entries)
- Archive important info to long-term memory
- Search past conversations via long-term memory
- Speak responses aloud (answer_tts) — use sparingly, only when truly helpful
- Generate images when the conversation references something visual
- Track entities, action items, quotes (if those tools are enabled)

Be concise. Act on what's new in the transcript. Don't repeat actions you've already taken.
If nothing meaningful happened, do nothing — it's fine to not call any tools."""


class SessionAgent:
    """Manages the Pydantic AI agent for a single session."""

    def __init__(
        self,
        session_config: SessionConfig,
        tools: list[Callable],
        get_short_term_context: Callable[[], str],
        emit_agent_start: Callable[[], Awaitable[None]],
        emit_agent_done: Callable[[], Awaitable[None]],
        emit_tool_call: Callable[[str, dict, object, str | None], Awaitable[None]],
    ):
        self._config = session_config
        self._tools = tools
        self._get_short_term_context = get_short_term_context
        self._emit_agent_start = emit_agent_start
        self._emit_agent_done = emit_agent_done
        self._emit_tool_call = emit_tool_call
        self._agent = self._build_agent()
        self._running = False
        self._loop_task: asyncio.Task | None = None
        self._last_transcript_count = 0

    def _build_agent(self) -> Agent:
        model = AnthropicModel(
            settings.claude_model,
            api_key=settings.anthropic_api_key,
        )

        # Wrap each tool to emit tool_call events
        wrapped_tools = [self._wrap_tool(t) for t in self._tools]

        return Agent(
            model=model,
            tools=wrapped_tools,
        )

    def _wrap_tool(self, fn: Callable) -> Callable:
        """Wrap a tool function to emit tool_call WS events on each invocation."""
        import functools
        import inspect

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            tool_args = {}
            sig = inspect.signature(fn)
            params = list(sig.parameters.keys())
            for i, arg in enumerate(args):
                if i < len(params):
                    tool_args[params[i]] = arg
            tool_args.update(kwargs)

            result = None
            error = None
            try:
                result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            except Exception as exc:
                error = str(exc)
                result = f"Tool error: {exc}"

            await self._emit_tool_call(fn.__name__, tool_args, result, error)
            return result

        if not asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                # For sync tools, we can't await emit — schedule it
                tool_args = {}
                result = fn(*args, **kwargs)
                asyncio.create_task(self._emit_tool_call(fn.__name__, tool_args, result, None))
                return result
            return sync_wrapper

        return wrapper

    async def start_loop(self, get_transcript: Callable[[], list[TranscriptChunk]], interval_s: int) -> None:
        self._running = True
        self._loop_task = asyncio.create_task(self._agent_loop(get_transcript, interval_s))

    async def stop_loop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _agent_loop(self, get_transcript: Callable[[], list[TranscriptChunk]], interval_s: int) -> None:
        while self._running:
            await asyncio.sleep(interval_s)
            if not self._running:
                break
            try:
                await self.invoke_once(get_transcript())
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Agent loop error (skipping cycle): %s", exc)

    async def invoke_once(self, transcript: list[TranscriptChunk]) -> None:
        """Run one agent invocation with the given transcript chunks."""
        # Skip if no new transcript since last run
        new_chunks = transcript[self._last_transcript_count:]
        if not new_chunks:
            logger.debug("Agent skipping — no new transcript")
            return

        self._last_transcript_count = len(transcript)

        # Build context window (last N seconds)
        cutoff = time.time() - settings.agent_transcript_window_s
        window = [c for c in new_chunks if c.ts >= cutoff]
        if not window:
            return

        transcript_text = "\n".join(
            f"[{c.speaker} {c.ts:.0f}] {c.text}" for c in window
        )

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            short_term_memory=self._get_short_term_context()
        )

        user_prompt = f"New transcript:\n{transcript_text}"

        await self._emit_agent_start()
        try:
            async with asyncio.timeout(settings.agent_timeout_s):
                await self._agent.run(user_prompt, system_prompt=system_prompt)
        except asyncio.TimeoutError:
            logger.warning("Agent timed out after %ds", settings.agent_timeout_s)
        except Exception as exc:
            logger.error("Agent invocation failed: %s", exc)
        finally:
            await self._emit_agent_done()
```

**Step 2: Commit**

```bash
git add backend/agent.py
git commit -m "feat(backend): Pydantic AI agent with tool wrapping and interval loop"
```

---

## Task 12: WebSocket handler (session orchestration)

**Files:**
- Create: `backend/ws_handler.py`

**Step 1: Create backend/ws_handler.py**

```python
"""WebSocket handler — session lifecycle and audio pipeline."""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from database import get_db
from models import (
    SessionConfig, Session, TranscriptChunk,
    WsTranscriptChunk, WsAgentStart, WsAgentDone,
    WsToolCall, WsMemoryUpdate, WsImageGenerated,
    WsTtsChunk, WsError, WsSessionStatus,
)
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from stt import ScribeSTT
from agent import SessionAgent
from tools.memory_ops import build_memory_tools
from tools.tts_tool import build_tts_tool
from tools.image_tool import build_image_tool
from tools import get_plugin_tools

logger = logging.getLogger(__name__)


class ActiveSession:
    """One active WebSocket session."""

    def __init__(self, ws: WebSocket, config: SessionConfig):
        self.id = f"sess_{uuid.uuid4().hex[:12]}"
        self.ws = ws
        self.config = config
        self.transcript: list[TranscriptChunk] = []
        self._db = None
        self._short_term: ShortTermMemory | None = None
        self._long_term: LongTermMemory | None = None
        self._stt: ScribeSTT | None = None
        self._agent: SessionAgent | None = None

    async def setup(self) -> None:
        self._db = await get_db()

        # Persist session row
        await self._db.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at, config) VALUES (?, ?, ?)",
            (self.id, time.time(), self.config.model_dump_json()),
        )
        await self._db.commit()

        # Memory
        self._short_term = ShortTermMemory(self.id, self._db)
        self._long_term = LongTermMemory(self.id, self._db)
        await self._short_term.load()

        # Build tools
        memory_tools = build_memory_tools(
            self._short_term, self._long_term, self._emit_memory_update
        )
        tts_tool = build_tts_tool(self.config.voice_id, self._emit_tts_chunk)
        image_tool = build_image_tool(self.config.image_provider, self._emit_image_generated)
        plugin_tools = get_plugin_tools(self.config.tools)

        all_tools = memory_tools + [tts_tool, image_tool] + plugin_tools

        # Agent
        self._agent = SessionAgent(
            session_config=self.config,
            tools=all_tools,
            get_short_term_context=self._short_term.as_context_str,
            emit_agent_start=self._emit_agent_start,
            emit_agent_done=self._emit_agent_done,
            emit_tool_call=self._emit_tool_call,
        )

        # STT
        self._stt = ScribeSTT(
            on_transcript=self._on_transcript,
            speaker_diarization=self.config.speaker_diarization,
        )
        await self._stt.start()

        # Start agent loop
        await self._agent.start_loop(
            get_transcript=lambda: self.transcript,
            interval_s=self.config.agent_interval_s,
        )

        await self._emit(WsSessionStatus(state="listening"))
        logger.info("Session %s started", self.id)

    async def teardown(self) -> None:
        if self._agent:
            await self._agent.stop_loop()
        if self._stt:
            await self._stt.stop()
        if self._db:
            await self._db.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (time.time(), self.id),
            )
            await self._db.commit()
        logger.info("Session %s ended", self.id)

    async def handle_audio(self, data: bytes) -> None:
        if self._stt:
            await self._stt.send_audio(data)

    async def handle_config_update(self, config_patch: dict) -> None:
        for k, v in config_patch.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    # ── Transcript callback ────────────────────────────────────────────────

    async def _on_transcript(self, text: str, speaker: str) -> None:
        chunk = TranscriptChunk(text=text, speaker=speaker)
        self.transcript.append(chunk)
        await self._emit(WsTranscriptChunk(text=text, speaker=speaker, ts=chunk.ts))

    # ── Emit helpers ───────────────────────────────────────────────────────

    async def _emit(self, event) -> None:
        try:
            await self.ws.send_text(event.model_dump_json())
        except Exception as exc:
            logger.debug("WS send failed: %s", exc)

    async def _emit_agent_start(self) -> None:
        await self._emit(WsAgentStart())

    async def _emit_agent_done(self) -> None:
        await self._emit(WsAgentDone())

    async def _emit_tool_call(self, tool: str, args: dict, result, error: str | None) -> None:
        event = WsToolCall(
            tool=tool,
            args=args,
            result=result if not isinstance(result, Exception) else str(result),
            error=error,
        )
        await self._emit(event)

    async def _emit_memory_update(self) -> None:
        if self._short_term:
            await self._emit(WsMemoryUpdate(short_term=self._short_term.all()))

    async def _emit_tts_chunk(self, audio_b64: str, text: str) -> None:
        await self._emit(WsTtsChunk(audio_b64=audio_b64, text=text))

    async def _emit_image_generated(self, url: str, prompt: str) -> None:
        await self._emit(WsImageGenerated(url=url, prompt=prompt))

    async def emit_error(self, code: str, message: str, fatal: bool = False) -> None:
        await self._emit(WsError(code=code, message=message, fatal=fatal))


async def websocket_handler(ws: WebSocket) -> None:
    """Main WebSocket endpoint handler."""
    await ws.accept()
    session: ActiveSession | None = None

    try:
        async for raw in ws.iter_text() if False else _ws_frames(ws):
            if isinstance(raw, bytes):
                # Binary = audio PCM
                if session:
                    await session.handle_audio(raw)
                continue

            # Text = JSON control frame
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "session_start":
                if session:
                    await session.teardown()
                config = SessionConfig(**msg.get("config", {}))
                session = ActiveSession(ws, config)
                try:
                    await session.setup()
                except Exception as exc:
                    logger.error("Session setup failed: %s", exc)
                    err = WsError(code="session_init_failed", message=str(exc), fatal=True)
                    await ws.send_text(err.model_dump_json())

            elif msg_type == "session_end":
                if session:
                    await session.teardown()
                    session = None

            elif msg_type == "config_update":
                if session:
                    await session.handle_config_update(msg.get("config", {}))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        if session:
            await session.teardown()


async def _ws_frames(ws: WebSocket):
    """Yield text or binary frames from a WebSocket."""
    while True:
        msg = await ws.receive()
        if msg["type"] == "websocket.disconnect":
            break
        elif msg["type"] == "websocket.receive":
            if "bytes" in msg and msg["bytes"]:
                yield msg["bytes"]
            elif "text" in msg and msg["text"]:
                yield msg["text"]
```

**Step 2: Commit**

```bash
git add backend/ws_handler.py
git commit -m "feat(backend): WebSocket handler, session lifecycle, audio pipeline"
```

---

## Task 13: FastAPI main app

**Files:**
- Create: `backend/main.py`

**Step 1: Create backend/main.py**

```python
"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
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
    # Startup: init DB
    await get_db()
    logger.info("Database initialized")
    yield
    # Shutdown: close DB
    await close_db()
    logger.info("Database closed")


app = FastAPI(title="Listening Companion API", lifespan=lifespan)

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


# Serve frontend static files in production
_frontend_dist = Path(settings.frontend_dist)
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
    logger.info("Serving frontend from %s", _frontend_dist)
else:
    logger.info("No frontend dist found at %s — API-only mode", _frontend_dist)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
```

**Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): FastAPI app, health endpoint, WS route, static files"
```

---

## Task 14: Tests

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_memory.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/tests/test_tools.py`

**Step 1: Create backend/tests/__init__.py** (empty)

**Step 2: Create backend/tests/conftest.py**

```python
import asyncio
import pytest
import aiosqlite
from pathlib import Path


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    from database import SCHEMA
    await db.executescript(SCHEMA)
    await db.commit()
    yield db
    await db.close()
```

**Step 3: Create backend/tests/test_memory.py**

```python
import pytest
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory


@pytest.mark.asyncio
async def test_short_term_save_and_retrieve(db):
    mem = ShortTermMemory("sess_test", db)
    entry = await mem.save("Meeting about Q1 goals", ["meeting", "goals"])
    assert entry.id.startswith("mem_")
    assert entry.content == "Meeting about Q1 goals"
    all_entries = mem.all()
    assert len(all_entries) == 1
    assert all_entries[0].id == entry.id


@pytest.mark.asyncio
async def test_short_term_update(db):
    mem = ShortTermMemory("sess_test", db)
    entry = await mem.save("Initial content", [])
    updated = await mem.update(entry.id, "Updated content")
    assert updated is not None
    assert updated.content == "Updated content"
    assert mem.all()[0].content == "Updated content"


@pytest.mark.asyncio
async def test_short_term_remove(db):
    mem = ShortTermMemory("sess_test", db)
    entry = await mem.save("To be removed", [])
    removed = await mem.remove(entry.id)
    assert removed is True
    assert len(mem.all()) == 0


@pytest.mark.asyncio
async def test_short_term_remove_nonexistent(db):
    mem = ShortTermMemory("sess_test", db)
    removed = await mem.remove("mem_nonexistent")
    assert removed is False


@pytest.mark.asyncio
async def test_short_term_context_str(db):
    mem = ShortTermMemory("sess_test", db)
    await mem.save("Topic: AI agents", ["topic"])
    ctx = mem.as_context_str()
    assert "Topic: AI agents" in ctx
    assert "#topic" in ctx


@pytest.mark.asyncio
async def test_short_term_load_from_db(db):
    # Save via one instance
    mem1 = ShortTermMemory("sess_abc", db)
    entry = await mem1.save("Persisted entry", ["persistent"])

    # Load via new instance (simulates restart)
    mem2 = ShortTermMemory("sess_abc", db)
    await mem2.load()
    loaded = mem2.all()
    assert len(loaded) == 1
    assert loaded[0].id == entry.id
    assert loaded[0].content == "Persisted entry"


@pytest.mark.asyncio
async def test_long_term_save_and_search(db):
    mem = LongTermMemory("sess_test", db)
    await mem.save("The team decided to use FastAPI for the backend", ["decision", "tech"])
    await mem.save("Alice is the project lead", ["person"])

    results = await mem.search("FastAPI backend decision")
    assert len(results) >= 1
    assert any("FastAPI" in r.content for r in results)
```

**Step 4: Create backend/tests/test_models.py**

```python
from models import MemoryEntry, SessionConfig, new_id, now
import time


def test_new_id_prefix():
    id_ = new_id("mem_")
    assert id_.startswith("mem_")
    assert len(id_) == 4 + 12  # "mem_" + 12 hex chars


def test_memory_entry_defaults():
    entry = MemoryEntry(content="test")
    assert entry.id.startswith("mem_")
    assert entry.tags == []
    assert entry.created_at <= time.time()


def test_session_config_defaults():
    config = SessionConfig()
    assert config.agent_interval_s == 30
    assert config.image_provider == "placeholder"
    assert config.tools == []
```

**Step 5: Create backend/tests/test_tools.py**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_memory_tools_save(db):
    from memory.short_term import ShortTermMemory
    from memory.long_term import LongTermMemory
    from tools.memory_ops import build_memory_tools

    short = ShortTermMemory("sess_test", db)
    long = LongTermMemory("sess_test", db)
    emit = AsyncMock()

    tools = build_memory_tools(short, long, emit)
    save_fn = next(t for t in tools if t.__name__ == "save_short_term_memory")

    result = await save_fn("Test content", ["tag1"])
    assert result.startswith("mem_")
    emit.assert_called_once()
    assert len(short.all()) == 1


@pytest.mark.asyncio
async def test_memory_tools_remove(db):
    from memory.short_term import ShortTermMemory
    from memory.long_term import LongTermMemory
    from tools.memory_ops import build_memory_tools

    short = ShortTermMemory("sess_test", db)
    long = LongTermMemory("sess_test", db)
    emit = AsyncMock()

    tools = build_memory_tools(short, long, emit)
    save_fn = next(t for t in tools if t.__name__ == "save_short_term_memory")
    remove_fn = next(t for t in tools if t.__name__ == "remove_short_term_memory")

    entry_id = await save_fn("To remove", [])
    result = await remove_fn(entry_id)
    assert "Removed" in result
    assert len(short.all()) == 0


@pytest.mark.asyncio
async def test_image_tool_placeholder():
    from tools.image_tool import build_image_tool

    emit = AsyncMock()
    tool = build_image_tool("placeholder", emit)
    result = await tool("A dragon in a forest")
    assert "placehold.co" in result or "generated" in result.lower()
    emit.assert_called_once()
```

**Step 6: Run tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: all tests pass (long_term search test may be slow due to model download on first run).

**Step 7: Commit**

```bash
git add backend/tests/
git commit -m "test(backend): memory, model, and tool tests"
```

---

## Task 15: .env setup and smoke test

**Files:**
- Create: `backend/.env.example`

**Step 1: Create backend/.env.example**

```
ELEVENLABS_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
DATABASE_PATH=listening_companion.db
FRONTEND_DIST=../frontend/dist
```

**Step 2: Copy .env from openclaw**

```bash
cp ~/.openclaw/.env backend/.env
```

**Step 3: Smoke test — start the server**

```bash
cd backend && uv run uvicorn main:app --reload --port 8000
```

Expected: Server starts, "Database initialized" in logs.

**Step 4: Test health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

**Step 5: Final commit**

```bash
git add backend/.env.example
git commit -m "feat(backend): .env.example"
```

**Step 6: Tag completion**

```bash
git add -A && git commit -m "feat: complete Phase 2 Python backend

- FastAPI app with WebSocket endpoint at /ws
- ElevenLabs Scribe STT WebSocket bridge
- ElevenLabs TTS v3 streaming (EU endpoint)
- Pydantic AI agent with configurable interval loop
- Short-term memory (in-memory + SQLite backup)
- Long-term memory (SQLite + numpy cosine similarity)
- Tool registry with @tool decorator and auto-discovery
- Core tools: save/update/remove short-term, save/search long-term, TTS, image gen
- Plugin tool example: entity_tracker
- Session management in SQLite
- Serves frontend/dist static files in production
- pydantic-settings config via .env
- Full test suite (memory, models, tools)" --allow-empty
```
