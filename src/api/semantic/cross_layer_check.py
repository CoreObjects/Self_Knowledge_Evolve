"""cross_layer_check operator — five-layer ontology coverage analysis."""

from __future__ import annotations

import logging

from semcore.providers.base import GraphStore

log = logging.getLogger(__name__)

# Neo4j label per knowledge layer
_LAYER_LABELS = {
    "concept":   "OntologyNode",
    "mechanism": "MechanismNode",
    "method":    "MethodNode",
    "condition": "ConditionRuleNode",
    "scenario":  "ScenarioPatternNode",
}

# Expected cross-layer adjacency (source → target)
_LAYER_PAIRS = [
    ("concept", "mechanism"),
    ("mechanism", "method"),
    ("method", "condition"),
    ("condition", "scenario"),
    ("method", "scenario"),
]


def cross_layer_check(
    source_layer: str | None = None,
    target_layer: str | None = None,
    gaps: bool = False,
    limit: int = 50,
    *,
    graph: GraphStore,
) -> dict:
    log.debug("cross_layer_check src=%s tgt=%s gaps=%s", source_layer, target_layer, gaps)

    # If specific pair requested
    if source_layer and target_layer:
        return _check_pair(source_layer, target_layer, gaps, limit, graph)

    # Otherwise check all standard pairs
    results = {}
    all_gaps = []
    for src, tgt in _LAYER_PAIRS:
        pair_result = _check_pair(src, tgt, gaps, limit, graph)
        key = f"{src}_to_{tgt}"
        results[key] = pair_result["coverage"]
        if gaps and pair_result.get("gap_nodes"):
            all_gaps.extend(pair_result["gap_nodes"])

    result = {"coverage": results}
    if gaps:
        result["gap_nodes"] = all_gaps[:limit]
        result["total_gaps"] = len(all_gaps)
    log.info("cross_layer_check: %s", {k: f"{v:.0%}" for k, v in results.items()})
    return result


def _check_pair(
    source_layer: str, target_layer: str,
    include_gaps: bool, limit: int,
    graph: GraphStore,
) -> dict:
    src_label = _LAYER_LABELS.get(source_layer, "OntologyNode")
    tgt_label = _LAYER_LABELS.get(target_layer, "OntologyNode")

    # Count source nodes that have at least one RELATED_TO edge to a target-layer node
    total_rows = graph.read(
        f"MATCH (n:{src_label}) WHERE n.lifecycle_state = 'active' RETURN count(n) AS cnt"
    )
    total = total_rows[0]["cnt"] if total_rows else 0

    connected_rows = graph.read(
        f"""
        MATCH (n:{src_label})-[r_fact WHERE r_fact.predicate IS NOT NULL]-(m:{tgt_label})
        WHERE n.lifecycle_state = 'active'
        RETURN count(DISTINCT n) AS cnt
        """
    )
    connected = connected_rows[0]["cnt"] if connected_rows else 0

    coverage = connected / max(total, 1)

    result = {
        "source_layer": source_layer,
        "target_layer": target_layer,
        "total_nodes": total,
        "connected_nodes": connected,
        "coverage": round(coverage, 4),
    }

    if include_gaps:
        gap_rows = graph.read(
            f"""
            MATCH (n:{src_label})
            WHERE n.lifecycle_state = 'active'
              AND NOT EXISTS {{ MATCH (n)-[r_fact WHERE r_fact.predicate IS NOT NULL]-(:{tgt_label}) }}
            RETURN n.node_id AS node_id, n.canonical_name AS name
            ORDER BY n.node_id
            LIMIT $limit
            """,
            limit=limit,
        )
        result["gap_nodes"] = [
            {"node_id": r["node_id"], "name": r["name"],
             "layer": source_layer, "missing_layer": target_layer}
            for r in gap_rows
        ]

    return result