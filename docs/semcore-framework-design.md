# semcore 框架设计文档

> 版本：v0.2
> 日期：2026-03-25
> 状态：决策已确认，进入实现

---

## 1. 设计目标

你的电信知识库工程有一个可复用的内核：**治理优先的语义知识流水线**。`semcore` 的目标是把这个内核抽象成框架，让电信域成为第一个实例，未来金融、医疗、法律等域可以用同一套框架落地，只换域相关的实现。

核心差异化：不是 RAG 框架，而是**知识基础设施框架**——治理、溯源、本体演化是一等公民。

---

## 2. 整体层次

```
┌──────────────────────────────────────────────────────────────┐
│  L5  Application Layer                                       │
│       REST API / CLI / SDK                                   │
├──────────────────────────────────────────────────────────────┤
│  L4  Operator Layer                                          │
│       13 个语义算子（lookup / expand / impact / ...）          │
│       可注册、可扩展的算子注册表                                 │
├──────────────────────────────────────────────────────────────┤
│  L3  Governance Layer          ← semcore 核心差异化            │
│       ConfidenceScorer / ConflictDetector / EvolutionGate    │
├──────────────────────────────────────────────────────────────┤
│  L2  Knowledge Layer                                         │
│       Ontology（5层节点）/ Fact / EDU / RSTRelation           │
│       OntologyProvider（YAML→运行时）                          │
├──────────────────────────────────────────────────────────────┤
│  L1  Pipeline Layer                                          │
│       Stage ABC → PipelineContext → Pipeline                 │
│       6 个内置阶段（可替换、可插拔）                             │
├──────────────────────────────────────────────────────────────┤
│  L0  Provider Layer                                          │
│       LLMProvider / EmbeddingProvider / GraphStore /         │
│       RelationalStore / ObjectStore（全部 ABC，无依赖）         │
└──────────────────────────────────────────────────────────────┘
```

规则：**上层依赖下层接口，不依赖下层实现**。`semcore` 包本身零外部依赖（只用标准库 + `abc` + `dataclasses`）。

---

## 3. 包结构

```
semcore/                        ← 框架包（无外部依赖）
  core/
    types.py                    ← 所有领域数据类型（dataclass）
    context.py                  ← PipelineContext
  providers/
    base.py                     ← LLMProvider, EmbeddingProvider,
                                   GraphStore, RelationalStore, ObjectStore
  pipeline/
    base.py                     ← Stage ABC, Pipeline, StageRegistry
  operators/
    base.py                     ← SemanticOperator ABC, OperatorResult,
                                   OperatorRegistry
  governance/
    base.py                     ← ConfidenceScorer, ConflictDetector,
                                   EvolutionGate ABCs
  ontology/
    base.py                     ← OntologyProvider ABC
  app.py                        ← SemanticApp（组合根）+ AppConfig

src/                            ← 电信域实现（依赖 semcore 接口）
  providers/                    ← AnthropicLLM, BGE_M3Embedding,
                                   Neo4jGraphStore, PostgresStore
  pipeline/stages/              ← Stage1–6（实现 Stage ABC）
  api/semantic/                 ← 13 算子（实现 SemanticOperator ABC）
  ontology/                     ← YAMLOntologyProvider
  governance/                   ← TelecomConfidenceScorer,
                                   TelecomEvolutionGate
```

---

## 4. 核心类型（`core/types.py`）

| 类型 | 说明 |
|------|------|
| `KnowledgeLayer` | Enum：concept / mechanism / method / condition / scenario |
| `OntologyNode` | node_id, label, layer, aliases, attributes |
| `RelationDef` | id, label, domain_layer, range_layer, is_symmetric |
| `Document` | source_doc_id, url, site_key, source_rank, raw_text, doc_type |
| `Segment / EDU` | segment_id, source_doc_id, raw_text, segment_type, token_count |
| `Tag` | segment_id, ontology_node_id, tag_type, confidence |
| `ConfidenceScore` | source_authority, extraction_method, ontology_fit, cross_source_consistency, temporal_validity → `total()` |
| `Fact` | fact_id, subject, predicate, object, confidence: ConfidenceScore, domain |
| `Evidence` | evidence_id, fact_id, segment_id, exact_span, source_rank |
| `RSTRelation` | relation_id, src_edu_id, dst_edu_id, relation_type, source |
| `EvolutionCandidate` | candidate_id, surface_forms, composite_score, review_status |

---

## 5. Provider 接口（`providers/base.py`）

