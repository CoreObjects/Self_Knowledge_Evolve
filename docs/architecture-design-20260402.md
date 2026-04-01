# 语义知识操作系统 — 架构设计文档

**版本**：v0.3
**日期**：2026-04-02

---

# 1. 系统定位与核心价值

本系统是面向网络通信领域的**可治理、可演化、带溯源的语义知识基础设施**。

**不是** RAG，**不是**搜索引擎，**不是**网页爬虫。核心价值在于：

| 能力 | 说明 |
|------|------|
| 本体锚定的知识组织 | 5 层领域本体（153 节点 + 54 种关系 + 156 条别名）统一所有存储系统的 schema |
| 多源数据接入 | 爬虫/文件导入/API 上传均在 Pipeline 外部，通过 documents 表 + MinIO 解耦 |
| 7 阶段处理流水线 | 清洗 → 切段+RST → 对齐 → 演化 → 抽取 → 去重 → 索引 |
| 21 种 RST 语篇关系 | 通用修辞结构理论关系，6 大逻辑类别 |
| 5 维置信度 + 溯源 | 每条事实带来源权威度、抽取方式、本体适配等多维评分 |
| 受控本体演化 | 候选概念经五维评分 + 六项门控，防止本体漂移 |
| 15 个语义算子 | 术语查询、图遍历、影响传播、语义搜索、演化管理 |

### 首版领域范围

IP 数通网络：Ethernet · VLAN · STP · LACP · OSPF · IS-IS · BGP · MPLS · SR-MPLS · SRv6 · EVPN · VXLAN · L3VPN · VRF · QoS · ACL · NAT · BFD

---

# 2. 总体逻辑架构

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

┌─ semcore 框架层（零外部依赖 ABCs）────────────────────────────────────────────┐
│  providers/base.py   LLMProvider · EmbeddingProvider · GraphStore ·           │
│                      RelationalStore · ObjectStore                            │
│  ontology/base.py    OntologyProvider (get_node / resolve_alias / version)   │
│  governance/base.py  ConfidenceScorer · ConflictDetector · EvolutionGate     │
│  operators/base.py   SemanticOperator · OperatorMiddleware · OperatorRegistry│
│  pipeline/base.py    Stage · Pipeline (LinearNode / BranchNode / SwitchNode) │
│  core/types.py       OntologyNode · Document · Segment · Fact · Evidence …   │
│  core/context.py     PipelineContext (typed fields + stage_outputs + meta)    │
│  app.py              AppConfig (纯数据) → SemanticApp (组合根)               │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 基础设施层 ─────────────────────────────────────────────────────────────────┐
│  PostgreSQL telecom_kb        Neo4j              MinIO                        │
│    public: 知识数据              本体图 + 知识图谱    raw/ + cleaned/          │
│    governance: 治理数据                                                       │
│  PostgreSQL telecom_crawler   BAAI/bge-m3                                    │
│    爬虫调度数据                  1024 维向量 → PG pgvector                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 外部数据源（Pipeline 之外）─────────────────────────────────────────────────┐
│  Spider 爬虫 · 文件导入 · API 上传  → MinIO(raw/) + documents(status='raw')  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 关键设计原则

1. **本体是统一骨架** — YAML 是唯一源头，同步投影到 Neo4j（图遍历）、PG lexicon_aliases（SQL 查询）、内存 OntologyRegistry（Pipeline 对齐）。三个存储系统的 schema 均由本体定义约束。
2. **semcore 是纯抽象底座** — 零外部依赖 ABCs，所有领域实现可替换。
3. **SemanticApp 是唯一入口** — `app.query()` 走算子，`app.ingest()` 走流水线，上层 API/Worker 只和 SemanticApp 交互。
4. **数据源与 Pipeline 解耦** — 任何能往 documents 表 + MinIO 写数据的进程都是合法数据源，Pipeline 只认 `source_doc_id`。

---

# 3. 分层架构详解

## 3.1 semcore 框架层

零外部依赖的抽象层，定义系统的所有契约。

| 模块 | 核心抽象 | 职责 |
|------|----------|------|
| `core/types.py` | OntologyNode, Document, Segment, Fact, Evidence, ConfidenceScore, EvolutionCandidate, KnowledgeLayer, SourceRank | 系统内流转的所有数据类型 |
| `core/context.py` | PipelineContext | 流水线共享数据包（doc/segments/tags/facts/evidence + stage_outputs + meta + errors） |
| `providers/base.py` | LLMProvider, EmbeddingProvider, GraphStore, RelationalStore, ObjectStore | 5 种基础设施抽象，每种一个 ABC |
| `ontology/base.py` | OntologyProvider | 本体只读视图（get_node / get_layer_nodes / resolve_alias / version） |
| `governance/base.py` | ConfidenceScorer, ConflictDetector, EvolutionGate | 治理三件套 ABC |
| `operators/base.py` | SemanticOperator, OperatorMiddleware, OperatorRegistry | 算子框架（无状态查询 + 洋葱模型中间件 + 注册分发） |
| `pipeline/base.py` | Stage, Pipeline, LinearNode, BranchNode, SwitchNode | 流水线框架（可组合阶段 + 条件路由） |
| `app.py` | AppConfig, SemanticApp | 组合根（AppConfig 纯数据注入 → SemanticApp 运行时） |

