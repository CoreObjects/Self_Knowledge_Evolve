"""semantic_expand operator — ontology node neighbourhood traversal."""

from __future__ import annotations

from semcore.providers.base import GraphStore

import logging

log = logging.getLogger(__name__)


def expand(
    node_id: str,
    relation_types: list[str] | None = None,
    depth: int = 1,
    min_confidence: float = 0.5,
    include_facts: bool = True,
    include_segments: bool = False,
    *,
    graph: GraphStore,
) -> dict:
    log.debug("expand node=%s depth=%d rel_types=%s", node_id, depth, relation_types)
    depth = min(max(depth, 1), 3)

    # Validate node exists
    center_rows = graph.read(
        "MATCH (n:OntologyNode {node_id: $id}) RETURN n LIMIT 1", id=node_id
    )
    if not center_rows:
        return {"error": f"Node '{node_id}' not found", "center": None, "neighbors": []}

    center = dict(center_rows[0]["n"])

    # Build neighbour query
    rel_filter = ""
    if relation_types:
        rel_types_str = "|".join(relation_types)
        rel_filter = f":{rel_types_str}"

    # Simplified single-hop query that works without APOC
    neighbors_cypher = f"""
    MATCH (center:OntologyNode {{node_id: $node_id}})
    MATCH (center)-[r]-(neighbor:OntologyNode)
    WHERE neighbor.node_id <> $node_id
      AND coalesce(r.confidence, 1.0) >= $min_confidence
    RETURN DISTINCT
        neighbor.node_id        AS node_id,
        neighbor.canonical_name AS canonical_name,
        type(r)                 AS relation,
        CASE WHEN startNode(r).node_id = $node_id THEN 'outbound' ELSE 'inbound' END AS direction,
        coalesce(r.confidence, 1.0) AS confidence
    LIMIT 50
    """
    neighbor_rows = graph.read(
        neighbors_cypher, node_id=node_id, min_confidence=min_confidence
    )
    neighbors = [dict(r) for r in neighbor_rows]

    result: dict = {"center": center, "neighbors": neighbors}

    if include_facts:
        facts_cypher = """
        MATCH (f:Fact)
        WHERE (f.subject = $node_id OR f.object = $node_id)
          AND f.confidence >= $min_confidence
          AND f.lifecycle_state = 'active'
        RETURN f.fact_id AS fact_id, f.subject AS subject,
               f.predicate AS predicate, f.object AS object,
               f.confidence AS confidence
        LIMIT 30
        """
        result["facts"] = [dict(r) for r in graph.read(
            facts_cypher, node_id=node_id, min_confidence=min_confidence
        )]

    if include_segments:
        seg_cypher = """
        MATCH (s:KnowledgeSegment)-[:TAGGED_WITH]->(n:OntologyNode {node_id: $node_id})
        RETURN s.segment_id AS segment_id, s.segment_type AS segment_type,
               s.section_title AS section_title, s.confidence AS confidence
        LIMIT 20
        """
        result["segments"] = [dict(r) for r in graph.read(seg_cypher, node_id=node_id)]

    log.info("expand node=%s: %d neighbours, facts=%s, segments=%s",
             node_id, len(neighbors),
             len(result.get("facts", [])) if include_facts else "n/a",
             len(result.get("segments", [])) if include_segments else "n/a")
    return result