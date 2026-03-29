# semcore 重构计划

> 版本：v0.1
> 日期：2026-03-25
> 前提：semcore 框架已完成（`semcore/semcore/`），现将 `src/` 接入框架

---

## 1. 重构目标

将现有 `src/` 中所有业务模块声明为 `semcore` 各 ABC 的具体实现，
最终通过 `SemanticApp` 统一组合，实现：

- Provider 可替换（换 LLM / 换数据库 / 换 Embedding 无需改业务代码）
- Pipeline 可组合（6 阶段可插拔、可条件路由）
- Operator 可注册（13 个算子统一由 OperatorRegistry 分发）
- Governance 可插拔（置信度模型 / 冲突检测 / 演化门控可替换）

**不重写业务逻辑**：所有现有算法、SQL、Cypher 保持不变，只做适配层包装。

---

## 2. 变更全景

### 2.1 新增文件（适配层）

```
src/
  providers/
    __init__.py
    postgres_store.py      ← PostgresRelationalStore(RelationalStore)
    neo4j_store.py         ← Neo4jGraphStore(GraphStore)
    anthropic_llm.py       ← ClaudeLLMProvider(LLMProvider)
    bge_m3_embedding.py    ← BGEM3EmbeddingProvider(EmbeddingProvider)
    minio_store.py         ← MinioObjectStore(ObjectStore)

  ontology/
    yaml_provider.py       ← YAMLOntologyProvider(OntologyProvider)
                              [薄包装 OntologyRegistry]

  governance/
    __init__.py
    confidence_scorer.py   ← TelecomConfidenceScorer(ConfidenceScorer)
    conflict_detector.py   ← TelecomConflictDetector(ConflictDetector)
    evolution_gate.py      ← TelecomEvolutionGate(EvolutionGate)

  operators/
    __init__.py
    lookup_op.py           ← LookupOperator(SemanticOperator)
    resolve_op.py          ← ResolveOperator
    expand_op.py           ← ExpandOperator
    filter_op.py           ← FilterOperator
    path_op.py             ← PathOperator
    dependency_op.py       ← DependencyOperator
    impact_op.py           ← ImpactOperator
    evidence_op.py         ← EvidenceRankOperator
    conflict_op.py         ← ConflictDetectOperator
    fact_merge_op.py       ← FactMergeOperator
    candidate_op.py        ← CandidateDiscoverOperator
    attach_score_op.py     ← AttachScoreOperator
    evolution_gate_op.py   ← EvolutionGateOperator
    semantic_search_op.py  ← SemanticSearchOperator
    edu_search_op.py       ← EduSearchOperator

  pipeline/
    pipeline_factory.py    ← build_pipeline() 工厂函数，含条件路由

  app_factory.py           ← build_app(settings) → SemanticApp
```

### 2.2 修改文件（签名适配）

| 文件 | 改动 | 影响范围 |
|------|------|----------|
| `pipeline/stages/stage1_ingest.py` | `IngestStage` 实现 `Stage` ABC，`process(ctx, app)` | 仅签名 |
| `pipeline/stages/stage2_segment.py` | 同上 | 仅签名 |
| `pipeline/stages/stage3_align.py` | 同上，从 `app.ontology` 取 provider | 签名 + OntologyProvider |
| `pipeline/stages/stage4_extract.py` | 同上，从 `app.llm` 取 provider | 签名 + LLMProvider |
| `pipeline/stages/stage5_dedup.py` | 同上 | 仅签名 |
| `pipeline/stages/stage6_index.py` | 同上，从 `app.graph/embedding` 取 | 签名 + 多 provider |
| `api/semantic/router.py` | 用 `app.query(op_name, **kwargs)` 替换直接 import | 全部端点 |
| `app.py` | 用 `app_factory.build_app()` 构造 `SemanticApp`，mount router | 启动逻辑 |

### 2.3 保持不变（内部实现）

