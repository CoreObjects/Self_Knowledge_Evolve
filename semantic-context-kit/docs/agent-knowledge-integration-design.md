# Agent 系统与语义知识操作系统集成 — 方案讨论记录

**日期**：2026-04-05
**状态**：方案讨论阶段

---

# 一、背景

两个系统：
- **miniAgents**：自研 Agent 框架（Reasoner→Planner→Actor→Observer 循环，Blackboard 通信，Skill/Tool 三层加载）
- **语义知识操作系统**（Self_Knowledge_Evolve）：领域知识基础设施（5 层本体，21 算子，7 阶段 Pipeline，候选演化，质量评估）

目标：将两者结合，形成数据飞轮，持续积累业务经验和知识，服务于专业领域的项目全流程方案设计。

---

# 二、核心问题：Agent 运行时和语义知识系统到底是什么关系

## 2.1 排除的方案："加几个 API"

最直觉的想法是把知识系统当工具——Agent 在需要时调 API 查知识。但这意味着 LLM 要自己判断"什么时候需要查、查什么"，它经常不知道自己不知道什么。

## 2.2 真实定位：知识系统参与 Agent 的思考过程

不是被动的工具，而是在 Agent 循环的固定位置**自动注入**结构化领域知识：

| Agent 阶段 | 知识系统的角色 | 做什么 |
|---|---|---|
| **Reasoner** | "视野" | 根据 goal 中的关键词自动匹配本体节点，把五层推理链注入上下文。LLM 看到的 prompt 里已经有结构化的领域知识了 |
| **Planner** | "方法论脚手架" | domain_context 里的 method 链路作为任务分解的参考框架。LLM 参考领域方法论来分解任务，而不是自由发挥 |
| **Actor** | "工具" | 执行时需要查具体事实——这一步才是传统的 API 调用 |
| **Observer** | "检查清单" | condition 层的约束作为评估依据。LLM 对照领域约束清单逐项检查，而不是凭感觉说 OK |

关键区别：**调用时机从"LLM 决定调"变成"框架固定调"，调用结果从"工具返回值"变成"系统 prompt 的一部分"。**

代码改动可能只有几十行（在 Reasoner 组装上下文时插入一次知识查询），但效果上差异巨大——LLM 的输出质量高度依赖输入的上下文质量。

---

# 三、大小两层知识系统

## 3.1 核心发现

如果语义知识系统只是在 Reasoner 阶段自动注入上下文，那不需要一个云端大系统——一个轻量的、项目级的知识组织器就够了。但同时确实需要一个长期积累的云端平台。

**这不是一个系统，是两个**：

### 小的：项目级知识组织器

- 跟着项目走，跟着 Agent 走
- 轻量（Python 类，几百行，内存或 SQLite）
- 不需要预定义本体——从大的继承一个"领域视图"
- 实时学习：项目过程中积累需求、讨论、设计、验证
- 核心能力：标注（文本→概念）、检索（概念→文本）、推理链（五层）

### 大的：组织级知识平台

- 长期存在，持续积累
- 完整本体 + 治理 + 质量评估
- 爬虫 + Pipeline 持续运行
- 就是当前已经建好的语义知识操作系统

## 3.2 两者的关系：Git 式的 fork-work-merge

```
项目开始
    ↓
大的 → 导出领域视图 → 小的（初始知识骨架）
    ↓
项目过程中：小的实时积累项目知识
Agent 在 Reasoner/Planner/Observer 阶段从小的查询
    ↓
项目结束
    ↓
小的 → 回传项目知识 → 大的（进入 Pipeline → 候选池 → 审批 → 沉淀）
```

## 3.3 两个关键接口

### 接口 1：导出领域视图（项目开始时调一次）

```
大的 → 小的
输入：项目关键词（如"园区网双出口"）
输出：{
    相关节点子集（50-100个概念 + 描述 + 别名），
    相关关系子集，
    相关 method/condition/scenario，
    相关证据摘要
}
```

小的拿到这个就有了初始知识骨架，不需要从零建本体。

### 接口 2：回传项目知识（项目结束时调一次）

```
小的 → 大的
输入：{
    项目过程中发现的新术语，
    项目产出的方案文档，
    验证结果和经验总结，
    Agent 对话中的关键决策
}
→ 进入大的的 Pipeline → 候选池 → 审批 → 沉淀
```

## 3.4 数据飞轮

```
项目 1 → 小的学到经验 → 回传大的 → 审批沉淀
                                    ↓
项目 2 → 从大的拉取（已包含项目 1 的经验）→ 小的更强
                                    ↓
项目 3 → 从大的拉取（包含项目 1+2 的经验）→ 更强
```

---

# 四、Skill 和语义知识系统的关系

## 4.1 Skill 和知识系统存的是不同层次的知识

