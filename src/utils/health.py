"""Startup health checks for external dependencies."""

from __future__ import annotations

import logging

from src.db import health_check as db_health_check
from src.utils.llm_extract import LLMExtractor

log = logging.getLogger(__name__)


def startup_health_check() -> bool:
    """Check DB and LLM connectivity.

    Returns True if all *required* services (postgres, neo4j) are healthy.
    LLM is treated as optional — a failure is logged as warning, not error.
    """
    db_status = db_health_check()
    llm_ok = LLMExtractor().ping()

    core_ok = all(db_status.values())  # postgres + neo4j are required

    if core_ok and llm_ok:
        log.info(
            "Startup health check ok: postgres=%s neo4j=%s llm=%s",
            db_status.get("postgres"),
            db_status.get("neo4j"),
            llm_ok,
        )
    elif core_ok and not llm_ok:
        log.warning(
            "Startup health check: core services ok, LLM unavailable (degraded). "
            "postgres=%s neo4j=%s llm=%s",
            db_status.get("postgres"),
            db_status.get("neo4j"),
            llm_ok,
        )
    else:
        log.error(
            "Startup health check failed: postgres=%s neo4j=%s llm=%s",
            db_status.get("postgres"),
            db_status.get("neo4j"),
            llm_ok,
        )

    return core_ok
