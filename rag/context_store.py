"""Simple JSON-based RAG context store for event enrichment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)


class ContextStore:
    """JSON-based context store for RAG enrichment (RAG_MODE=simple).

    Stores scraped content indexed by event/topic for later retrieval.
    Used by the RAG Enrichment Agent to cache web-scraped data.

    Storage: data/context_store.json
    """

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or settings.DATA_DIR / "context_store.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store: dict[str, list[dict]] = self._load()

    def _load(self) -> dict:
        """Load store from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self):
        """Persist store to disk."""
        try:
            with open(self.store_path, "w") as f:
                json.dump(self._store, f, indent=2, default=str)
        except IOError as e:
            logger.error("context_store_save_failed", error=str(e))

    def add_context(
        self,
        topic: str,
        content: str,
        source_url: str = "",
        tags: list[str] | None = None,
    ):
        """Store context content for a topic.

        Args:
            topic: The event/topic identifier.
            content: The text content to store.
            source_url: Where the content was scraped from.
            tags: Searchable tags.
        """
        if topic not in self._store:
            self._store[topic] = []

        # Deduplicate by source URL
        if source_url:
            for existing in self._store[topic]:
                if existing.get("source_url") == source_url:
                    logger.debug("context_duplicate_skipped", url=source_url)
                    return

        entry = {
            "content": content[:5000],  # Cap content length
            "source_url": source_url,
            "tags": tags or [],
            "added_at": datetime.now(timezone.utc).isoformat(),
        }

        self._store[topic].append(entry)
        self._save()
        logger.info("context_added", topic=topic[:40], chars=len(content))

    def get_context(self, topic: str) -> list[dict]:
        """Retrieve all stored context for a topic.

        Args:
            topic: The event/topic identifier.

        Returns:
            List of context entry dicts.
        """
        return self._store.get(topic, [])

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search across all topics by keyword matching.

        Args:
            query: Search query.
            top_k: Max results to return.

        Returns:
            List of matching context entries with their topic.
        """
        query_lower = query.lower()
        results = []

        for topic, entries in self._store.items():
            for entry in entries:
                score = 0
                if query_lower in topic.lower():
                    score += 3
                if query_lower in entry.get("content", "").lower():
                    score += 2
                if any(query_lower in tag.lower() for tag in entry.get("tags", [])):
                    score += 2

                if score > 0:
                    results.append({
                        "topic": topic,
                        "score": score,
                        **entry,
                    })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_summary(self, topic: str, max_chars: int = 2000) -> str:
        """Get a combined text summary of all context for a topic.

        Args:
            topic: The event/topic identifier.
            max_chars: Max total characters to return.

        Returns:
            Combined context string.
        """
        entries = self.get_context(topic)
        if not entries:
            return ""

        parts = []
        total = 0
        for entry in entries:
            text = entry.get("content", "")
            source = entry.get("source_url", "unknown")
            chunk = f"[Source: {source}]\n{text}\n"
            if total + len(chunk) > max_chars:
                break
            parts.append(chunk)
            total += len(chunk)

        return "\n---\n".join(parts)

    def topic_count(self) -> int:
        """Return number of topics stored."""
        return len(self._store)

    def clear(self):
        """Clear all stored contexts."""
        self._store = {}
        self._save()
