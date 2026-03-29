"""Governance ABCs — confidence scoring, conflict detection, evolution gating."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from semcore.core.types import ConfidenceScore, EvolutionCandidate, Fact

if TYPE_CHECKING:
    from semcore.providers.base import RelationalStore


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class ConfidenceScorer(ABC):
    """Compute a multi-dimensional confidence score for an extracted Fact."""

    @abstractmethod
    def score(self, fact: Fact, context: dict[str, Any]) -> ConfidenceScore:
        """Return a ConfidenceScore for *fact*.

        Args:
            fact: The fact whose confidence is being evaluated.
            context: Arbitrary extraction context (source_rank, method, …).
        """


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

@dataclass
class Conflict:
    fact_id_a:     str
    fact_id_b:     str
    conflict_type: str    # e.g. "contradictory_object", "duplicate"
    description:   str    = ""
    attributes:    dict[str, Any] = field(default_factory=dict)


class ConflictDetector(ABC):
    """Detect logical or factual conflicts between a new fact and the store."""

    @abstractmethod
    def detect(
        self, fact: Fact, store: "RelationalStore"
    ) -> list[Conflict]:
        """Return zero or more conflicts found for *fact* given existing data."""


# ---------------------------------------------------------------------------
# Ontology evolution gate
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    passed:      bool
    gate_scores: dict[str, float]   # gate_name → score (0.0–1.0)
    reason:      str                = ""
    attributes:  dict[str, Any]     = field(default_factory=dict)

    def failed_gates(self) -> list[str]:
        """Return names of gates that did not pass."""
        from semcore.governance.base import EvolutionGate  # local import to avoid cycles
        # Callers can use gate_scores directly; this is a convenience helper.
        return [k for k, v in self.gate_scores.items() if v < 0.5]


class EvolutionGate(ABC):
    """Multi-criteria gate that decides whether a candidate can enter the ontology.

    Subclasses declare the gate names in ``GATES`` and implement the scoring
    logic in ``evaluate``.
    """

    #: Ordered list of gate names this implementation enforces.
    GATES: list[str] = []

    @abstractmethod
    def evaluate(
        self,
        candidate: EvolutionCandidate,
        store: "RelationalStore",
    ) -> GateResult:
        """Run all gates against *candidate* and return an aggregate result.

        Convention: a GateResult is considered *passed* only when ALL individual
        gate scores are >= the implementation's configured threshold.
        """