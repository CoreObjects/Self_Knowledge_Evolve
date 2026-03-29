# Architecture Decision Records

记录项目关键设计决策，供后续开发参考。

---

## ADR-001 本体模型的工程承载主体

**决策**：YAML 是本体的唯一源头，Neo4j 是运行时投影，PostgreSQL 负责治理。

**三层分工**：
```
YAML 文件 (ontology/)          → 源头，人工可读可编辑，版本控制跟踪
  ↓ scripts/load_ontology.py
Neo4j (OntologyNode / edges)   → 运行时，支撑图遍历算子
PostgreSQL (ontology_versions) → 治理，记录版本历史和审核状态
```

**为什么不用 Neo4j 直接定义 schema**：Neo4j 是 schema-less 图数据库，没有强制的类型系统；用 YAML 作 source of truth 可以让本体修改走 Git 审查流程，而不是直接改数据库。

---

## ADR-002 pgvector 当前未启用

**决策**：pgvector 暂不引入，当前所有语义查询通过 Neo4j 图遍历 + PostgreSQL 精确匹配完成。

**原因**：
- 现阶段知识库冷启动，数据量不足以支撑向量检索的精度优势
- 引入 embedding 需要额外的模型服务，增加运维复杂度
- 当前的精确匹配 + 图遍历已能覆盖核心业务场景

**未来接入点**（需要时再做）：
- `lookup` 算子加模糊语义查询兜底
- `stage3_align` 软对齐（精确未命中 → 向量相似度补充）
- `attach_score` 用向量相似度替代 Jaccard 关键词重叠

---

## ADR-003 Embedding 模型选型预研结论

**推荐模型**：`BAAI/bge-m3`

| 维度 | 评估 |
|------|------|
| 中英双语 | 强，专为中英混合训练 |
| 技术领域文本 | 学术/技术 benchmark 表现好 |
| 本地部署 | 支持，模型文件约 2.3GB |
| 内存需求 | ~3GB RAM（CPU 推理） |
| 费用 | 免费开源 |

**备选**：
- 内存受限 → `paraphrase-multilingual-MiniLM-L12-v2`（500MB，精度略低）
- 不想维护本地模型 → OpenAI `text-embedding-3-small`（加 `OPENAI_API_KEY` 即可）

**建议架构**：embedding 服务独立为一个 Docker 容器，对外暴露 `POST /embed`，主服务通过 HTTP 调用，解耦模型版本。

---

## ADR-004 系统定位与适用场景

**定位**：有治理能力、可演化、带溯源的电信领域结构化知识基础设施
- 不是 RAG，不是搜索引擎
- 核心价值在于知识的**可治理性、可溯源性、可演化性**

**真正有竞争力的场景**：

1. **跨厂商术语归一化** — 华为/思科/中兴同一概念统一到 canonical node，`resolve()` 算子直接支持
2. **故障影响链路推导** — `impact_propagate()` 沿 CAUSES/IMPACTS 边 BFS，给 NOC 提供机器可读的影响面
3. **依赖闭包分析** — `dependency_closure()` 用于变更前影响面评估
4. **知识溯源与置信度** — 每条 Fact 附带 source_authority + 5维置信度公式，区别于所有 RAG 系统
5. **本体防漂移** — `evolution_gate()` 六项门控，候选术语必须经过人工审核才进核心本体

**不适合的场景**：
- 一次性问答（直接用 LLM 更快）
- 通用知识（没有领域本体就没有优势）
- 文档量极少（图稀疏时算子无意义）

---

## ADR-005 Stage 4 抽取的已知局限

**当前实现**：15 条正则模式匹配关系抽取

**局限**：
- 只能抽取文本中明确出现 pattern 的关系，复杂语义关系漏掉
- 召回率有限，适合规范技术文档（RFC、配置指南），不适合叙述性文章

**后续改进方向**：接入 LLM 做关系抽取（传入段落 + 候选关系类型 → 结构化输出），正则作为快速通道保留。

---

## ADR-006 知识冷启动策略

**问题**：图谱节点稀疏时，图遍历算子（expand、path、impact）价值有限。

**建议优先级**：
1. 先跑 `scripts/load_ontology.py` 把 YAML 本体全量加载进 Neo4j（骨架）
2. 选 2-3 个核心子域（如 IP 路由、MPLS）的高质量文档（RFC + 主流厂商白皮书）跑完整 pipeline
3. 验证 `lookup` / `expand` / `path_infer` 三个算子有合理返回后，再扩大数据规模
