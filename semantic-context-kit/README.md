# Semantic Context Kit

Agent 运行时的项目级语义知识组织器。轻量、零依赖、即插即用。

## 定位

不是数据库，不是搜索引擎 —— 是 Agent 的"领域视野"。

- 从[电信语义知识操作系统](../Self_Knowledge_Evolve/)继承领域视图
- 在 Agent 循环中自动注入结构化知识上下文
- 项目过程中积累经验，结束后回传大平台

## 快速开始

```python
from semantic_context_kit import SemanticContextKit

# 从大平台加载领域视图
kit = SemanticContextKit.from_platform(
    "http://localhost:8000",
    keywords=["BGP", "OSPF", "VXLAN"]
)

# Agent Reasoner: 自动注入领域知识
brief = kit.knowledge_brief("双出口园区网设计")

# Agent Observer: 方案风险检查
risks = kit.risk_check(["BGP", "OSPF", "VRRP"], scenario="dual-exit")

# 积累项目知识
kit.learn("选择了OSPF多区域方案", item_type="decision")

# 项目结束: 回传大平台
kit.save_learned("project_knowledge.json")
```

## 3 个 Agent API

| API | Agent 阶段 | 功能 |
|-----|-----------|------|
| `knowledge_brief(query)` | Reasoner | 返回概念+方法+条件+场景+证据，注入 system prompt |
| `risk_check(selected, scenario)` | Observer | 冲突检测+风险+遗漏+依赖缺失 |
| `experience_recall(query)` | Planner | 最佳实践+历史教训 |

## 安装

```bash
pip install -e .                    # 核心（零依赖）
pip install -e ".[platform]"       # + 大平台加载支持
```

## Demo

```bash
# 确保大平台在 localhost:8000 运行
python examples/demo_agent_integration.py
```