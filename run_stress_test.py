"""
Stress test: crawl diverse webpage types → full pipeline.

Tests HTML pages, plain text, vendor docs, specs, tutorials, etc.
Runs crawler + pipeline in parallel. Stops after all URLs processed or timeout.
"""

from __future__ import annotations

import json
import sys
import logging
import threading
import time
import traceback
import uuid
import hashlib
from pathlib import Path

_semcore_path = str(Path(__file__).parent / "semcore")
if _semcore_path not in sys.path:
    sys.path.insert(0, _semcore_path)

from src.config.settings import settings
from src.utils.logging import setup_logging

setup_logging(settings.LOG_LEVEL)
log = logging.getLogger("stress_test")

TIMEOUT_HOURS = 3
TIMEOUT_SECONDS = TIMEOUT_HOURS * 3600
PIPELINE_SLEEP = 10
PIPELINE_BATCH = 3

_stop_event = threading.Event()
_failed_docs: list[dict] = []
_failed_lock = threading.Lock()


def record_failure(source_doc_id: str, error: str, stage: str = "unknown") -> None:
    with _failed_lock:
        _failed_docs.append({
            "source_doc_id": source_doc_id,
            "error": error[:500],
            "stage": stage,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })


# ── Diverse URL set: different formats, sizes, languages, structures ──────

SOURCES = [
    # ── IETF specs (HTML rendering of RFCs) ──
    {
        "site_key": "ietf-datatracker",
        "site_name": "IETF Datatracker",
        "source_rank": "S",
        "urls": [
            "https://datatracker.ietf.org/doc/html/rfc8040",   # RESTCONF
            "https://datatracker.ietf.org/doc/html/rfc6241",   # NETCONF
            "https://datatracker.ietf.org/doc/html/rfc7950",   # YANG
            "https://datatracker.ietf.org/doc/html/rfc5765",   # STP MIB
            "https://datatracker.ietf.org/doc/html/rfc2544",   # Benchmarking
            "https://datatracker.ietf.org/doc/html/rfc3768",   # VRRP
            "https://datatracker.ietf.org/doc/html/rfc7938",   # BGP in Large-Scale DC
            "https://datatracker.ietf.org/doc/html/rfc5798",   # VRRPv3
            "https://datatracker.ietf.org/doc/html/rfc2131",   # DHCP
            "https://datatracker.ietf.org/doc/html/rfc1034",   # DNS Concepts
            "https://datatracker.ietf.org/doc/html/rfc4456",   # BGP Route Reflection (if not already)
        ],
    },
    # ── Huawei Info Center (vendor docs, mixed CN/EN) ──
    {
        "site_key": "huawei-info",
        "site_name": "Huawei Info Center",
        "source_rank": "A",
        "urls": [
            "https://info.support.huawei.com/info-finder/encyclopedia/en/BGP.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/OSPF.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/MPLS.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/VXLAN.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/EVPN.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/SRv6.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/QoS.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/ACL.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/VLAN.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/NAT.html",
        ],
    },
    # ── Cloudflare Learning Center (tech articles, clean HTML) ──
    {
        "site_key": "cloudflare-learn",
        "site_name": "Cloudflare Learning",
        "source_rank": "B",
        "urls": [
            "https://www.cloudflare.com/learning/network-layer/what-is-a-router/",
            "https://www.cloudflare.com/learning/network-layer/what-is-routing/",
            "https://www.cloudflare.com/learning/network-layer/what-is-bgp/",
            "https://www.cloudflare.com/learning/network-layer/what-is-an-autonomous-system/",
            "https://www.cloudflare.com/learning/network-layer/what-is-mpls/",
            "https://www.cloudflare.com/learning/security/glossary/what-is-bgp-hijacking/",
            "https://www.cloudflare.com/learning/ddos/glossary/open-systems-interconnection-model-osi/",
        ],
    },
    # ── Juniper TechLibrary (vendor docs) ──
    {
        "site_key": "juniper-techlib",
        "site_name": "Juniper TechLibrary",
        "source_rank": "A",
        "urls": [
            "https://www.juniper.net/documentation/us/en/software/junos/bgp/topics/topic-map/bgp-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/ospf/topics/topic-map/ospf-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/mpls/topics/topic-map/mpls-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/evpn-vxlan/topics/concept/evpn-vxlan-overview.html",
        ],
    },
    # ── NetworkLessons (tutorial style) ──
    {
        "site_key": "networklessons",
        "site_name": "NetworkLessons",
        "source_rank": "B",
        "urls": [
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-bgp",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-ospf",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-mpls",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-vxlan",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-qos",
        ],
    },
]