```python
class LLMProvider(ABC):
    def complete(self, prompt: str, system: str, max_tokens: int) -> str: ...
    def extract_structured(self, text: str, output_schema: dict) -> dict: ...

class EmbeddingProvider(ABC):
    def encode(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...

class GraphStore(ABC):
    def write(self, query: str, **params) -> None: ...
    def read(self, query: str, **params) -> list[dict]: ...

class RelationalStore(ABC):
    def fetchone(self, sql: str, params) -> dict | None: ...
    def fetchall(self, sql: str, params) -> list[dict]: ...
    def execute(self, sql: str, params) -> None: ...
    def transaction(self) -> ContextManager: ...   # yields cursor

class ObjectStore(ABC):
    def put(self, key: str, data: bytes) -> str: ...   # returns uri
    def get(self, uri: str) -> bytes: ...
```

接口只规定行为契约，不规定实现。Neo4j / PostgreSQL / MinIO / 任意替代品均可。

---

## 6. Pipeline 接口（`pipeline/base.py`）

### PipelineContext

在阶段间流动的有类型数据包，每个 Stage 读取、填充、传递。

```python
@dataclass
class PipelineContext:
    source_doc_id: str
    doc:           Document | None       = None
    segments:      list[Segment]         = field(default_factory=list)
    tags:          list[Tag]             = field(default_factory=list)
    facts:         list[Fact]            = field(default_factory=list)
    evidence:      list[Evidence]        = field(default_factory=list)
    rst_relations: list[RSTRelation]     = field(default_factory=list)
    meta:          dict                  = field(default_factory=dict)  # 阶段自定义
    errors:        list[str]             = field(default_factory=list)  # 非致命错误
```

### Stage ABC

```python
class Stage(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def process(self, ctx: PipelineContext, app: "SemanticApp") -> PipelineContext: ...

    def can_skip(self, ctx: PipelineContext) -> bool:
        return False
```

关键设计：`app` 作为参数传入 `process()`，而不是注入到 Stage 构造函数。Stage 保持无状态，可被多个 Pipeline 复用。

### Pipeline

```python
class Pipeline:
    def add_stage(self, stage: Stage) -> "Pipeline": ...     # 链式调用
    def run(self, source_doc_id: str, app: "SemanticApp") -> PipelineContext: ...
    def run_from(self, stage_name: str, ctx: PipelineContext, app: "SemanticApp") -> PipelineContext: ...
    # run_from 支持断点续跑，调试单阶段时不需要重跑全流程
```

---

## 7. Operator 接口（`operators/base.py`）

```python
@dataclass
class OperatorResult:
    data:              Any
    latency_ms:        int
    ontology_version:  str
    errors:            list[str] = field(default_factory=list)

class SemanticOperator(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def execute(self, app: "SemanticApp", **kwargs) -> OperatorResult: ...

class OperatorRegistry:
    def register(self, op: SemanticOperator) -> None: ...
    def get(self, name: str) -> SemanticOperator: ...
    def execute(self, name: str, app: "SemanticApp", **kwargs) -> OperatorResult: ...
    def list_names(self) -> list[str]: ...
```

13 个现有算子全部变成 `SemanticOperator` 的实现类，注册到 `OperatorRegistry`。
`router.py` 只做 HTTP 参数解析 → 调用 `registry.execute()`，不再直接 import 算子模块。

---

## 8. Governance 接口（`governance/base.py`）

```python
class ConfidenceScorer(ABC):
    @abstractmethod
    def score(self, fact: Fact, context: dict) -> ConfidenceScore: ...

@dataclass
class Conflict:
    fact_id_a:     str
    fact_id_b:     str
    conflict_type: str
    description:   str

class ConflictDetector(ABC):
    @abstractmethod
    def detect(self, fact: Fact, store: RelationalStore) -> list[Conflict]: ...

@dataclass
class GateResult:
    passed:      bool
    gate_scores: dict[str, float]
    reason:      str

class EvolutionGate(ABC):
    GATES: list[str]   # 门控名称列表，由实现类定义

    @abstractmethod
    def evaluate(
        self, candidate: EvolutionCandidate, store: RelationalStore
    ) -> GateResult: ...
```

---

## 9. Ontology 接口（`ontology/base.py`）

