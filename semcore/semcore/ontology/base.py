"""OntologyProvider ABC — runtime access to the ontology graph."""

from __future__ import annotations

from abc import ABC, abstractmethod

from semcore.core.types import KnowledgeLayer, OntologyNode, RelationDef


class OntologyProvider(ABC):
    """Read-only runtime view of the ontology.

    Implementations load from YAML, a database, or any other source.
    The framework only ever reads through this interface, so the backing
    store is fully transparent.
    """

    @abstractmethod
    def get_node(self, node_id: str) -> OntologyNode | None:
        """Return the node with the given ID, or None if not found."""

    @abstractmethod
    def get_layer_nodes(self, layer: KnowledgeLayer) -> list[OntologyNode]:
        """Return all nodes belonging to a knowledge layer."""

    @abstractmethod
    def get_all_nodes(self) -> list[OntologyNode]:
        """Return every node in the ontology."""

    @abstractmethod
    def get_relations(self) -> list[RelationDef]:
        """Return all relation definitions."""

    @abstractmethod
    def resolve_alias(
        self,
        surface_form: str,
        *,
        lang: str = "en",
        domain: str | None = None,
    ) -> OntologyNode | None:
        """Find the canonical node for a surface alias string.

        Args:
            surface_form: Raw text mention (e.g. "OSPF", "开放最短路径优先").
            lang: ISO 639-1 language code hint.
            domain: Optional domain filter (e.g. "ip_network").

        Returns:
            The canonical OntologyNode, or None if unresolved.
        """

    @abstractmethod
    def version(self) -> str:
        """Return the ontology version string (e.g. "v0.2.0")."""