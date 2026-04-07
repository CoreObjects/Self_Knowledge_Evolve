"""In-memory indexes for fast annotation and retrieval."""

from __future__ import annotations

import re
from collections import defaultdict

from .models import ConceptNode, Relation, Evidence


class KnowledgeIndex:
    """Memory-efficient indexes over a domain view."""

    def __init__(self) -> None:
        self.nodes: dict[str, ConceptNode] = {}
        self.alias_map: dict[str, str] = {}          # lowercase alias → node_id
        self.layer_index: dict[str, list[str]] = defaultdict(list)  # layer → [node_id]
        self.parent_index: dict[str, str] = {}        # child_id → parent_id
        self.child_index: dict[str, list[str]] = defaultdict(list)  # parent_id → [child_id]
        self.relations: dict[str, list[Relation]] = defaultdict(list)  # node_id → [Relation]
        self.evidence: dict[str, list[Evidence]] = defaultdict(list)   # node_id → [Evidence]

        # Pre-compiled regex patterns for short aliases (word-boundary matching)
        self._short_patterns: dict[str, re.Pattern] = {}

    def add_node(self, node: ConceptNode) -> None:
        self.nodes[node.node_id] = node
        self.layer_index[node.layer].append(node.node_id)
        if node.parent_id:
            self.parent_index[node.node_id] = node.parent_id
            self.child_index[node.parent_id].append(node.node_id)
        # Index aliases
        for alias in [node.name] + node.aliases:
            key = alias.lower()
            self.alias_map[key] = node.node_id
            if len(key) <= 3:
                self._short_patterns[key] = re.compile(
                    r"\b" + re.escape(key) + r"\b", re.IGNORECASE
                )

    def add_relation(self, rel: Relation) -> None:
        self.relations[rel.source].append(rel)
        self.relations[rel.target].append(rel)

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence[ev.node_id].append(ev)

    def lookup_alias(self, text: str) -> str | None:
        """Resolve a text string to a node_id via alias match."""
        return self.alias_map.get(text.lower())

    def get_node(self, node_id: str) -> ConceptNode | None:
        return self.nodes.get(node_id)

    def get_layer_nodes(self, layer: str) -> list[ConceptNode]:
        return [self.nodes[nid] for nid in self.layer_index.get(layer, [])
                if nid in self.nodes]

    def get_children(self, node_id: str) -> list[ConceptNode]:
        return [self.nodes[cid] for cid in self.child_index.get(node_id, [])
                if cid in self.nodes]

    def get_relations(self, node_id: str) -> list[Relation]:
        return self.relations.get(node_id, [])

    def get_evidence(self, node_id: str) -> list[Evidence]:
        return self.evidence.get(node_id, [])

    def get_neighbors(self, node_id: str) -> list[tuple[str, str, str]]:
        """Return [(neighbor_id, relation_type, direction)] for a node."""
        results = []
        for rel in self.get_relations(node_id):
            if rel.source == node_id:
                results.append((rel.target, rel.relation_type, "out"))
            else:
                results.append((rel.source, rel.relation_type, "in"))
        return results