### 组合根模式

```python
AppConfig(
    llm       = ClaudeLLMProvider(settings),
    embedding = BGEM3EmbeddingProvider(),
    graph     = Neo4jGraphStore(),
    store     = PostgresRelationalStore(),        # 知识库
    crawler_store = CrawlerPostgresRelationalStore(),  # 爬虫库
    objects   = MinioObjectStore(settings),
    ontology  = YAMLOntologyProvider(registry),
    confidence_scorer = TelecomConfidenceScorer(),
    conflict_detector = TelecomConflictDetector(),
    evolution_gate    = TelecomEvolutionGate(),
    operators   = ALL_OPERATORS,                  # 15 个算子实例
    middlewares = [TimingMiddleware(), LoggingMiddleware()],
    pipeline    = build_pipeline(),               # 7 阶段
)
→ SemanticApp(config)
```

## 3.2 基础设施层

| Provider ABC | 实现 | 后端 |
|---|---|---|
| RelationalStore | PostgresRelationalStore | psycopg2 → telecom_kb |
| RelationalStore | CrawlerPostgresRelationalStore | psycopg2 → telecom_crawler |
| GraphStore | Neo4jGraphStore | neo4j driver |
| ObjectStore | MinioObjectStore | MinIO S3 SDK |
| LLMProvider | ClaudeLLMProvider | Anthropic / OpenAI / DeepSeek 兼容 |
| EmbeddingProvider | BGEM3EmbeddingProvider | sentence-transformers BAAI/bge-m3 |

## 3.3 本体层

```
YAML (ontology/)  ── 唯一源头 ──────────────────────────────────
    │                                                            │
    ↓ load_ontology.py                                           │
    ├──→ Neo4j: 5 类 label 节点 + SUBCLASS_OF 边 + Alias 节点   │  三者 schema
    ├──→ PG lexicon_aliases: surface_form → canonical_node_id    │  均由本体
    └──→ PG governance.ontology_versions: 版本记录               │  定义约束
                                                                 │
    ↓ OntologyRegistry.from_default()                            │
    └──→ 内存: nodes dict + alias_map + relation_ids ────────────┘
         └─ YAMLOntologyProvider 包装，供 Pipeline + Operator 使用
```

### 五层知识模型

| 层 | YAML 文件 | Neo4j 标签 | 节点数 | 语义 |
|----|----------|-----------|--------|------|
| concept | ip_network.yaml | OntologyNode | 74 | 是什么 |
| mechanism | ip_network_mechanisms.yaml | MechanismNode | 24 | 为什么/怎么运作 |
| method | ip_network_methods.yaml | MethodNode | 22 | 怎么做 |
| condition | ip_network_conditions.yaml | ConditionRuleNode | 20 | 何时用/约束 |
| scenario | ip_network_scenarios.yaml | ScenarioPatternNode | 13 | 在什么场景下组合应用 |

## 3.4 治理层

### 置信度评分（ConfidenceScorer）

```
Confidence = 0.30 × source_authority
           + 0.20 × extraction_method
           + 0.20 × ontology_fit
           + 0.20 × cross_source_consistency
           + 0.10 × temporal_validity
```

| 来源等级 | 权重 | 抽取方式 | 权重 |
|----------|------|----------|------|
| S (IETF/3GPP/IEEE) | 1.0 | manual | 1.0 |
| A (Cisco/Huawei) | 0.85 | rule | 0.85 |
| B (白皮书) | 0.65 | llm | 0.70 |
| C (博客/论坛) | 0.40 | | |

### 冲突检测（ConflictDetector）

检测条件：同一 subject + predicate，不同 object → `contradictory_value` 冲突。

### 演化门控（EvolutionGate）

6 项门控全部通过才允许晋升：

| 门控 | 阈值 | 含义 |
|------|------|------|
| source_count | ≥ 3 | 至少 3 篇文档提及 |
| source_diversity | ≥ 0.6 | 来自 3+ 个不同站点 |
| temporal_stability | ≥ 0.7 | 在候选池存活 ≥ 14 天 |
| structural_fit | ≥ 0.65 | 与已有本体的 Jaccard 重叠 |
| composite_score | ≥ 0.65 | 加权综合分 |
| synonym_risk | ≤ 0.4 | 不是已有别名的简单变体 |

