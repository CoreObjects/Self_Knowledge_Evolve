"""SemanticContextKit — the main entry point."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .annotator import Annotator
from .checker import RiskChecker
from .index import KnowledgeIndex
from .loader import load_from_dict, load_from_json, load_from_platform
from .models import AnnotationTag, LearnedItem
from .reasoner import Reasoner

log = logging.getLogger(__name__)


class SemanticContextKit:
    """Project-level semantic knowledge organizer for Agent integration.

    Usage:
        # Load from a domain view file
        kit = SemanticContextKit.from_file("domain_view.json")

        # Or load from the big platform
        kit = SemanticContextKit.from_platform("http://localhost:8000",
                                                keywords=["BGP", "OSPF"])

        # Annotate text
        tags = kit.annotate("Configure OSPF area for backbone")

        # Get knowledge brief (for Agent Reasoner)
        brief = kit.knowledge_brief("dual-exit campus network design")

        # Check risks (for Agent Observer)
        risks = kit.risk_check(["BGP", "OSPF", "VRRP"], scenario="dual-exit")

        # Learn from project (accumulate)
        kit.learn("Chose OSPF multi-area due to 500+ devices",
                  concepts=["IP.OSPF"], item_type="decision")
    """

    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index
        self._annotator = Annotator(index)
        self._reasoner = Reasoner(index)
        self._checker = RiskChecker(index)
        self._learned: list[LearnedItem] = []
        self._project_id: str = ""

    # ── Factory methods ──────────────────────────────────────────

    @classmethod
    def from_file(cls, path: str | Path) -> "SemanticContextKit":
        """Load from a JSON domain view file."""
        index = load_from_json(path)
        kit = cls(index)
        log.info("Kit loaded from %s: %d nodes", path, len(index.nodes))
        return kit

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticContextKit":
        """Load from a Python dict."""
        index = load_from_dict(data)
        return cls(index)

    @classmethod
    def from_platform(
        cls,
        base_url: str,
        keywords: list[str],
        max_nodes: int = 200,
    ) -> "SemanticContextKit":
        """Load a domain view from the big platform's API."""
        index = load_from_platform(base_url, keywords, max_nodes)
        kit = cls(index)
        log.info("Kit loaded from platform: %d nodes", len(index.nodes))
        return kit

    # ── Core capabilities ────────────────────────────────────────

    def annotate(self, text: str) -> list[AnnotationTag]:
        """Tag text with domain concepts."""
        return self._annotator.annotate(text)

    def lookup(self, term: str) -> dict:
        """Look up a concept by name or alias."""
        node_id = self._index.lookup_alias(term)
        if not node_id:
            return {"error": f"'{term}' not found"}
        node = self._index.get_node(node_id)
        if not node:
            return {"error": f"Node '{node_id}' not in index"}
        return {
            "node": {
                "node_id": node.node_id,
                "name": node.name,
                "layer": node.layer,
                "description": node.description,
                "aliases": node.aliases,
                "parent_id": node.parent_id,
            },
            "relations": [
                {"source": r.source, "type": r.relation_type, "target": r.target,
                 "confidence": r.confidence}
                for r in self._index.get_relations(node_id)
            ],
            "evidence": [
                {"text": e.text, "source": e.source, "authority": e.authority}
                for e in self._index.get_evidence(node_id)
            ],
        }

    def reasoning_chain(self, node_id_or_name: str) -> dict:
        """Build five-layer reasoning chain from a concept."""
        node_id = self._index.lookup_alias(node_id_or_name) or node_id_or_name
        return self._reasoner.reasoning_chain(node_id)

    # ── Agent APIs ───────────────────────────────────────────────

    def knowledge_brief(self, query: str) -> dict:
        """API 1: "What do I need to know about this topic?"

        For Agent Reasoner — returns structured domain context to inject
        into the system prompt.
        """
        return self._reasoner.knowledge_brief(query, self._annotator)

    def risk_check(self, selected: list[str], scenario: str = "") -> dict:
        """API 2: "What's wrong with this plan?"

        For Agent Observer — returns conflicts, risks, missing items,
        dependency gaps.
        """
        return self._checker.risk_check(selected, scenario)

    def experience_recall(self, query: str) -> dict:
        """API 3: "How was this done before?"

        For Agent Planner — returns best practices and lessons learned.
        """
        return self._reasoner.experience_recall(query, self._annotator)

    # ── Learning (project knowledge accumulation) ────────────────

    def learn(
        self,
        text: str,
        concepts: list[str] | None = None,
        item_type: str = "observation",
        **metadata,
    ) -> None:
        """Accumulate project knowledge."""
        if concepts is None:
            # Auto-detect concepts
            tags = self.annotate(text)
            concepts = [t.node_id for t in tags]
        self._learned.append(LearnedItem(
            text=text, concepts=concepts, item_type=item_type, metadata=metadata,
        ))
        log.debug("Learned: [%s] %s (concepts=%s)", item_type, text[:60], concepts)

    def learn_term(self, term: str, parent: str = "", description: str = "") -> None:
        """Record a new term discovered during the project."""
        self.learn(
            text=f"New term: {term}",
            concepts=[parent] if parent else [],
            item_type="term",
            term=term, parent_concept=parent, description=description,
        )

    # ── Export ───────────────────────────────────────────────────

    def export_learned(self) -> dict:
        """Export accumulated project knowledge for backfeed to the big platform."""
        return {
            "project_id": self._project_id,
            "exported_at": datetime.now().isoformat(),
            "learned_items": [
                {
                    "text": item.text,
                    "concepts": item.concepts,
                    "item_type": item.item_type,
                    "metadata": item.metadata,
                    "timestamp": item.timestamp,
                }
                for item in self._learned
            ],
            "stats": {
                "total_items": len(self._learned),
                "decisions": sum(1 for i in self._learned if i.item_type == "decision"),
                "terms": sum(1 for i in self._learned if i.item_type == "term"),
                "observations": sum(1 for i in self._learned if i.item_type == "observation"),
                "lessons": sum(1 for i in self._learned if i.item_type == "lesson"),
            },
        }

    def save_learned(self, path: str | Path) -> None:
        """Save learned items to a JSON file."""
        Path(path).write_text(
            json.dumps(self.export_learned(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info("Saved %d learned items to %s", len(self._learned), path)

    # ── Info ─────────────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self._index.nodes)

    @property
    def relation_count(self) -> int:
        return sum(len(v) for v in self._index.relations.values()) // 2

    def summary(self) -> str:
        """One-line summary of the kit's state."""
        layers = {}
        for nid, node in self._index.nodes.items():
            layers[node.layer] = layers.get(node.layer, 0) + 1
        return (
            f"SemanticContextKit: {self.node_count} nodes, "
            f"{self.relation_count} relations, "
            f"{len(self._learned)} learned items, "
            f"layers={layers}"
        )