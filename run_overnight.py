"""
Overnight runner: clean start → load ontology → crawler + pipeline in parallel threads.

Usage:
    python run_overnight.py

On completion or interrupt, prints final stats + list of failed document IDs
for re-processing.
"""

from __future__ import annotations

import json
import sys
import logging
import threading
import time
import traceback
from pathlib import Path

# semcore path
_semcore_path = str(Path(__file__).parent / "semcore")
if _semcore_path not in sys.path:
    sys.path.insert(0, _semcore_path)

from src.config.settings import settings
from src.utils.logging import setup_logging

setup_logging(settings.LOG_LEVEL)
log = logging.getLogger("run_overnight")

# ── Config ────────────────────────────────────────────────────────────────
RUN_HOURS = 6
RUN_SECONDS = RUN_HOURS * 3600
CRAWLER_SLEEP = 30
PIPELINE_SLEEP = 15
PIPELINE_BATCH = 5

_stop_event = threading.Event()
_failed_docs: list[dict] = []       # {"source_doc_id": ..., "error": ..., "stage": ...}
_failed_lock = threading.Lock()


def record_failure(source_doc_id: str, error: str, stage: str = "unknown") -> None:
    with _failed_lock:
        _failed_docs.append({
            "source_doc_id": source_doc_id,
            "error": error[:500],
            "stage": stage,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })


# ── Phase 0: Clean start ─────────────────────────────────────────────────

def clean_all_stores() -> None:
    """Truncate all PG tables, clear Neo4j and MinIO."""
    import psycopg2
    from minio import Minio
    from neo4j import GraphDatabase

    log.info("Cleaning all stores...")

    # PG telecom_kb
    conn = psycopg2.connect(dsn=settings.postgres_dsn)
    conn.autocommit = True
    cur = conn.cursor()
    for t in [
        'governance.conflict_records', 'governance.review_records',
        'governance.evolution_candidates', 'evidence', 'facts',
        'segment_tags', 't_rst_relation', 'segments', 'documents', 'lexicon_aliases',
    ]:
        try:
            cur.execute(f'TRUNCATE TABLE {t} CASCADE')
        except Exception as e:
            log.warning("  truncate %s: %s", t, e)
    conn.close()
    log.info("  PG telecom_kb: truncated")

    # PG telecom_crawler
    conn = psycopg2.connect(dsn=settings.crawler_postgres_dsn)
    conn.autocommit = True
    cur = conn.cursor()
    for t in ['extraction_jobs', 'crawl_tasks', 'source_registry']:
        try:
            cur.execute(f'TRUNCATE TABLE {t} CASCADE')
        except Exception as e:
            log.warning("  truncate %s: %s", t, e)
    conn.close()
    log.info("  PG telecom_crawler: truncated")

    # Neo4j
    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        summary = session.run('MATCH (n) DETACH DELETE n').consume()
        log.info("  Neo4j: deleted %d nodes, %d rels",
                 summary.counters.nodes_deleted, summary.counters.relationships_deleted)
    driver.close()

    # MinIO
    client = Minio(settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE)
    deleted = 0
    for bucket in [settings.MINIO_BUCKET_RAW, settings.MINIO_BUCKET_CLEANED]:
        try:
            for obj in client.list_objects(bucket, recursive=True):
                client.remove_object(bucket, obj.object_name)
                deleted += 1
        except Exception:
            pass
    log.info("  MinIO: deleted %d objects", deleted)


def load_ontology() -> None:
    """Load YAML ontology into Neo4j + PG lexicon."""
    log.info("Loading ontology...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/load_ontology.py"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent),
    )
    if result.returncode != 0:
        log.error("load_ontology.py failed:\n%s\n%s", result.stdout, result.stderr)
        raise RuntimeError("Ontology load failed")
    log.info("Ontology loaded:\n%s", result.stdout[-500:] if result.stdout else "(no output)")


