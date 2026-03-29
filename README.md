# Telecom Semantic Knowledge Base

A governance-first semantic knowledge infrastructure for the network & telecommunications domain.
Transforms public web corpora into computable, traceable, evolvable knowledge — organized by a domain ontology, stored across multi-modal backends, and exposed through a unified semantic operator API.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Dev Mode (no Docker)](#dev-mode-no-docker)
- [Configuration](#configuration)
- [Database Initialization](#database-initialization)
- [Ontology](#ontology)
- [Pipeline](#pipeline)
- [Semantic API](#semantic-api)
- [Development Roadmap](#development-roadmap)
- [Design Documents](#design-documents)

---

## Overview

This system is **not** a plain vector search engine or a web scraper.
It is a semantic knowledge infrastructure with five core capabilities:

| Capability | Description |
|---|---|
| **Ontology-anchored organization** | All knowledge is tagged against a versioned 5-layer domain ontology — stable concepts, controlled relations, alias resolution |
| **Knowledge extraction pipeline** | 6-stage pipeline converts raw HTML → clean segments → ontology-aligned facts + evidence |
| **Multi-modal storage** | PostgreSQL (metadata), Neo4j (graph), pgvector (segment embeddings), MinIO (raw documents) |
| **Semantic operator API** | 15 operators for lookup, graph traversal, dependency analysis, impact propagation, semantic search, and ontology evolution |
| **Controlled evolution** | New concepts enter a candidate pool and pass a scored gate before touching the core ontology |

### First-version scope: IP / Data Communication Network

Ethernet · VLAN · STP/RSTP/MSTP · LACP · OSPF · IS-IS · BGP · MPLS · LDP · SR-MPLS · SRv6 · EVPN · VXLAN · L3VPN · VRF · QoS · ACL · NAT · IPsec · BFD · NETCONF · YANG · Telemetry

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    semcore Framework (semcore/)                    │
│   ABCs: Provider · Pipeline · Governance · Operator · App         │
└───────────────────────────────┬───────────────────────────────────┘
                                │ implements
┌───────────────────────────────▼───────────────────────────────────┐
│                        Ontology Core Layer                        │
│   YAML definitions  →  OntologyRegistry  →  Neo4j OntologyNodes   │
└───────────────────────────────┬───────────────────────────────────┘
                                │ semantic skeleton
┌───────────────────────────────▼───────────────────────────────────┐
│                      Corpus Ingestion Layer                       │
│   Spider (robots/rate-limit)  →  Extractor  →  Normalizer         │
└───────────────────────────────┬───────────────────────────────────┘
                                │ clean text
┌───────────────────────────────▼───────────────────────────────────┐
│                     Knowledge Processing Pipeline                 │
│  Stage 1 Ingest → Stage 2 Segment → Stage 3 Align                │
│  Stage 4 Extract → Stage 5 Dedup  → Stage 6 Index + Embed        │
└──────┬──────────────────┬──────────────────────┬──────────────────┘
       │                  │                      │
┌──────▼──────┐  ┌────────▼────────┐  ┌─────────▼──────────┐
│ PostgreSQL  │  │     Neo4j       │  │ pgvector / MinIO   │
│  metadata   │  │  ontology+graph │  │ embeddings + docs  │
└──────┬──────┘  └────────┬────────┘  └─────────┬──────────┘
       └──────────────────┴──────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              Semantic Operator API  (FastAPI / semcore)          │
│  lookup · resolve · expand · filter · path · dependency         │
│  impact_propagate · evidence_rank · conflict_detect             │
│  fact_merge · candidate_discover · attach_score · evolution_gate│
│  semantic_search · edu_search                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Storage roles

| Store | Role |
|---|---|
| **PostgreSQL** | Source registry, crawl tasks, document metadata, segments, facts, evidence, conflict records, ontology versions, evolution candidates |
| **Neo4j** | Ontology nodes, concept graph, fact nodes, evidence nodes, TAGGED_WITH / SUPPORTED_BY / BELONGS_TO edges |
| **pgvector** | Segment embeddings (`embedding` column on `segments`); title/content vectors on `t_edu_detail` |
| **MinIO / S3** | Raw HTML snapshots, cleaned text, PDF attachments |

---

## Project Structure

```
Self_Knowledge_Evolve/
│
├── semcore/                                # Reusable framework package (zero external deps)
│   └── semcore/
│       ├── core/types.py                   # Domain dataclasses: OntologyNode, Fact, Segment …
│       ├── core/context.py                 # PipelineContext (typed fields + stage_outputs + meta)
│       ├── providers/base.py               # ABCs: LLMProvider, EmbeddingProvider, GraphStore …
│       ├── ontology/base.py                # OntologyProvider ABC
│       ├── governance/base.py              # ConfidenceScorer, ConflictDetector, EvolutionGate ABCs
│       ├── operators/base.py               # SemanticOperator, OperatorMiddleware, OperatorRegistry
│       ├── pipeline/base.py                # Stage ABC, Pipeline (linear + branch + switch routing)
│       └── app.py                          # SemanticApp + AppConfig (composition root)
│
├── docs/
│   ├── semcore-framework-design.md         # Framework design decisions
│   ├── refactoring-plan.md                 # src/ → semcore migration plan
│   ├── architecture-decisions.md           # ADR log (embedding, storage, LLM)
│   ├── telecom-semantic-kb-system-design.md
│   ├── telecom-ontology-design.md
│   └── development-plan-detailed.md
│
├── ontology/                               # Ontology source of truth (YAML)
│   ├── top/
│   │   └── relations.yaml                  # 54 controlled relation types
│   ├── domains/
│   │   ├── ip_network.yaml                 # ~66 concept nodes
│   │   ├── ip_network_mechanisms.yaml      # 24 mechanism nodes
│   │   ├── ip_network_methods.yaml         # 22 method nodes
│   │   ├── ip_network_conditions.yaml      # 20 condition nodes
│   │   └── ip_network_scenarios.yaml       # 13 scenario nodes
│   ├── lexicon/
│   │   └── aliases.yaml                    # EN/ZH aliases + vendor terms (793 entries)
│   └── governance/
│       └── evolution_policy.yaml           # Anti-drift thresholds
│
├── scripts/
│   ├── init_postgres.sql                   # DDL: 13 tables + pgvector extension
│   ├── init_neo4j.py                       # Neo4j constraints + indexes
│   └── load_ontology.py                    # YAML → Neo4j + PG lexicon
│
├── src/
│   ├── app.py                              # FastAPI entry point (production)
│   ├── app_factory.py                      # build_app() + get_app() singleton
│   ├── config/
│   │   └── settings.py                     # Pydantic settings, reads .env
│   ├── db/
│   │   ├── postgres.py                     # PG connection pool + helpers
│   │   └── neo4j_client.py                 # Neo4j driver wrapper
│   ├── dev/                                # In-memory stubs for local dev
│   │   ├── fake_postgres.py                # SQLite :memory: backend
│   │   ├── fake_neo4j.py                   # Dict-backed Neo4j stub
│   │   └── seed.py                         # Seeds stubs from YAML ontology
│   ├── providers/                          # semcore Provider implementations
│   │   ├── postgres_store.py
│   │   ├── neo4j_store.py
│   │   ├── anthropic_llm.py
│   │   ├── bge_m3_embedding.py
│   │   └── minio_store.py
│   ├── ontology/
│   │   ├── registry.py                     # In-memory OntologyRegistry (YAML loader)
│   │   ├── validator.py                    # YAML structural validation
│   │   └── yaml_provider.py                # OntologyProvider backed by registry
│   ├── governance/
│   │   ├── confidence_scorer.py            # TelecomConfidenceScorer
│   │   ├── conflict_detector.py            # TelecomConflictDetector
│   │   └── evolution_gate.py               # TelecomEvolutionGate (6 gate checks)
│   ├── operators/                          # 15 SemanticOperator implementations
│   │   ├── __init__.py                     # ALL_OPERATORS list
│   │   ├── lookup_op.py
│   │   ├── resolve_op.py
│   │   ├── expand_op.py
│   │   ├── filter_op.py
│   │   ├── path_op.py
│   │   ├── dependency_op.py
│   │   ├── impact_op.py
│   │   ├── evidence_op.py
│   │   ├── evolution_op.py
│   │   └── search_op.py
│   ├── pipeline/
│   │   ├── pipeline_factory.py             # build_pipeline() with switch routing
│   │   └── stages/
│   │       ├── stage1_ingest.py            # Rules C1–C5: fetch, dedup, doc_type
│   │       ├── stage2_segment.py           # Rules S1–S4: structural+semantic split
│   │       ├── stage3_align.py             # Rules A1–A5: ontology tagging
│   │       ├── stage4_extract.py           # Rules R1–R4: relation extraction
│   │       ├── stage5_dedup.py             # Rules D1–D5: SimHash + fact dedup
│   │       └── stage6_index.py             # Rules I1–I3: Neo4j indexing + embedding
│   ├── utils/
│   │   ├── text.py                         # Normalization, token count, truncate
│   │   ├── hashing.py                      # SHA-256, SimHash, Hamming, Jaccard
│   │   ├── confidence.py                   # Weighted confidence scoring
│   │   ├── embedding.py                    # BAAI/bge-m3 embedding + pg literal helper
│   │   ├── llm_extract.py                  # Claude API relation extraction
│   │   └── logging.py                      # Structured logging setup
│   ├── api/
│   │   └── semantic/
│   │       ├── lookup.py                   # Term → ontology node
│   │       ├── resolve.py                  # Alias → canonical node
│   │       ├── expand.py                   # Node neighbourhood traversal
│   │       ├── filter.py                   # Parameterized fact/segment filter
│   │       ├── path.py                     # Shortest path between nodes
│   │       ├── dependency.py               # Dependency closure BFS
│   │       ├── impact.py                   # Fault impact propagation BFS
│   │       ├── evidence.py                 # Evidence rank, conflict detect, fact merge
│   │       ├── evolution.py                # Candidate discover, attach score, gate
│   │       └── router.py                   # FastAPI router → OperatorRegistry
│   └── crawler/
│       ├── spider.py                       # HTTP fetch, robots.txt, rate limit
│       ├── extractor.py                    # trafilatura + readability extraction
│       └── normalizer.py                   # Boilerplate removal, hash computation
│
├── tests/
├── run_dev.py                              # Dev entry point (in-memory, no Docker)
├── docker-compose.yml                      # PostgreSQL + Neo4j containers
├── .env.example                            # Connection config template
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL and Neo4j)

### 1. Clone and install

```bash
git clone git@github.com:ZoeRen-pp/Self_Knowledge_Evolve.git
cd Self_Knowledge_Evolve

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure connections

```bash
cp .env.example .env
```

Edit `.env` — minimum required fields:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=telecom_kb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Start infrastructure

```bash
docker-compose up -d
```

### 4. Initialize databases

```bash
# PostgreSQL: create all 13 tables + pgvector extension
psql -h localhost -U postgres -d telecom_kb -f scripts/init_postgres.sql

# Neo4j: create uniqueness constraints and lookup indexes
python scripts/init_neo4j.py
```

### 5. Load the ontology

```bash
# Dry-run (validate only, no writes)
python scripts/load_ontology.py --dry-run

# Load all domains + aliases into Neo4j + PostgreSQL lexicon
python scripts/load_ontology.py
```

### 6. Start the API server

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

```bash
curl http://localhost:8000/health
# {"postgres": true, "neo4j": true, "status": "ok"}
```

---

## Dev Mode (no Docker)

Run the full API against in-memory SQLite + dict stores, seeded from YAML ontology.
No PostgreSQL, Neo4j, or any external service required.

```bash
python run_dev.py
# or
uvicorn run_dev:app --port 8000
```

**How it works:** `run_dev.py` injects `src.dev.fake_postgres` and `src.dev.fake_neo4j` into
`sys.modules` before any operator imports, then seeds them from the YAML ontology files.
The production `src/app.py` and all `.env` settings are untouched.

**Verified endpoints in dev mode:**

```bash
curl http://localhost:8000/health
# {"postgres": true, "neo4j": true, "status": "ok"}

curl "http://localhost:8000/api/v1/semantic/lookup?term=BGP"
# matched_node: IP.BGP, match_type: exact

curl "http://localhost:8000/api/v1/semantic/resolve?alias=border+gateway+protocol"
# resolved: {node_id: IP.BGP, confidence: 0.9}
```

---

## Configuration

All settings are read from `.env` via `src/config/settings.py`.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `""` | PostgreSQL host (required) |
| `POSTGRES_PORT` | `""` | PostgreSQL port (required) |
| `POSTGRES_DB` | `""` | Database name (required) |
| `POSTGRES_USER` | `""` | Username (required) |
| `POSTGRES_PASSWORD` | `""` | Password (required) |
| `POSTGRES_POOL_MIN` | `""` | Min pool connections (required) |
| `POSTGRES_POOL_MAX` | `""` | Max pool connections (required) |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `changeme` | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `MINIO_ENDPOINT` | `""` | MinIO endpoint (required) |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `LLM_API_KEY` | `""` | Anthropic API key (Claude for relation extraction) |
| `LLM_ENABLED` | `false` | Enable LLM extraction in stage 4 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Sentence-transformer model |
| `EMBEDDING_ENABLED` | `false` | Enable embedding generation in stage 6 |
| `EMBEDDING_DIM` | `1024` | Vector dimension |
| `ONTOLOGY_VERSION` | `v0.2.0` | Active ontology version tag |
| `LOG_LEVEL` | `INFO` | Logging level |
| `STARTUP_HEALTH_REQUIRED` | `true` | Fail startup if health check is not OK |

---

## Database Initialization

### PostgreSQL tables (13)

| Table | Purpose |
|---|---|
| `source_registry` | Site whitelist, source rank (S/A/B/C), crawl config |
| `crawl_tasks` | URL queue, status tracking, retry count |
| `documents` | Document metadata, content hashes, dedup grouping |
| `segments` | Semantic segments with SimHash and pgvector `embedding` column |
| `segment_tags` | Canonical / semantic_role / context tags per segment |
| `facts` | Normalized SPO triples with confidence and lifecycle |
| `evidence` | Source evidence linking facts to segments and documents |
| `conflict_records` | Detected contradictions between facts |
| `ontology_versions` | Versioned ontology snapshots and change log |
| `evolution_candidates` | Candidate new concepts with scoring dimensions |
| `review_records` | Audit trail for all human review actions |
| `lexicon_aliases` | Mirror of ontology aliases for SQL-side resolution |
| `t_edu_detail` | Educational content with `title_vec` + `content_vec` for dual-vector search |

### Neo4j node labels

`OntologyNode` · `MechanismNode` · `MethodNode` · `ConditionRuleNode` · `ScenarioPatternNode`
`KnowledgeSegment` · `SourceDocument` · `Fact` · `Evidence`

### Neo4j edge types (key)

`SUBCLASS_OF` · `RELATED_TO` · `DEPENDS_ON` · `USES` · `IMPACTS` · `CAUSES`
`SUPPORTED_BY` · `EXTRACTED_FROM` · `BELONGS_TO` · `TAGGED_WITH` · `ALIAS_OF` · `CONTRADICTS`

---

## Ontology

The ontology lives in `ontology/` YAML files — **these are the source of truth**, not Neo4j.
Neo4j is the runtime projection; PostgreSQL tracks versions and governance.

### Five knowledge layers

| Layer | Node type | Count | Example |
|---|---|---|---|
| **concept** | `OntologyNode` | 66 | IP.BGP, IP.OSPF, IP.EVPN |
| **mechanism** | `MechanismNode` | 24 | MECH.BGP_ROUTE_REFLECTOR, MECH.ECMP |
| **method** | `MethodNode` | 22 | METHOD.BGP_ROUTE_FILTERING, METHOD.QOS_MARKING |
| **condition** | `ConditionRuleNode` | 20 | COND.BGP_SESSION_DOWN, COND.OSPF_ADJACENCY_FAIL |
| **scenario** | `ScenarioPatternNode` | 13 | SCENE.DC_FABRIC, SCENE.WAN_SDWAN |

### Modification workflow

```
Edit YAML file
     ↓
python scripts/load_ontology.py --dry-run   ← validate
     ↓
Human review (for domain/core changes)
     ↓
python scripts/load_ontology.py             ← write to Neo4j + PG
     ↓
Bump ONTOLOGY_VERSION in .env
```

### Candidate concept admission thresholds

```yaml
min_source_count:       3      # must appear in 3+ documents
min_source_diversity:   0.6    # from 3+ distinct sites
min_temporal_stability: 0.7    # present in 2+ crawl cycles
min_structural_fit:     0.65   # can attach to a clear parent node
min_composite_score:    0.65
synonym_risk_max:       0.4    # must not be a simple synonym
require_human_review:   true
```

---

## Pipeline

The 6-stage pipeline converts a crawled document into indexed graph knowledge.
Each stage is a `semcore.pipeline.base.Stage` implementation.

```
crawl_task
    │
    ▼ Stage 1 — Ingest (rules C1–C5)
    │  robots check · rate limit · content_hash dedup
    │  text extraction · doc_type detection
    │
    ▼ Stage 2 — Segment (rules S1–S4)    [switch routing: rfc / cli / default]
    │  structural split: headings / tables / code blocks
    │  semantic role classification: definition / config / fault / …
    │  length control: 30–512 tokens; sliding window for oversized
    │
    ▼ Stage 3 — Align (rules A1–A5)
    │  alias dictionary exact match
    │  ontology node lookup → canonical tags + 5-layer tags
    │  unmatched terms → evolution_candidates table
    │
    ▼ Stage 4 — Extract (rules R1–R4)
    │  15 regex relation patterns → (subject, predicate, object)
    │  predicate validation against controlled relation set
    │  both endpoints must resolve to ontology nodes
    │  confidence scoring (5 dimensions)
    │
    ▼ Stage 5 — Dedup (rules D1–D5)
    │  segment dedup: SimHash hamming ≤ 3 + Jaccard > 0.85
    │  fact dedup: exact SPO triple match → merge_cluster
    │  conflict detection: same subject+predicate, different object
    │
    ▼ Stage 6 — Index (rules I1–I3)
       gate: segment confidence ≥ 0.5, fact confidence ≥ 0.5
       write PG (already done) → Neo4j nodes + edges
       BAAI/bge-m3 embedding → segments.embedding + t_edu_detail vectors
       mark document status = 'indexed'
```

### Run the pipeline

```python
from src.app_factory import get_app
from semcore.core.context import PipelineContext

app = get_app()

ctx = PipelineContext(meta={"crawl_task_id": 1})
app.ingest(ctx)
```

---

## Semantic API

Base URL: `http://localhost:8000/api/v1/semantic`

All requests go through the `OperatorRegistry` (with `TimingMiddleware` + `LoggingMiddleware`).
All responses include a `meta` envelope:

```json
{
  "meta": { "ontology_version": "v0.2.0", "latency_ms": 12 },
  "result": { ... }
}
```

### Operator reference (15 operators)

#### Lookup & Resolution

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/lookup` | Resolve a term (alias/full name/Chinese) to its ontology node + optional evidence |
| `GET` | `/resolve` | Map an alias or vendor term to the canonical node ID |

```bash
curl "http://localhost:8000/api/v1/semantic/lookup?term=BGP&include_evidence=true"
curl "http://localhost:8000/api/v1/semantic/resolve?alias=Border+Gateway+Protocol"
curl "http://localhost:8000/api/v1/semantic/resolve?alias=Etherchannel&vendor=Cisco"
```

#### Graph Traversal

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/expand` | Expand a node's neighbourhood (depth 1–3, filter by relation types) |
| `GET` | `/path` | Shortest semantic path between two ontology nodes |
| `GET` | `/dependency_closure` | Full dependency tree via BFS (DEPENDS_ON + REQUIRES) |

```bash
curl "http://localhost:8000/api/v1/semantic/expand?node_id=IP.EVPN&depth=2"
curl "http://localhost:8000/api/v1/semantic/path?start_node_id=IP.EVPN_VXLAN&end_node_id=IP.BGP"
curl "http://localhost:8000/api/v1/semantic/dependency_closure?node_id=IP.EVPN_VXLAN"
```

#### Impact & Filtering

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/impact_propagate` | BFS fault/change blast-radius from an event node |
| `POST` | `/filter` | Parameterized filter over facts, segments, or concepts |

```bash
curl -X POST "http://localhost:8000/api/v1/semantic/impact_propagate" \
  -H "Content-Type: application/json" \
  -d '{"event_node_id":"IP.BGP","event_type":"fault","max_depth":3}'
```

#### Evidence & Governance

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/evidence_rank` | Rank evidence supporting a fact by quality |
| `GET` | `/conflict_detect` | Find contradictory facts for a topic node |
| `POST` | `/fact_merge` | Merge duplicate facts into one canonical fact |

#### Ontology Evolution

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/candidate_discover` | Surface new candidate concepts from recent corpus |
| `GET` | `/attach_score` | Score which parent node a candidate best fits |
| `POST` | `/evolution_gate` | Check whether a candidate passes all 6 admission gates |

```bash
curl "http://localhost:8000/api/v1/semantic/candidate_discover?window_days=30&min_frequency=5"
curl -X POST "http://localhost:8000/api/v1/semantic/evolution_gate" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":"<uuid>"}'
```

#### Semantic Search (requires `EMBEDDING_ENABLED=true`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/semantic_search` | ANN search over `segments.embedding` (pgvector); optional layer filter |
| `POST` | `/edu_search` | Dual-vector search over `t_edu_detail` (title_vec + content_vec weighted) |

```bash
curl -X POST "http://localhost:8000/api/v1/semantic/semantic_search" \
  -H "Content-Type: application/json" \
  -d '{"query":"BGP route reflector configuration","top_k":5,"layer_filter":"mechanism"}'

curl -X POST "http://localhost:8000/api/v1/semantic/edu_search" \
  -H "Content-Type: application/json" \
  -d '{"query":"OSPF area design","top_k":5,"title_weight":0.4}'
```

Full interactive documentation: **http://localhost:8000/docs**

---

## Development Roadmap

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Ontology definition — 5-layer YAML, 54 relation types, 145 nodes | ✅ Complete |
| **Phase 2** | Crawl pipeline — ingest → segment → align → extract → dedup → index | ✅ Complete |
| **Phase 3** | Knowledge governance — multi-source merge, conflict resolution, confidence scoring | ✅ Complete |
| **Phase 4** | Semantic operator API — 15 operators via OperatorRegistry | ✅ Complete |
| **Phase 5** | Ontology evolution loop — discover → score → gate → publish | ✅ Complete |
| **Phase 6** | semcore framework — abstract ABCs, middleware, conditional routing | ✅ Complete |
| **Phase 7** | Embedding & semantic search — BAAI/bge-m3, pgvector, semantic_search + edu_search | ✅ Implemented (activation requires `EMBEDDING_ENABLED=true` + model download) |
| **Phase 8** | Application integration — Q&A, config understanding, fault analysis | 🔜 Planned |

### Next steps (Phase 8 candidates)

- [ ] Add site whitelist seeds for IETF RFC, Cisco Docs, Huawei iLearningX
- [ ] Add Airflow/Prefect DAG for scheduled batch crawling
- [ ] Enable LLM-assisted extraction for S/A-rank sources (`LLM_ENABLED=true`)
- [ ] Download and activate `BAAI/bge-m3` model (`EMBEDDING_ENABLED=true`)
- [ ] Add Q&A endpoint combining semantic_search + impact_propagate for fault diagnosis
- [ ] Add domain-specific pipeline branches (RFC segmenter, CLI config parser)

---

## Design Documents

Detailed design rationale is in `docs/`:

| Document | Contents |
|---|---|
| `semcore-framework-design.md` | Framework design: 6 layers, middleware onion model, conditional routing |
| `refactoring-plan.md` | Mapping of src/ to semcore ABCs; 26 new adapter files |
| `architecture-decisions.md` | ADR log: embedding model selection, storage choices, LLM strategy |
| `telecom-semantic-kb-system-design.md` | Full system design: storage selection, quality assurance, risk analysis |
| `telecom-ontology-design.md` | Ontology design principles, 5-layer knowledge model, YAML node format |
| `development-plan-detailed.md` | PostgreSQL DDL, Neo4j schema, complete pipeline rules (C1–I3), API specs |

---

## Source Trust Levels

| Rank | Sources | Role in system |
|---|---|---|
| **S** | IETF, 3GPP, ITU-T, IEEE, ETSI, MEF, ONF | Primary facts, high confidence |
| **A** | Cisco, Huawei, Juniper, Nokia, Arista, H3C | Secondary facts, vendor context |
| **B** | Technical whitepapers, open courseware | Supporting evidence |
| **C** | Blogs, forums, Q&A communities | Auxiliary evidence only |

Confidence formula: `0.30×source_authority + 0.20×extraction_quality + 0.20×ontology_fit + 0.20×cross_source_consistency + 0.10×temporal_validity`

---

## License

This project is for research and internal knowledge engineering purposes.
All crawled content remains the property of its original authors.
The system stores knowledge indexes and evidence references, not full-text reproductions.