def crawl_all(app) -> None:
    """Crawl all URLs, store raw to MinIO, create document records."""
    import httpx

    crawler_store = app.crawler_store or app.store
    knowledge_store = app.store
    objects = app.objects

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    total_ok = 0
    total_fail = 0

    for source in SOURCES:
        site_key = source["site_key"]
        source_rank = source["source_rank"]

        # Register source
        try:
            crawler_store.execute(
                """INSERT INTO source_registry (site_key, site_name, home_url, source_rank, crawl_enabled, updated_at)
                VALUES (%s,%s,%s,%s,true,NOW())
                ON CONFLICT (site_key) DO UPDATE SET crawl_enabled=true, updated_at=NOW()""",
                (site_key, source["site_name"], source["urls"][0], source_rank),
            )
        except Exception as exc:
            log.warning("Failed to register source %s: %s", site_key, exc)

        for url in source["urls"]:
            if _stop_event.is_set():
                break

            log.info("[CRAWL] %s → %s", site_key, url)

            # Check if already crawled
            existing = knowledge_store.fetchone(
                "SELECT source_doc_id FROM documents WHERE source_url=%s", (url,)
            )
            if existing:
                log.info("[CRAWL] already exists: %s", url)
                continue

            try:
                # Fetch with retries
                resp = None
                for attempt in range(3):
                    try:
                        with httpx.Client(timeout=30, follow_redirects=True, verify=False) as client:
                            resp = client.get(url, headers=headers)
                        if resp.status_code < 400:
                            break
                        if resp.status_code == 429:
                            wait = min(30, 5 * (attempt + 1))
                            log.warning("[CRAWL] 429 for %s, waiting %ds", url, wait)
                            time.sleep(wait)
                    except Exception as fetch_err:
                        log.warning("[CRAWL] attempt %d failed for %s: %s", attempt + 1, url, fetch_err)
                        time.sleep(3)

                if resp is None or resp.status_code >= 400:
                    log.warning("[CRAWL] FAILED %s (status=%s)", url, resp.status_code if resp else "none")
                    total_fail += 1
                    continue

                raw_content = resp.text
                if len(raw_content) < 500:
                    log.warning("[CRAWL] too short (%d bytes), skipping: %s", len(raw_content), url)
                    total_fail += 1
                    continue

                # Store raw to MinIO
                raw_bytes = raw_content.encode("utf-8", errors="replace")
                c_hash = hashlib.sha256(raw_bytes).hexdigest()
                raw_key = f"raw/{c_hash}.html"
                raw_uri = objects.put(raw_key, raw_bytes, content_type="text/html")

                # Create document record
                doc_id = str(uuid.uuid4())
                knowledge_store.execute(
                    """INSERT INTO documents (
                        source_doc_id, site_key, source_url, canonical_url,
                        source_rank, crawl_time, content_hash, raw_storage_uri, status
                    ) VALUES (%s,%s,%s,%s,%s,NOW(),%s,%s,'raw')
                    ON CONFLICT (source_doc_id) DO NOTHING""",
                    (doc_id, site_key, url, str(resp.url), source_rank, c_hash, raw_uri),
                )

                log.info("[CRAWL] OK %s → doc=%s (%d bytes)", url, doc_id[:12], len(raw_bytes))
                total_ok += 1

                # Rate limit
                time.sleep(2)

            except Exception as exc:
                log.error("[CRAWL] ERROR %s: %s", url, exc)
                total_fail += 1

    log.info("[CRAWL] Done: %d ok, %d failed", total_ok, total_fail)


