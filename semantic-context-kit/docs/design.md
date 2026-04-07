# Semantic Context Kit — 设计文档

日期：2026-04-06
版本：v0.1 (首版)
状态：开发中

## 1. 定位

Agent 运行时的**项目级语义知识组织器**。不是数据库，不是搜索引擎——是 Agent 的"领域视野"。

| | 大平台 (Self_Knowledge_Evolve) | 本组件 (semantic-context-kit) |
|---|---|---|
| 定位 | 组织级知识基础设施 | 项目级上下文组织器 |
| 生命周期 | 长期运行 | 跟项目走 |
| 存储 | PG + Neo4j + MinIO | 内存 + 可选 SQLite |
| 本体 | 完整五层，持续演化 | 从大的继承领域视图 |
| 依赖 | 多服务 | 零依赖（纯 Python） |
| 用途 | 知识采集/治理/质量 | Agent 上下文注入 |

## 2. 核心能力

### 2.1 领域视图加载

项目启动时从大平台导出一份领域知识子集：

```python
kit = SemanticContextKit.from_platform_export("domain_view.json")
# 或者从本地 YAML/JSON 加载
kit = SemanticContextKit.from_file("telecom_networking.json")
```

领域视图包含：
- 概念节点（id, name, aliases, description, layer）
- 关系（src, type, dst）
- 五层推理链模板
- 证据摘要

### 2.2 文本标注（text → concepts）

给一段文本自动标注涉及的领域概念：

```python
tags = kit.annotate("配置 OSPF 区域划分时需要注意 ABR 的路由汇总策略")
# → [("OSPF", "IP.OSPF", 1.0), ("ABR", "IP.ABR", 1.0), 
#     ("路由汇总", "METHOD.RouteSummarization", 0.85)]
```

### 2.3 概念检索（concept → knowledge）

给定概念，返回相关知识：

```python
info = kit.lookup("OSPF")
# → {node: {...}, facts: [...], methods: [...], conditions: [...], evidence: [...]}
```

### 2.4 五层推理链

从概念到场景的完整推理路径：

```python
chain = kit.reasoning_chain("IP.OSPF")
# → concept: OSPF
#   → mechanism: LinkStateFlooding, NeighborAdjacencyFormation
#     → method: OSPFAreaDeploymentMethod
#       → condition: LargeScaleApplicability
#         → scenario: SpineLeafUnderlayOverlayScenario
```

### 2.5 项目知识积累

运行过程中积累新知识：

```python
kit.learn("在本项目中，因为设备数量超过500台，选择了OSPF多区域划分方案",
          concepts=["IP.OSPF"], decision="multi-area", source="project")
kit.learn_term("Super Spine", parent="IP.SPINE_LEAF",
               description="三层 Spine-Leaf 架构中的顶层交换机")
```

### 2.6 导出回传

项目结束时导出积累的知识，回传大平台：

```python
export = kit.export_learned()
# → {new_terms: [...], decisions: [...], documents: [...]}
# POST 到大平台的 Pipeline 入口
```

## 3. 面向 Agent 的 3 个高级 API

### API 1: knowledge_brief

"关于这个话题，我需要知道什么"

```python
brief = kit.knowledge_brief("企业园区网双出口设计")
# → {
#     concepts: [{name, description, layer}...],
#     scenario: "DualExitCampusScenario",
#     methods: [{name, steps, conditions}...],
#     risks: [{name, description}...],
#     evidence: [{source, text, authority}...],
#   }
```

Agent Reasoner 阶段调用，返回值直接注入 system prompt。

### API 2: risk_check

"这个方案有什么问题"

```python
risks = kit.risk_check(
    selected=["BGP", "OSPF", "VRRP"],
    scenario="dual-exit campus"
)
# → {
#     conflicts: ["BGP+OSPF 需要路由再分发边界控制"],
#     risks: ["AsymmetricPathRisk", "RoutingLoopRisk"],
#     missing: ["未选择 BFD，建议快速故障检测"],
#     dependency_gaps: ["需要配合 Route Policy"],
#   }
```

Agent Observer 阶段调用，作为方案检查清单。

### API 3: experience_recall

"类似的事情以前怎么做的"

```python
exp = kit.experience_recall("MPLS L3VPN 多租户隔离")
# → {
#     best_practices: [{method, description, evidence}...],
#     lessons: [{risk, description, source}...],
#   }
```

Agent Planner 阶段调用，提供历史经验参考。

## 4. 数据结构

### 4.1 节点（ConceptNode）

```python
@dataclass
class ConceptNode:
    node_id: str              # "IP.OSPF"
    name: str                 # "OSPF"
    layer: str                # concept|mechanism|method|condition|scenario
    description: str          # "Link-state IGP..."
    aliases: list[str]        # ["Open Shortest Path First", "OSPFv2", ...]
    parent_id: str | None     # "IP.ROUTING_PROTOCOL"
    properties: dict          # 自由属性
```

### 4.2 关系（Relation）

