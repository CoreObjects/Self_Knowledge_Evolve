# Telecom Semantic Knowledge Base

面向网络通信领域的可治理、可演化、带溯源的语义知识操作系统。

将公开文档（RFC、厂商手册、技术白皮书等）转化为结构化、可计算的知识对象，通过领域本体组织，经多模存储持久化，由语义算子 API 对外服务，为 Agent 提供结构化知识上下文。

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **本体锚定的知识组织** | 5 层领域本体（概念/机制/方法/条件/场景），153 节点 + 54 种关系 + 156 别名 + 104 种子关系 |
| **持续爬取 + 链接发现** | Spider 自动从页面提取同站链接，滚雪球式持续爬取，Pipeline 并行处理 |
| **7 阶段处理流水线** | 清洗 → 语义切段 → 本体对齐 → 演化 → LLM 抽取 → 去重 → 索引 |
| **21 种 RST 语篇关系** | 6 大类通用修辞结构关系，LLM 判定 + 规则回退 |
| **多模存储** | PostgreSQL（知识+治理）、Neo4j（动态边类型图谱）、pgvector（向量）、MinIO（文档） |
| **21 个语义算子** | 查询、图遍历、影响分析、语义搜索、质量评估、Agent 上下文组装 |
| **受控演化** | 概念+关系候选自动发现 → 评分 → 门控 → 审批 → YAML 写入 → Git 版本管理 → 增量回填 |
| **候选合并** | 自动去重（括号缩写归一化）+ 手动合并 + LLM 同义判断 |
| **本体质量评估** | 5 维 20 指标（粒度/正交性/层间连通/可发现性/结构健康）|
| **系统监控看板** | 3 标签页（Monitor / Ontology Quality / Review），自动刷新 |

### 首版领域范围：IP 数通网络

Ethernet · VLAN · STP · LACP · OSPF · IS-IS · BGP · MPLS · SR-MPLS · SRv6 · EVPN · VXLAN · L3VPN · VRF · QoS · ACL · NAT · BFD · NETCONF · YANG

---

## 系统逻辑架构

```
┌─ 上层入口 ──────────────────────────────────────────────────────────────────┐
│  FastAPI REST API                        worker.py                          │
│    ├─ /api/v1/semantic/*  (21 算子)        └─ 爬取(链接发现) + Pipeline      │
│    ├─ /api/v1/system/*    (监控+审批+合并)                                  │
│    └─ /dashboard          (3 标签页看板)                                    │
│         ↓                                      ↓                            │
│  ┌─ SemanticApp ──────────────────────────────────────────────────────────┐ │
│  │  app.query(op_name)          app.ingest(source_doc_id)                 │ │
│  │       ↓                           ↓                                    │ │
│  │  OperatorRegistry (21)       Pipeline (7 stages)                       │ │
│  │  + Middleware 链              linear / branch / switch                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ 领域实现层 ──────────────────────────────────────────────────────────────────┐
│                                                                               │
│  ┌─ 本体层（统一语义骨架）──────────────────────────────────────────────────┐ │
│  │  YAML (ontology/) ── 唯一源头，Git 版本管理                              │ │
│  │    domains/    → 153 节点（5 层）+ 演化节点 (ip_network_evolved.yaml)    │ │
│  │    seeds/      → 104 种子关系 + 3 分类修正                               │ │
│  │    patterns/   → 语义角色 + 上下文信号 + 谓语信号（外部化正则）          │ │
│  │    lexicon/    → 别名（持续增长）                                        │ │
│  │    top/        → 关系类型（持续增长）                                    │ │
│  │       ↓ load_ontology.py + OntologyRegistry                              │ │
│  │  Neo4j（动态边类型） · PG lexicon_aliases · 内存 alias_map               │ │
│  │  本体统一三个存储系统的 schema                                           │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─ 治理层 ────────────────┐  ┌─ 流水线层 ──────────────────────────────┐   │
│  │ ConfidenceScorer        │  │ preprocessing/                          │   │
│  │   5 维置信度加权         │  │   extractor + normalizer                │   │
│  │ ConflictDetector        │  │ stages/                                 │   │
│  │ EvolutionGate           │  │   1.清洗 → 2.语义切段+RST → 3.对齐     │   │
│  │   6 项门控              │  │   → 3b.演化 → 4.LLM抽取 → 5.去重      │   │
│  │ Review + Merge          │  │   → 6.索引                              │   │
│  │ BackfillWorker          │  │ 链接发现 → 持续爬取                     │   │
│  └─────────────────────────┘  └─────────────────────────────────────────┘   │
│                                                                               │
│  ┌─ 算子层 (21 个 SemanticOperator) ──────────────────────────────────────┐ │
│  │ 查询: lookup · resolve · expand · filter · path · dependency_closure    │ │
│  │ 分析: impact_propagate · evidence_rank · conflict_detect · fact_merge   │ │
│  │ 演化: candidate_discover · attach_score · evolution_gate                │ │
│  │ 搜索: semantic_search · edu_search                                      │ │
│  │ 检查: graph_inspect · cross_layer_check · ontology_inspect              │ │
│  │       stale_knowledge · ontology_quality                                │ │
│  │ Agent: context_assemble (完整上下文包)                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─ 监控层 ──────────────────────────────────────────────────────────────┐  │
│  │ StatsCollector (7 类) · StatsScheduler (5 min)                         │ │
│  │ OntologyQualityCalculator (5 维 20 指标)                               │ │
│  │ Drilldown (21 指标 → 算子) · Review + Merge + LLM 同义判断             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘

┌─ semcore 框架层（零外部依赖 ABCs）────────────────────────────────────────────┐
│  providers/base · ontology/base · governance/base · operators/base             │
│  pipeline/base · core/types · core/context · app.py                           │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 基础设施层 ─────────────────────────────────────────────────────────────────┐
│  PG telecom_kb (public + governance)  Neo4j (动态边)  MinIO (raw+cleaned)    │
│  PG telecom_crawler                   BAAI/bge-m3     DeepSeek LLM           │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 外部数据源（Pipeline 之外）─────────────────────────────────────────────────┐
│  Spider 爬虫(链接发现) · 文件导入 · API 上传 → MinIO + documents(raw)        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 一键启动（生产模式）

```bash
python scripts/reset_and_run.py
# 杀进程 → 清缓存 → 清数据 → 验证空 → 加载本体 → 启动 Worker → 启动 API
# Dashboard: http://localhost:8000/dashboard
```

### 本地开发（无需 Docker）

```bash
python run_dev.py
# SQLite + dict 替代，零外部依赖
# http://127.0.0.1:8000/docs
```

### 手动步骤

```bash
cp .env.example .env                          # 配置连接
psql -d telecom_kb -f scripts/init_postgres.sql
psql -d telecom_crawler -f scripts/init_crawler_postgres.sql
python scripts/init_neo4j.py
python scripts/load_ontology.py               # 153 节点 + 104 种子
uvicorn src.app:app --host 0.0.0.0 --port 8000
python worker.py                              # 爬取 + Pipeline
```

---

## 流水线

```
documents(raw) + MinIO
    ↓ Stage 1 — 清洗 (trafilatura/readability, 质量门控, doc_type)
    ↓ Stage 2 — 语义切段 (段落→句子→滑窗三级切分) + RST (21种)
    ↓ Stage 3 — 对齐 (alias matching + LLM 候选概念发现)
    ↓ Stage 3b — 演化 (五维评分 + 六项门控)
    ↓ Stage 4 — LLM 抽取 (→ merged context retry → 共现兜底, 无正则)
    ↓               未知 predicate → 候选关系池
    ↓ Stage 5 — 去重 (SimHash + 冲突检测)
    ↓ Stage 6 — 索引 (Neo4j 动态边类型, 无重复, 向量嵌入)
    ↓
    爬虫链接发现 → 新 URL 入队 → 持续循环