def pipeline_thread(app) -> None:
    """Pipeline loop: poll documents(status='raw'), run full pipeline."""
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
                    else:
                        log.info("[PIPELINE] doc=%s done in %.1fs", doc_id, elapsed)
                except Exception as exc:
                    elapsed = time.monotonic() - t0
                    log.error("[PIPELINE] doc=%s FAILED after %.1fs: %s",
                              doc_id, elapsed, str(exc)[:300])
                    record_failure(doc_id, str(exc), stage="pipeline")
                    try:
                        store.execute(
                            "UPDATE documents SET status='failed' WHERE source_doc_id=%s AND status != 'indexed'",
                            (doc_id,),
                        )
                    except Exception:
                        pass

        except Exception as exc:
            log.error("[PIPELINE] poll error: %s", exc)
            _stop_event.wait(PIPELINE_SLEEP)

    log.info("[PIPELINE] stopped")


def print_stats(app) -> None:
    store = app.store

    def cnt(sql):
        try:
            r = store.fetchone(sql)
            return r["cnt"] if r else 0
        except Exception:
            return "?"

    log.info("=" * 60)
    log.info("STRESS TEST RESULTS")
    log.info("=" * 60)
    log.info("  Documents total:      %s", cnt("SELECT count(*) as cnt FROM documents"))
    log.info("  Documents indexed:    %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='indexed'"))
    log.info("  Documents failed:     %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='failed'"))
    log.info("  Documents low_qual:   %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='low_quality'"))
    log.info("  Documents deduped:    %s", cnt("SELECT count(*) as cnt FROM documents WHERE status='deduped'"))
    log.info("  Segments:             %s", cnt("SELECT count(*) as cnt FROM segments"))
    log.info("  Segment tags:         %s", cnt("SELECT count(*) as cnt FROM segment_tags"))
    log.info("  RST relations:        %s", cnt("SELECT count(*) as cnt FROM t_rst_relation"))
    log.info("  Facts (total):        %s", cnt("SELECT count(*) as cnt FROM facts"))
    log.info("  Facts (llm):          %s", cnt("SELECT count(*) as cnt FROM evidence WHERE extraction_method='llm'"))
    log.info("  Facts (rule):         %s", cnt("SELECT count(*) as cnt FROM evidence WHERE extraction_method='rule'"))
    log.info("  Candidates:           %s", cnt("SELECT count(*) as cnt FROM governance.evolution_candidates"))
    log.info("  Conflicts:            %s", cnt("SELECT count(*) as cnt FROM governance.conflict_records"))

    # Per-site breakdown
    log.info("")
    log.info("Per-site breakdown:")
    rows = store.fetchall(
        "SELECT site_key, status, count(*) as cnt FROM documents GROUP BY site_key, status ORDER BY site_key, status"
    )
    for r in rows:
        log.info("  %-25s %-12s %s", r["site_key"], r["status"], r["cnt"])

    if _failed_docs:
        log.info("")
        log.info("FAILED DOCUMENTS (%d):", len(_failed_docs))
        for f in _failed_docs:
            log.info("  doc=%s  error=%s", f["source_doc_id"][:12], f["error"][:150])
        fail_path = Path(__file__).parent / "failed_docs.json"
        with open(fail_path, "w", encoding="utf-8") as fp:
            json.dump(_failed_docs, fp, indent=2, ensure_ascii=False)
        log.info("Saved to %s", fail_path)
    else:
        log.info("")
        log.info("No failed documents!")

    log.info("=" * 60)


def main() -> None:
    from src.app_factory import build_app

    log.info("=" * 60)
    log.info("STRESS TEST: diverse webpage types, %d hour timeout", TIMEOUT_HOURS)
    log.info("=" * 60)

    app = build_app()

    # Start pipeline thread
    t_pipeline = threading.Thread(target=pipeline_thread, args=(app,), name="pipeline", daemon=True)
    t_pipeline.start()

    # Crawl in main thread (finite set of URLs)
    crawl_all(app)

    # Wait for pipeline to finish remaining docs
    log.info("Crawling done. Waiting for pipeline to finish remaining docs...")
    while not _stop_event.is_set():
        remaining = app.store.fetchone(
            "SELECT count(*) as cnt FROM documents WHERE status IN ('raw','cleaned','segmented')"
        )
        if remaining and remaining["cnt"] == 0:
            log.info("All documents processed.")
            break
        log.info("Pipeline: %d documents remaining...", remaining["cnt"] if remaining else 0)
        _stop_event.wait(30)

    _stop_event.set()
    t_pipeline.join(timeout=300)
    print_stats(app)


if __name__ == "__main__":
    main()