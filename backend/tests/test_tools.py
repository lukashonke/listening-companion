import pytest
from unittest.mock import AsyncMock


class TestMemoryTools:
    async def test_save_creates_entry(self, db):
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from tools.memory_ops import build_memory_tools

        short = ShortTermMemory("sess_t", db)
        long = LongTermMemory("sess_t", db)
        emit = AsyncMock()

        tools = build_memory_tools(short, long, emit)
        save_fn = next(t for t in tools if t.__name__ == "save_short_term_memory")

        result = await save_fn("Test content", ["tag1"])
        assert result.startswith("mem_")
        emit.assert_called_once()
        assert len(short.all()) == 1

    async def test_remove_existing(self, db):
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from tools.memory_ops import build_memory_tools

        short = ShortTermMemory("sess_t2", db)
        long = LongTermMemory("sess_t2", db)
        emit = AsyncMock()
        tools = build_memory_tools(short, long, emit)
        save_fn = next(t for t in tools if t.__name__ == "save_short_term_memory")
        remove_fn = next(t for t in tools if t.__name__ == "remove_short_term_memory")

        entry_id = await save_fn("To remove", [])
        result = await remove_fn(entry_id)
        assert "Removed" in result
        assert len(short.all()) == 0

    async def test_remove_nonexistent(self, db):
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from tools.memory_ops import build_memory_tools

        short = ShortTermMemory("sess_t3", db)
        long = LongTermMemory("sess_t3", db)
        emit = AsyncMock()
        tools = build_memory_tools(short, long, emit)
        remove_fn = next(t for t in tools if t.__name__ == "remove_short_term_memory")

        result = await remove_fn("mem_doesnotexist")
        assert "not found" in result

    async def test_update_existing(self, db):
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from tools.memory_ops import build_memory_tools

        short = ShortTermMemory("sess_t4", db)
        long = LongTermMemory("sess_t4", db)
        emit = AsyncMock()
        tools = build_memory_tools(short, long, emit)
        save_fn = next(t for t in tools if t.__name__ == "save_short_term_memory")
        update_fn = next(t for t in tools if t.__name__ == "update_short_term_memory")

        entry_id = await save_fn("Original content", [])
        result = await update_fn(entry_id, "Updated content")
        assert "Updated" in result
        assert short.all()[0].content == "Updated content"

    async def test_long_term_save_and_search(self, db):
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from tools.memory_ops import build_memory_tools

        short = ShortTermMemory("sess_lt", db)
        long = LongTermMemory("sess_lt", db)
        emit = AsyncMock()
        tools = build_memory_tools(short, long, emit)
        save_lt = next(t for t in tools if t.__name__ == "save_long_term_memory")
        search_lt = next(t for t in tools if t.__name__ == "search_long_term_memory")

        await save_lt("The decision was to use Python for the backend", ["decision"])
        result = await search_lt("Python backend decision")
        assert "Python" in result


class TestImageTool:
    async def test_placeholder_generates_url(self):
        from tools.image_tool import build_image_tool

        emit = AsyncMock()
        tool = build_image_tool("placeholder", emit)
        result = await tool("A dragon in a forest")
        assert "placehold.co" in result or "Image generated" in result
        emit.assert_called_once()

    async def test_image_tool_calls_emit_with_url(self):
        from tools.image_tool import build_image_tool

        emit = AsyncMock()
        tool = build_image_tool("placeholder", emit)
        await tool("Test prompt")
        args = emit.call_args[0]
        assert args[0].startswith("https://")
        assert "Test" in args[1] or args[1] == "Test prompt"
