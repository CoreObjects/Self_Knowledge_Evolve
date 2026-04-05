# 候选合并 — 设计方案

**日期**：2026-04-05
**状态**：方案已确认，待开发

---

# 一、问题

同一概念以不同表述进入候选池，产生重复：
- "network layer reachability information" 和 "network layer reachability information (nlri)"
- "route reflector" 和 "RR"
- "forwarding equivalence class" 和 "FEC"

当前 normalize_term 只做小写+去空格，无法识别这些同义变体。

---

# 二、方案

## A：自动规则合并（写入时）

增强 normalize_term，在写入前自动归一化：
1. 去掉括号及内容："xxx (yyy)" → "xxx"，但把括号内容作为额外 surface_form
2. 去掉冠词前缀："the bgp protocol" → "bgp protocol"
3. 去掉尾部泛化词："xxx protocol"/"xxx mechanism" → "xxx"（可选，需谨慎）

改动位置：`src/utils/normalize.py` 的 `normalize_term` + Stage 3 `_upsert_candidates`

## C：手动合并（Review 页面）

Review 页面新增：
1. 多选候选（checkbox）
2. "Merge" 按钮 → 合并选中的候选为一个
3. 合并时可选"Ask LLM"按钮 → LLM 判断是否真的同义 + 推荐 canonical name

### 合并逻辑

```
选中 candidate A + candidate B → Merge
  → surface_forms = A.surface_forms + B.surface_forms（去重）
  → examples = A.examples + B.examples
  → source_count = A.source_count + B.source_count
  → seen_source_doc_ids = union
  → 保留 A 的 normalized_form 作为主键
  → 删除 B
```

### LLM 辅助

```
POST /api/v1/system/review/check_synonyms
body: { candidate_ids: [id_a, id_b] }
→ LLM 判断："network layer reachability information" 和 "NLRI" 是否同义？
→ 返回: { is_synonym: true, suggested_canonical: "NLRI", reason: "..." }
```

---

# 三、文件变更

| 文件 | 改动 |
|------|------|
| `src/utils/normalize.py` | 增强 normalize_term：去括号、提取缩写 |
| `src/pipeline/stages/stage3_align.py` | _upsert_candidates 把括号内缩写作为额外 surface_form |
| `src/api/system/review.py` | 新增 merge_candidates + check_synonyms |
| `src/api/system/router.py` | 新增 merge + check_synonyms 端点 |
| `static/dashboard.html` | Review 页面新增多选 + Merge 按钮 + LLM 辅助 |