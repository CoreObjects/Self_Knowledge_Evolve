"""
Embedding client using BAAI/bge-m3 (1024-dim, bilingual Chinese/English).

Usage:
    from src.utils.embedding import get_embeddings
    vecs = get_embeddings(["BGP best path selection", "BGP最优路径选择"])
    # → list of 1024-dim float lists, or None if embedding is disabled/unavailable
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

_model = None   # lazy-loaded SentenceTransformer instance
_enabled: Optional[bool] = None


def _is_enabled() -> bool:
    global _enabled
    if _enabled is None:
        from src.config.settings import settings
        _enabled = settings.EMBEDDING_ENABLED
    return _enabled


def _load_model():
    global _model
    if _model is not None:
        return _model
    from src.config.settings import settings
    try:
        from sentence_transformers import SentenceTransformer
        log.info("Loading embedding model %s on %s …", settings.EMBEDDING_MODEL, settings.EMBEDDING_DEVICE)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL, device=settings.EMBEDDING_DEVICE)
        log.info("Embedding model loaded (dim=%d)", settings.EMBEDDING_DIM)
    except ImportError:
        log.warning("sentence-transformers not installed; embedding disabled. "
                    "Run: pip install sentence-transformers")
        _enabled = False
    except Exception as exc:
        log.warning("Failed to load embedding model: %s; embedding disabled.", exc)
        _enabled = False
    return _model


def get_embeddings(texts: list[str]) -> list[list[float]] | None:
    """
    Encode a batch of texts with bge-m3.

    Returns:
        List of 1024-dim float vectors, or None if embedding is disabled.
    """
    if not _is_enabled():
        return None
    model = _load_model()
    if model is None:
        return None
    if not texts:
        return []
    from src.config.settings import settings
    try:
        vecs = model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,   # cosine similarity via dot product
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]
    except Exception as exc:
        log.warning("Embedding inference failed: %s", exc)
        return None


def embed_query(query: str) -> list[float] | None:
    """Encode a single query string."""
    results = get_embeddings([query])
    if results:
        return results[0]
    return None


def vector_to_pg_literal(vec: list[float]) -> str:
    """Format a float list as a PostgreSQL vector literal string."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"