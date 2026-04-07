"""Reasoning chain assembly + knowledge_brief + experience_recall."""

from __future__ import annotations

from .index import KnowledgeIndex
from .models import ConceptNode


LAYER_ORDER = ["concept", "mechanism", "method", "condition", "scenario"]


class Reasoner:
    """Build five-layer reasoning chains and knowledge briefs."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index

    def reasoning_chain(self, node_id: str, max_hops: int = 2) -> dict:
        """Build a five-layer reasoning chain starting from a concept node.

        Traverses relations to find connected nodes in each layer:
        concept → mechanism → method → condition → scenario
        """
        idx = self._index
        seed = idx.get_node(node_id)
        if not seed:
            return {"seed": node_id, "layers": {}}

        layers: dict[str, list[dict]] = {layer: [] for layer in LAYER_ORDER}

        # BFS from seed node, collecting nodes by layer
        visited = {node_id}
        frontier = [node_id]

        for _hop in range(max_hops):
            next_frontier = []
            for current_id in frontier:
                for neighbor_id, rel_type, direction in idx.get_neighbors(current_id):
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    neighbor = idx.get_node(neighbor_id)
                    if not neighbor:
                        continue
                    layer = neighbor.layer
                    if layer in layers:
                        layers[layer].append({
                            "node_id": neighbor.node_id,
                            "name": neighbor.name,
                            "description": neighbor.description,
                            "relation": rel_type,
                            "from": current_id,
                        })
                    next_frontier.append(neighbor_id)
            frontier = next_frontier

        # Remove empty layers
        layers = {k: v for k, v in layers.items() if v}

        return {"seed": node_id, "seed_name": seed.name, "layers": layers}

    def knowledge_brief(self, query: str, annotator=None) -> dict:
        """Build a comprehensive knowledge brief for a query.

        If annotator is provided, auto-detect concepts from query text.
        Otherwise, try to resolve query as a single concept.
        """
        idx = self._index

        # Find relevant concepts
        concept_ids = []
        if annotator:
            tags = annotator.annotate(query)
            concept_ids = [t.node_id for t in tags]

        if not concept_ids:
            # Try direct lookup
            node_id = idx.lookup_alias(query)
            if node_id:
                concept_ids = [node_id]

        if not concept_ids:
            return {"query": query, "concepts": [], "error": "No matching concepts found"}

        # Aggregate knowledge from all matched concepts
        all_concepts = []
        all_methods = []
        all_conditions = []
        all_scenarios = []
        all_risks = []
        all_evidence = []

        for cid in concept_ids[:5]:  # limit to 5 seed concepts
            node = idx.get_node(cid)
            if not node:
                continue

            all_concepts.append({
                "node_id": node.node_id,
                "name": node.name,
                "layer": node.layer,
                "description": node.description,
            })

            # Build reasoning chain
            chain = self.reasoning_chain(cid)
            layers = chain.get("layers", {})

            all_methods.extend(layers.get("method", []))
            all_conditions.extend(layers.get("condition", []))
            all_scenarios.extend(layers.get("scenario", []))

            # Conditions can indicate risks
            for cond in layers.get("condition", []):
                if any(kw in cond.get("description", "").lower()
                       for kw in ["risk", "constraint", "limit", "fail", "error"]):
                    all_risks.append(cond)

            # Gather evidence
            for ev in idx.get_evidence(cid):
                all_evidence.append({
                    "text": ev.text,
                    "source": ev.source,
                    "authority": ev.authority,
                })

        return {
            "query": query,
            "concepts": all_concepts,
            "methods": all_methods,
            "conditions": all_conditions,
            "scenarios": all_scenarios,
            "risks": all_risks,
            "evidence": all_evidence[:10],
        }

    def experience_recall(self, query: str, annotator=None) -> dict:
        """Recall relevant experience: best practices, lessons, evidence.

        Focuses on method + condition + scenario layers.
        """
        brief = self.knowledge_brief(query, annotator)
        return {
            "query": query,
            "best_practices": brief.get("methods", []),
            "lessons": brief.get("risks", []),
            "evidence": brief.get("evidence", []),
        }
