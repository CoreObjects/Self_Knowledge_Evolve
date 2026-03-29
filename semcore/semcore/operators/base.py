"""Semantic operator ABC and registry with middleware support."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from semcore.app import SemanticApp

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class OperatorResult:
    data:              Any
    latency_ms:        int               = 0
    ontology_version:  str               = ""
    errors:            list[str]         = field(default_factory=list)
    meta:              dict[str, Any]    = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Operator ABC
# ---------------------------------------------------------------------------

class SemanticOperator(ABC):
    """Base class for all semantic operators.

    A semantic operator is a named, stateless function that reads from the
    knowledge stores (via *app*) and returns a structured result.  Operators
    must not mutate persistent state; writes belong in pipeline stages.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique operator identifier used for registration and routing."""

    @abstractmethod
    def execute(self, app: "SemanticApp", **kwargs: Any) -> OperatorResult:
        """Run the operator and return a result.

        Args:
            app: The SemanticApp instance providing all provider handles.
            **kwargs: Operator-specific parameters (validated by the HTTP
                      layer before being passed here).
        """


# ---------------------------------------------------------------------------
# Middleware ABC
# ---------------------------------------------------------------------------

class OperatorMiddleware(ABC):
    """Interceptor applied around every operator execution (onion model).

    Registration order: first-registered = outermost layer.
    Execution order:
        mw1.before → mw2.before → operator.execute → mw2.after → mw1.after
    """

    def before(
        self,
        op_name: str,
        app: "SemanticApp",
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Pre-process kwargs before the operator runs.  Return (possibly
        modified) kwargs.  Default: transparent pass-through."""
        return kwargs

    def after(
        self,
        op_name: str,
        result: OperatorResult,
    ) -> OperatorResult:
        """Post-process the result after the operator returns.  Default:
        transparent pass-through."""
        return result

    def on_error(
        self,
        op_name: str,
        exc: Exception,
    ) -> OperatorResult | None:
        """Handle an exception raised by the operator.

        Return an OperatorResult to swallow the error and substitute a
        response; return None to re-raise the exception.  Default: re-raise.
        """
        return None


# ---------------------------------------------------------------------------
# Built-in middleware
# ---------------------------------------------------------------------------

class TimingMiddleware(OperatorMiddleware):
    """Automatically fills OperatorResult.latency_ms."""

    # We store start time in a simple per-call dict keyed by object id to
    # remain thread-safe without threading.local overhead for single-thread use.
    # For production multi-threaded use, replace with contextvars.

    def before(self, op_name: str, app: "SemanticApp", kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs["__t0__"] = time.monotonic()
        return kwargs

    def after(self, op_name: str, result: OperatorResult) -> OperatorResult:
        t0 = result.meta.pop("__t0__", None)
        if t0 is not None:
            result.latency_ms = int((time.monotonic() - t0) * 1000)
        return result


class LoggingMiddleware(OperatorMiddleware):
    """Logs operator name, latency, and any errors."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger or log

    def after(self, op_name: str, result: OperatorResult) -> OperatorResult:
        self._log.info(
            "operator=%s latency_ms=%d errors=%d",
            op_name, result.latency_ms, len(result.errors),
        )
        return result

    def on_error(self, op_name: str, exc: Exception) -> OperatorResult | None:
        self._log.error("operator=%s raised %s: %s", op_name, type(exc).__name__, exc)
        return None   # re-raise


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class OperatorRegistry:
    """Registry of SemanticOperators with chainable middleware.

    Usage::

        registry = OperatorRegistry()
        registry.use(TimingMiddleware()).use(LoggingMiddleware())
        registry.register(LookupOperator())
        result = registry.execute("lookup", app, term="BGP")
    """

    def __init__(self) -> None:
        self._ops:         dict[str, SemanticOperator]  = {}
        self._middlewares: list[OperatorMiddleware]      = []

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, op: SemanticOperator) -> "OperatorRegistry":
        if op.name in self._ops:
            raise ValueError(f"Operator '{op.name}' is already registered.")
        self._ops[op.name] = op
        return self

    def use(self, middleware: OperatorMiddleware) -> "OperatorRegistry":
        """Append a middleware layer.  First added = outermost."""
        self._middlewares.append(middleware)
        return self

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, name: str) -> SemanticOperator:
        try:
            return self._ops[name]
        except KeyError:
            raise KeyError(f"No operator registered under '{name}'.") from None

    def list_names(self) -> list[str]:
        return sorted(self._ops)

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        name: str,
        app: "SemanticApp",
        **kwargs: Any,
    ) -> OperatorResult:
        """Run *name* operator through all middleware layers."""
        op = self.get(name)

        # before hooks (outermost → innermost)
        current_kwargs = dict(kwargs)
        for mw in self._middlewares:
            current_kwargs = mw.before(name, app, current_kwargs)

        # strip internal timing key from kwargs before passing to operator
        _t0 = current_kwargs.pop("__t0__", None)

        # execute
        try:
            result = op.execute(app, **current_kwargs)
        except Exception as exc:
            for mw in reversed(self._middlewares):
                substitute = mw.on_error(name, exc)
                if substitute is not None:
                    return substitute
            raise

        # re-attach timing key so TimingMiddleware.after can read it
        if _t0 is not None:
            result.meta["__t0__"] = _t0

        # after hooks (innermost → outermost)
        for mw in reversed(self._middlewares):
            result = mw.after(name, result)

        return result