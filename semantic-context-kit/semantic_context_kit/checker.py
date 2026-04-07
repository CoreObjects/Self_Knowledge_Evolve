"""Risk checker — conflicts, missing dependencies, constraint violations."""

from __future__ import annotations

from .index import KnowledgeIndex


class RiskChecker:
    """Check a proposed plan for conflicts, risks, and gaps."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index

    def risk_check(
        self,
        selected: list[str],
        scenario: str = "",
    ) -> dict:
        """Check a set of selected concepts/technologies for issues.

        Args:
            selected: List of concept names or node_ids.
            scenario: Optional scenario description for context.

        Returns:
            {conflicts, risks, missing, dependency_gaps}
        """
        idx = self._index

        # Resolve names to node_ids
        node_ids = []
        for item in selected:
            nid = idx.lookup_alias(item) or item
            if nid in idx.nodes:
                node_ids.append(nid)

        conflicts = []
        risks = []
        missing = []
        dependency_gaps = []

        # Check pairwise conflicts: if two selected nodes have conflicting relations
        for i, nid_a in enumerate(node_ids):
            rels_a = idx.get_relations(nid_a)
            for nid_b in node_ids[i + 1:]:
                # Check if they have a "conflicts_with" or similar relation
                for rel in rels_a:
                    partner = rel.target if rel.source == nid_a else rel.source
                    if partner == nid_b and rel.relation_type in (
                        "conflicts_with", "incompatible_with", "replaces",
                    ):
                        node_a = idx.get_node(nid_a)
                        node_b = idx.get_node(nid_b)
                        conflicts.append({
                            "a": node_a.name if node_a else nid_a,
                            "b": node_b.name if node_b else nid_b,
                            "relation": rel.relation_type,
                            "detail": rel.evidence or "",
                        })

        # Check dependencies: each selected node's depends_on targets should also be selected
        all_selected = set(node_ids)
        for nid in node_ids:
            for rel in idx.get_relations(nid):
                if rel.source == nid and rel.relation_type in (
                    "depends_on", "requires", "uses_protocol",
                ):
                    if rel.target not in all_selected:
                        dep_node = idx.get_node(rel.target)
                        dep_name = dep_node.name if dep_node else rel.target
                        node = idx.get_node(nid)
                        dependency_gaps.append({
                            "node": node.name if node else nid,
                            "missing_dependency": dep_name,
                            "relation": rel.relation_type,
                        })

        # Check conditions: gather condition-layer nodes connected to selected concepts
        for nid in node_ids:
            for neighbor_id, rel_type, direction in idx.get_neighbors(nid):
                neighbor = idx.get_node(neighbor_id)
                if not neighbor:
                    continue
                if neighbor.layer == "condition":
                    risks.append({
                        "condition": neighbor.name,
                        "description": neighbor.description,
                        "related_to": idx.get_node(nid).name if idx.get_node(nid) else nid,
                    })

        # Check for common missing items based on scenario keywords
        if scenario:
            scenario_lower = scenario.lower()
            # Simple heuristic: check if BFD is selected when HA keywords present
            ha_keywords = ["redundancy", "failover", "high availability", "dual", "backup"]
            if any(kw in scenario_lower for kw in ha_keywords):
                bfd_id = idx.lookup_alias("bfd")
                if bfd_id and bfd_id not in all_selected:
                    missing.append({
                        "suggestion": "BFD",
                        "reason": "高可用场景建议配置 BFD 快速故障检测",
                    })

        return {
            "selected": [idx.get_node(nid).name if idx.get_node(nid) else nid
                        for nid in node_ids],
            "conflicts": conflicts,
            "risks": risks,
            "missing": missing,
            "dependency_gaps": dependency_gaps,
        }
