"""Drilldown — pure routing layer mapping metric names to operator calls.

No SQL or Cypher here. All data access goes through app.query().
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# metric_name → (operator_name, default_params)
METRIC_TO_QUERY: dict[str, tuple[str, dict]] = {
    # ── Knowledge quality ─────────────────────────────────────────
    "isolated_nodes":         ("graph_inspect",      {"inspect_type": "isolated_nodes"}),
    "low_confidence_facts":   ("filter",             {"object_type": "fact", "filters": {"max_confidence": 0.5}, "sort_by": "confidence", "sort_order": "asc"}),
    "single_evidence_weak":   ("stale_knowledge",    {"type": "weak_evidence"}),

    # ── Sources ───────────────────────────────────────────────────
    "docs_by_rank":           ("filter",             {"object_type": "documents", "sort_by": "source_rank"}),
    "docs_by_site":           ("filter",             {"object_type": "documents", "sort_by": "site_key"}),

    # ── Evolution ─────────────────────────────────────────────────
    "pending_candidates":     ("candidate_discover", {"window_days": 365, "min_frequency": 1, "min_source_count": 1}),

    # ── Pipeline ──────────────────────────────────────────────────
    "backlog_docs":           ("filter",             {"object_type": "documents", "filters": {"status": "raw"}}),
    "failed_docs":            ("filter",             {"object_type": "documents", "filters": {"status": "failed"}}),

    # ── Graph health ──────────────────────────────────────────────
    "super_nodes":            ("graph_inspect",      {"inspect_type": "super_nodes", "threshold": 50}),
    "unused_predicates":      ("graph_inspect",      {"inspect_type": "unused_predicates"}),
    "predicate_concentration":("graph_inspect",      {"inspect_type": "predicate_concentration"}),
    "degree_distribution":    ("graph_inspect",      {"inspect_type": "degree_distribution"}),
    "cross_layer_gaps":       ("cross_layer_check",  {"gaps": True}),
    "stale_facts":            ("stale_knowledge",    {"type": "fact", "days": 90}),
    "stale_docs":             ("stale_knowledge",    {"type": "doc", "days": 90}),

    # ── Ontology health ───────────────────────────────────────────
    "no_alias_nodes":         ("ontology_inspect",   {"inspect_type": "no_alias"}),
    "single_child_nodes":     ("ontology_inspect",   {"inspect_type": "single_child"}),
    "alias_conflicts":        ("ontology_inspect",   {"inspect_type": "alias_conflicts"}),
    "inheritance_stats":      ("ontology_inspect",   {"inspect_type": "inheritance_stats"}),
    "relation_candidates":    ("ontology_inspect",   {"inspect_type": "relation_candidates"}),

    # ── Ontology quality (full report) ────────────────────────────
    "ontology_quality":       ("ontology_quality",   {}),
}


def drilldown(metric_name: str, app, **override_params) -> dict:
    """Route a metric name to the appropriate operator call.

    Args:
        metric_name: Key from METRIC_TO_QUERY.
        app: SemanticApp instance.
        **override_params: Override default params (e.g. threshold, days, limit).

    Returns:
        Operator result data dict.
    """
    entry = METRIC_TO_QUERY.get(metric_name)
    if entry is None:
        return {
            "error": f"Unknown metric '{metric_name}'",
            "available_metrics": sorted(METRIC_TO_QUERY.keys()),
        }

    op_name, default_params = entry
    params = {**default_params, **override_params}
    log.debug("drilldown %s → %s(%s)", metric_name, op_name, params)

    result = app.query(op_name, **params)
    return result.data