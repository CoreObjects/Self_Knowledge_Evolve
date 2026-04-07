"""Text annotator — tag text with domain concepts."""

from __future__ import annotations

import re

from .index import KnowledgeIndex
from .models import AnnotationTag


class Annotator:
    """Match domain concepts in free text."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index

    def annotate(self, text: str) -> list[AnnotationTag]:
        """Find all domain concept mentions in text.

        Returns list of AnnotationTag sorted by confidence (descending).
        Short aliases (<=3 chars) require word-boundary match.
        """
        text_lower = text.lower()
        found: dict[str, AnnotationTag] = {}  # node_id → best tag

        for alias, node_id in self._index.alias_map.items():
            if node_id in found:
                continue  # already matched this node

            if len(alias) <= 3:
                # Short alias: use pre-compiled word-boundary pattern
                pattern = self._index._short_patterns.get(alias)
                if pattern and pattern.search(text):
                    node = self._index.get_node(node_id)
                    name = node.name if node else alias
                    conf = 1.0 if name.lower() == alias else 0.90
                    found[node_id] = AnnotationTag(
                        surface_form=alias, node_id=node_id, confidence=conf,
                    )
            else:
                if alias in text_lower:
                    node = self._index.get_node(node_id)
                    name = node.name if node else alias
                    conf = 1.0 if name.lower() == alias else 0.90
                    found[node_id] = AnnotationTag(
                        surface_form=alias, node_id=node_id, confidence=conf,
                    )

        return sorted(found.values(), key=lambda t: -t.confidence)

    def extract_keywords(self, text: str) -> list[str]:
        """Extract domain-relevant keywords from text (node names that appear)."""
        tags = self.annotate(text)
        return [t.surface_form for t in tags]