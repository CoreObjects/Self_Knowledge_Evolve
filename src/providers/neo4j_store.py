"""Neo4jGraphStore — GraphStore implementation backed by src/db/neo4j_client.py."""

from __future__ import annotations

from typing import Any

from semcore.providers.base import GraphStore
import src.db.neo4j_client as neo4j


class Neo4jGraphStore(GraphStore):
    def write(self, query: str, **params: Any) -> None:
        neo4j.run_write(query, **params)

    def read(self, query: str, **params: Any) -> list[dict[str, Any]]:
        return neo4j.run_query(query, **params)