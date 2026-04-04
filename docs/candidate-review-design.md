# 候选审批与增量回填 — 设计方案

**日期**：2026-04-04
**状态**：方案已确认，待开发

---

# 一、设计目标

1. 统一候选概念和候选关系的管理（一套表、一套评分、一套审批流程）
2. 提供审批 API 入口（列出 / 通过 / 拒绝）
3. 审批通过后自动入库（写 YAML + Neo4j + 版本号）
4. 新概念入库后增量回填已有文档（不重跑全量 Pipeline）
5. 回填在独立后台线程运行，不打断主进程

---

# 二、统一候选管理

## 2.1 合并 relation_candidates 到 evolution_candidates

删除 `governance.relation_candidates` 表，在 `governance.evolution_candidates` 中新增字段：

```sql
ALTER TABLE governance.evolution_candidates
  ADD COLUMN IF NOT EXISTS candidate_type VARCHAR(32) NOT NULL DEFAULT 'concept',
  ADD COLUMN IF NOT EXISTS examples JSONB DEFAULT '[]';
  -- candidate_type: 'concept' | 'relation'
  -- examples: 关系候选的使用示例 [{subject, object, segment_id, source_doc_id}]
```

## 2.2 写入逻辑统一

| 来源 | candidate_type | surface_forms | examples |
|------|---------------|---------------|----------|
| Stage 3 候选概念 | concept | ['QUIC', 'quic protocol'] | [] |
| Stage 4 候选关系 | relation | ['replaces'] | [{subject:'IP.STP', object:'IP.RSTP', ...}] |

两者共享同一套：
- source_count / source_diversity 累加
- composite_score 评分
- review_status 状态机（discovered → scored → pending_review → accepted / rejected）
- 六项门控逻辑

---

# 三、审批 API

## 3.1 端点

```
GET  /api/v1/system/review
     ?type=concept|relation|all  (default: all)
     ?status=pending_review|discovered|all  (default: pending_review)
     &limit=20
     → 列出待审核候选

GET  /api/v1/system/review/{candidate_id}
     → 查看单个候选详情（含 examples、source 文档列表）

POST /api/v1/system/review/{candidate_id}/approve
     body: {
       "reviewer": "user_name",
       "note": "审批说明",
       "parent_node_id": "IP.ROUTING" (概念候选必填),
       "aliases": ["QUIC", "quic protocol"] (可选)
     }
     → 审批通过 → 写入本体 + 触发增量回填

POST /api/v1/system/review/{candidate_id}/reject
     body: {"reviewer": "user_name", "note": "拒绝原因"}
     → 标记 rejected
```

## 3.2 审批通过时的动作

### 概念候选通过

1. 生成 node_id：`EVOLVED.{NORMALIZED_FORM.upper()}`
2. 写入 Neo4j OntologyNode（lifecycle_state='active', maturity_level='evolved'）
3. 写入 OntologyRegistry 内存（alias_map 热更新）
4. 写入 PG lexicon_aliases（surface_forms → node_id）
5. 写入 `governance.review_records` 审计
6. bump `governance.ontology_versions`（版本号 + diff）
7. 更新 `evolution_candidates.review_status = 'accepted'`
8. **启动增量回填线程**

### 关系候选通过

1. 将 predicate_name 加入 OntologyRegistry.relation_ids（热更新）
2. 从 examples 回溯创建 Facts + Evidence
3. 写入 Neo4j（动态 relationship type）
4. 写入 `governance.review_records` 审计
5. bump `governance.ontology_versions`
6. 更新 `evolution_candidates.review_status = 'accepted'`

---

# 四、增量回填（概念入库后）

## 4.1 触发条件

新概念审批通过后，需要在已有文档中找到提及这个概念的段落，补上 segment_tags 和 facts。

## 4.2 流程

