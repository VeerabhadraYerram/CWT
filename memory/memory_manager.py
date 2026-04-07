"""Persistent memory manager — Hermes-inspired JSON-based memory system."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)


class MemoryManager:
    """Manages persistent memory across agent sessions.

    Implements Hermes' memory pattern:
    - Save notable observations, outcomes, and learnings
    - Search memories by keyword
    - Retrieve recent memories for context injection

    Storage: memory/store/memory.json
    """

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or settings.MEMORY_DIR / "memory.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._memories: list[dict] = self._load()

    def _load(self) -> list[dict]:
        """Load memories from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("memory_load_failed", error=str(e))
        return []

    def _save(self):
        """Persist memories to disk."""
        try:
            with open(self.store_path, "w") as f:
                json.dump(self._memories, f, indent=2, default=str)
        except IOError as e:
            logger.error("memory_save_failed", error=str(e))

    def save_memory(
        self,
        content: str,
        category: str = "observation",
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Store a new memory entry.

        Args:
            content: The memory content text.
            category: Type of memory (observation, outcome, learning, skill, feedback).
            tags: Searchable tags for retrieval.
            metadata: Additional structured data.

        Returns:
            The memory ID.
        """
        memory_id = f"mem_{len(self._memories):04d}"
        entry = {
            "id": memory_id,
            "content": content,
            "category": category,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._memories.append(entry)
        self._save()

        logger.info("memory_saved", id=memory_id, category=category)
        return memory_id

    def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories by keyword match on content and tags.

        Args:
            query: Search query string.
            limit: Max results to return.

        Returns:
            List of matching memory entries, most recent first.
        """
        query_lower = query.lower()
        results = []

        for mem in reversed(self._memories):
            content_match = query_lower in mem["content"].lower()
            tag_match = any(query_lower in tag.lower() for tag in mem.get("tags", []))
            category_match = query_lower in mem.get("category", "").lower()

            if content_match or tag_match or category_match:
                results.append(mem)
                if len(results) >= limit:
                    break

        return results

    def get_recent(self, n: int = 5, category: str | None = None) -> list[dict]:
        """Get the N most recent memories, optionally filtered by category.

        Args:
            n: Number of memories to return.
            category: Optional category filter.

        Returns:
            List of recent memory entries.
        """
        memories = self._memories
        if category:
            memories = [m for m in memories if m.get("category") == category]
        return list(reversed(memories[-n:]))

    def get_all(self) -> list[dict]:
        """Return all memories."""
        return list(self._memories)

    def count(self) -> int:
        """Return total memory count."""
        return len(self._memories)

    def clear(self):
        """Clear all memories (use with caution)."""
        self._memories = []
        self._save()
        logger.info("memory_cleared")