```python
class OntologyProvider(ABC):
    @abstractmethod
    def get_node(self, node_id: str) -> OntologyNode | None: ...

    @abstractmethod
    def get_layer_nodes(self, layer: KnowledgeLayer) -> list[OntologyNode]: ...

    @abstractmethod
    def get_relations(self) -> list[RelationDef]: ...

    @abstractmethod
    def resolve_alias(self, surface_form: str, lang: str = "en") -> OntologyNode | None: ...

    @abstractmethod
    def version(self) -> str: ...
```

YAML → 运行时加载的逻辑留在 `src/ontology/YAMLOntologyProvider`（实现类），框架不感知 YAML。

---

## 10. SemanticApp 组合根（`app.py`）

```python
@dataclass
class AppConfig:
    # Providers
    llm:                LLMProvider
    embedding:          EmbeddingProvider
    graph:              GraphStore
    store:              RelationalStore
    objects:            ObjectStore
    # Knowledge
    ontology:           OntologyProvider
    # Governance
    confidence_scorer:  ConfidenceScorer
    conflict_detector:  ConflictDetector
    evolution_gate:     EvolutionGate
    # Pipeline & Operators
    pipeline_stages:    list[Stage]
    operators:          list[SemanticOperator]

class SemanticApp:
    def __init__(self, config: AppConfig): ...
    # 持有全部 provider 引用；pipeline 和 operators 从 config 中注册

    def ingest(self, source_doc_id: str) -> PipelineContext: ...
    def query(self, op_name: str, **kwargs) -> OperatorResult: ...
```

**一个新域的接入**只需要：实现各 Provider ABC、实现 Stage 列表、实现算子列表，构造 `AppConfig` 传入 `SemanticApp`。框架核心不需要修改。

---

## 11. 当前代码 → 框架角色映射

| 当前文件 | 框架角色 | 迁移成本 |
|----------|----------|----------|
| `src/db/postgres.py` | 实现 `RelationalStore` | 低：加 `implements` 声明 |
| `src/db/neo4j_client.py` | 实现 `GraphStore` | 低 |
| `src/utils/llm_extract.py` | 实现 `LLMProvider`（Claude） | 中：接口对齐 |
| `src/utils/embedding.py` | 实现 `EmbeddingProvider`（bge-m3） | 低 |
| `src/ontology/registry.py` | 实现 `OntologyProvider`（YAML） | 中：接口对齐 |
| `src/utils/confidence.py` | 实现 `ConfidenceScorer` | 低 |
| `src/pipeline/stages/stage*.py` | 实现 `Stage` ABC（6 个） | 中：签名调整 |
| `src/api/semantic/*.py`（非 router） | 实现 `SemanticOperator`（13 个） | 中 |
| `src/api/semantic/router.py` | 保持 HTTP 层，调用 `registry.execute()` | 低 |
| `src/config/settings.py` | `AppConfig` 工厂函数，读 `.env` | 低 |

现有代码**不需要立刻重构**。框架抽象和当前实现可以并行演进——先建 `semcore/` 定义接口，再逐步让 `src/` 各模块声明"实现某接口"，最终在 `app.py` 完成统一组合。

---

## 12. 扩展路径（积累方向）

| 扩展类型 | 操作 |
|----------|------|
| **新增算子** | 实现 `SemanticOperator`，注册到 `AppConfig.operators`，router 自动可路由 |
| **换 LLM** | 换一个 `LLMProvider` 实现类，其他不动 |
| **新 Pipeline 阶段** | 实现 `Stage`，插入 `AppConfig.pipeline_stages` 对应位置 |
| **新域（如金融）** | 新建 `src_finance/`，实现同套接口，构造不同 `AppConfig`，`semcore` 零修改 |
| **数据清洗策略库** | Stage 按职责细分，不同清洗策略形成策略列表，用 `Pipeline.add_stage()` 链式组合 |
| **新 Governance 策略** | 实现 `ConfidenceScorer` / `EvolutionGate`，在 `AppConfig` 中替换 |

---

## 13. 已确认设计决策与详细设计

### 决策 1：独立可发布 Python 包

目录布局采用 src-layout（PEP 517 标准）：

```
semcore/                     ← git 仓库 / monorepo 子目录
  pyproject.toml             ← 包元数据 + 构建配置
  semcore/                   ← 实际 Python 包（import semcore）
    __init__.py
    core/
    providers/
    pipeline/
    operators/
    governance/
    ontology/
    app.py
```

`pyproject.toml` 关键配置：
```toml
[project]
name = "semcore"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []           # 框架核心零外部依赖

[project.optional-dependencies]
telecom = ["psycopg2-binary", "neo4j", "anthropic", "sentence-transformers"]
```