```
src/utils/confidence.py    ← 被 TelecomConfidenceScorer 调用
src/utils/text.py          ← 被各 Stage 调用
src/utils/hashing.py       ← 被各 Stage 调用
src/utils/llm_extract.py   ← 被 ClaudeLLMProvider 和 Stage 调用
src/utils/embedding.py     ← 被 BGEM3EmbeddingProvider 调用
src/db/postgres.py         ← 被 PostgresRelationalStore 调用
src/db/neo4j_client.py     ← 被 Neo4jGraphStore 调用
src/ontology/registry.py   ← 被 YAMLOntologyProvider 包装
src/ontology/validator.py  ← 保持不变
src/api/semantic/lookup.py 等 ← 被 XxxOperator 调用，函数本身不变
scripts/*                  ← 保持不变
ontology/*.yaml            ← 保持不变
```

---

## 3. 各层详细设计

### 3.1 Provider 层

#### PostgresRelationalStore
```python
class PostgresRelationalStore(RelationalStore):
    # 委托给 src/db/postgres.py 的模块级函数
    def fetchone(self, sql, params=None): return pg.fetchone(sql, params)
    def fetchall(self, sql, params=None): return pg.fetchall(sql, params)
    def execute(self, sql, params=None):  return pg.execute(sql, params)
    @contextmanager
    def transaction(self): yield from pg.get_conn().__enter__().cursor()
```

#### Neo4jGraphStore
```python
class Neo4jGraphStore(GraphStore):
    def write(self, query, **params): neo4j.run_write(query, **params)
    def read(self,  query, **params): return neo4j.run_query(query, **params)
```

#### ClaudeLLMProvider
```python
class ClaudeLLMProvider(LLMProvider):
    # 包装 LLMExtractor，适配两个抽象方法
    def complete(self, prompt, *, system="", max_tokens=512) -> str: ...
    def extract_structured(self, text, output_schema, *, system="") -> dict: ...
    # 保留原有扩展方法供 Stage 直接调用（非 ABC 部分）
    def extract_triples(...): ...
    def extract_rst_relations(...): ...
    def generate_title(...): ...
```

#### BGEM3EmbeddingProvider
```python
class BGEM3EmbeddingProvider(EmbeddingProvider):
    def encode(self, texts) -> list[list[float]]: return get_embeddings(texts) or []
    def dimension(self) -> int: return 1024
```

#### MinioObjectStore
```python
class MinioObjectStore(ObjectStore):
    # 当前 Stage1 是 stub，这里先实现为本地文件系统存储
    # MinIO 真实对接留后续实现
    def put(self, key, data, *, content_type="..."): ...
    def get(self, uri) -> bytes: ...
    def exists(self, uri) -> bool: ...
```

---

### 3.2 Ontology 层

#### YAMLOntologyProvider
```python
class YAMLOntologyProvider(OntologyProvider):
    def __init__(self, registry: OntologyRegistry): self._reg = registry
    def get_node(self, node_id): return self._reg.get_node(node_id)
    def get_layer_nodes(self, layer): return self._reg.get_layer_nodes(layer.value)
    def get_all_nodes(self): return list(self._reg.nodes.values())
    def get_relations(self): return [...]  # 从 _reg.relation_ids 构造 RelationDef
    def resolve_alias(self, surface, *, lang="en", domain=None):
        nid = self._reg.lookup_alias(surface)
        return self._reg.get_node(nid) if nid else None
    def version(self): return settings.ONTOLOGY_VERSION
```

---

### 3.3 Governance 层

#### TelecomConfidenceScorer
```python
class TelecomConfidenceScorer(ConfidenceScorer):
    def score(self, fact: Fact, context: dict) -> ConfidenceScore:
        # 调用 src/utils/confidence.py 的 score_fact()
        total = confidence.score_fact(
            source_rank=context.get("source_rank", "C"),
            extraction_method=context.get("extraction_method", "rule"),
            ontology_fit=context.get("ontology_fit", 0.5),
            cross_source_consistency=context.get("cross_source_consistency", 0.5),
            temporal_validity=context.get("temporal_validity", 1.0),
        )
        return ConfidenceScore(...)  # 分解回五维
```

