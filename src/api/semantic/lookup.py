"""semantic_lookup operator — term → ontology node + evidence."""

from __future__ import annotations

from semcore.providers.base import GraphStore, RelationalStore
from src.utils.text import normalize_text


def lookup(
    term: str,
    scope: str | None = None,
    lang: str = "en",
    ontology_version: str | None = None,
    include_evidence: bool = False,
    max_evidence: int = 3,
    *,
    store: RelationalStore,
    graph: GraphStore,
) -> dict:
    """Resolve a term to its ontology node(s)."""
    term_lower = normalize_text(term)

    # 1. Exact match on canonical_name
    node, match_type = _exact_match(term_lower, scope, graph)

    # 2. Alias match in Neo4j
    if not node:
        node, match_type = _alias_match(term_lower, scope, graph)

    # 3. Alias match in PostgreSQL lexicon_aliases
    if not node:
        node, match_type = _pg_alias_match(term_lower, scope, store, graph)

    if not node:
        return {"matched_node": None, "match_type": "not_found", "input_surface_form": term}

    evidence = []
    if include_evidence:
        evidence = _fetch_evidence(node["node_id"], max_evidence, store)

    return {
        "matched_node":      node,
        "match_type":        match_type,
        "input_surface_form": term,
        "aliases":           node.get("aliases", []),
        "allowed_relations": node.get("allowed_relations", []),
        "evidence":          evidence,
    }


def _exact_match(term_lower: str, scope: str | None, graph: GraphStore) -> tuple[dict | None, str]:
    cypher = """
    MATCH (n:OntologyNode)
    WHERE toLower(n.canonical_name) = $term
    """
    if scope:
        cypher += " AND n.domain STARTS WITH $scope"
    cypher += " RETURN n LIMIT 1"
    params = {"term": term_lower, "scope": scope or ""}
    rows = graph.read(cypher, **params)
    if rows:
        return _node_to_dict(rows[0]["n"]), "exact"
    return None, ""


def _alias_match(term_lower: str, scope: str | None, graph: GraphStore) -> tuple[dict | None, str]:
    cypher = """
    MATCH (a:Alias)-[:ALIAS_OF]->(n:OntologyNode)
    WHERE toLower(a.surface_form) = $term
    """
    if scope:
        cypher += " AND n.domain STARTS WITH $scope"
    cypher += " RETURN n, a.alias_type AS alias_type LIMIT 1"
    rows = graph.read(cypher, term=term_lower, scope=scope or "")
    if rows:
        return _node_to_dict(rows[0]["n"]), "alias"
    return None, ""


def _pg_alias_match(
    term_lower: str, scope: str | None, store: RelationalStore, graph: GraphStore
) -> tuple[dict | None, str]:
    rows = store.fetchall(
        "SELECT canonical_node_id, alias_type FROM lexicon_aliases WHERE lower(surface_form)=%s LIMIT 1",
        (term_lower,),
    )
    if not rows:
        return None, ""
    node_id = rows[0]["canonical_node_id"]
    node_rows = graph.read(
        "MATCH (n:OntologyNode {node_id: $id}) RETURN n LIMIT 1", id=node_id
    )
    if node_rows:
        return _node_to_dict(node_rows[0]["n"]), "alias"
    return None, ""


def _fetch_evidence(node_id: str, limit: int, store: RelationalStore) -> list[dict]:
    return store.fetchall(
        """
        SELECT e.evidence_id, e.exact_span, d.canonical_url as source_url,
               d.source_rank, e.evidence_score
        FROM evidence e
        JOIN documents d ON e.source_doc_id = d.source_doc_id
        JOIN segment_tags st ON e.segment_id = st.segment_id
        WHERE st.ontology_node_id = %s AND st.tag_type = 'canonical'
        ORDER BY e.evidence_score DESC
        LIMIT %s
        """,
        (node_id, limit),
    )


def _node_to_dict(n) -> dict:
    if hasattr(n, "items"):
        return dict(n)
    return n