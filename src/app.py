"""
FastAPI application entry point.

Run:
    uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.db import health_check
from src.utils.health import startup_health_check
from src.api.semantic.router import router as semantic_router
from src.utils.logging import setup_logging

app = FastAPI(
    title="Telecom Semantic KB API",
    version="0.1.0",
    description="Semantic knowledge base for network & telecom domain.",
    docs_url="/docs",
    redoc_url="/redoc",
)

log = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging(settings.LOG_LEVEL)
    if not startup_health_check():
        log.error("Startup health check failed.")
        if settings.STARTUP_HEALTH_REQUIRED:
            log.error("Shutting down.")
            raise RuntimeError("Startup health check failed.")
        log.warning(
            "Continuing startup with degraded health (STARTUP_HEALTH_REQUIRED=false)."
        )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(semantic_router)


# ── Utility endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health() -> dict:
    status = health_check()
    status["status"] = "ok" if all(status.values()) else "degraded"
    return status


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
