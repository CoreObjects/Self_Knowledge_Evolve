"""TelecomConflictDetector — ConflictDetector extracted from stage5_dedup logic."""

from __future__ import annotations

from semcore.core.types import Fact
from semcore.governance.base import Conflict, ConflictDetector
from semcore.providers.base import RelationalStore

import logging

log = logging.getLogger(__name__)


class TelecomConflictDetector(ConflictDetector):
    def detect(self, fact: Fact, store: RelationalStore) -> list[Conflict]:
        """Find existing facts with same subject+predicate but different object."""
        log.debug("conflict_detect: %s %s %s", fact.subject, fact.predicate, fact.object)
        rows = store.fetchall(
            """
            SELECT fact_id FROM facts
            WHERE subject = %s AND predicate = %s AND object != %s
              AND lifecycle_state = 'active'
            """,
            (fact.subject, fact.predicate, fact.object),
        )
        conflicts = [
            Conflict(
                fact_id_a=fact.fact_id,
                fact_id_b=row["fact_id"],
                conflict_type="contradictory_value",
                description=(
                    f"{fact.subject} {fact.predicate} has conflicting objects"
                ),
            )
            for row in rows
        ]
        if conflicts:
            log.info("conflict_detect: %s %s → %d conflicts", fact.subject, fact.predicate, len(conflicts))
        return conflicts