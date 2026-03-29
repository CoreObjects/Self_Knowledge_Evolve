"""BGEM3EmbeddingProvider — EmbeddingProvider backed by src/utils/embedding.py."""

from __future__ import annotations

from semcore.providers.base import EmbeddingProvider
from src.utils import embedding as _emb


class BGEM3EmbeddingProvider(EmbeddingProvider):
    def encode(self, texts: list[str]) -> list[list[float]]:
        result = _emb.get_embeddings(texts)
        if result is None:
            return [[] for _ in texts]
        return result

    def dimension(self) -> int:
        from src.config.settings import settings
        return settings.EMBEDDING_DIM

    def to_pg_literal(self, vec: list[float]) -> str:
        return _emb.vector_to_pg_literal(vec)

    def embed_query(self, query: str) -> list[float] | None:
        return _emb.embed_query(query)