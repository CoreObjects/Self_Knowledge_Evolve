"""Scheduler — periodically runs StatsCollector and writes snapshots to PG."""

from __future__ import annotations

import json
import logging
import threading
import time

log = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 300  # 5 minutes


class StatsScheduler:
    """Background thread that collects stats on a fixed interval."""

    def __init__(self, collector, store, interval: int = _DEFAULT_INTERVAL):
        self._collector = collector
        self._store = store
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="stats-scheduler", daemon=True,
        )
        self._thread.start()
        log.info("StatsScheduler started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        log.info("StatsScheduler stopped")

    def collect_now(self) -> dict:
        """Run collection immediately and return the snapshot."""
        return self._collect_and_store()

    def _run_loop(self) -> None:
        # Initial collection after a short delay
        self._stop_event.wait(10)
        while not self._stop_event.is_set():
            try:
                self._collect_and_store()
            except Exception as exc:
                log.error("Stats collection failed: %s", exc, exc_info=True)
            self._stop_event.wait(self._interval)

    def _collect_and_store(self) -> dict:
        snapshot = self._collector.collect_all()
        try:
            self._store.execute(
                "INSERT INTO system_stats_snapshots (snapshot) VALUES (%s::jsonb)",
                (json.dumps(snapshot, default=str),),
            )
            # Cleanup: keep only last 7 days
            self._store.execute(
                "DELETE FROM system_stats_snapshots WHERE created_at < NOW() - INTERVAL '7 days'"
            )
            log.debug("Stats snapshot saved")
        except Exception as exc:
            log.warning("Failed to save stats snapshot: %s", exc)
        return snapshot