---

### 决策 2：强类型 Stage 输出 + `meta` 兜底

`PipelineContext` 上的**框架核心字段**强类型（`segments`、`facts` 等）。
**阶段私有输出**存入 `stage_outputs: dict[str, Any]`，由 Stage 自己提供类型化的存取辅助方法：

```python
# 框架侧：PipelineContext 只知道核心类型
@dataclass
class PipelineContext:
    source_doc_id: str
    doc:           Document | None          = None
    segments:      list[Segment]            = field(default_factory=list)
    tags:          list[Tag]                = field(default_factory=list)
    facts:         list[Fact]               = field(default_factory=list)
    evidence:      list[Evidence]           = field(default_factory=list)
    rst_relations: list[RSTRelation]        = field(default_factory=list)
    stage_outputs: dict[str, Any]           = field(default_factory=dict)  # 阶段私有
    meta:          dict[str, Any]           = field(default_factory=dict)  # 非结构化
    errors:        list[str]                = field(default_factory=list)

# 域实现侧：Stage 定义自己的输出类型并提供辅助方法
@dataclass
class SegmentStageOutput:
    edu_titles: dict[str, str]

class SegmentStage(Stage):
    name = "segment"

    def set_output(self, ctx: PipelineContext, out: SegmentStageOutput) -> None:
        ctx.stage_outputs[self.name] = out

    def get_output(self, ctx: PipelineContext) -> SegmentStageOutput | None:
        return ctx.stage_outputs.get(self.name)
```

框架不感知 `SegmentStageOutput`，类型安全由域实现层自己保证。

---

### 决策 3：OperatorRegistry 中间件

中间件接口：

```python
class OperatorMiddleware(ABC):
    def before(
        self, op_name: str, app: "SemanticApp", kwargs: dict
    ) -> dict:
        """可修改入参，返回修改后的 kwargs。默认透传。"""
        return kwargs

    def after(
        self, op_name: str, result: "OperatorResult"
    ) -> "OperatorResult":
        """可修改结果，返回修改后的 result。默认透传。"""
        return result

    def on_error(
        self, op_name: str, exc: Exception
    ) -> "OperatorResult | None":
        """返回 OperatorResult 则吞掉异常；返回 None 则继续上抛。"""
        return None
```

注册与执行顺序：先注册 = 最外层（洋葱模型）：

```python
registry.use(AuditMiddleware())   # 最外层：记录所有调用
registry.use(TimingMiddleware())  # 次外层：计时
# 执行顺序：Audit.before → Timing.before → operator → Timing.after → Audit.after
```

框架内置两个中间件（可直接使用）：

| 中间件 | 功能 |
|--------|------|
| `TimingMiddleware` | 自动填充 `OperatorResult.latency_ms` |
| `LoggingMiddleware` | 记录算子名、耗时、错误到 logger |

---

### 决策 4：条件路由 API

Pipeline 支持三种节点类型，内部统一表示为 `PipelineNode`：

```python
# 线性节点（原有）
pipeline.add_stage(IngestStage())

# 二元分支：condition 返回 True 走 if_true，否则 if_false
pipeline.branch(
    condition=lambda ctx, app: ctx.doc.doc_type == "rfc",
    if_true=RFCSegmentStage(),
    if_false=DefaultSegmentStage(),
)

# 多路分支：key 函数返回字符串，匹配 branches，未命中走 default
pipeline.switch(
    key=lambda ctx, app: ctx.doc.doc_type,
    branches={
        "rfc":   RFCSegmentStage(),
        "cli":   CLISegmentStage(),
        "fault": FaultSegmentStage(),
    },
    default=DefaultSegmentStage(),
)

# 分支后继续线性
pipeline.add_stage(AlignStage())
```

内部节点类型（`pipeline/base.py`）：

```python
@dataclass
class LinearNode:
    stage: Stage

@dataclass
class BranchNode:
    condition: Callable[[PipelineContext, "SemanticApp"], bool]
    if_true:   Stage
    if_false:  Stage

@dataclass
class SwitchNode:
    key:      Callable[[PipelineContext, "SemanticApp"], str]
    branches: dict[str, Stage]
    default:  Stage

PipelineNode = LinearNode | BranchNode | SwitchNode
```

`run_from(stage_name, ctx, app)` 支持断点续跑，按 `stage.name` 定位到链中位置。
分支节点的 name 为 `branch:{if_true.name}|{if_false.name}`，switch 节点为 `switch:{key_repr}`。