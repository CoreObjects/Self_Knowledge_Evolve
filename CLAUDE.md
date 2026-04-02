# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**Telecom Semantic Knowledge Base** — a governance-enabled, evolving, source-attributed knowledge infrastructure. **Not RAG, not a search engine.** Core value: cross-vendor term normalization, fault impact chain analysis, knowledge provenance with 5-dim confidence scoring, ontology drift prevention, and vector semantic search.

## Commands

### Local Development (no Docker required)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_dev.py                 # → http://127.0.0.1:8000/docs
```
Smoke test: `curl http://localhost:8000/health` and `curl "http://localhost:8000/api/v1/semantic/lookup?term=BGP"`

### Production Setup
```bash
cp .env.example .env
psql -h localhost -U postgres -d telecom_kb -f scripts/init_postgres.sql
psql -h localhost -U postgres -d telecom_crawler -f scripts/init_crawler_postgres.sql
python scripts/init_neo4j.py
python scripts/load_ontology.py       # YAML → Neo4j + PG lexicon (cold start)
uvicorn src.app:app --host 0.0.0.0 --port 8000
python worker.py                      # background: crawler + pipeline scheduler
```

### Ontology Changes
```bash
# Edit ontology/domains/*.yaml or ontology/top/relations.yaml or ontology/lexicon/aliases.yaml
python scripts/load_ontology.py       # sync YAML → Neo4j + PG; never edit Neo4j directly
```

### Docker (PostgreSQL + Neo4j only)
```bash
docker-compose up -d
```

## Architecture

### Layer Stack
```
semcore ABCs  (semcore/semcore/)               ← zero-dependency framework, publishable standalone
    ↑ implements
src/ domain implementation                     ← telecom-specific providers, operators, pipeline
    ↑ wired by
src/app_factory.py → build_app() → SemanticApp singleton
    ↑ serves
src/app.py (FastAPI) → src/api/semantic/router.py → OperatorRegistry
```

`semcore` is not installed as a package — it's imported via `sys.path.insert(0, "semcore")` in run scripts, or `pip install -e semcore`.

### Knowledge Persistence
```
ontology/*.yaml  →  source of truth (version-controlled)
      ↓ scripts/load_ontology.py
Neo4j            →  runtime graph projection (5 node label types, graph traversal)
PostgreSQL       →  relational store + governance audit log
OntologyRegistry →  in-memory cache used by pipeline alignment stages
```

### 7-Stage Pipeline (triggered by `source_doc_id`)
```
Stage 1: Ingest    → extract text, denoise, quality gate, doc_type detection
Stage 2: Segment   → structure segmentation, semantic role classification, 21 RST relation types
Stage 3: Align     → alias matching, 5-layer tagging, candidate term discovery
Stage 3b: Evolve   → 5-dim scoring, 6-gate review, auto-promote/pending
Stage 4: Extract   → regex patterns + optional LLM → (S, P, O) triples with confidence
Stage 5: Dedup     → SimHash dedup, fact merging, conflict detection
Stage 6: Index     → confidence gate, Neo4j ingestion, vector embedding
```
To feed the pipeline: insert a `documents` row with `status='raw'` and upload the file to MinIO `raw/`. The worker polls automatically.

### 15 Semantic Operators (REST `/api/v1/semantic/`)
`lookup`, `resolve`, `expand`, `path`, `dependency_closure`, `impact_propagate`, `filter`, `evidence_rank`, `conflict_detect`, `fact_merge`, `candidate_discover`, `attach_score`, `evolution_gate`, `semantic_search` (requires `EMBEDDING_ENABLED=true`), `edu_search`

All responses follow: `{"meta": {"ontology_version": ..., "latency_ms": ...}, "result": {...}}`

### Dev Mode (in-memory, no external services)
`src/dev/` replaces all external stores:
- `fake_postgres.py` → SQLite `:memory:` for knowledge DB
- `fake_crawler_postgres.py` → SQLite `:memory:` for crawler DB
- `fake_neo4j.py` → dict-based graph store
- `seed.py` → seeds from YAML ontology at startup

## Key Conventions

### Adding a New Operator
1. `src/api/semantic/xxx.py` — business logic
2. `src/operators/xxx_op.py` — `SemanticOperator` wrapper
3. `src/operators/__init__.py` — register in `ALL_OPERATORS`
4. `src/api/semantic/router.py` — add FastAPI endpoint

### Database Split
- **`telecom_kb`** (main): `documents`, `segments`, `facts`, `evidence`, plus `governance` schema (`evolution_candidates`, `conflict_records`, `review_records`, `ontology_versions`)
- **`telecom_crawler`** (separate DB): `source_registry`, `crawl_tasks`, `extraction_jobs`
- In pipeline stages: use `app.store` for knowledge DB, `app.crawler_store` for crawler DB — never cross them
- Governance tables require `governance.` schema prefix in SQL; dev mode SQLite strips it automatically

### Confidence Formula
```
score = 0.30×source_authority + 0.20×extraction_method
      + 0.20×ontology_fit + 0.20×cross_source_consistency + 0.10×temporal_validity
```
Source authority tiers: S (IETF/3GPP/ITU-T/IEEE) → 1.0 · A (Cisco/Huawei/Juniper) → 0.85 · B (whitepapers) → 0.65 · C (blogs/forums) → 0.40

### Optional Features
- `LLM_ENABLED=true` — enables Claude API for Stage 4 relation extraction (`LLM_API_KEY` required)
- `EMBEDDING_ENABLED=true` — enables vector search; requires `BAAI/bge-m3` model downloaded locally (1024-dim, bilingual)

## Five-Layer Ontology Model

| Layer | YAML file | Neo4j label | Count |
|-------|-----------|-------------|-------|
| concept | `ip_network.yaml` | `OntologyNode` | 74 |
| mechanism | `ip_network_mechanisms.yaml` | `MechanismNode` | 24 |
| method | `ip_network_methods.yaml` | `MethodNode` | 22 |
| condition | `ip_network_conditions.yaml` | `ConditionRuleNode` | 20 |
| scenario | `ip_network_scenarios.yaml` | `ScenarioPatternNode` | 13 |

Relations: 54 types in `ontology/top/relations.yaml`. Aliases: 793 entries in `ontology/lexicon/aliases.yaml` (Chinese/English + vendor variants).

## Design Docs

All architecture decisions are documented before implementation. Key references:
- `docs/architecture-decisions.md` — ADR-001 to ADR-009
- `docs/semcore-framework-design.md` — framework abstraction rationale
- `docs/development-spec-20260402.md` — full development specification
- `docs/telecom-ontology-design.md` — 5-layer knowledge model design