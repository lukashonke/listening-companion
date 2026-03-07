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
    """Return 5 memory tools bound to this session's memory objects."""

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
