"""Entity tracker plugin — tracks named entities mentioned in conversation."""
from tools import tool


@tool(tags=["plugin"])
async def track_entity(name: str, entity_type: str, description: str) -> str:
    """
    Track a named entity mentioned in the conversation.
    Use whenever a significant new entity is introduced that should be remembered.

    NOTE: This is a stub/example plugin. It returns a confirmation string but does not
    persist data to memory. To make entities persistent, chain with save_short_term_memory.

    Args:
        name: The entity's name (e.g. "Alice", "Project Phoenix", "Zurich")
        entity_type: One of: person, place, item, concept, organization
        description: Brief description of who/what this entity is
    """
    return f"Tracked {entity_type} '{name}': {description}"
