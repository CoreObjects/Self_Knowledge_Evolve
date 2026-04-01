# Telecom Semantic Knowledge Base

面向网络通信领域的可治理、可演化、带溯源的语义知识基础设施。

将公开文档（RFC、厂商手册、技术白皮书等）转化为结构化、可计算的知识对象，通过领域本体组织，经多模存储持久化，由语义算子 API 对外服务。

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **本体锚定的知识组织** | 5 层领域本体（概念/机制/方法/条件/场景），153 节点 + 54 种受控关系 + 156 条别名 |
| **多源数据接入** | 爬虫、文件导入、API 上传均可灌入系统，Pipeline 不感知数据来源 |
| **7 阶段处理流水线** | 清洗 → 切段 → 本体对齐 → 本体演化 → 关系抽取 → 去重 → 图谱索引 |
| **21 种 RST 语篇关系** | 基于修辞结构理论的通用语篇逻辑关系，6 大类 |
| **多模存储** | PostgreSQL（知识+治理）、Neo4j（图谱）、pgvector（向量）、MinIO（文档） |
| **15 个语义算子** | 术语查询、图遍历、依赖分析、故障影响传播、语义搜索、本体演化 |
| **受控演化** | 新概念进入候选池 → 五维评分 → 六项门控 → 人工/自动晋升 |

### 首版领域范围：IP 数通网络

Ethernet · VLAN · STP · LACP · OSPF · IS-IS · BGP · MPLS · SR-MPLS · SRv6 · EVPN · VXLAN · L3VPN · VRF · QoS · ACL · NAT · BFD · NETCONF · YANG

---

## 系统逻辑架构