自动晋升条件：门控全过 + composite ≥ 0.85 + 候选池 ≥ 7 天。

## 3.5 流水线层

7 个 Stage 实现，通过 `build_pipeline()` 组装为线性流水线。

### 文本预处理（preprocessing/）

| 模块 | 职责 |
|------|------|
| `extractor.py` | ContentExtractor — HTML 正文提取（trafilatura → readability → 正则回退），文档类型检测，质量门控 |
| `normalizer.py` | DocumentNormalizer — 网页样板去噪（cookie/社交/版权 5 类正则）、重复段落删除、Unicode 归一化 |

### 7 阶段概览

| Stage | 名称 | 输入 | 输出 | DB 写入 |
|-------|------|------|------|---------|
| 1 | Ingest/Clean | source_doc_id | cleaned text → MinIO | documents(status→cleaned) |
| 2 | Segment | cleaned text | segments + RST relations | segments, t_rst_relation |
| 3 | Align | segments | ontology tags + candidates | segment_tags, governance.evolution_candidates |
| 3b | Evolve | candidates | scored/promoted candidates | governance.evolution_candidates, Neo4j(auto-accept) |
| 4 | Extract | segments + tags | facts + evidence | facts, evidence |
| 5 | Dedup | facts + segments | merged/conflicted | facts(merge), governance.conflict_records |
| 6 | Index | all above | graph nodes + embeddings | Neo4j, segments(embedding/title_vec/content_vec) |

## 3.6 算子层

15 个 SemanticOperator，通过 OperatorRegistry 注册，Middleware 链拦截（TimingMiddleware + LoggingMiddleware）。

| 类别 | 算子 | 端点 |
|------|------|------|
| 查询解析 | lookup, resolve | GET /lookup, GET /resolve |
| 图遍历 | expand, path, dependency_closure | GET |
| 影响分析 | impact_propagate, filter | POST |
| 证据治理 | evidence_rank, conflict_detect, fact_merge | GET/POST |
| 本体演化 | candidate_discover, attach_score, evolution_gate | GET/POST |
| 语义搜索 | semantic_search, edu_search | POST |

## 3.7 API 层

FastAPI 路由，前缀 `/api/v1/semantic`。所有端点通过 `app.query(op_name, **kwargs)` 分发到 OperatorRegistry。

统一响应格式：
```json
{
  "meta": {"ontology_version": "v0.2.0", "latency_ms": 12},
  "result": { ... }
}
```

---

# 4. 数据库架构

## 4.1 PostgreSQL — 知识库 telecom_kb

### public schema（7 张表）

| 表 | 职责 | 核心字段 |
|----|------|----------|
| documents | 文档元数据 + 状态流转 | source_doc_id, site_key, source_url, source_rank, content_hash, raw_storage_uri, cleaned_storage_uri, status(raw/cleaned/segmented/indexed) |
| segments | 知识片段 + EDU + 向量 | segment_id, source_doc_id, segment_type, raw_text, title, title_vec(1024), content_vec(1024), embedding(1024), content_source, simhash_value, confidence |
| t_rst_relation | RST 语篇关系 | nn_relation_id, relation_type(21种), src_edu_id→segments, dst_edu_id→segments, relation_source(rule/llm) |
| segment_tags | 片段本体标签 | segment_id, tag_type(canonical/semantic_role/context/mechanism_tag/…), ontology_node_id, confidence |
| facts | 三元组知识 | fact_id, subject, predicate, object, confidence, lifecycle_state, merge_cluster_id |
| evidence | 事实溯源 | evidence_id, fact_id, source_doc_id, segment_id, source_rank, extraction_method, exact_span |
| lexicon_aliases | 本体别名镜像 | surface_form, canonical_node_id, alias_type, vendor, language |

### governance schema（4 张表）

| 表 | 职责 |
|----|------|
| governance.evolution_candidates | 候选概念 + 五维评分 + 审核状态 |
| governance.conflict_records | 矛盾事实记录 + 解决状态 |
| governance.review_records | 人工审核操作审计（预留） |
| governance.ontology_versions | 本体版本 + 快照 + 变更差异 |

## 4.2 PostgreSQL — 爬虫库 telecom_crawler

| 表 | 职责 |
|----|------|
| source_registry | 站点注册（site_key, source_rank, seed_urls, rate_limit） |
| crawl_tasks | 爬取任务队列（url, status, retry_count, raw_storage_uri） |
| extraction_jobs | 流水线任务追踪（job_type, source_doc_id, status） |

## 4.3 Neo4j

### 节点标签