| | Skill | 语义知识系统 |
|---|---|---|
| **是什么** | "怎么做一件事"的操作步骤 | "领域里什么和什么有什么关系" |
| **例子** | "做双出口方案：先选协议→配策略→配检测→验证" | "BGP depends_on TCP，双出口有非对称路径风险" |
| **类比** | 厨师的菜谱 | 食材百科 |
| **谁写** | 领域专家手写 | Pipeline 自动抽取 + 专家审批 |

## 4.2 运行时配合

Skill 提供流程框架，知识系统提供每一步的领域事实：

```
Skill 说第 2 步"选择主备路由协议"
  → Agent 查知识系统："双出口路由协议选择"
  → 返回：推荐 BGP（大规模）或 Static（小规模）
    条件：LargeScaleApplicability → BGP
    风险：AsymmetricPathRisk
    证据：华为配置指南原文
  → Agent 基于这些知识做出选择
```

## 4.3 Skill 和本体五层模型的映射

```
一个 Skill 本质上是：
    "在 [scenario] 下，
     按 [method 1 → method 2 → method 3] 的顺序执行，
     每步需要满足 [condition]，
     涉及 [concept] 和 [mechanism]"
```

Skill ≈ Scenario + Method + Condition 的自然语言包装。

## 4.4 离线闭环（非运行时）

- **专家写 Skill 时**：可以用云端知识系统检索领域知识辅助编写
- **项目结束后**：Skill 作为重要语料回传给大的知识系统
  - Skill 中蕴含的 method 步骤 → 丰富 method 层
  - Skill 中的约束条件 → 丰富 condition 层
  - Skill 对应的场景 → 丰富 scenario 层
- **这是飞轮的生产侧**：新 Skill 丰富知识 → 知识让 Agent 更好执行 Skill → 执行结果产生新经验 → 新经验沉淀为新 Skill

---

# 五、知识网关层：面向 Agent 的高级 API

Agent 不需要知道背后有 21 个算子。面向 Agent 的接口收敛为 3 个：

## API 1: knowledge_brief — "关于这个话题，我需要知道什么"

```
输入: "企业园区网双出口设计"
输出:
    涉及概念: [BGP, VRRP, Route Policy, ...]
    适用场景: DualExitCampusInternetScenario
    推荐方法: DualExitConfigurationMethod + BGPPolicyConfigurationMethod
    约束条件: DualExitApplicability, AsymmetricPathRisk
    关键证据: [{来源, 原文, 权威等级}...]
```

底层：context_assemble + 五层推理链 + cross_layer_check 的组合。

## API 2: risk_check — "这个方案有什么问题"

```
输入: { 选型: [BGP, OSPF, VRRP], 场景: "dual-exit campus" }
输出:
    冲突: "BGP+OSPF 需要路由再分发边界控制"
    风险: [AsymmetricPathRisk, RoutingLoopRisk]
    遗漏: "未选择 BFD，建议快速故障检测"
    依赖缺失: "EVPN_VXLAN 需要 BGP+VXLAN"
```

底层：dependency_closure + conflict_detect + cross_layer_check + condition 匹配。

## API 3: experience_recall — "类似的事情以前怎么做的"

```
输入: "MPLS L3VPN 多租户隔离"
输出:
    最佳实践: [{method, 描述, 条件, 证据}]
    反面教训: [{risk, 描述, 来源}]
```

底层：scenario 匹配 + context_assemble + evidence_rank。

---

# 六、具有独特价值的查询场景

## Case 1：故障全链路推演

"BGP 邻居断了，哪些业务受影响？每个该怎么排查？注意什么约束？"
→ 一次查询返回：故障→影响面→排查方法→注意事项→受影响场景

## Case 2：多源矛盾裁决

"OSPF Hello Interval 默认值，RFC 说 10s，博客说 30s——听谁的？"
→ 按 source_authority 排序，量化裁决

## Case 3：变更前影响面评估

"要改 VRF 配置，全网有多少东西会被波及？"
→ 依赖闭包 + 风险 + 验证方法 + 知识新鲜度

## Case 4：知识空白发现（元认知）

"我们对 SRv6 掌握了多少知识？缺什么？"
→ 系统知道自己不知道什么

## Case 5：推理链还原

"为什么说 EVPN-VXLAN 适合多租户 DC？把推理过程展示出来"
→ 五层跨层关系 + RST 语篇逻辑 + 多源证据溯源

---

# 七、待定问题

1. **小的知识组织器的具体实现**：内存结构、索引方式、和 Agent 框架的代码集成点
2. **领域视图导出接口的具体设计**：导出什么粒度的知识子集，格式是什么
3. **回传接口的具体设计**：项目知识怎么进入 Pipeline，需不需要专门的 stage
4. **Blackboard 语义标注**：是否需要在 Agent 通信层做本体标注（可后做）
5. **多项目并行时大的知识系统的隔离和合并策略**