```
┌─ 上层入口 ──────────────────────────────────────────────────────────────────┐
│                                                                             │
│  FastAPI REST API (router.py)           worker.py                           │
│    └─ 15 语义算子端点                     └─ 爬取 + Pipeline 调度            │
│         ↓                                      ↓                            │
│  ┌─ SemanticApp ──────────────────────────────────────────────────────────┐ │
│  │  app.query(op_name)          app.ingest(source_doc_id)                 │ │
│  │       ↓                           ↓                                    │ │
│  │  OperatorRegistry            Pipeline (7 stages)                       │ │
│  │  + Middleware 链              linear / branch / switch                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
         │                              │
         │  ┌───────────────────────────┘
         │  │
┌─ 领域实现层 ──────────────────────────────────────────────────────────────────┐
│                                                                               │
│  ┌─ 本体层（统一语义骨架）──────────────────────────────────────────────────┐ │
│  │  YAML (ontology/) ── 唯一源头，版本控制                                  │ │
│  │       ↓ load_ontology.py                                                 │ │
│  │  OntologyRegistry (内存) ── alias_map / relation_ids / nodes             │ │
│  │       ↓ 同步投影                                                         │ │
│  │  Neo4j (5 类 label)     PG lexicon_aliases     PG governance.versions    │ │
│  │                                                                          │ │
│  │  本体统一三个存储系统的 schema：                                          │ │
│  │  · Neo4j 节点/边类型 = 本体定义的 5 层 + 54 种关系                       │ │
│  │  · PG segment_tags.ontology_node_id = 本体 node_id                       │ │
│  │  · PG facts.subject/object = 本体 node_id                                │ │
│  │  · PG lexicon_aliases = 本体别名镜像                                     │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─ 治理层 ────────────────┐  ┌─ 流水线层 ──────────────────────────────┐   │
│  │ ConfidenceScorer        │  │ preprocessing/                          │   │
│  │   5 维置信度加权         │  │   extractor (正文提取)                  │   │
│  │ ConflictDetector        │  │   normalizer (去噪归一化)               │   │
│  │   same S+P diff O       │  │ stages/                                 │   │
│  │ EvolutionGate           │  │   1.清洗 → 2.切段+RST → 3.对齐         │   │
│  │   6 项门控              │  │   → 3b.演化 → 4.抽取 → 5.去重 → 6.索引 │   │
│  └─────────────────────────┘  └─────────────────────────────────────────┘   │
│                                                                               │
│  ┌─ 算子层 (15 个 SemanticOperator) ──────────────────────────────────────┐ │
│  │ lookup · resolve · expand · filter · path · dependency_closure          │ │
│  │ impact_propagate · evidence_rank · conflict_detect · fact_merge         │ │
│  │ candidate_discover · attach_score · evolution_gate                      │ │
│  │ semantic_search · edu_search                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
         │
┌─ semcore 框架层（零外部依赖 ABCs）────────────────────────────────────────────┐
│  providers/base.py   LLMProvider · EmbeddingProvider · GraphStore ·           │
│                      RelationalStore · ObjectStore                            │
│  ontology/base.py    OntologyProvider (get_node / resolve_alias / version)   │
│  governance/base.py  ConfidenceScorer · ConflictDetector · EvolutionGate     │
│  operators/base.py   SemanticOperator · OperatorMiddleware · OperatorRegistry│
│  pipeline/base.py    Stage · Pipeline (LinearNode / BranchNode / SwitchNode) │
│  app.py              AppConfig (纯数据) → SemanticApp (组合根)               │
└──────────────────────────────────────────────────────────────────────────────┘
         │
┌─ 基础设施层 ─────────────────────────────────────────────────────────────────┐
│  PostgreSQL telecom_kb        Neo4j              MinIO                        │
│    public: 知识数据              本体图 + 知识图谱    raw/ + cleaned/          │
│    governance: 治理数据                                                       │
│  PostgreSQL telecom_crawler   BAAI/bge-m3                                    │
│    爬虫调度数据                  1024 维向量 → PG pgvector                     │
└──────────────────────────────────────────────────────────────────────────────┘
         │
┌─ 外部数据源（Pipeline 之外）─────────────────────────────────────────────────┐
│  Spider 爬虫 · 文件导入 · API 上传  → MinIO(raw/) + documents(status='raw')  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**关键设计原则**：
- **本体是统一骨架** — YAML 是唯一源头，同步投影到 Neo4j（图遍历）、PG lexicon_aliases（SQL 查询）、内存 OntologyRegistry（Pipeline 对齐），三个存储的 schema 均由本体定义约束
- **semcore 是纯抽象底座** — 零依赖 ABCs，领域实现全部可替换
- **SemanticApp 是唯一入口** — `app.query()` 走算子，`app.ingest()` 走流水线，上层 API/Worker 只和 SemanticApp 交互
- **数据源与 Pipeline 解耦** — 任何能往 documents 表 + MinIO 写数据的进程都是合法数据源

### 存储分工

| 存储 | 内容 | 本体关联 |
|------|------|----------|
| **PG telecom_kb** (public) | documents, segments, facts, evidence, segment_tags, lexicon_aliases, t_rst_relation | segment_tags/facts 的 node_id 引用本体；lexicon_aliases 镜像本体别名 |
| **PG telecom_kb** (governance) | evolution_candidates, conflict_records, review_records, ontology_versions | 治理本体生命周期 |
| **PG telecom_crawler** | source_registry, crawl_tasks, extraction_jobs | 无本体关联 |
| **Neo4j** | 5 类本体节点 + KnowledgeSegment/Fact/Evidence + 关系边 | 本体的运行时图投影 |
| **pgvector** | segments.embedding / title_vec / content_vec (1024 维) | 向量索引，不直接关联本体 |
| **MinIO** | raw/ (原始文档), cleaned/ (清洗后文本) | 不关联本体 |

---

## 项目结构

```
Self_Knowledge_Evolve/
│
├── semcore/semcore/                    # 框架包（零外部依赖）
│   ├── core/types.py                   # 领域数据类：OntologyNode, Fact, Segment …
│   ├── core/context.py                 # PipelineContext
│   ├── providers/base.py               # ABCs: LLMProvider, EmbeddingProvider, GraphStore …
│   ├── ontology/base.py                # OntologyProvider ABC
│   ├── governance/base.py              # ConfidenceScorer, ConflictDetector, EvolutionGate ABCs
│   ├── operators/base.py               # SemanticOperator + OperatorRegistry + Middleware
│   ├── pipeline/base.py                # Stage ABC, Pipeline (linear/branch/switch)
│   └── app.py                          # SemanticApp + AppConfig
│
├── src/
│   ├── app.py                          # FastAPI 入口
│   ├── app_factory.py                  # build_app() 组合根
│   ├── config/settings.py              # Pydantic Settings (.env)
│   ├── db/
│   │   ├── postgres.py                 # 知识库连接池
│   │   ├── crawler_postgres.py         # 爬虫库连接池
│   │   └── neo4j_client.py             # Neo4j driver
│   ├── providers/                      # 6 个 Provider 实现
│   ├── ontology/                       # OntologyRegistry + YAML 校验
│   ├── governance/                     # 置信度/冲突/演化门控
│   ├── pipeline/
│   │   ├── preprocessing/              # 文本预处理（extractor + normalizer）
│   │   ├── pipeline_factory.py         # build_pipeline()
│   │   └── stages/                     # 7 个 Stage 实现
│   ├── operators/                      # 15 个 SemanticOperator
│   ├── api/semantic/                   # 算子业务逻辑 + FastAPI router
│   ├── crawler/                        # Spider（Pipeline 外部数据源）
│   ├── utils/                          # 文本/哈希/置信度/嵌入/LLM
│   └── dev/                            # 内存替代（fake_postgres/fake_neo4j）
│
├── ontology/                           # 本体 YAML（唯一源头）
│   ├── domains/                        # 5 个领域文件，153 节点
│   ├── lexicon/aliases.yaml            # 156 条别名
│   ├── top/relations.yaml              # 54 种关系类型
│   └── governance/evolution_policy.yaml
│
├── scripts/
│   ├── init_postgres.sql               # 知识库 DDL (public + governance)
│   ├── init_crawler_postgres.sql       # 爬虫库 DDL
│   ├── init_neo4j.py                   # 约束 + 索引
│   ├── load_ontology.py                # YAML → Neo4j + PG
│   └── migrations/                     # 增量迁移脚本
│
├── worker.py                           # 后台 Worker（爬取 + Pipeline）
└── run_dev.py                          # 本地开发（内存模式，零外部依赖）
```

---

## 快速开始

### 本地开发（无需 Docker）

```bash
git clone https://github.com/xuanx-ai/Self_Knowledge_Evolve.git
cd Self_Knowledge_Evolve