```
新概念 "QUIC" 入库
    ↓
后台线程启动（不打断主 Worker / API）
    ↓
Step 1: 在 PG segments 中搜索包含该术语的段落
    SELECT segment_id, source_doc_id, raw_text
    FROM segments
    WHERE lifecycle_state = 'active'
      AND raw_text ILIKE '%quic%'
    ↓
Step 2: 对命中的 segments 补跑对齐
    - 生成 canonical tag: (segment_id, 'canonical', 'QUIC', 'EVOLVED.QUIC')
    - 写入 segment_tags
    ↓
Step 3: 对命中的 segments 补跑抽取
    - LLM 优先：传入 segment text + 新节点 + 已有节点
    - 产出新 facts + evidence
    ↓
Step 4: 补跑索引
    - 新 facts 写入 Neo4j（动态 relationship type）
    - 新 TAGGED_WITH 边写入 Neo4j
    ↓
Step 5: 记录回填结果
    - 回填了多少 segments / tags / facts
    - 写入 review_records 作为审计
```

## 4.3 独立线程设计

```python
# src/stats/backfill.py

class BackfillWorker:
    """Run incremental backfill in a background thread."""

    def __init__(self, app):
        self._app = app
        self._thread: threading.Thread | None = None

    def backfill_concept(self, node_id: str, surface_forms: list[str]) -> None:
        """Start background thread to backfill a newly accepted concept."""
        self._thread = threading.Thread(
            target=self._run_concept_backfill,
            args=(node_id, surface_forms),
            name=f"backfill-{node_id}",
            daemon=True,
        )
        self._thread.start()
        log.info("Backfill started for %s in background", node_id)

    def _run_concept_backfill(self, node_id, surface_forms):
        # Step 1: search segments
        # Step 2: add tags
        # Step 3: extract facts (LLM)
        # Step 4: index to Neo4j
        # Step 5: log results
        ...
```

## 4.4 对主进程的影响

- 回填线程是 daemon thread，主进程退出时自动终止
- 回填只读/写 PG + Neo4j，和主 Pipeline 使用相同的连接池
- 不会重复处理（通过 `ON CONFLICT DO NOTHING` 避免）
- 回填进度可通过 stats API 查看

---

# 五、版本控制

每次审批操作触发版本变更：

```python
# 版本号格式：v0.2.0 → v0.2.1（patch bump）
new_version = bump_patch(current_version)

store.execute("""
    INSERT INTO governance.ontology_versions (version_tag, description, diff_from_prev, status)
    VALUES (%s, %s, %s::jsonb, 'active')
""", (new_version, f"Approved {candidate_type}: {normalized_form}", diff_json))

# 更新 settings.ONTOLOGY_VERSION（运行时）
# 后续 facts 的 ontology_version 字段使用新版本号
```

---

# 六、模块结构

```
src/api/system/
├── router.py          # 现有 stats/drilldown + 新增 review 端点
└── review.py          # 审批业务逻辑（approve/reject/list）

src/stats/
├── backfill.py        # 增量回填后台线程（新增）
├── collector.py       # 已有
├── scheduler.py       # 已有
└── drilldown.py       # 已有
```

---

# 七、文件变更

| 文件 | 改动 |
|------|------|
| `scripts/init_postgres.sql` | evolution_candidates 加 candidate_type + examples 列；删 relation_candidates 表 |
| `scripts/migrations/006_unify_candidates.sql` | 迁移脚本 |
| `src/pipeline/stages/stage4_extract.py` | `_record_relation_candidate` 改写入 evolution_candidates (type='relation') |
| `src/api/system/review.py` | 新文件：审批业务逻辑 |
| `src/api/system/router.py` | 新增 review 端点 |
| `src/stats/backfill.py` | 新文件：增量回填线程 |
| `src/dev/fake_postgres.py` | 更新 evolution_candidates 表结构 |

---

# 八、Dashboard 新增

审批入口集成到 Dashboard：
- 新增 "Review" 标签页
- 列出 pending_review 的概念和关系候选
- 每条可展开查看 examples / source docs
- Approve / Reject 按钮直接调 API
