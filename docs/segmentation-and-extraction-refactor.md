# 切段改善 + 去除正则抽取 — 设计方案

**日期**：2026-04-04
**状态**：方案已确认，待开发

---

# 一、切段改善

## 1.1 问题

当前 Stage 2 对超长段落的处理：
```
标题切分 → 段落超 1024 tokens → sliding_window_split(window=512, overlap=64)
```

滑窗不理解语义边界，把完整段落切碎，导致：
- 跨块的关系描述被断开，LLM 看不到完整上下文
- 所有 segment 都是固定 512 tokens，没有自然边界
- RST 关系在滑窗块之间失去意义

## 1.2 改善方案

### 层 1：改进切分边界（替代滑窗）

优先级从高到低，逐级尝试：

```
超长段落 (>1024 tokens)
    │
    ├── 尝试 1：按段落边界切分（双换行 \n\n）
    │   → 每个子段落 ≤ 1024 tokens？→ 完成
    │
    ├── 尝试 2：按句号边界切分（. + 空格）
    │   → 贪心合并：连续短句合并到一个 segment 直到接近上限
    │   → 每个 segment ≤ 1024 tokens？→ 完成
    │
    └── 尝试 3：滑窗兜底（window=512, overlap=64）
        → 最后手段，极端长文本（如连续 ASCII 图表）
```

### 层 3：抽取时合并相邻 segment（不改切分）

Stage 4 抽取 facts 时，如果一个 segment 的 LLM 返回空：
- 检查与前一个 segment 的 RST 关系
- 如果是 Elaboration / Sequence / Restatement → 合并两段文本重新送 LLM
- 只在 LLM 首次返回空时触发，不递归

```python
# Stage 4 伪代码
for i, seg in enumerate(segments):
    facts = llm_extract(seg.text)
    if not facts and i > 0:
        rst = get_rst_relation(segments[i-1], seg)
        if rst.type in ('Elaboration', 'Sequence', 'Restatement', 'Explanation'):
            merged_text = segments[i-1].text + "\n" + seg.text
            facts = llm_extract(merged_text)
```

---

# 二、去除正则抽取

## 2.1 数据依据

上一轮运行数据：
- rule 抽的 7597 条中，只有 122 条 active（1.6%），4388 条 conflicted（57%）
- LLM 抽的 6365 条中，440 条 active（6.9%），质量高 4 倍
- 正则匹配的是紧邻动词的单个词，碰巧命中别名产生虚假三元组

## 2.2 改动

Stage 4 抽取优先级链：

```
改前：LLM → regex → co-occurrence
改后：LLM → LLM with merged context → co-occurrence (仅 2 节点 1 谓语)
```

- 完全删除 `_extract_regex` 方法
- 删除 `ontology/patterns/relation_extraction.yaml`（不再需要）
- `ontology/patterns/predicate_signals.yaml` 保留（共现策略仍需要）

## 2.3 保留的回退路径

当 LLM 完全不可用（熔断或未配置）时：
- 只有共现策略兜底（恰好 2 个节点 + 1 个谓语信号 → 最多 1 条 fact）
- 不用正则——宁可不抽也不产噪声

---

# 三、文件变更

| 文件 | 改动 |
|------|------|
| `src/pipeline/stages/stage2_segment.py` | `_process_chunk` 改为段落→句子→滑窗三级切分 |
| `src/pipeline/stages/stage4_extract.py` | 删除 `_extract_regex`，增加 merged context 二次 LLM 尝试 |
| `ontology/patterns/relation_extraction.yaml` | 删除 |
| `src/ontology/registry.py` | 移除 `relation_extraction_patterns` 加载 |
| `src/ontology/yaml_provider.py` | 移除 `relation_extraction_patterns` 属性 |