python -m venv .venv
.venv\Scripts\activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

python run_dev.py
# → http://127.0.0.1:8000/docs
```

内存模式自动从 YAML 本体 seed 数据，可直接测试：

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/v1/semantic/lookup?term=BGP"
curl "http://localhost:8000/api/v1/semantic/resolve?alias=border+gateway+protocol"
```

### 生产部署

```bash
cp .env.example .env
# 编辑 .env 填入数据库连接信息

# 初始化数据库
psql -h localhost -U postgres -d telecom_kb -f scripts/init_postgres.sql
psql -h localhost -U postgres -d telecom_crawler -f scripts/init_crawler_postgres.sql
python scripts/init_neo4j.py

# 加载本体
python scripts/load_ontology.py

# 启动 API
uvicorn src.app:app --host 0.0.0.0 --port 8000

# 启动 Worker（爬取 + Pipeline）
python worker.py
```

---

## 配置

所有配置通过 `.env` 读取，详见 `.env.example`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | — | 知识库连接（必填） |
| `CRAWLER_POSTGRES_*` | 同主库 | 爬虫库连接（留空则复用主库参数） |
| `NEO4J_URI/USER/PASSWORD` | bolt://localhost:7687 | Neo4j 连接 |
| `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` | — | MinIO 连接 |
| `LLM_ENABLED` | false | 启用 LLM 关系抽取 |
| `LLM_API_KEY` | — | Anthropic/OpenAI/DeepSeek API Key |
| `EMBEDDING_ENABLED` | false | 启用向量嵌入（需下载 BAAI/bge-m3） |
| `ONTOLOGY_VERSION` | v0.2.0 | 当前本体版本标记 |

---

## 流水线

7 阶段处理流水线，输入为 `source_doc_id`，从 documents 表 + MinIO 开始。

