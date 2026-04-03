"""Neo4jGraphStore — GraphStore implementation backed by src/db/neo4j_client.py."""

from __future__ import annotations

from typing import Any

from semcore.providers.base import GraphStore
import src.db.neo4j_client as neo4j

import logging

log = logging.getLogger(__name__)


class Neo4jGraphStore(GraphStore):
    def write(self, query: str, **params: Any) -> None:
        log.debug("neo4j write: %s", query[:120])
        neo4j.run_write(query, **params)

    def read(self, query: str, **params: Any) -> list[dict[str, Any]]:
        log.debug("neo4j read: %s", query[:120])
        rows = neo4j.run_query(query, **params)
        log.debug("neo4j read: %d rows", len(rows))
        return rows