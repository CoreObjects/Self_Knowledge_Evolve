"""TelecomConfidenceScorer — ConfidenceScorer backed by src/utils/confidence.py."""

from __future__ import annotations

from typing import Any

from semcore.core.types import ConfidenceScore, Fact
from semcore.governance.base import ConfidenceScorer
from src.utils import confidence as _conf

import logging

log = logging.getLogger(__name__)


class TelecomConfidenceScorer(ConfidenceScorer):
    def score(self, fact: Fact, context: dict[str, Any]) -> ConfidenceScore:
        log.debug("scoring fact=%s rank=%s method=%s",
                  fact.fact_id[:12] if fact.fact_id else "?",
                  context.get("source_rank", "C"), context.get("extraction_method", "rule"))
        source_rank        = context.get("source_rank", "C")
        extraction_method  = context.get("extraction_method", "rule")
        ontology_fit       = float(context.get("ontology_fit", 0.8))
        cross_consistency  = float(context.get("cross_source_consistency", 0.5))
        temporal_validity  = float(context.get("temporal_validity", 1.0))

        sa = _conf.SOURCE_AUTHORITY.get(source_rank, 0.40)
        em = _conf.EXTRACTION_METHOD.get(extraction_method, 0.70)

        return ConfidenceScore(
            source_authority         = sa,
            extraction_method        = em,
            ontology_fit             = ontology_fit,
            cross_source_consistency = cross_consistency,
            temporal_validity        = temporal_validity,
        )