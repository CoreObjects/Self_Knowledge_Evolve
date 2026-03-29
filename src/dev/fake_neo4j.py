"""
In-memory Neo4j substitute backed by OntologyRegistry data.
Replaces src.db.neo4j_client so operators can run without a real Neo4j instance.

Implements only the Cypher patterns actually used by the semantic operators.
Seeded via src.dev.seed.seed_from_registry().
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

# Populated by seed_from_registry()
_nodes: dict[str, dict] = {}          # node_id  → node properties dict
_aliases: dict[str, str] = {}         # lower(surface_form) → node_id
_rel_store: list[dict] = []           # minimal edge list (not used in dev)


# ── Public seed API (called from seed.py) ────────────────────────────────────

def seed_nodes(nodes: dict[str, dict]) -> None:
    _nodes.update(nodes)
    logger.info("fake_neo4j: seeded %d OntologyNode records", len(nodes))


def seed_aliases(aliases: dict[str, str]) -> None:
    _aliases.update(aliases)
    logger.info("fake_neo4j: seeded %d alias entries", len(aliases))


# ── Query dispatcher ──────────────────────────────────────────────────────────

def run_query(cypher: str, **params: Any) -> list[dict[str, Any]]:
    """
    Handle the Cypher patterns used by semantic operators.
    Unrecognised patterns return an empty list (safe degradation).
    """
    c = cypher.strip()

    # Pattern 1 — exact match by canonical_name
    # MATCH (n:OntologyNode) WHERE toLower(n.canonical_name) = $term [...] RETURN n LIMIT 1
    if "canonical_name) = $term" in c:
        term  = (params.get("term") or "").lower()
        scope = params.get("scope") or ""
        for node in _nodes.values():
            if node.get("canonical_name", "").lower() == term:
                if not scope or node.get("domain", "").startswith(scope):
                    return [{"n": dict(node)}]
        return []

    # Pattern 2 — alias match via alias_map
    # MATCH (a:Alias)-[:ALIAS_OF]->(n:OntologyNode) WHERE toLower(a.surface_form) = $term
    if "surface_form) = $term" in c:
        term  = (params.get("term") or "").lower()
        scope = params.get("scope") or ""
        nid   = _aliases.get(term)
        if nid:
            node = _nodes.get(nid)
            if node and (not scope or node.get("domain", "").startswith(scope)):
                return [{"n": dict(node), "alias_type": "synonym"}]
        return []

    # Pattern 3a — node by id, return full node
    # MATCH (n:OntologyNode {node_id: $id}) RETURN n LIMIT 1
    if "node_id: $id" in c and "canonical_name" not in c:
        nid  = params.get("id") or params.get("node_id") or ""
        node = _nodes.get(nid)
        return [{"n": dict(node)}] if node else []

    # Pattern 3b — node by id, return canonical_name only
    # MATCH (n:OntologyNode {node_id: $id}) RETURN n.canonical_name AS name LIMIT 1
    if "node_id: $id" in c and "canonical_name" in c:
        nid  = params.get("id") or params.get("node_id") or ""
        node = _nodes.get(nid)
        return [{"name": node.get("canonical_name", nid)}] if node else []

    # Pattern 4 — expand: neighbours via RELATED_TO  (minimal: return empty)
    # MATCH (n {node_id: $node_id})-[r:RELATED_TO*1..N]-(m) ...
    if "RELATED_TO" in c:
        return []

    # Pattern 5 — path queries (return empty for dev)
    if "shortestPath" in c or "allShortestPaths" in c:
        return []

    logger.debug("fake_neo4j: unhandled Cypher pattern, returning []: %.120s", c)
    return []


def run_write(cypher: str, **params: Any) -> list[dict[str, Any]]:
    """No-op for dev — we don't persist Neo4j writes."""
    return []


def ping() -> bool:
    return True


def close_driver() -> None:
    pass


@contextmanager
def get_session():
    yield _FakeSession()


class _FakeSession:
    def run(self, cypher, **params):
        rows = run_query(cypher, **params)
        return _FakeResult(rows)

    def execute_write(self, fn):
        return fn(_FakeTx())

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class _FakeTx:
    def run(self, cypher, **params):
        run_write(cypher, **params)
        return _FakeResult([])


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)