def drop_cross_db_fks() -> None:
    """Drop any remaining cross-DB FK constraints on documents table."""
    import psycopg2
    conn = psycopg2.connect(dsn=settings.postgres_dsn)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name='documents' AND constraint_type='FOREIGN KEY'
    """)
    for (fk_name,) in cur.fetchall():
        if 'crawl_task' in fk_name or 'site_key' in fk_name:
            cur.execute(f'ALTER TABLE documents DROP CONSTRAINT IF EXISTS {fk_name}')
            log.info("  Dropped FK: %s", fk_name)
    conn.close()


# ── Seed sources ──────────────────────────────────────────────────────────

SEED_SOURCES = [
    {
        "site_key": "ietf-datatracker",
        "site_name": "IETF Datatracker",
        "home_url": "https://datatracker.ietf.org/",
        "source_rank": "S",
        "rate_limit_rps": 0.5,
        "seed_urls": [
            "https://datatracker.ietf.org/doc/html/rfc4271",   # BGP-4
            "https://datatracker.ietf.org/doc/html/rfc4456",   # BGP Route Reflection
            "https://datatracker.ietf.org/doc/html/rfc2328",   # OSPF v2
            "https://datatracker.ietf.org/doc/html/rfc5340",   # OSPF v3
            "https://datatracker.ietf.org/doc/html/rfc3031",   # MPLS Architecture
            "https://datatracker.ietf.org/doc/html/rfc4364",   # BGP/MPLS IP VPN
            "https://datatracker.ietf.org/doc/html/rfc7432",   # BGP MPLS EVPN
            "https://datatracker.ietf.org/doc/html/rfc7348",   # VXLAN
            "https://datatracker.ietf.org/doc/html/rfc5880",   # BFD
            "https://datatracker.ietf.org/doc/html/rfc793",    # TCP
            "https://datatracker.ietf.org/doc/html/rfc791",    # IPv4
            "https://datatracker.ietf.org/doc/html/rfc8200",   # IPv6
            "https://datatracker.ietf.org/doc/html/rfc4760",   # MP-BGP
            "https://datatracker.ietf.org/doc/html/rfc5308",   # IS-IS for IPv4/IPv6
            "https://datatracker.ietf.org/doc/html/rfc3032",   # MPLS Label Stack
            "https://datatracker.ietf.org/doc/html/rfc8402",   # Segment Routing
            "https://datatracker.ietf.org/doc/html/rfc8986",   # SRv6
            "https://datatracker.ietf.org/doc/html/rfc2474",   # DiffServ / QoS
            "https://datatracker.ietf.org/doc/html/rfc2697",   # srTCM
            "https://datatracker.ietf.org/doc/html/rfc4303",   # IPsec ESP
        ],
    },
]


# ── Crawler thread ────────────────────────────────────────────────────────

def crawler_thread(app) -> None:
    from src.crawler.spider import Spider

    crawler_store = app.crawler_store or app.store
    knowledge_store = app.store

    def _jsonb(v):
        return json.dumps(v, ensure_ascii=True) if v is not None else None

    # Seed
    for src in SEED_SOURCES:
        try:
            crawler_store.execute(
                """INSERT INTO source_registry (
                    site_key, site_name, home_url, source_rank, crawl_enabled,
                    rate_limit_rps, seed_urls, scope_rules, extra_headers, updated_at
                ) VALUES (%s,%s,%s,%s,true,%s,%s,%s,%s,NOW())
                ON CONFLICT (site_key) DO UPDATE SET crawl_enabled=true, updated_at=NOW()""",
                (src["site_key"], src["site_name"], src["home_url"], src["source_rank"],
                 src["rate_limit_rps"], _jsonb(src.get("seed_urls")),
                 _jsonb(src.get("scope_rules")), _jsonb(src.get("extra_headers"))),
            )
            for url in src["seed_urls"]:
                crawler_store.execute(
                    """INSERT INTO crawl_tasks (site_key, url, task_type, priority, status, scheduled_at)
                    VALUES (%s,%s,'full',10,'pending',NOW())
                    ON CONFLICT (url) DO NOTHING""",
                    (src["site_key"], url),
                )
        except Exception as exc:
            log.error("[CRAWLER] seed error: %s", exc)

    log.info("[CRAWLER] seeded %d URLs", sum(len(s["seed_urls"]) for s in SEED_SOURCES))

    spider = Spider(object_store=app.objects, store=crawler_store, knowledge_store=knowledge_store)

    while not _stop_event.is_set():
        try:
            results = spider.run_pending_tasks(limit=5)
            if results:
                done = sum(1 for r in results if r.get("status") == "done")
                log.info("[CRAWLER] cycle: %d done, %d total", done, len(results))
        except Exception as exc:
            log.error("[CRAWLER] cycle error: %s", exc)
        _stop_event.wait(CRAWLER_SLEEP)

    spider.close()
    log.info("[CRAWLER] stopped")


# ── Pipeline thread ───────────────────────────────────────────────────────

def pipeline_thread(app) -> None:
    from semcore.core.context import PipelineContext

    store = app.store

    while not _stop_event.is_set():
        try:
            rows = store.fetchall(
                "SELECT source_doc_id FROM documents WHERE status='raw' ORDER BY created_at ASC LIMIT %s",
                (PIPELINE_BATCH,),
            )
            if not rows:
                _stop_event.wait(PIPELINE_SLEEP)
                continue

            for row in rows:
                if _stop_event.is_set():
                    break
                doc_id = str(row["source_doc_id"])
                log.info("[PIPELINE] start doc=%s", doc_id)
                t0 = time.monotonic()
                try:
                    ctx = PipelineContext(source_doc_id=doc_id)
                    ctx = app.ingest_context(ctx)
                    elapsed = time.monotonic() - t0
                    if ctx.has_errors():
                        log.warning("[PIPELINE] doc=%s done in %.1fs with %d errors",
                                    doc_id, elapsed, len(ctx.errors))
                        for err in ctx.errors[:3]:
                            log.warning("[PIPELINE]   %s", err)
                    else:
                        log.info("[PIPELINE] doc=%s done in %.1fs", doc_id, elapsed)
                except Exception as exc:
                    elapsed = time.monotonic() - t0
                    error_msg = str(exc)
                    log.error("[PIPELINE] doc=%s FAILED after %.1fs: %s",
                              doc_id, elapsed, error_msg)
                    record_failure(doc_id, error_msg, stage="pipeline")
                    # Mark failed so we skip it next cycle
                    try:
                        store.execute(
                            "UPDATE documents SET status='failed' WHERE source_doc_id=%s AND status='raw'",
                            (doc_id,),
                        )
                    except Exception:
                        pass

        except Exception as exc:
            log.error("[PIPELINE] poll error: %s", exc)
            _stop_event.wait(PIPELINE_SLEEP)

    log.info("[PIPELINE] stopped")


# ── Main ──────────────────────────────────────────────────────────────────

def print_stats(app) -> None:
    store = app.store
    crawler_store = app.crawler_store or store

    def cnt(sql, s=store):
        try:
            r = s.fetchone(sql)
            return r["cnt"] if r else 0
        except Exception:
            return "?"

    log.info("=" * 60)
    log.info("FINAL STATS")
    log.info("=" * 60)
    log.info("  Crawl tasks done:     %s", cnt("SELECT count(*) as cnt FROM crawl_tasks WHERE status='done'", crawler_store))
    log.info("  Documents total:      %s", cnt("SELECT count(*) as cnt FROM documents"))
    log.info("  Documents indexed:    %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='indexed'"))
    log.info("  Documents failed:     %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='failed'"))
    log.info("  Segments:             %s", cnt("SELECT count(*) as cnt FROM segments"))
    log.info("  Segment tags:         %s", cnt("SELECT count(*) as cnt FROM segment_tags"))
    log.info("  RST relations:        %s", cnt("SELECT count(*) as cnt FROM t_rst_relation"))
    log.info("  Facts:                %s", cnt("SELECT count(*) as cnt FROM facts"))
    log.info("  Evidence:             %s", cnt("SELECT count(*) as cnt FROM evidence"))
    log.info("  Candidates:           %s", cnt("SELECT count(*) as cnt FROM governance.evolution_candidates"))
    log.info("  Conflicts:            %s", cnt("SELECT count(*) as cnt FROM governance.conflict_records"))

    if _failed_docs:
        log.info("")
        log.info("FAILED DOCUMENTS (%d):", len(_failed_docs))
        log.info("-" * 60)
        for f in _failed_docs:
            log.info("  doc=%s  stage=%s  time=%s", f["source_doc_id"], f["stage"], f["timestamp"])
            log.info("    error: %s", f["error"][:200])

        # Write to file for re-run
        fail_path = Path(__file__).parent / "failed_docs.json"
        with open(fail_path, "w", encoding="utf-8") as fp:
            json.dump(_failed_docs, fp, indent=2, ensure_ascii=False)
        log.info("")
        log.info("Failed doc IDs saved to: %s", fail_path)
        log.info("Re-run: UPDATE documents SET status='raw' WHERE source_doc_id IN (...)")
    else:
        log.info("")
        log.info("No failed documents!")

    log.info("=" * 60)


def main() -> None:
    from src.app_factory import build_app

    log.info("=" * 60)
    log.info("OVERNIGHT RUN: %d hours", RUN_HOURS)
    log.info("=" * 60)

    # Phase 0: clean start
    clean_all_stores()
    drop_cross_db_fks()

    # Phase 1: load ontology
    load_ontology()

    # Phase 2: build app and start threads
    app = build_app()
    log.info("SemanticApp built")

    t_crawler = threading.Thread(target=crawler_thread, args=(app,), name="crawler", daemon=True)
    t_pipeline = threading.Thread(target=pipeline_thread, args=(app,), name="pipeline", daemon=True)

    t_crawler.start()
    t_pipeline.start()
    log.info("Crawler + Pipeline threads started")

    try:
        _stop_event.wait(RUN_SECONDS)
    except KeyboardInterrupt:
        log.info("Interrupted")

    _stop_event.set()
    log.info("Stopping threads...")
    t_crawler.join(timeout=60)
    t_pipeline.join(timeout=300)

    print_stats(app)
    log.info("Done.")


if __name__ == "__main__":
    main()