| 标签 | 来源 | 数量 |
|------|------|------|
| OntologyNode | 本体 concept 层 | 74 |
| MechanismNode | 本体 mechanism 层 | 24 |
| MethodNode | 本体 method 层 | 22 |
| ConditionRuleNode | 本体 condition 层 | 20 |
| ScenarioPatternNode | 本体 scenario 层 | 13 |
| Alias | 本体别名 | 156 |
| KnowledgeSegment | Stage 6 写入 | 动态增长 |
| SourceDocument | Stage 6 写入 | 动态增长 |
| Fact | Stage 6 写入 | 动态增长 |
| Evidence | Stage 6 写入 | 动态增长 |

### 关系边类型

`SUBCLASS_OF` · `ALIAS_OF` · `RELATED_TO` · `DEPENDS_ON` · `USES` · `REQUIRES` · `IMPACTS` · `CAUSES` · `BELONGS_TO` · `TAGGED_WITH` · `SUPPORTED_BY` · `EXTRACTED_FROM`

## 4.4 MinIO

| Bucket | 内容 | Key 格式 |
|--------|------|----------|
| telecom-kb-raw | 原始文档（HTML/TXT/PDF） | `raw/{sha256}.html` |
| telecom-kb-cleaned | 清洗后纯文本 | `cleaned/{normalized_hash}.txt` |

---

# 5. RST 语篇关系体系

21 种通用 RST 关系类型，按 6 个逻辑类别组织：

| 类别 | 类型 | 语义 |
|------|------|------|
| **因果逻辑** | Cause-Result | A 导致 B（回溯） |
| | Result-Cause | B 是因为 A（叙述方向反） |
| | Purpose | A 是为了 B（前瞻目标） |
| | Means | 通过 B 实现 A（方法路径） |
| **条件/使能** | Condition | 如果 A 则 B |
| | Unless | 除非 A 否则 B |
| | Enablement | A 使 B 成为可能 |
| **展开/细化** | Elaboration | B 对 A 细化展开 |
| | Explanation | B 解释 A 的原理 |
| | Restatement | B 换种方式复述 A |
| | Summary | B 总结 A |
| **对比/让步** | Contrast | A 和 B 形成对比 |
| | Concession | 尽管 A 但 B |
| **证据/评价** | Evidence | B 为 A 提供证据 |
| | Evaluation | B 对 A 做出评价 |
| | Justification | B 为 A 的决策提供理由 |
| **结构/组织** | Background | A 为理解 B 提供背景 |
| | Preparation | A 为 B 做铺垫 |
| | Sequence | A 在 B 之前（时间/逻辑顺序） |
| | Joint | A 和 B 并列同层级 |
| | Problem-Solution | A 提出问题，B 给出解决方案 |

### 判定方式

- **LLM 启用时**：LLM 从 21 种中选择最匹配的类型
- **LLM 关闭时**：37 条规则映射（segment_type pair → RST type），未命中默认 Sequence
- `t_rst_relation.relation_source` 记录判定来源（`llm` / `rule`）

---

# 6. 数据流

## 6.1 文档生命周期

```
外部数据源                     Pipeline                          图谱
────────────                   ────────                          ──────
Spider/导入/上传
  ↓
MinIO(raw/) +
documents(status='raw')
                    ──→ Stage 1: 清洗
                         extract + normalize + quality gate
                         documents(status='cleaned')
                         MinIO(cleaned/)
                    ──→ Stage 2: 切段 + RST
                         segments + t_rst_relation
                         documents(status='segmented')
                    ──→ Stage 3: 本体对齐
                         segment_tags + evolution_candidates
                    ──→ Stage 3b: 演化
                         candidates 评分/晋升
                    ──→ Stage 4: 关系抽取
                         facts + evidence
                    ──→ Stage 5: 去重
                         merge_cluster + conflict_records
                    ──→ Stage 6: 索引
                         Neo4j 节点/边 + 向量嵌入
                         documents(status='indexed')
                                                       ──→ 语义算子 API 查询
```

## 6.2 文档状态流转

```
raw → cleaned → segmented → indexed
 │       │
 │       └→ low_quality（质量不达标）
 └→ deduped（内容哈希重复）
```

---

# 7. 部署架构

## 7.1 本地开发模式

```bash
python run_dev.py
```

- SQLite `:memory:` 替代 PostgreSQL（fake_postgres + fake_crawler_postgres）
- dict 替代 Neo4j（fake_neo4j）
- 从 YAML 本体自动 seed
- 无需任何外部服务

## 7.2 生产模式

| 服务 | 用途 |
|------|------|
| PostgreSQL (telecom_kb) | 知识 + 治理数据 |
| PostgreSQL (telecom_crawler) | 爬虫调度（可与知识库同实例不同 database） |
| Neo4j | 本体图 + 知识图谱 |
| MinIO | 原始/清洗文档 |
| FastAPI (uvicorn) | REST API 服务 |
| worker.py | 后台爬取 + Pipeline 调度 |
| BAAI/bge-m3 | 本地向量模型（可选，需 EMBEDDING_ENABLED=true） |