#### TelecomConflictDetector
```python
class TelecomConflictDetector(ConflictDetector):
    # 从 stage5_dedup.py 的 process_facts() 中提取冲突检测逻辑
    def detect(self, fact: Fact, store: RelationalStore) -> list[Conflict]: ...
```

#### TelecomEvolutionGate
```python
class TelecomEvolutionGate(EvolutionGate):
    GATES = [
        "source_count", "source_diversity", "temporal_stability",
        "structural_fit", "composite_score", "synonym_risk"
    ]
    def evaluate(self, candidate, store) -> GateResult:
        # 调用 src/api/semantic/evolution.py 的门控逻辑
        ...
```

---

### 3.4 Pipeline 层

#### Stage 签名适配模式

所有 6 个 Stage 统一改为：

```python
class IngestStage(Stage):
    name = "ingest"

    def process(self, ctx: PipelineContext, app: SemanticApp) -> PipelineContext:
        # 原 process(crawl_task_id) 的逻辑迁入
        # 从 ctx.meta["crawl_task_id"] 取参数
        # 使用 app.store / app.objects 替代直接调用 postgres.py
        crawl_task_id = ctx.meta["crawl_task_id"]
        ...
        ctx.doc = Document(...)
        return ctx
```

各 Stage 获取依赖的方式：

| Stage | 从 app 取什么 |
|-------|--------------|
| Stage1 | `app.store`, `app.objects` |
| Stage2 | `app.store`, `app.llm`（ClaudeLLMProvider 扩展方法） |
| Stage3 | `app.store`, `app.ontology` |
| Stage4 | `app.store`, `app.ontology`, `app.llm` |
| Stage5 | `app.store` |
| Stage6 | `app.store`, `app.graph`, `app.embedding` |

#### 条件路由 Pipeline

```python
# src/pipeline/pipeline_factory.py
def build_pipeline() -> Pipeline:
    return (
        Pipeline()
        .add_stage(IngestStage())
        .switch(
            key=lambda ctx, _: (ctx.doc.doc_type if ctx.doc else "unknown"),
            branches={
                "rfc":     RFCSegmentStage(),    # 未来实现，预留接口
                "cli":     CLISegmentStage(),     # 未来实现，预留接口
            },
            default=SegmentStage(),              # 当前默认实现
        )
        .add_stage(AlignStage())
        .add_stage(ExtractStage())
        .add_stage(DedupStage())
        .add_stage(IndexStage())
    )
```

当前 rfc/cli 分支用 `DefaultSegmentStage`（复用 SegmentStage），
待未来实现专用 Stage 时只需替换分支，不改主流程。

---

### 3.5 Operator 层

每个算子的适配模式（以 lookup 为例）：

```python
# src/operators/lookup_op.py
from src.api.semantic import lookup as _lookup   # 现有实现函数不变

class LookupOperator(SemanticOperator):
    name = "lookup"

    def execute(self, app: SemanticApp, **kwargs) -> OperatorResult:
        data = _lookup.lookup(
            kwargs["term"],
            kwargs.get("scope"),
            kwargs.get("lang", "en"),
            kwargs.get("ontology_version"),
            kwargs.get("include_evidence", False),
            kwargs.get("max_evidence", 3),
        )
        return OperatorResult(
            data=data,
            ontology_version=app.ontology.version(),
        )
```

#### Router 简化

`router.py` 所有端点统一简化为：

```python
# 改造前（以 lookup 为例）
@router.get("/lookup")
def lookup(term: str = Query(...), ...):
    t0 = time.monotonic()
    try:
        return _wrap(_lookup.lookup(term, ...), t0)
    except Exception as exc:
        return _err(str(exc))

# 改造后
@router.get("/lookup")
def lookup(term: str = Query(...), ..., _app: SemanticApp = Depends(get_app)):
    result = _app.query("lookup", term=term, ...)
    return {"meta": {"ontology_version": result.ontology_version,
                     "latency_ms": result.latency_ms},
            "result": result.data}
```

