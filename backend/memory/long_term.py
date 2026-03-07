"""Long-term memory backed by SQLite with sentence-transformer embeddings.

Architecture note: The design document specifies sqlite-vec for vector search
(``vec_distance_cosine``). We use in-Python numpy cosine similarity instead —
no native extension is required and the implementation is simpler. This is fine
for small datasets (< a few thousand entries). To scale, replace the
``search`` method's scoring loop with a sqlite-vec virtual-table query using
``vec_distance_cosine``.
"""
from __future__ import annotations
import asyncio
import json
import logging
import struct

import aiosqlite
import numpy as np

from models import LongTermEntry, now

logger = logging.getLogger(__name__)

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
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, _embed, content)
        try:
            await self._db.execute(
                """INSERT INTO long_term_memory
                   (id, session_id, content, tags, embedding, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.session_id,
                    entry.content,
                    json.dumps(entry.tags),
                    _vec_to_blob(embedding),
                    entry.created_at,
                ),
            )
            await self._db.commit()
        except Exception as exc:
            logger.warning("Long-term memory save failed: %s", exc)
        return entry

    async def search(self, query: str, top_k: int = 5) -> list[LongTermEntry]:
        loop = asyncio.get_running_loop()
        query_vec = await loop.run_in_executor(None, _embed, query)

        rows = []
        async with self._db.execute(
            "SELECT id, content, tags, embedding, created_at FROM long_term_memory WHERE session_id = ?",
            (self._session_id,),
        ) as cursor:
            async for row in cursor:
                rows.append(dict(row))

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
            results.append(
                LongTermEntry(
                    id=row["id"],
                    session_id=self._session_id,
                    content=row["content"],
                    tags=json.loads(row["tags"]),
                    created_at=row["created_at"],
                )
            )
        return results
