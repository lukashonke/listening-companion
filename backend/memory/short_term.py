from __future__ import annotations
import asyncio
import json
import logging
import time

import aiosqlite

from models import MemoryEntry, now
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
        lines = [
            f"[{e.id}] {e.content}" + (f" #{' #'.join(e.tags)}" if e.tags else "")
            for e in entries
        ]
        return "\n".join(lines)

    async def _persist(self, entry: MemoryEntry) -> None:
        try:
            await self._db.execute(
                """INSERT OR REPLACE INTO short_term_memory
                   (id, session_id, content, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    self._session_id,
                    entry.content,
                    json.dumps(entry.tags),
                    entry.created_at,
                    entry.updated_at,
                ),
            )
            await self._db.commit()
        except Exception as exc:
            logger.warning("SQLite write failed (in-memory state preserved): %s", exc)

    async def _prune_if_needed(self) -> None:
        if len(self._entries) <= settings.short_term_memory_max:
            return
        # Tagged entries are exempt from pruning — the cap is a soft limit when all entries are tagged.
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