耗时、日志、错误处理全部由 `TimingMiddleware` + `LoggingMiddleware` 统一处理，
router 只做 HTTP 参数解析 → 调用 → 格式化响应。

---

### 3.6 App 工厂

```python
# src/app_factory.py
from semcore import AppConfig, SemanticApp
from semcore.operators.base import TimingMiddleware, LoggingMiddleware

def build_app() -> SemanticApp:
    from src.config.settings import settings
    from src.providers.postgres_store   import PostgresRelationalStore
    from src.providers.neo4j_store      import Neo4jGraphStore
    from src.providers.anthropic_llm    import ClaudeLLMProvider
    from src.providers.bge_m3_embedding import BGEM3EmbeddingProvider
    from src.providers.minio_store      import MinioObjectStore
    from src.ontology.yaml_provider     import YAMLOntologyProvider
    from src.ontology.registry          import OntologyRegistry
    from src.governance.confidence_scorer import TelecomConfidenceScorer
    from src.governance.conflict_detector import TelecomConflictDetector
    from src.governance.evolution_gate    import TelecomEvolutionGate
    from src.pipeline.pipeline_factory    import build_pipeline
    from src.operators import ALL_OPERATORS   # list of all operator instances

    registry = OntologyRegistry.from_default()

    config = AppConfig(
        llm       = ClaudeLLMProvider(settings),
        embedding = BGEM3EmbeddingProvider(settings),
        graph     = Neo4jGraphStore(),
        store     = PostgresRelationalStore(),
        objects   = MinioObjectStore(settings),
        ontology  = YAMLOntologyProvider(registry),
        confidence_scorer = TelecomConfidenceScorer(),
        conflict_detector = TelecomConflictDetector(),
        evolution_gate    = TelecomEvolutionGate(),
        operators   = ALL_OPERATORS,
        middlewares = [TimingMiddleware(), LoggingMiddleware()],
    )
    config.pipeline = build_pipeline()
    return SemanticApp(config)
```

---

## 4. 依赖关系变化

```
重构前：
  app.py → router.py → lookup.py/... → postgres.py/neo4j_client.py
  pipeline_runner → stage1/2/3/4/5/6 → postgres.py/neo4j_client.py

重构后：
  app.py → app_factory.build_app() → SemanticApp
    ├── app.query("lookup") → OperatorRegistry → LookupOperator → lookup.py
    ├── app.ingest(id)      → Pipeline → IngestStage → app.store/app.graph
    └── app.store           → PostgresRelationalStore → postgres.py
```

---

## 5. 实施顺序（由内向外）

| 步骤 | 内容 | 理由 |
|------|------|------|
| 1 | `src/providers/` — 5 个 Provider 包装类 | 其他所有层依赖 Provider，先建底座 |
| 2 | `src/ontology/yaml_provider.py` | Stage3/4 和 Operator 都需要 |
| 3 | `src/governance/` — 3 个 Governance 类 | 不依赖其他层，独立实现 |
| 4 | `src/operators/` — 15 个 Operator 类 | 包装现有函数，验证 registry 可用 |
| 5 | `src/pipeline/stages/` — 6 个 Stage 适配 | 最复杂，留到 Provider 稳定后 |
| 6 | `src/pipeline/pipeline_factory.py` | 组装 Pipeline |
| 7 | `src/app_factory.py` | 最终组合 |
| 8 | `src/api/semantic/router.py` | 切换到 registry，删除手动路由 |
| 9 | `src/app.py` | 用 `build_app()` 替换旧启动逻辑 |

---

## 6. 不做的事

- 不重写现有算法（Cypher、SQL、正则）
- 不修改 `ontology/*.yaml` 和 `scripts/`
- 不引入新的外部依赖
- ObjectStore 的 MinIO 真实实现推后（先用本地 FS stub 通过接口验证）
- 条件路由的 RFC/CLI 专用 Stage 推后（先用 default 占位）