```python
@dataclass
class Relation:
    source: str               # "IP.OSPF"
    relation_type: str        # "uses_protocol"
    target: str               # "IP.TCP"
    confidence: float         # 0.85
    evidence: str | None      # 来源摘要
```

### 4.3 证据（Evidence）

```python
@dataclass
class Evidence:
    node_id: str              # 关联节点
    text: str                 # 原文片段
    source: str               # "RFC 2328" | "华为配置指南"
    authority: str            # S|A|B|C
```

### 4.4 项目知识（LearnedItem）

```python
@dataclass
class LearnedItem:
    text: str                 # 原始文本
    concepts: list[str]       # 关联概念
    item_type: str            # decision|term|observation|lesson
    metadata: dict            # 自由元数据
    timestamp: str
```

## 5. 内部索引

为了快速标注和检索，维护以下内存索引：

```
alias_index:  {"ospf": "IP.OSPF", "open shortest path first": "IP.OSPF", ...}
              → O(1) 别名查找

layer_index:  {"concept": [...], "mechanism": [...], ...}
              → 按层快速遍历

parent_index: {"IP.OSPF": "IP.ROUTING_PROTOCOL", ...}
              → 层级向上遍历

child_index:  {"IP.ROUTING_PROTOCOL": ["IP.OSPF", "IP.BGP", ...]}
              → 层级向下展开

relation_index: {"IP.OSPF": [Relation(...), ...]}
              → 节点的所有关系

evidence_index: {"IP.OSPF": [Evidence(...), ...]}
              → 节点的证据
```

## 6. 与 Agent 框架的集成点

```
Agent Loop:
  ┌─────────────────────────────────────────┐
  │ Reasoner                                │
  │   goal_text → kit.annotate(goal_text)   │
  │   concepts → kit.knowledge_brief(goal)  │ ← 自动注入领域视野
  │   → domain_context 注入 system prompt   │
  ├─────────────────────────────────────────┤
  │ Planner                                 │
  │   kit.experience_recall(task)           │ ← 历史经验参考
  │   kit.reasoning_chain(concept)          │ ← 方法论脚手架
  ├─────────────────────────────────────────┤
  │ Actor                                   │
  │   kit.lookup(concept) 按需查事实        │ ← 传统工具调用
  ├─────────────────────────────────────────┤
  │ Observer                                │
  │   kit.risk_check(plan)                  │ ← 条件检查清单
  │   kit.learn(result)                     │ ← 积累项目经验
  └─────────────────────────────────────────┘
```

关键：Reasoner/Planner/Observer 是**框架固定调用**（不依赖 LLM 判断），Actor 是按需调用。

## 7. 文件结构

```
semantic-context-kit/
├── semantic_context_kit/
│   ├── __init__.py
│   ├── kit.py              # SemanticContextKit 主类
│   ├── models.py           # 数据结构 (ConceptNode, Relation, Evidence, LearnedItem)
│   ├── index.py            # 内存索引
│   ├── annotator.py        # 文本标注 (text → concepts)
│   ├── reasoner.py         # 五层推理链 + knowledge_brief
│   ├── checker.py          # risk_check (冲突/风险/遗漏)
│   └── loader.py           # 领域视图加载 (JSON/YAML/platform API)
├── tests/
│   ├── test_kit.py
│   └── test_annotator.py
├── examples/
│   ├── demo_agent_integration.py
│   └── sample_domain_view.json
├── docs/
│   └── design.md
├── pyproject.toml
└── README.md
```

## 8. 零依赖原则

核心包零外部依赖（纯 Python 标准库）。可选依赖：
- `requests`：从大平台 API 加载领域视图
- `pyyaml`：YAML 格式支持
- Embedding 支持：通过回调函数注入，不硬依赖任何模型库

## 9. 与大平台的协议

### 领域视图导出格式（JSON）

```json
{
  "version": "0.4",
  "domain": "IP Networking",
  "exported_at": "2026-04-06T20:00:00Z",
  "nodes": [
    {"node_id": "IP.OSPF", "name": "OSPF", "layer": "concept",
     "description": "...", "aliases": ["OSPFv2", "OSPFv3"],
     "parent_id": "IP.ROUTING_PROTOCOL"}
  ],
  "relations": [
    {"source": "IP.OSPF", "type": "uses_protocol", "target": "IP.TCP",
     "confidence": 0.95}
  ],
  "evidence": [
    {"node_id": "IP.OSPF", "text": "OSPF uses Dijkstra...",
     "source": "RFC 2328", "authority": "S"}
  ]
}
```

### 回传格式（JSON）

```json
{
  "project_id": "campus-dual-exit-2026",
  "learned_items": [
    {"text": "选择了OSPF多区域方案", "concepts": ["IP.OSPF"],
     "item_type": "decision", "timestamp": "..."},
    {"text": "Super Spine", "item_type": "term",
     "parent_concept": "IP.SPINE_LEAF", "description": "..."}
  ]
}
```
