"""Vector store stub for advanced RAG mode (ChromaDB).

This module provides a vector-based semantic search store for RAG enrichment.
It requires optional dependencies: chromadb and sentence-transformers.

To enable:
    1. pip install chromadb sentence-transformers
    2. Set RAG_MODE=advanced in .env

If dependencies are not installed, falls back gracefully to the simple
JSON-based ContextStore.
"""

from __future__ import annotations

import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)

# Try to import ChromaDB — graceful fallback if not installed
_CHROMADB_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMADB_AVAILABLE = True
except ImportError:
    pass


class VectorStore:
    """ChromaDB-based vector store for semantic RAG search.

    Falls back to a no-op if ChromaDB is not installed.
    Use ContextStore (rag/context_store.py) for the simple alternative.
    """

    def __init__(self, collection_name: str = "prediction_markets"):
        self.collection_name = collection_name
        self._collection = None

        if not _CHROMADB_AVAILABLE:
            logger.info("vector_store_unavailable", reason="chromadb not installed")
            return

        if settings.RAG_MODE != "advanced":
            logger.info("vector_store_skipped", reason="RAG_MODE != advanced")
            return

        try:
            persist_dir = str(settings.DATA_DIR / "chroma_db")
            client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            ))
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("vector_store_ready", collection=collection_name)
        except Exception as e:
            logger.error("vector_store_init_failed", error=str(e))

    @property
    def is_available(self) -> bool:
        return self._collection is not None

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ):
        """Add documents to the vector store.

        Args:
            texts: List of text strings to embed.
            metadatas: Optional metadata dicts for each document.
            ids: Optional unique IDs for each document.
        """
        if not self.is_available:
            return

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(texts))]

        try:
            self._collection.add(
                documents=texts,
                metadatas=metadatas or [{}] * len(texts),
                ids=ids,
            )
            logger.info("vector_store_added", count=len(texts))
        except Exception as e:
            logger.error("vector_store_add_failed", error=str(e))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for similar documents.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of dicts with 'text', 'metadata', 'distance' keys.
        """
        if not self.is_available:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            output = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                output.append({
                    "text": doc,
                    "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                    "distance": results.get("distances", [[]])[0][i] if results.get("distances") else 0,
                })
            return output
        except Exception as e:
            logger.error("vector_store_search_failed", error=str(e))
            return []
