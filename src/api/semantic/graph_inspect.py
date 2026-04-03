"""graph_inspect operator — graph structure health inspection."""

from __future__ import annotations

import logging
from collections import Counter

from semcore.providers.base import GraphStore, RelationalStore

log = logging.getLogger(__name__)


def graph_inspect(
    inspect_type: str,
    threshold: int = 50,
    limit: int = 50,
    *,
    graph: GraphStore,
    store: RelationalStore,
) -> dict:
    log.debug("graph_inspect type=%s threshold=%d", inspect_type, threshold)

    handler = _INSPECT_HANDLERS.get(inspect_type)
    if handler is None:
        return {"error": f"Unknown inspect_type '{inspect_type}'", "valid_types": list(_INSPECT_HANDLERS)}
    return handler(graph=graph, store=store, threshold=threshold, limit=limit)


def _isolated_nodes(*, graph: GraphStore, **_kw) -> dict:
    """Ontology nodes with zero RELATED_TO edges (no knowledge discovered)."""
    rows = graph.read(
        """
        MATCH (n:OntologyNode)
        WHERE n.lifecycle_state = 'active'
        OPTIONAL MATCH (n)-[r:RELATED_TO]-()
        WITH n, count(r) AS rel_count
        WHERE rel_count = 0
        RETURN n.node_id AS node_id, n.canonical_name AS name,
               labels(n) AS labels
        ORDER BY n.node_id
        """
    )
    nodes = [dict(r) for r in rows]
    log.info("isolated_nodes: %d found", len(nodes))
    return {"inspect_type": "isolated_nodes", "count": len(nodes), "nodes": nodes}


def _super_nodes(*, graph: GraphStore, threshold: int, limit: int, **_kw) -> dict:
    """Nodes with degree exceeding threshold — may indicate extraction noise."""
    rows = graph.read(
        """
        MATCH (n:OntologyNode)
        WHERE n.lifecycle_state = 'active'
        OPTIONAL MATCH (n)-[r:RELATED_TO]-()
        WITH n, count(r) AS degree
        WHERE degree > $threshold
        RETURN n.node_id AS node_id, n.canonical_name AS name, degree
        ORDER BY degree DESC
        LIMIT $limit
        """,
        threshold=threshold, limit=limit,
    )
    nodes = []
    for r in rows:
        node = dict(r)
        # Get predicate distribution for this node
        pred_rows = graph.read(
            """
            MATCH (n:OntologyNode {node_id: $nid})-[r:RELATED_TO]-()
            RETURN r.predicate AS predicate, count(r) AS cnt
            ORDER BY cnt DESC LIMIT 5
            """,
            nid=r["node_id"],
        )
        node["top_predicates"] = {pr["predicate"]: pr["cnt"] for pr in pred_rows}
        nodes.append(node)
    log.info("super_nodes (threshold=%d): %d found", threshold, len(nodes))
    return {"inspect_type": "super_nodes", "threshold": threshold, "count": len(nodes), "nodes": nodes}


def _degree_distribution(*, graph: GraphStore, **_kw) -> dict:
    """Global degree statistics across all ontology nodes."""
    rows = graph.read(
        """
        MATCH (n:OntologyNode)
        WHERE n.lifecycle_state = 'active'
        OPTIONAL MATCH (n)-[r:RELATED_TO]-()
        WITH n, count(r) AS degree
        RETURN avg(degree) AS avg_degree,
               percentileCont(degree, 0.5) AS median_degree,
               max(degree) AS max_degree,
               min(degree) AS min_degree,
               stDev(degree) AS stddev_degree,
               count(n) AS node_count
        """
    )
    stats = dict(rows[0]) if rows else {}
    log.info("degree_distribution: avg=%.1f max=%s", stats.get("avg_degree", 0), stats.get("max_degree", 0))
    return {"inspect_type": "degree_distribution", **stats}


def _predicate_concentration(*, graph: GraphStore, limit: int, **_kw) -> dict:
    """Nodes where edges are concentrated on a single predicate type."""
    rows = graph.read(
        """
        MATCH (n:OntologyNode)-[r:RELATED_TO]-()
        WHERE n.lifecycle_state = 'active'
        WITH n, r.predicate AS pred, count(r) AS pred_cnt
        ORDER BY n.node_id, pred_cnt DESC
        WITH n, collect({predicate: pred, count: pred_cnt}) AS preds,
             sum(pred_cnt) AS total
        WHERE total >= 5 AND head(preds).count > total * 0.8
        RETURN n.node_id AS node_id, n.canonical_name AS name,
               total AS total_edges,
               head(preds).predicate AS dominant_predicate,
               head(preds).count AS dominant_count,
               toFloat(head(preds).count) / total AS concentration
        ORDER BY concentration DESC
        LIMIT $limit
        """,
        limit=limit,
    )
    nodes = [dict(r) for r in rows]
    log.info("predicate_concentration: %d nodes with >80%% single-predicate", len(nodes))
    return {"inspect_type": "predicate_concentration", "count": len(nodes), "nodes": nodes}


def _unused_predicates(*, store: RelationalStore, **_kw) -> dict:
    """Relation types defined in ontology but never used in any Fact."""
    from src.ontology.registry import OntologyRegistry
    registry = OntologyRegistry.from_default()
    defined = registry.relation_ids

    used_rows = store.fetchall("SELECT DISTINCT predicate FROM facts")
    used = {r["predicate"] for r in used_rows}

    unused = sorted(defined - used)
    log.info("unused_predicates: %d/%d defined types unused", len(unused), len(defined))
    return {
        "inspect_type": "unused_predicates",
        "defined_count": len(defined),
        "used_count": len(used),
        "unused_count": len(unused),
        "unused": unused,
    }


_INSPECT_HANDLERS = {
    "isolated_nodes": _isolated_nodes,
    "super_nodes": _super_nodes,
    "degree_distribution": _degree_distribution,
    "predicate_concentration": _predicate_concentration,
    "unused_predicates": _unused_predicates,
}