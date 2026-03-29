"""Provider ABCs — infrastructure contracts with zero external dependencies.

Each provider abstracts one infrastructure concern.  Domain implementations
(e.g. AnthropicLLMProvider, Neo4jGraphStore) live in the consuming project
and are injected via AppConfig.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Contract for any text-generation / structured-extraction LLM backend."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 512,
    ) -> str:
        """Return the model's raw text completion."""

    @abstractmethod
    def extract_structured(
        self,
        text: str,
        output_schema: dict[str, Any],
        *,
        system: str = "",
    ) -> dict[str, Any]:
        """Extract structured data conforming to *output_schema* from *text*.

        The schema follows JSON Schema conventions.  Implementations may use
        tool-calling, constrained decoding, or prompt-engineering to satisfy
        the schema.
        """


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Contract for text embedding models."""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        Always returns a list of the same length as *texts*, even on partial
        failure (use zero-vectors as placeholders).
        """

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimensionality (e.g. 1024 for bge-m3)."""


# ---------------------------------------------------------------------------
# Graph store
# ---------------------------------------------------------------------------

class GraphStore(ABC):
    """Contract for property-graph databases (Neo4j, NebulaGraph, …)."""

    @abstractmethod
    def write(self, query: str, **params: Any) -> None:
        """Execute a write query (Cypher / nGQL / …).

        Implementations should handle connection pooling and retries
        internally.
        """

    @abstractmethod
    def read(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Execute a read query and return rows as plain dicts."""


# ---------------------------------------------------------------------------
# Relational store
# ---------------------------------------------------------------------------

class RelationalStore(ABC):
    """Contract for relational databases (PostgreSQL, SQLite, …)."""

    @abstractmethod
    def fetchone(
        self, sql: str, params: tuple | dict | None = None
    ) -> dict[str, Any] | None:
        """Return at most one row as a plain dict, or None."""

    @abstractmethod
    def fetchall(
        self, sql: str, params: tuple | dict | None = None
    ) -> list[dict[str, Any]]:
        """Return all matching rows as plain dicts."""

    @abstractmethod
    def execute(
        self, sql: str, params: tuple | dict | None = None
    ) -> None:
        """Execute a DML statement (INSERT / UPDATE / DELETE)."""

    @abstractmethod
    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """Yield a cursor (or equivalent) inside a single transaction.

        Usage::

            with store.transaction() as cur:
                cur.execute(...)
                cur.executemany(...)
        """
        yield  # pragma: no cover


# ---------------------------------------------------------------------------
# Object store
# ---------------------------------------------------------------------------

class ObjectStore(ABC):
    """Contract for blob / object storage (MinIO, S3, GCS, local FS, …)."""

    @abstractmethod
    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        """Store *data* under *key* and return the canonical URI."""

    @abstractmethod
    def get(self, uri: str) -> bytes:
        """Retrieve and return the raw bytes stored at *uri*."""

    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Return True if the object at *uri* exists."""