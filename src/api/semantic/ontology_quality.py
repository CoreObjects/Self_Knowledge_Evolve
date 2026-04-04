"""ontology_quality operator — compute full quality report."""

from __future__ import annotations

import logging

from semcore.providers.base import GraphStore, RelationalStore

log = logging.getLogger(__name__)


def ontology_quality(
    *,
    store: RelationalStore,
    graph: GraphStore,
) -> dict:
    """Compute all 5 dimensions of ontology quality."""
    log.debug("ontology_quality: computing full report")
    from src.stats.ontology_quality import OntologyQualityCalculator
    calc = OntologyQualityCalculator(store=store, graph=graph)
    return calc.compute_all()