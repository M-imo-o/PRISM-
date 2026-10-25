"""Persistent ChromaDB storage for the standalone Level 4 archive."""
from __future__ import annotations

from typing import Any, Sequence


class L4StorageError(RuntimeError):
    """Raised when the L4 ChromaDB store cannot be used."""


class L4:
    """Local persistent vector storage for document chunks."""

    def __init__(self, persist_directory: str, collection_name: str):
        try:
            import chromadb

            client = chromadb.PersistentClient(path=persist_directory)
            self.collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            if (self.collection.metadata or {}).get("hnsw:space") != "cosine":
                raise L4StorageError(
                    f"Collection {collection_name!r} is not configured for cosine similarity."
                )
        except ImportError as exc:
            raise L4StorageError("Install chromadb to use the L4 vector store.") from exc
        except L4StorageError:
            raise
        except Exception as exc:
            raise L4StorageError(f"Could not initialize ChromaDB: {exc}") from exc

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        metadatas: Sequence[dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        self.collection.upsert(
            ids=list(ids),
            documents=list(documents),
            metadatas=list(metadatas),
            embeddings=[list(embedding) for embedding in embeddings],
        )

    def remove_stale(self, source_path: str, current_ids: set[str]) -> None:
        existing = self.collection.get(where={"source_path": source_path}, include=["metadatas"])
        stale_ids = [item_id for item_id in existing.get("ids", []) if item_id not in current_ids]
        if stale_ids:
            self.collection.delete(ids=stale_ids)

    def query(self, embedding: Sequence[float], top_k: int) -> dict[str, Any]:
        return self.collection.query(
            query_embeddings=[list(embedding)],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
