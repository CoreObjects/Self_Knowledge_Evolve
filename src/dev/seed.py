"""
Seed the in-memory fake databases from the YAML OntologyRegistry.

Call seed_from_registry() once at startup, after fake modules are injected
into sys.modules but before any operator is invoked.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def seed_from_registry() -> None:
    """Load YAML ontology into fake_postgres and fake_neo4j stores."""
    from src.ontology.registry import OntologyRegistry
    from src.dev import fake_postgres, fake_neo4j

    reg = OntologyRegistry.from_default()

    # ── Seed Neo4j fake ───────────────────────────────────────────────────
    fake_neo4j.seed_nodes(reg.nodes)
    fake_neo4j.seed_aliases(reg.alias_map)

    # ── Seed Postgres fake (lexicon_aliases table) ────────────────────────
    conn = fake_postgres._get_conn()
    cur  = conn.cursor()

    # Insert from registry alias_map (surface_form → node_id)
    for surface_form, node_id in reg.alias_map.items():
        node = reg.nodes.get(node_id) or {}
        cur.execute(
            """
            INSERT OR IGNORE INTO lexicon_aliases
                (surface_form, canonical_node_id, alias_type, language, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                surface_form,
                node_id,
                "synonym",
                "en",
                0.9,
            ),
        )

    # Also insert with display names as surface_forms
    for node_id, node in reg.nodes.items():
        for alias in node.get("aliases", []):
            cur.execute(
                """
                INSERT OR IGNORE INTO lexicon_aliases
                    (surface_form, canonical_node_id, alias_type, language, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (alias.lower(), node_id, "alias", "en", 0.85),
            )

    conn.commit()

    alias_count = conn.execute("SELECT COUNT(*) FROM lexicon_aliases").fetchone()[0]
    logger.info(
        "seed_from_registry: %d nodes, %d aliases → %d lexicon_aliases rows",
        len(reg.nodes),
        len(reg.alias_map),
        alias_count,
    )