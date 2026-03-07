import pytest
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory


class TestShortTermMemory:
    async def test_save_and_retrieve(self, db):
        mem = ShortTermMemory("sess_test", db)
        entry = await mem.save("Meeting about Q1 goals", ["meeting", "goals"])
        assert entry.id.startswith("mem_")
        all_entries = mem.all()
        assert len(all_entries) == 1
        assert all_entries[0].content == "Meeting about Q1 goals"
        assert "goals" in all_entries[0].tags

    async def test_update(self, db):
        mem = ShortTermMemory("sess_test", db)
        entry = await mem.save("Initial content", [])
        updated = await mem.update(entry.id, "Updated content")
        assert updated is not None
        assert updated.content == "Updated content"
        assert mem.all()[0].content == "Updated content"

    async def test_update_nonexistent(self, db):
        mem = ShortTermMemory("sess_test", db)
        result = await mem.update("mem_doesnotexist", "new content")
        assert result is None

    async def test_remove(self, db):
        mem = ShortTermMemory("sess_test", db)
        entry = await mem.save("To be removed", [])
        removed = await mem.remove(entry.id)
        assert removed is True
        assert len(mem.all()) == 0

    async def test_remove_nonexistent(self, db):
        mem = ShortTermMemory("sess_test", db)
        assert await mem.remove("mem_nonexistent") is False

    async def test_context_str_empty(self, db):
        mem = ShortTermMemory("sess_test", db)
        assert mem.as_context_str() == "(empty)"

    async def test_context_str_with_entries(self, db):
        mem = ShortTermMemory("sess_test", db)
        await mem.save("Topic: AI agents", ["topic"])
        ctx = mem.as_context_str()
        assert "Topic: AI agents" in ctx
        assert "#topic" in ctx

    async def test_persist_and_load(self, db):
        """Entries survive across ShortTermMemory instances (SQLite persistence)."""
        mem1 = ShortTermMemory("sess_persist", db)
        entry = await mem1.save("Persisted entry", ["persistent"])

        mem2 = ShortTermMemory("sess_persist", db)
        await mem2.load()
        loaded = mem2.all()
        assert len(loaded) == 1
        assert loaded[0].id == entry.id
        assert loaded[0].content == "Persisted entry"

    async def test_multiple_sessions_isolated(self, db):
        """Entries from different sessions don't bleed into each other."""
        mem_a = ShortTermMemory("sess_a", db)
        mem_b = ShortTermMemory("sess_b", db)
        await mem_a.save("Session A entry", [])
        await mem_b.save("Session B entry", [])

        fresh_a = ShortTermMemory("sess_a", db)
        await fresh_a.load()
        assert len(fresh_a.all()) == 1
        assert fresh_a.all()[0].content == "Session A entry"


class TestLongTermMemory:
    async def test_save_and_search(self, db):
        mem = LongTermMemory("sess_ltm", db)
        await mem.save("The team decided to use FastAPI for the backend", ["decision"])
        await mem.save("Alice is the project lead", ["person"])

        results = await mem.search("FastAPI backend framework decision")
        assert len(results) >= 1
        assert any("FastAPI" in r.content for r in results)

    async def test_search_empty(self, db):
        mem = LongTermMemory("sess_empty", db)
        results = await mem.search("anything")
        assert results == []

    async def test_search_top_k(self, db):
        mem = LongTermMemory("sess_topk", db)
        for i in range(10):
            await mem.save(f"Entry number {i} about various topics", [])

        results = await mem.search("entry topics", top_k=3)
        assert len(results) <= 3
