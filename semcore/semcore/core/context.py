"""PipelineContext — the typed data packet that flows between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semcore.core.types import (
    Document, Evidence, Fact, RSTRelation, Segment, Tag,
)


@dataclass
class PipelineContext:
    """Carries all in-flight knowledge artefacts through a pipeline run.

    Layout
    ------
    - Core typed fields (segments, facts, …): known to the framework; populated
      by the built-in stages.
    - stage_outputs: typed per-stage private payloads.  Each Stage owns its
      own key (= Stage.name) and provides typed get/set helpers on the Stage
      class itself.  The framework never reads these values.
    - meta: unstructured overflow for anything that doesn't fit above.
    - errors: non-fatal error messages recorded during the run (a fatal error
      should raise; non-fatal should append here and let the run continue).
    """

    source_doc_id: str

    # ── Core knowledge artefacts ──────────────────────────────────────────────
    doc:           Document | None      = None
    segments:      list[Segment]        = field(default_factory=list)
    tags:          list[Tag]            = field(default_factory=list)
    facts:         list[Fact]           = field(default_factory=list)
    evidence:      list[Evidence]       = field(default_factory=list)
    rst_relations: list[RSTRelation]    = field(default_factory=list)

    # ── Stage-private typed outputs ───────────────────────────────────────────
    # Key = Stage.name; value = domain-defined dataclass instance.
    # Use Stage.set_output / Stage.get_output helpers for type-safe access.
    stage_outputs: dict[str, Any]       = field(default_factory=dict)

    # ── Unstructured overflow ─────────────────────────────────────────────────
    meta:   dict[str, Any]              = field(default_factory=dict)
    errors: list[str]                   = field(default_factory=list)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def record_error(self, msg: str) -> None:
        self.errors.append(msg)

    def has_errors(self) -> bool:
        return bool(self.errors)