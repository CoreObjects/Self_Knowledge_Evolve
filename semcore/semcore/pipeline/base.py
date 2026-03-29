"""Pipeline framework: Stage ABC, conditional routing nodes, and Pipeline."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from semcore.core.context import PipelineContext

if TYPE_CHECKING:
    from semcore.app import SemanticApp

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage ABC
# ---------------------------------------------------------------------------

class Stage(ABC):
    """A single, stateless pipeline step.

    Design contract
    ---------------
    - ``process`` receives the full context and the app handle, and must
      return a (possibly modified) context.
    - Stages must NOT mutate the app or any shared state outside the context.
    - A Stage may write to ``ctx.stage_outputs[self.name]`` for typed private
      output; it should document the expected output type as a class attribute
      ``output_type``.
    - Raising an exception aborts the pipeline.  Non-fatal problems should be
      recorded via ``ctx.record_error()`` instead.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage identifier (used for logging and ``run_from``)."""

    @abstractmethod
    def process(
        self, ctx: PipelineContext, app: "SemanticApp"
    ) -> PipelineContext:
        """Execute this stage and return the updated context."""

    def can_skip(self, ctx: PipelineContext) -> bool:
        """Return True if this stage should be skipped for the given context.

        Default: never skip.
        """
        return False

    # ── Typed output helpers (optional, for domain stages) ───────────────────

    def set_output(self, ctx: PipelineContext, value: Any) -> None:
        ctx.stage_outputs[self.name] = value

    def get_output(self, ctx: PipelineContext) -> Any | None:
        return ctx.stage_outputs.get(self.name)


# ---------------------------------------------------------------------------
# Routing node types
# ---------------------------------------------------------------------------

@dataclass
class LinearNode:
    """Wraps a single Stage for linear execution."""
    stage: Stage

    @property
    def name(self) -> str:
        return self.stage.name


@dataclass
class BranchNode:
    """Binary conditional: routes context to one of two stages."""
    condition: Callable[[PipelineContext, "SemanticApp"], bool]
    if_true:   Stage
    if_false:  Stage

    @property
    def name(self) -> str:
        return f"branch:{self.if_true.name}|{self.if_false.name}"


@dataclass
class SwitchNode:
    """Multi-way conditional: routes context to one of N stages by key."""
    key:      Callable[[PipelineContext, "SemanticApp"], str]
    branches: dict[str, Stage]
    default:  Stage
    _key_repr: str = field(default="", init=False)

    def __post_init__(self) -> None:
        keys = "|".join(sorted(self.branches))
        self._key_repr = keys

    @property
    def name(self) -> str:
        return f"switch:{self._key_repr}"


# Union of all node types
PipelineNode = LinearNode | BranchNode | SwitchNode


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """An ordered sequence of pipeline nodes (stages and routing constructs).

    Construction (fluent API)::

        pipeline = (
            Pipeline()
            .add_stage(IngestStage())
            .branch(
                condition=lambda ctx, app: ctx.doc.doc_type == "rfc",
                if_true=RFCSegmentStage(),
                if_false=DefaultSegmentStage(),
            )
            .switch(
                key=lambda ctx, app: ctx.doc.doc_type,
                branches={"cli": CLIAlignStage(), "rfc": RFCAlignStage()},
                default=DefaultAlignStage(),
            )
            .add_stage(ExtractStage())
        )

    Execution::

        ctx = pipeline.run(source_doc_id, app)
        # Resume from a specific stage (e.g. for debugging):
        ctx = pipeline.run_from("extract", existing_ctx, app)
    """

    def __init__(self) -> None:
        self._nodes: list[PipelineNode] = []

    # ── Fluent construction ───────────────────────────────────────────────────

    def add_stage(self, stage: Stage) -> "Pipeline":
        self._nodes.append(LinearNode(stage=stage))
        return self

    def branch(
        self,
        *,
        condition: Callable[[PipelineContext, "SemanticApp"], bool],
        if_true: Stage,
        if_false: Stage,
    ) -> "Pipeline":
        self._nodes.append(BranchNode(condition=condition, if_true=if_true, if_false=if_false))
        return self

    def switch(
        self,
        *,
        key: Callable[[PipelineContext, "SemanticApp"], str],
        branches: dict[str, Stage],
        default: Stage,
    ) -> "Pipeline":
        self._nodes.append(SwitchNode(key=key, branches=branches, default=default))
        return self

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(self, source_doc_id: str, app: "SemanticApp") -> PipelineContext:
        """Run the full pipeline for *source_doc_id*."""
        ctx = PipelineContext(source_doc_id=source_doc_id)
        return self._execute_nodes(self._nodes, ctx, app)

    def run_context(self, ctx: PipelineContext, app: "SemanticApp") -> PipelineContext:
        """Run the full pipeline using a pre-built context."""
        return self._execute_nodes(self._nodes, ctx, app)

    def run_from(
        self,
        stage_name: str,
        ctx: PipelineContext,
        app: "SemanticApp",
    ) -> PipelineContext:
        """Resume execution from the node whose name equals *stage_name*.

        Useful for re-running a single stage during debugging without
        re-ingesting the document.
        """
        # Locate the start index
        start = next(
            (i for i, n in enumerate(self._nodes) if n.name == stage_name),
            None,
        )
        if start is None:
            raise ValueError(
                f"No pipeline node named '{stage_name}'. "
                f"Available: {[n.name for n in self._nodes]}"
            )
        return self._execute_nodes(self._nodes[start:], ctx, app)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _execute_nodes(
        self,
        nodes: list[PipelineNode],
        ctx: PipelineContext,
        app: "SemanticApp",
    ) -> PipelineContext:
        for node in nodes:
            ctx = self._execute_node(node, ctx, app)
        return ctx

    def _execute_node(
        self,
        node: PipelineNode,
        ctx: PipelineContext,
        app: "SemanticApp",
    ) -> PipelineContext:
        if isinstance(node, LinearNode):
            return self._run_stage(node.stage, ctx, app)

        if isinstance(node, BranchNode):
            chosen = node.if_true if node.condition(ctx, app) else node.if_false
            return self._run_stage(chosen, ctx, app)

        if isinstance(node, SwitchNode):
            key_value = node.key(ctx, app)
            chosen = node.branches.get(key_value, node.default)
            return self._run_stage(chosen, ctx, app)

        raise TypeError(f"Unknown pipeline node type: {type(node)}")  # pragma: no cover

    def _run_stage(
        self,
        stage: Stage,
        ctx: PipelineContext,
        app: "SemanticApp",
    ) -> PipelineContext:
        if stage.can_skip(ctx):
            log.debug("pipeline stage='%s' skipped", stage.name)
            return ctx
        log.debug("pipeline stage='%s' starting", stage.name)
        ctx = stage.process(ctx, app)
        log.debug("pipeline stage='%s' done  errors=%d", stage.name, len(ctx.errors))
        return ctx

    # ── Introspection ─────────────────────────────────────────────────────────

    def stage_names(self) -> list[str]:
        """Return the names of all top-level pipeline nodes."""
        return [n.name for n in self._nodes]
