"""Domain view loader — JSON/YAML/platform API."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .index import KnowledgeIndex
from .models import ConceptNode, Relation, Evidence

log = logging.getLogger(__name__)


def load_from_json(path: str | Path) -> KnowledgeIndex:
    """Load a domain view from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _build_index(data)


def load_from_dict(data: dict) -> KnowledgeIndex:
    """Load a domain view from a Python dict."""
    return _build_index(data)


def load_from_platform(
    base_url: str,
    keywords: list[str],
    max_nodes: int = 200,
) -> KnowledgeIndex:
    """Load a domain view from the big platform's API.

    Calls context_assemble for each keyword, then merges results.
    Requires `requests` library.
    """
    try:
        import requests
    except ImportError:
        raise ImportError("pip install requests — required for platform loading")

    nodes = {}
    relations = []
    evidence = []

    for kw in keywords:
        # First lookup the term
        resp = requests.get(f"{base_url}/api/v1/semantic/lookup", params={"term": kw}, timeout=10)
        if resp.status_code != 200:
            continue
        result = resp.json().get("result", {})
        matched = result.get("matched_node") or result.get("node") or {}
        node_id = matched.get("node_id")
        if not node_id:
            continue

        # Then get context assembly
        ctx_resp = requests.post(
            f"{base_url}/api/v1/semantic/context_assemble",
            json={"node_ids": [node_id], "max_segments": 3, "max_hops": 2},
            timeout=30,
        )
        if ctx_resp.status_code != 200:
            continue
        ctx = ctx_resp.json().get("result", {})

        # Collect seed node
        nodes[node_id] = {
            "node_id": node_id,
            "name": matched.get("canonical_name", kw),
            "layer": matched.get("knowledge_layer") or "concept",
            "description": matched.get("description", ""),
            "aliases": [a if isinstance(a, str) else a.get("surface_form", "")
                       for a in (result.get("aliases") or [])],
            "parent_id": matched.get("parent_id"),
        }

        # Collect reasoning chain nodes
        for chain_item in ctx.get("reasoning_chain", []):
            for layer_name, layer_nodes in (chain_item.get("layers") or {}).items():
                for n in layer_nodes:
                    nid = n.get("node_id", "")
                    if nid and nid not in nodes:
                        nodes[nid] = {
                            "node_id": nid,
                            "name": n.get("name", nid),
                            "layer": layer_name,
                            "description": n.get("description", ""),
                            "aliases": [],
                        }
                    if nid:
                        relations.append({
                            "source": n.get("from", node_id),
                            "type": n.get("relation", "related_to"),
                            "target": nid,
                            "confidence": 0.85,
                        })

        # Collect facts as relations
        for fact in ctx.get("facts", []):
            relations.append({
                "source": fact.get("subject", ""),
                "type": fact.get("predicate", ""),
                "target": fact.get("object", ""),
                "confidence": fact.get("confidence", 0.5),
            })

        # Collect evidence
        for seg in ctx.get("segments", []):
            evidence.append({
                "node_id": node_id,
                "text": (seg.get("raw_text") or "")[:500],
                "source": seg.get("section_title") or "",
                "authority": "B",
            })

        if len(nodes) >= max_nodes:
            break

    log.info("Loaded from platform: %d nodes, %d relations, %d evidence",
             len(nodes), len(relations), len(evidence))

    return _build_index({
        "nodes": list(nodes.values()),
        "relations": relations,
        "evidence": evidence,
    })


def _build_index(data: dict) -> KnowledgeIndex:
    """Build KnowledgeIndex from a domain view dict."""
    idx = KnowledgeIndex()

    for n in data.get("nodes", []):
        node = ConceptNode(
            node_id=n["node_id"],
            name=n.get("name", n["node_id"]),
            layer=n.get("layer", "concept"),
            description=n.get("description", ""),
            aliases=n.get("aliases", []),
            parent_id=n.get("parent_id"),
            properties=n.get("properties", {}),
        )
        idx.add_node(node)

    for r in data.get("relations", []):
        rel = Relation(
            source=r.get("source", ""),
            relation_type=r.get("type", "related_to"),
            target=r.get("target", ""),
            confidence=r.get("confidence", 1.0),
            evidence=r.get("evidence"),
        )
        if rel.source and rel.target:
            idx.add_relation(rel)

    for e in data.get("evidence", []):
        ev = Evidence(
            node_id=e.get("node_id", ""),
            text=e.get("text", ""),
            source=e.get("source", ""),
            authority=e.get("authority", "C"),
        )
        if ev.node_id and ev.text:
            idx.add_evidence(ev)

    log.info("Index built: %d nodes, %d aliases", len(idx.nodes), len(idx.alias_map))
    return idx