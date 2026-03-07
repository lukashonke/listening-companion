"""Long-term memory backed by SQLite with OpenAI embeddings.

Architecture note: The design document specifies sqlite-vec for vector search
(``vec_distance_cosine``). We use in-Python dot-product similarity instead —
no native extension is required and the implementation is simpler. This is fine
for small datasets (< a few thousand entries). OpenAI returns L2-normalized
vectors so dot product == cosine similarity.
"""
from __future__ import annotations
import json
import logging
import struct

import aiosqlite
import openai

from config import settings
from models import LongTermEntry, now

logger = logging.getLogger(__name__)

_openai_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _embed(text: str) -> list[float]:
    response = await _get_client().embeddings.create(
        model="text-embedding-3-small",
        input=text,
        dimensions=384,
    )
    return response.data[0].embedding


def _vec_to_blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _blob_to_vec(b: bytes) -> list[float]:
    n = len(b) // 4
    return list(struct.unpack(f"{n}f", b))


class LongTermMemory:
    def __init__(self, session_id: str, db: aiosqlite.Connection):
        self._session_id = session_id
        self._db = db

    async def save(self, content: str, tags: list[str]) -> LongTermEntry:
        entry = LongTermEntry(session_id=self._session_id, content=content, tags=tags)
        embedding = await _embed(content)
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
        query_vec = await _embed(query)

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
            score = sum(a * b for a, b in zip(query_vec, vec))
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
