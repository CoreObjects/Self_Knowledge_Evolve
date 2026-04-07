"""
In-memory ObjectStore substitute for local development.

Used by run_dev.py so the app can run without a MinIO service.
"""

from __future__ import annotations

from semcore.providers.base import ObjectStore


class InMemoryObjectStore(ObjectStore):
    """Simple in-memory object store keyed by URI."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        del content_type  # unused in dev mode
        norm_key = key.lstrip("/")
        uri = f"dev://{norm_key}" if not norm_key.startswith("dev://") else norm_key
        self._objects[uri] = bytes(data)
        return uri

    def get(self, uri: str) -> bytes:
        return self._objects.get(uri, b"")

    def exists(self, uri: str) -> bool:
        return uri in self._objects
