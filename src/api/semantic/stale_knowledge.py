"""stale_knowledge operator — time decay and weak evidence queries."""

from __future__ import annotations

import logging

from semcore.providers.base import RelationalStore

log = logging.getLogger(__name__)


def stale_knowledge(
    query_type: str = "fact",
    days: int = 90,
    limit: int = 50,
    *,
    store: RelationalStore,
) -> dict:
    log.debug("stale_knowledge type=%s days=%d", query_type, days)

    handler = _QUERY_HANDLERS.get(query_type)
    if handler is None:
        return {"error": f"Unknown query_type '{query_type}'", "valid_types": list(_QUERY_HANDLERS)}
    return handler(store=store, days=days, limit=limit)


def _stale_facts(*, store: RelationalStore, days: int, limit: int) -> dict:
    """Facts whose most recent evidence is older than N days."""
    rows = store.fetchall(
        """
        SELECT f.fact_id, f.subject, f.predicate, f.object, f.confidence,
               max(e.created_at) AS latest_evidence
        FROM facts f
        JOIN evidence e ON f.fact_id = e.fact_id
        WHERE f.lifecycle_state = 'active'
        GROUP BY f.fact_id, f.subject, f.predicate, f.object, f.confidence
        HAVING max(e.created_at) < NOW() - INTERVAL '%s days'
        ORDER BY max(e.created_at) ASC
        LIMIT %s
        """,
        (days, limit),
    )
    facts = [dict(r) for r in rows]
    log.info("stale_facts (>%d days): %d found", days, len(facts))
    return {"query_type": "fact", "days": days, "count": len(facts), "items": facts}


def _stale_docs(*, store: RelationalStore, days: int, limit: int) -> dict:
    """Documents whose crawl_time is older than N days."""
    rows = store.fetchall(
        """
        SELECT source_doc_id, site_key, source_url, title, doc_type,
               crawl_time, status
        FROM documents
        WHERE crawl_time < NOW() - INTERVAL '%s days'
          AND status = 'indexed'
        ORDER BY crawl_time ASC
        LIMIT %s
        """,
        (days, limit),
    )
    docs = [dict(r) for r in rows]
    log.info("stale_docs (>%d days): %d found", days, len(docs))
    return {"query_type": "doc", "days": days, "count": len(docs), "items": docs}


def _weak_evidence(*, store: RelationalStore, limit: int, **_kw) -> dict:
    """Facts with only 1 evidence record and source_rank <= B."""
    rows = store.fetchall(
        """
        SELECT f.fact_id, f.subject, f.predicate, f.object, f.confidence,
               e.source_rank, e.extraction_method
        FROM facts f
        JOIN evidence e ON f.fact_id = e.fact_id
        WHERE f.lifecycle_state = 'active'
        GROUP BY f.fact_id, f.subject, f.predicate, f.object, f.confidence,
                 e.source_rank, e.extraction_method
        HAVING count(e.evidence_id) = 1
           AND max(e.source_rank) IN ('B', 'C')
        ORDER BY f.confidence ASC
        LIMIT %s
        """,
        (limit,),
    )
    facts = [dict(r) for r in rows]
    log.info("weak_evidence: %d single-source low-rank facts", len(facts))
    return {"query_type": "weak_evidence", "count": len(facts), "items": facts}


_QUERY_HANDLERS = {
    "fact": _stale_facts,
    "doc": _stale_docs,
    "weak_evidence": _weak_evidence,
}