"""Background worker to run crawler and pipeline."""

from __future__ import annotations

import json
import logging
import time

from semcore.core.context import PipelineContext

from src.app_factory import get_app
from src.config.settings import settings
from src.crawler.spider import Spider
from src.utils.health import startup_health_check
from src.utils.logging import setup_logging

log = logging.getLogger(__name__)

# Consecutive idle cycles before switching to exponential backoff
_IDLE_BACKOFF_START = 3
_IDLE_BACKOFF_MAX = 300  # cap at 5 minutes

# Retry policy for failed crawl tasks
_MAX_RETRIES = 3
_RETRY_BACKOFF_MINUTES = [5, 30, 120]  # delay before 1st, 2nd, 3rd retry


_SEED_SOURCES: list[dict] = [
    # ══════════════════════════════════════════════════════════════
    # S-rank: Authoritative standards bodies
    # ══════════════════════════════════════════════════════════════
    {
        "site_key": "ietf-datatracker",
        "site_name": "IETF Datatracker",
        "home_url": "https://datatracker.ietf.org/",
        "source_rank": "S",
        "rate_limit_rps": 0.5,
        "seed_urls": [
            # ── Core routing ──
            "https://datatracker.ietf.org/doc/html/rfc4271",   # BGP-4
            "https://datatracker.ietf.org/doc/html/rfc4456",   # BGP Route Reflection
            "https://datatracker.ietf.org/doc/html/rfc4760",   # MP-BGP
            "https://datatracker.ietf.org/doc/html/rfc7938",   # BGP in Large-Scale DC
            "https://datatracker.ietf.org/doc/html/rfc4364",   # BGP/MPLS IP VPN
            "https://datatracker.ietf.org/doc/html/rfc4684",   # Constrained Route Distribution
            "https://datatracker.ietf.org/doc/html/rfc5065",   # BGP Confederations
            "https://datatracker.ietf.org/doc/html/rfc6811",   # BGP RPKI Validation
            "https://datatracker.ietf.org/doc/html/rfc2328",   # OSPF v2
            "https://datatracker.ietf.org/doc/html/rfc5340",   # OSPF v3
            "https://datatracker.ietf.org/doc/html/rfc3630",   # OSPF-TE
            "https://datatracker.ietf.org/doc/html/rfc5308",   # IS-IS for IPv4/IPv6
            "https://datatracker.ietf.org/doc/html/rfc5305",   # IS-IS TE Extensions
            # ── MPLS / SR ──
            "https://datatracker.ietf.org/doc/html/rfc3031",   # MPLS Architecture
            "https://datatracker.ietf.org/doc/html/rfc3032",   # MPLS Label Stack
            "https://datatracker.ietf.org/doc/html/rfc3209",   # RSVP-TE
            "https://datatracker.ietf.org/doc/html/rfc5036",   # LDP
            "https://datatracker.ietf.org/doc/html/rfc8402",   # Segment Routing Architecture
            "https://datatracker.ietf.org/doc/html/rfc8986",   # SRv6 Network Programming
            "https://datatracker.ietf.org/doc/html/rfc9252",   # BGP Overlay SR
            # ── EVPN / VXLAN / Overlay ──
            "https://datatracker.ietf.org/doc/html/rfc7432",   # BGP MPLS EVPN
            "https://datatracker.ietf.org/doc/html/rfc7348",   # VXLAN
            "https://datatracker.ietf.org/doc/html/rfc8365",   # EVPN Overlay Framework
            "https://datatracker.ietf.org/doc/html/rfc9136",   # IP Prefix EVPN
            # ── L2 / Switching ──
            "https://datatracker.ietf.org/doc/html/rfc5765",   # STP MIB
            "https://datatracker.ietf.org/doc/html/rfc7130",   # BFD on LAG
            "https://datatracker.ietf.org/doc/html/rfc8668",   # LLDP YANG
            # ── IP fundamentals ──
            "https://datatracker.ietf.org/doc/html/rfc791",    # IPv4
            "https://datatracker.ietf.org/doc/html/rfc8200",   # IPv6
            "https://datatracker.ietf.org/doc/html/rfc793",    # TCP
            "https://datatracker.ietf.org/doc/html/rfc768",    # UDP
            "https://datatracker.ietf.org/doc/html/rfc2131",   # DHCP
            "https://datatracker.ietf.org/doc/html/rfc1034",   # DNS Concepts
            "https://datatracker.ietf.org/doc/html/rfc792",    # ICMP
            "https://datatracker.ietf.org/doc/html/rfc4443",   # ICMPv6
            # ── Redundancy / HA ──
            "https://datatracker.ietf.org/doc/html/rfc3768",   # VRRP
            "https://datatracker.ietf.org/doc/html/rfc5798",   # VRRPv3
            "https://datatracker.ietf.org/doc/html/rfc5880",   # BFD
            "https://datatracker.ietf.org/doc/html/rfc5881",   # BFD for IPv4/IPv6
            # ── QoS / Security ──
            "https://datatracker.ietf.org/doc/html/rfc2474",   # DiffServ
            "https://datatracker.ietf.org/doc/html/rfc2475",   # DiffServ Architecture
            "https://datatracker.ietf.org/doc/html/rfc2697",   # srTCM
            "https://datatracker.ietf.org/doc/html/rfc2698",   # trTCM
            "https://datatracker.ietf.org/doc/html/rfc2544",   # Benchmarking
            "https://datatracker.ietf.org/doc/html/rfc4303",   # IPsec ESP
            "https://datatracker.ietf.org/doc/html/rfc7296",   # IKEv2
            # ── Network management ──
            "https://datatracker.ietf.org/doc/html/rfc6241",   # NETCONF
            "https://datatracker.ietf.org/doc/html/rfc8040",   # RESTCONF
            "https://datatracker.ietf.org/doc/html/rfc7950",   # YANG
            "https://datatracker.ietf.org/doc/html/rfc8345",   # Network Topology YANG
            # ── NAT / Multicast ──
            "https://datatracker.ietf.org/doc/html/rfc3022",   # Traditional NAT
            "https://datatracker.ietf.org/doc/html/rfc6146",   # NAT64
            "https://datatracker.ietf.org/doc/html/rfc4601",   # PIM-SM
            "https://datatracker.ietf.org/doc/html/rfc3376",   # IGMPv3
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    # ══════════════════════════════════════════════════════════════
    # A-rank: Major vendor documentation
    # ══════════════════════════════════════════════════════════════
    {
        "site_key": "huawei-info",
        "site_name": "Huawei Info Center",
        "home_url": "https://info.support.huawei.com/",
        "source_rank": "A",
        "rate_limit_rps": 0.3,
        "seed_urls": [
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
            "https://info.support.huawei.com/info-finder/encyclopedia/en/DHCP.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/DNS.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/IPsec.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/BFD.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/VRRP.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/IS-IS.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/NETCONF.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/Segment+Routing.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/LACP.html",
            "https://info.support.huawei.com/info-finder/encyclopedia/en/STP.html",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    {
        "site_key": "juniper-techlib",
        "site_name": "Juniper TechLibrary",
        "home_url": "https://www.juniper.net/documentation/",
        "source_rank": "A",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://www.juniper.net/documentation/us/en/software/junos/bgp/topics/topic-map/bgp-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/ospf/topics/topic-map/ospf-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/mpls/topics/topic-map/mpls-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/evpn-vxlan/topics/concept/evpn-vxlan-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/is-is/topics/topic-map/is-is-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/segment-routing/topics/concept/segment-routing-overview.html",
            "https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/bfd.html",
            "https://www.juniper.net/documentation/us/en/software/junos/nat/topics/topic-map/nat-overview.html",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    {
        "site_key": "arista-docs",
        "site_name": "Arista Documentation",
        "home_url": "https://www.arista.com/en/um-eos/",
        "source_rank": "A",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://www.arista.com/en/um-eos/eos-border-gateway-protocol-bgp",
            "https://www.arista.com/en/um-eos/eos-open-shortest-path-first-version-3-ospfv3",
            "https://www.arista.com/en/um-eos/eos-vxlan",
            "https://www.arista.com/en/um-eos/eos-evpn-overview",
            "https://www.arista.com/en/um-eos/eos-multi-protocol-label-switching-mpls-overview",
            "https://www.arista.com/en/um-eos/eos-segment-routing",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    # ══════════════════════════════════════════════════════════════
    # B-rank: Technical learning / whitepapers
    # ══════════════════════════════════════════════════════════════
    {
        "site_key": "networklessons",
        "site_name": "NetworkLessons",
        "home_url": "https://networklessons.com/",
        "source_rank": "B",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-bgp",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-ospf",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-mpls",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-vxlan",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-qos",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-is-is",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-sd-wan",
            "https://networklessons.com/cisco/ccnp-encor-350-401/introduction-to-vrf-lite",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    {
        "site_key": "cloudflare-learn",
        "site_name": "Cloudflare Learning Center",
        "home_url": "https://www.cloudflare.com/learning/",
        "source_rank": "B",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://www.cloudflare.com/learning/network-layer/what-is-bgp/",
            "https://www.cloudflare.com/learning/network-layer/what-is-routing/",
            "https://www.cloudflare.com/learning/network-layer/what-is-a-router/",
            "https://www.cloudflare.com/learning/network-layer/what-is-an-autonomous-system/",
            "https://www.cloudflare.com/learning/network-layer/what-is-mpls/",
            "https://www.cloudflare.com/learning/security/glossary/what-is-bgp-hijacking/",
            "https://www.cloudflare.com/learning/ddos/glossary/open-systems-interconnection-model-osi/",
            "https://www.cloudflare.com/learning/network-layer/what-is-a-wan/",
            "https://www.cloudflare.com/learning/network-layer/what-is-a-lan/",
            "https://www.cloudflare.com/learning/network-layer/what-is-a-subnet/",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    {
        "site_key": "packetlife",
        "site_name": "PacketLife.net",
        "home_url": "https://packetlife.net/",
        "source_rank": "B",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://packetlife.net/blog/2008/sep/22/ospf-area-types/",
            "https://packetlife.net/blog/2009/jun/10/understanding-bgp-path-selection/",
            "https://packetlife.net/blog/2010/jan/19/mpls-fundamentals/",
            "https://packetlife.net/blog/2010/feb/1/vlan-trunking/",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
    {
        "site_key": "ipspace",
        "site_name": "ipSpace.net Blog",
        "home_url": "https://blog.ipspace.net/",
        "source_rank": "B",
        "rate_limit_rps": 0.3,
        "seed_urls": [
            "https://blog.ipspace.net/2024/01/bgp-labs-simple-routing-policy.html",
            "https://blog.ipspace.net/2022/09/evpn-bridging-routing.html",
            "https://blog.ipspace.net/2023/03/segment-routing-overview.html",
            "https://blog.ipspace.net/2022/03/vxlan-evpn-behind-curtain.html",
        ],
        "scope_rules": None,
        "extra_headers": None,
    },
]


def _jsonb(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True)


def _auto_enqueue_seeds(store) -> None:
    total_urls = 0
    for src in _SEED_SOURCES:
        store.execute(
            """
            INSERT INTO source_registry (
                site_key, site_name, home_url, source_rank, crawl_enabled,
                rate_limit_rps, seed_urls, scope_rules, extra_headers, updated_at
            ) VALUES (
                %s, %s, %s, %s, true,
                %s, %s::jsonb, %s::jsonb, %s::jsonb, NOW()
            )
            ON CONFLICT (site_key) DO UPDATE SET
                site_name = EXCLUDED.site_name,
                home_url = EXCLUDED.home_url,
                source_rank = EXCLUDED.source_rank,
                crawl_enabled = true,
                rate_limit_rps = EXCLUDED.rate_limit_rps,
                seed_urls = EXCLUDED.seed_urls,
                scope_rules = EXCLUDED.scope_rules,
                extra_headers = EXCLUDED.extra_headers,
                updated_at = NOW()
            """,
            (
                src["site_key"],
                src["site_name"],
                src["home_url"],
                src["source_rank"],
                src["rate_limit_rps"],
                _jsonb(src.get("seed_urls")),
                _jsonb(src.get("scope_rules")),
                _jsonb(src.get("extra_headers")),
            ),
        )

        for url in src["seed_urls"]:
            store.execute(
                """
                INSERT INTO crawl_tasks (
                    site_key, url, task_type, priority, status, scheduled_at
                ) VALUES (
                    %s, %s, 'full', %s, 'pending', NOW()
                )
                ON CONFLICT (url) DO UPDATE SET
                    site_key = EXCLUDED.site_key,
                    task_type = EXCLUDED.task_type,
                    priority = EXCLUDED.priority,
                    status = 'pending',
                    scheduled_at = NOW(),
                    started_at = NULL,
                    finished_at = NULL,
                    retry_count = 0,
                    http_status = NULL,
                    error_msg = NULL,
                    raw_storage_uri = NULL,
                    content_hash = NULL,
                    parent_task_id = NULL
                """,
                (src["site_key"], url, 10),
            )
        total_urls += len(src["seed_urls"])

    log.info(
        "Auto-enqueued %d seed URLs across %d sources",
        total_urls,
        len(_SEED_SOURCES),
    )


def _retry_failed_tasks(store) -> int:
    """Re-queue failed tasks that haven't exceeded max retries and whose backoff has elapsed."""
    retried = 0
    for attempt, delay_min in enumerate(_RETRY_BACKOFF_MINUTES):
        rows = store.fetchall(
            """
            SELECT id, url, retry_count
            FROM crawl_tasks
            WHERE status = 'failed'
              AND retry_count = %s
              AND finished_at < NOW() - INTERVAL '%s minutes'
            ORDER BY priority DESC, id ASC
            LIMIT 20
            """,
            (attempt, delay_min),
        )
        for row in rows:
            store.execute(
                """
                UPDATE crawl_tasks
                SET status = 'pending',
                    scheduled_at = NOW(),
                    retry_count = retry_count + 1,
                    started_at = NULL,
                    finished_at = NULL,
                    error_msg = NULL
                WHERE id = %s
                """,
                (row["id"],),
            )
            retried += 1
            log.info(
                "Retrying failed task id=%s url=%s (attempt %d/%d)",
                row["id"], row["url"], row["retry_count"] + 1, _MAX_RETRIES,
            )
    return retried


def _fetch_pipeline_tasks(knowledge_store, limit: int) -> list[str]:
    """Find documents in 'raw' status ready for pipeline processing."""
    rows = knowledge_store.fetchall(
        """
        SELECT source_doc_id FROM documents
        WHERE status = 'raw'
        ORDER BY created_at ASC
        LIMIT %s
        """,
        (limit,),
    )
    return [str(row["source_doc_id"]) for row in rows]


def _run_pipeline(app, doc_ids: list[str]) -> None:
    for doc_id in doc_ids:
        ctx = PipelineContext(source_doc_id=doc_id)
        try:
            app.ingest_context(ctx)
            log.info("Pipeline completed for doc=%s errors=%d", doc_id, len(ctx.errors))
        except Exception as exc:
            log.error("Pipeline failed for doc=%s err=%s", doc_id, exc, exc_info=True)


def main() -> None:
    setup_logging(settings.LOG_LEVEL)
    if not startup_health_check():
        raise SystemExit("Startup health check failed.")

    app = get_app()
    crawler_store = app.crawler_store or app.store
    _auto_enqueue_seeds(crawler_store)
    spider = Spider(object_store=app.objects, store=crawler_store, knowledge_store=app.store)
    log.info(
        "Worker started: crawl_limit=%d pipeline_limit=%d sleep=%ds",
        settings.WORKER_CRAWL_LIMIT,
        settings.WORKER_PIPELINE_LIMIT,
        settings.WORKER_SLEEP_SECS,
    )

    idle_count = 0
    try:
        while True:
            try:
                # Retry failed tasks that are ready for another attempt
                retried = _retry_failed_tasks(crawler_store)

                crawl_results = spider.run_pending_tasks(limit=settings.WORKER_CRAWL_LIMIT)

                # Pipeline picks up all documents in 'raw' status (from any source)
                doc_ids = _fetch_pipeline_tasks(app.store, settings.WORKER_PIPELINE_LIMIT)
                if doc_ids:
                    _run_pipeline(app, doc_ids)

                has_work = len(crawl_results) > 0 or len(doc_ids) > 0 or retried > 0
                if has_work:
                    idle_count = 0
                    log.info(
                        "Worker cycle done: crawled=%d pipeline_docs=%d retried=%d",
                        len(crawl_results),
                        len(doc_ids),
                        retried,
                    )
                else:
                    idle_count += 1
                    if idle_count <= _IDLE_BACKOFF_START:
                        log.info("Worker cycle done: crawled=0 pipeline_tasks=0")
                    else:
                        log.debug("Worker idle (cycle %d)", idle_count)
            except Exception as exc:
                log.error("Worker cycle error: %s", exc, exc_info=True)
                idle_count = 0  # reset on error so next cycle logs at INFO

            # Exponential backoff when idle
            if idle_count > _IDLE_BACKOFF_START:
                backoff = min(
                    settings.WORKER_SLEEP_SECS * (2 ** (idle_count - _IDLE_BACKOFF_START)),
                    _IDLE_BACKOFF_MAX,
                )
                time.sleep(backoff)
            else:
                time.sleep(settings.WORKER_SLEEP_SECS)
    finally:
        spider.close()


if __name__ == "__main__":
    main()
