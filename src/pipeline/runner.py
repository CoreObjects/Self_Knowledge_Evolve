"""Pipeline orchestration — runs all 6 stages in sequence for a document.

NOTE: This is a legacy runner. Prefer using SemanticApp.ingest() which
properly runs stages through the semcore Pipeline with PipelineContext.
This runner is kept for batch operations that need direct task-level control.
"""

from __future__ import annotations

import logging
import time

from src.app_factory import get_app
from src.utils.logging import get_logger

log = get_logger(__name__)


class PipelineRunner:
    def __init__(self) -> None:
        self._app = get_app()

    def run_document(self, crawl_task_id: int) -> dict:
        """Run the full semcore pipeline for one crawl task."""
        from semcore.core.context import PipelineContext
        summary: dict = {"crawl_task_id": crawl_task_id, "stages_completed": [], "stats": {}}
        t0 = time.monotonic()

        ctx = PipelineContext(source_doc_id="")
        ctx.meta["crawl_task_id"] = crawl_task_id

        try:
            ctx = self._app.ingest_context(ctx)
            summary["source_doc_id"] = ctx.source_doc_id
            summary["stages_completed"] = self._app.pipeline_stages()
            if ctx.has_errors():
                summary["errors"] = ctx.errors
        except Exception as exc:
            log.error("Pipeline failed for task %d: %s", crawl_task_id, exc, exc_info=True)
            summary["status"] = "failed"
            summary["error"] = str(exc)
            return summary

        summary["elapsed_s"] = round(time.monotonic() - t0, 2)
        summary["status"] = "done"
        log.info(
            "Pipeline completed for task %d (doc %s) in %.2fs",
            crawl_task_id, summary.get("source_doc_id", "?"), summary["elapsed_s"],
        )
        return summary

    def run_batch(self, limit: int = 10) -> list[dict]:
        """Fetch pending tasks and run pipeline for each."""
        store = self._app.store
        tasks = store.fetchall(
            """
            SELECT ct.id FROM crawl_tasks ct
            WHERE ct.status = 'done'
              AND NOT EXISTS (
                SELECT 1 FROM documents d WHERE d.crawl_task_id = ct.id AND d.status != 'raw'
              )
            ORDER BY ct.priority DESC, ct.id ASC
            LIMIT %s
            """,
            (limit,),
        )
        results = []
        for task in tasks:
            result = self.run_document(task["id"])
            results.append(result)
        return results

    def run_pending(self, limit: int = 50) -> None:
        """Convenience: run batch and log summary."""
        log.info("Starting pipeline batch, limit=%d", limit)
        results = self.run_batch(limit)
        done    = sum(1 for r in results if r.get("status") == "done")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        failed  = sum(1 for r in results if r.get("status") == "failed")
        log.info("Batch complete: %d done, %d skipped, %d failed", done, skipped, failed)