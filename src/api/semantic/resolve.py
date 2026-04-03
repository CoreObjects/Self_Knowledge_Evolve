"""semantic_resolve operator — alias/vendor-term → canonical node."""

from __future__ import annotations

import logging

from semcore.providers.base import GraphStore, RelationalStore
from src.utils.text import normalize_text

log = logging.getLogger(__name__)


def resolve(
    alias: str,
    scope: str | None = None,
    vendor: str | None = None,
    *,
    store: RelationalStore,
    graph: GraphStore,
) -> dict:
    log.debug("resolve alias=%r vendor=%r", alias, vendor)
    alias_lower = normalize_text(alias)

    sql = "SELECT * FROM lexicon_aliases WHERE lower(surface_form) = %s"
    params: list = [alias_lower]
    if vendor:
        sql += " AND lower(vendor) = %s"
        params.append(vendor.lower())
    sql += " ORDER BY confidence DESC"
    rows = store.fetchall(sql, tuple(params))

    if not rows:
        log.info("resolve no match: alias=%r", alias)
        return {"input": alias, "resolved": None, "alternatives": []}

    primary = rows[0]
    alternatives = rows[1:]

    # Enrich with canonical_name from Neo4j
    node_row = graph.read(
        "MATCH (n:OntologyNode {node_id: $id}) RETURN n.canonical_name AS name LIMIT 1",
        id=primary["canonical_node_id"],
    )
    canonical_name = node_row[0]["name"] if node_row else primary["canonical_node_id"]
    log.info("resolve matched: alias=%r → %s (conf=%.2f, alternatives=%d)",
             alias, primary["canonical_node_id"], float(primary["confidence"]), len(alternatives))

    return {
        "input": alias,
        "resolved": {
            "node_id":        primary["canonical_node_id"],
            "canonical_name": canonical_name,
            "confidence":     float(primary["confidence"]),
            "alias_type":     primary["alias_type"],
        },
        "alternatives": [
            {
                "node_id":    r["canonical_node_id"],
                "alias_type": r["alias_type"],
                "vendor":     r.get("vendor"),
                "confidence": float(r["confidence"]),
            }
            for r in alternatives
        ],
    }