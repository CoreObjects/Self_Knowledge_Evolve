"""Data structures — zero external dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConceptNode:
    """A node in the domain knowledge graph."""
    node_id: str
    name: str
    layer: str = "concept"  # concept|mechanism|method|condition|scenario
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    parent_id: str | None = None
    properties: dict = field(default_factory=dict)


@dataclass
class Relation:
    """A typed relationship between two nodes."""
    source: str
    relation_type: str
    target: str
    confidence: float = 1.0
    evidence: str | None = None


@dataclass
class Evidence:
    """A source-attributed text fragment supporting a node."""
    node_id: str
    text: str
    source: str = ""        # "RFC 2328" | "Huawei Config Guide"
    authority: str = "C"    # S|A|B|C


@dataclass
class LearnedItem:
    """Knowledge accumulated during a project."""
    text: str
    concepts: list[str] = field(default_factory=list)
    item_type: str = "observation"  # decision|term|observation|lesson
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AnnotationTag:
    """A concept tag on a text span."""
    surface_form: str
    node_id: str
    confidence: float = 1.0