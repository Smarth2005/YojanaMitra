"""Semantic retrieval over the local Chroma collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CHROMA_DIR


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]
    distance: float


class Retriever:
    def __init__(self, path: Path = CHROMA_DIR, collection: Any = None, embedder: Any = None):
        self._embedder = embedder
        if collection is None:
            import chromadb
            from sentence_transformers import SentenceTransformer

            client = chromadb.PersistentClient(path=str(path))
            collection = client.get_or_create_collection("yojanamitra")
            self._embedder = embedder or SentenceTransformer("all-MiniLM-L6-v2")
        self.collection = collection

    def search(
        self,
        query: str,
        top_k: int = 4,
        state: str | None = None,
        scheme_name: str | None = None,
        sections: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        where: dict[str, Any] | None = None
        clauses: list[dict[str, Any]] = []
        if state:
            clauses.append(
                {"$or": [{"state_or_level": state}, {"state_or_level": "Central"}]}
            )
        if scheme_name:
            clauses.append({"scheme_name": {"$eq": scheme_name}})
        if sections:
            clauses.append({"section": {"$in": sections}})
        if clauses:
            where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        encoded = self._embedder.encode([query], normalize_embeddings=True)
        embedding = encoded.tolist() if hasattr(encoded, "tolist") else encoded
        result = self.collection.query(
            query_embeddings=embedding, n_results=top_k, where=where
        )
        texts = result.get("documents", [[]])[0]
        metadata = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            RetrievedChunk(text, meta, distance)
            for text, meta, distance in zip(texts, metadata, distances)
        ]