```

---

## 21 个语义算子

| 分类 | 算子 | 端点 |
|------|------|------|
| 查询 | lookup, resolve | GET |
| 图遍历 | expand, path, dependency_closure | GET |
| 影响 | impact_propagate, filter | POST |
| 证据 | evidence_rank, conflict_detect, fact_merge | GET/POST |
| 演化 | candidate_discover, attach_score, evolution_gate | GET/POST |
| 搜索 | semantic_search, edu_search | POST |
| 检查 | graph_inspect, cross_layer_check, ontology_inspect, stale_knowledge, ontology_quality | GET |
| Agent | **context_assemble** — 完整上下文包(推理链+段落原文+溯源) | POST |

---

## 本体演化闭环

```
Pipeline 发现候选 (concept + relation)
    ↓
Dashboard Review 页面
    ├─ View Sources — 查看关联原文
    ├─ Ask LLM — 同义判断
    ├─ Merge — 合并相似候选
    ├─ Approve → Neo4j + PG + YAML + Git commit + BackfillWorker
    └─ Reject → 标记拒绝
    ↓
后续 Pipeline 自动关联新节点
```

---

## 本体质量评估（5 维 20 指标）

| 维度 | 指标 |
|------|------|
| 粒度 | Gini 系数、超级节点、孤立率、标签密度、万金油 |
| 正交性 | 谓语共现 Jaccard、分布偏度、集中度、利用率 |
| 层间 | 覆盖率、短路率、完整路径数 |
| 可发现性 | 别名覆盖、关系利用、标签命中 |
| 结构 | 联通性、依赖环、最短路径 |

Dashboard Ontology Quality 标签页自动刷新雷达图 + 分层指标。

---

## 设计文档

| 文档 | 内容 |
|------|------|
| `docs/architecture-design-20260404.md` | 完整架构设计 |
| `docs/development-spec-20260404.md` | 完整开发方案 |
| `docs/architecture-decisions.md` | ADR 决策记录 (ADR-001 ~ ADR-010) |
| `docs/ontology-quality-framework.md` | 本体质量评价理论框架 |
| `docs/stats-monitoring-design.md` | 监控模块设计 |
| `docs/candidate-discovery-redesign.md` | LLM 候选发现设计 |
| `docs/candidate-review-design.md` | 审批 + 增量回填设计 |
| `docs/candidate-merge-design.md` | 候选合并设计 |
| `docs/ontology-versioning-design.md` | 版本管理设计 |
| `docs/pattern-externalization-design.md` | 正则外部化设计 |
| `docs/segmentation-and-extraction-refactor.md` | 切段 + 抽取重构 |

---

## 来源等级

| 等级 | 来源 | 权重 |
|------|------|------|
| **S** | IETF, 3GPP, ITU-T, IEEE | 1.0 |
| **A** | Cisco, Huawei, Juniper, Nokia | 0.85 |
| **B** | 白皮书, 教程 | 0.65 |
| **C** | 博客, 论坛 | 0.40 |

置信度：`0.30×source_authority + 0.20×extraction_method + 0.20×ontology_fit + 0.20×cross_source + 0.10×temporal`

---

## License

本项目用于研究和内部知识工程目的。所有爬取内容版权归原作者所有。