```
documents(raw) + MinIO
    │
    ▼ Stage 1 — 清洗 (C3-C5)
    │  正文提取 → 去噪归一化 → 质量门控 → 文档类型检测
    │
    ▼ Stage 2 — 切段 (S1-S4 + RST)
    │  结构切分 → 语义角色分类 → 长度控制 → RST 语篇关系（21种）
    │
    ▼ Stage 3 — 本体对齐 (A1-A5)
    │  别名匹配 → 五层标签 → 候选术语发现
    │
    ▼ Stage 3b — 本体演化
    │  五维评分 → 六项门控 → 自动晋升/待审
    │
    ▼ Stage 4 — 关系抽取 (R1-R4)
    │  15 正则模式 + LLM → (S, P, O) 三元组 + 置信度
    │
    ▼ Stage 5 — 去重 (D1-D5)
    │  SimHash 段落去重 → 事实合并 → 冲突检测
    │
    ▼ Stage 6 — 索引 (I1-I3)
       置信度门控 → Neo4j 入图 → 向量嵌入
       documents.status = 'indexed'
```

### 数据源接入

任何数据源只需两步即可接入 Pipeline：
1. 往 `documents` 表插入一条 `status='raw'` 的记录
2. 往 MinIO `raw/` 存放原始文档

Pipeline worker 会自动捞取并处理。

---

## 语义算子 API

Base URL: `http://localhost:8000/api/v1/semantic`

所有响应格式：`{"meta": {"ontology_version": "v0.2.0", "latency_ms": 12}, "result": {...}}`

### 查询与解析

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/lookup` | 术语 → 本体节点 + 证据 |
| GET | `/resolve` | 别名/厂商术语 → 标准节点 |

### 图遍历

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/expand` | 节点邻域展开（depth 1-3） |
| GET | `/path` | 两节点间最短路径 |
| GET | `/dependency_closure` | 依赖闭包 BFS |

### 影响分析

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/impact_propagate` | 故障/变更影响链路推导 |
| POST | `/filter` | 参数化对象过滤 + 分页 |

### 证据与治理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/evidence_rank` | 事实证据排序 |
| GET | `/conflict_detect` | 矛盾事实检测 |
| POST | `/fact_merge` | 重复事实合并 |

### 本体演化

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/candidate_discover` | 发现候选概念 |
| GET | `/attach_score` | 候选词挂接评分 |
| POST | `/evolution_gate` | 六项门控评审 |

### 语义搜索（需 EMBEDDING_ENABLED=true）

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/semantic_search` | 段落向量相似搜索 |
| POST | `/edu_search` | 标题+内容双向量加权搜索 |

交互文档：**http://localhost:8000/docs**

---

## 本体

本体定义在 `ontology/` YAML 文件中 —— 这是**唯一源头**，不要直接改 Neo4j。

### 五层知识模型

| 层 | Neo4j 标签 | 数量 | 示例 |
|----|-----------|------|------|
| concept | OntologyNode | 74 | IP.BGP, IP.OSPF, IP.EVPN |
| mechanism | MechanismNode | 24 | MECH.LinkStateFlooding, MECH.ECMPSelection |
| method | MethodNode | 22 | METHOD.AddressPlanningMethod |
| condition | ConditionRuleNode | 20 | COND.SmallScaleApplicability |
| scenario | ScenarioPatternNode | 13 | SCENE.DualExitCampusInternetScenario |

### 修改流程

```
编辑 YAML → load_ontology.py --dry-run（校验）→ 人工审核 → load_ontology.py（写入）
```

---

## 知识来源等级

| 等级 | 来源 | 置信权重 |
|------|------|----------|
| **S** | IETF, 3GPP, ITU-T, IEEE | 1.0 |
| **A** | Cisco, Huawei, Juniper, Nokia | 0.85 |
| **B** | 技术白皮书, 公开课程 | 0.65 |
| **C** | 博客, 论坛, 问答社区 | 0.40 |

置信度公式：`0.30×source_authority + 0.20×extraction_method + 0.20×ontology_fit + 0.20×cross_source_consistency + 0.10×temporal_validity`

---

## 设计文档

| 文档 | 内容 |
|------|------|
| `docs/architecture-design-20260402.md` | 当前完整架构设计 |
| `docs/development-spec-20260402.md` | 当前完整开发方案 |
| `docs/architecture-decisions.md` | ADR 决策记录（ADR-001 ~ ADR-009） |
| `docs/semcore-framework-design.md` | semcore 框架设计 |
| `docs/telecom-ontology-design.md` | 本体设计原则 |

---

## License

本项目用于研究和内部知识工程目的。所有爬取内容版权归原作者所有。系统存储知识索引和证据引用，不存储全文。