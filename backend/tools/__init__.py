"""Tool registry: @tool decorator for plugin tools + auto-discovery."""
from __future__ import annotations
import importlib
import pkgutil
import pathlib
import logging
from typing import Callable

log = logging.getLogger(__name__)

_PLUGIN_REGISTRY: dict[str, Callable] = {}


def tool(fn: Callable | None = None, *, tags: list[str] | None = None):
    """Register a plugin tool in the global registry."""
    def decorator(f: Callable) -> Callable:
        _PLUGIN_REGISTRY[f.__name__] = f
        f._tool_tags = tags or []
        return f
    return decorator(fn) if fn is not None else decorator


def discover_plugins() -> None:
    """Import all plugin modules in tools/ to populate registry."""
    tools_dir = pathlib.Path(__file__).parent
    _skip = {"__init__", "memory_ops", "tts_tool", "image_tool"}
    for _, module_name, _ in pkgutil.iter_modules([str(tools_dir)]):
        if module_name not in _skip:
            importlib.import_module(f"tools.{module_name}")


def get_plugin_tools(names: list[str]) -> list[Callable]:
    """Return registered plugin tools by name (logs warning for unknowns)."""
    discover_plugins()
    result = []
    for name in names:
        if name in _PLUGIN_REGISTRY:
            result.append(_PLUGIN_REGISTRY[name])
        else:
            log.warning("Unknown plugin tool requested: %s", name)
    return result
