# V3 Data Foundation Implementation Gap Audit

> 日期：2026-05-08  
> 状态：Batch 0 审计产物，尚未进入 migration / API 实现  
> 依据：`v3-data-foundation/design.md`、`specs/data-foundation/spec.md`、当前 backend Alembic history

## 1. 结论摘要

当前后端不是空白实现，已经存在多份 V3 相关 Alembic 迁移；但这些迁移与当前已确认的 `v3-data-foundation` schema 有系统性偏差。

最关键的偏差：

| 主题 | 当前实现 | 当前 spec |
|---|---|---|
| clean / tenant / contact 主键 | 多处是 `uuid` | 已确认使用 `bigint identity` |
| `tenant_keyword` | `uuid` 主键，缺 `keyword_raw / created_by / status` | `bigint identity` + 保存租户原始输入 + soft delete |
| raw 公司表 | 仍含 `task_id / last_seen_at`，腾道 source id 叫 `tid` | 不保留 `task_id / last_seen_at`，统一 `source_id` |
| raw 联系人表 | 缺 `lixiaoyun_raw_contacts / tendata_raw_contacts` | 两张 raw contacts 为确认 schema |
| clean sources / keywords | 现有是旧 `company_sources` 或缺失 | 需要 `clean_company_sources / clean_company_keywords` |
| tenant private fields | 仍有 `matched_keywords / score_adjustment` 等旧字段 | 本期不保留，关键词和调分历史都改关联模型 |
| collection_runs | `uuid` 主键，缺 `stage / triggered_by / triggered_tenant_id` | `bigint identity` + provider-specific stage + triggered tenant |
| API | 仍有旧 `/collection-keywords` 与旧 source_types 口径 | 需要新 admin/tenant contract |

因此，**不能直接进入 Batch 1 写新增 migration**。必须先确认现有 20260507/20260508 migration 是否已经跑到目标库。

## 2. Alembic 链路现状

命令：

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run alembic history --verbose
```

结果摘要：

| Revision | 角色 |
|---|---|
| `20260508_0033` | 当前 head；新增 `collection_runs` 并让 `collection_tasks` 关联 run |
| `20260507_0032` | 调整励销云每日 stage1 上限为 1000 |
| `20260507_0031` | `clean_companies` 新增 `pcb_suppliers` |
| `20260507_0030` | 评分模板新格式 |
| `20260507_0021` | mergepoint |
| `20260507_0025` | `tenant_companies` 添加调分字段 |
| `20260507_0017` | `collection_keywords` 关联 `keyword_master` |
| `20260507_0016` | 创建 `keyword_master / tenant_keyword` |
| `20260507_0015` | `tenant_contacts.contact_id` 迁到 `clean_contact_id` |
| `20260507_0014` | 重建 clean/tenant/competitor 数据模型 |
| `20260430_0009` | Phase 1 collection schema，创建旧 raw / clean / tenant / cleanup_queue |

重要观察：

- `20260507_0016` 是 branchpoint。
- `20260507_0021` 是 mergepoint。
- 当前 head 为 `20260508_0033`。
- 迁移链中已有多个和当前 spec 冲突的旧设计，不宜盲目追加。

## 3. 逐表 Gap Audit

### 3.1 keyword_master

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `20260507_0016` 已创建 | 需要创建 | 基本存在 |
| 主键 | `uuid PRIMARY KEY DEFAULT gen_random_uuid()` | `uuid` | 匹配 |
| 字段 | `id, keyword, keyword_normalized, created_at` | 同左 | 匹配 |
| 唯一约束 | `keyword_normalized UNIQUE` + 额外 unique index | `UNIQUE(keyword_normalized)` | 基本匹配 |
| 归一规则 | `20260507_0017` SQL 中用正则替换，和服务函数旧口径对齐 | 当前 spec 要保留 `FR-4 / C++` 等语义符号 | 规则冲突 |

建议处理：

- 如果 0017 未执行：修正 0017 内归一规则。
- 如果 0017 已执行：新增 forward migration / 数据修正脚本，且同步 `keyword_service.normalize_keyword`。

### 3.2 tenant_keyword

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `20260507_0016` 已创建 | 需要创建 | 存在但口径冲突 |
| 主键 | `uuid` | `bigint identity` | 冲突 |
| 字段 | `tenant_id, keyword_master_id, created_at` | 还需 `keyword_raw, created_by, status` | 缺字段 |
| 删除语义 | 无 `status` | soft delete：`active / deleted` | 缺失 |
| 唯一约束 | `(tenant_id, keyword_master_id)` | 同左 | 匹配 |

建议处理：

- 高优先级对齐。
- 主键类型冲突影响后续 API 和 FK，需要先决定修历史 migration 还是 forward migration。

### 3.3 lixiaoyun_raw_companies

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `20260430_0009` 已创建 | 需要创建 | 存在但旧口径 |
| 主键 | `bigserial` | `bigint identity` | 基本可接受，但命名需统一 |
| `keyword_master_id` | 缺失 | 必需 | 缺字段 |
| `task_id` | 存在且 NOT NULL FK | 不保留 | 多余且冲突 |
| `keyword_normalized` | 无 | 不保留 | 匹配 |
| `last_seen_at` | 存在 | 不保留 | 多余 |
| 唯一约束 | `UNIQUE(source_id)` | `UNIQUE(keyword_master_id, source_id)` | 冲突 |

建议处理：

- 需要改为按平台关键词去重。
- 需要移除或废弃 `task_id / last_seen_at`。

### 3.4 lixiaoyun_raw_contacts

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | 未发现迁移创建 | 需要创建 | 缺失 |
| 字段 | 无 | `raw_company_id, source_contact_id, name, position, email, phone, raw_payload, created_at` | 缺失 |
| 去重 | 无 | `(raw_company_id, source_contact_id)` 和 `(raw_company_id, email)` fallback | 缺失 |

建议处理：

- Batch 1 新建。

### 3.5 tendata_raw_companies

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `20260430_0009` 已创建 | 需要创建 | 存在但旧口径 |
| 主键 | `tid text PRIMARY KEY` | `id bigint identity` | 冲突 |
| source id | `tid` | `source_id text` 承接旧 `tid` | 需迁移/重命名 |
| `keyword_master_id` | 缺失 | 必需 | 缺字段 |
| `employee_num` | `int` | `text`，来源原始口径 | 冲突 |
| `task_id` | 存在 | 不保留 | 多余 |
| `last_seen_at` | 存在 | 不保留 | 多余 |
| 唯一约束 | 主键 `tid` | `UNIQUE(keyword_master_id, source_id)` | 冲突 |

建议处理：

- 这是 Batch 1 的核心表之一。
- 如果保留旧 `tid`，也应作为 `source_id` 数据迁移来源，而不是目标主键。

### 3.6 tendata_raw_contacts

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | 未发现迁移创建 | 需要创建 | 缺失 |
| 字段 | 无 | `raw_company_id, source_contact_id, name, position, email, phone, raw_payload, created_at` | 缺失 |
| 去重 | 无 | `(raw_company_id, source_contact_id)` 和 `(raw_company_id, email)` fallback | 缺失 |

建议处理：

- Batch 1 新建。

### 3.7 clean_companies

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `0009` 创建 bigserial，`0014` 又重建为 uuid | `bigint identity` | 当前 head 口径冲突 |
| 主键 | `uuid` | `bigint identity` | 冲突 |
| `name` | 存在 | 存在 | 匹配 |
| `name_normalized` | 存在 | 存在 | 匹配 |
| `reg_capital` | `text` | `numeric` | 冲突 |
| `employee_num` | `int` | `text` | 冲突 |
| `industry_tags` | `jsonb` | `text[]` | 冲突 |
| `product_tags` | `text[]` | `text[]` | 匹配 |
| `pcb_suppliers` | `0031` 新增 `text[] NOT NULL DEFAULT '{}'` | `text[]` | 基本匹配 |
| `data_completeness` | 存在 | 不保留 | 多余 |
| `sources` | 存在 | 不保留，改 `clean_company_sources` | 多余 |
| `updated_at` | 当前是 `last_updated` | `updated_at` | 冲突 |

建议处理：

- 主键类型是最大阻塞。
- 如果 0014 已执行到目标库，forward migration 将非常重；如果未执行，建议修正 0014。

### 3.8 clean_contacts

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `0014` 已创建 | 需要创建 | 存在但口径冲突 |
| 主键 | `uuid` | `bigint identity` | 冲突 |
| FK | `clean_company_id uuid` | `bigint` | 冲突 |
| 字段 | 多 `is_valid_email / sources / last_updated` | spec 不保留 | 多余 |
| email 类型 | `text` | `citext` | 冲突 |
| 唯一约束 | `0015` 加 `UNIQUE(clean_company_id, lower(email))` | `UNIQUE(clean_company_id, email) WHERE email IS NOT NULL` | 需调整 |

建议处理：

- 随 `clean_companies` 主键策略一起处理。

### 3.9 clean_company_sources

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | 未发现 `clean_company_sources`；旧迁移里有 `company_sources` 指向 `shared_companies` | 需要 `clean_company_sources` | 缺失 |
| source_type | 旧 `company_sources` 允许 `waimao_tong / tengdao / lixiaoyun` | V3 只允许 `tendata` | 冲突 |
| FK | 旧指向 `shared_companies` | 指向 `clean_companies` | 冲突 |

建议处理：

- Batch 1 新建 `clean_company_sources`。
- 旧 `company_sources` 是否保留/迁移需在 migration 策略中确认。

### 3.10 clean_company_keywords

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | 未发现 | 需要 | 缺失 |
| 逻辑 | 当前 `tenant_companies.matched_keywords` 或 `collection_keywords` 承载关键词关系 | 平台级事实表 | 冲突 |

建议处理：

- Batch 1 新建，Batch 2 定义迁移映射。

### 3.11 tenant_companies

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `0009` bigserial，`0014` 重建为 uuid | `bigint identity` | 当前 head 口径冲突 |
| FK | `clean_company_id uuid` | `bigint` | 冲突 |
| business_status | 旧枚举：`pending_score / scoring / ...` | `new / selected / in_plan / contacted / archived` 等待最终枚举实现 | 语义冲突 |
| data_status | 旧枚举：`incomplete / enriching / complete / enrichment_failed` | `ready / missing_contacts / insufficient_data` 等 | 语义冲突 |
| score 字段 | `total_score` | `model_score` + `score` | 冲突 |
| 调分字段 | `0025` 新增 `score_adjustment / score_adjusted_*` | 本期不保留 | 多余且已被用户明确否定 |
| matched keywords | `matched_keywords jsonb` | 不保留，改关联查询 | 多余 |
| note/tags | 当前 `notes` 和 `tags jsonb` | `note text` 和 `tags text[]` | 命名/类型冲突 |

建议处理：

- 需要强制纳入 Batch 1。
- `0025` 与当前用户决策直接冲突，必须处理。

### 3.12 tenant_contacts

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | canonical schema 创建，`0015` 修改 | 需要 | 存在但口径冲突 |
| 主键 | `uuid` | `bigint identity` | 冲突 |
| FK | `tenant_company_id uuid` + `clean_contact_id uuid` | `tenant_id + clean_contact_id + clean_company_id` bigint | 冲突 |
| 字段 | `grade / status / is_default / deleted_at` | `contact_status / is_sendable` | 冲突 |
| 可见性 | 当前强绑定 `tenant_company_id` | spec：公司可见则联系人可见，tenant_contacts 只 overlay 状态 | 语义冲突 |

建议处理：

- 随 tenant/clean 主键策略一起处理。
- 注意其他邮件表可能 FK 到 `tenant_contacts(id)`，forward migration 风险较高。

### 3.13 collection_runs

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| 表 | `0033` 已创建 | 需要 | 存在但口径冲突 |
| 主键 | `uuid` | `bigint identity` | 冲突 |
| keyword 字段 | 有 `keyword / keyword_normalized` 冗余 | spec 只需 `keyword_master_id` | 多余 |
| provider | 有 | 有 | 基本匹配 |
| stage | 缺失 | 必需 provider-specific | 缺字段 |
| triggered_by | 缺失 | 必需可空 FK | 缺字段 |
| triggered_tenant_id | 缺失 | 必需可空 FK | 缺字段 |
| provider/stage CHECK | 无 | 必需 | 缺失 |
| active run partial unique | 无 | 必需 | 缺失 |
| 索引 | `(keyword_master_id, provider, status)` | `(keyword_master_id, provider, stage, status)` | 需调整 |

建议处理：

- 如果 0033 未执行，建议修正 0033。
- 如果 0033 已执行，新增 forward migration，但 uuid→bigint 会牵连 `collection_tasks.run_id`。

### 3.14 collection_tasks

| 项 | 当前实现 | 当前 spec | 结论 |
|---|---|---|---|
| run_id | `uuid REFERENCES collection_runs(id)` | `bigint REFERENCES collection_runs(id)` | 随 collection_runs 主键冲突 |
| scheduled_biz_date | 已有 | 需要 | 匹配 |
| batch_no | 已有 | 需要 | 匹配 |
| page_size | 已有 | 需要 | 匹配 |
| cursor_snapshot | 已有 | 需要 | 匹配 |
| 索引 | `idx_collection_tasks_run_status(run_id, status)` | `INDEX(run_id, status, scheduled_at)` | 需补 scheduled_at |

建议处理：

- 除 `run_id` 类型和索引外，字段基本存在。

## 4. 额外实现偏差

### 4.1 API 仍是旧口径

当前代码中仍存在：

- `/admin/api/v1/collection-keywords`
- `/admin/api/v1/collection-keywords/trigger`
- `/admin/api/v1/collection-keywords/{keyword_normalized}/history`

这些路径仍围绕 `collection_keywords.keyword_normalized / source_types / stage1 / stage2` 工作。

当前 spec 需要：

- `/admin/api/v1/keywords`
- `/admin/api/v1/keywords/{keyword_master_id}/runs`
- `/admin/api/v1/collection-runs/{run_id}/tasks`
- raw / clean company APIs
- `/t/{tenant_slug}/api/v1/...` tenant routes

建议：

- 放到 Batch 3，不在 Batch 1 处理。

### 4.2 旧字段和用户决策冲突

明确冲突字段：

- `tenant_companies.matched_keywords`
- `tenant_companies.score_adjustment`
- `tenant_companies.score_adjusted_at`
- `tenant_companies.score_adjusted_by`
- `tenant_companies.score_adjust_reason`
- `clean_companies.data_completeness`
- `clean_companies.sources`
- raw 表 `task_id`
- raw 表 `last_seen_at`

这些字段不能在最终 schema 中继续作为 V3 真源。

## 5. Migration 策略待确认

Batch 0 到这里必须暂停，因为下一步取决于这些 migration 是否已经执行到目标数据库。

### 5.1 目标库只读查询结果

用户提供的数据库连接已做只读查询。连接串中的 `directConnection=true` 是非 PostgreSQL 参数，查询时仅在内存中移除该参数后连接。

第一次默认连接到了 `postgres` database，只看到 `postgres_log`，不是业务库。用户截图确认业务库名是 `clientget` 后，已重新连接 `/clientget` database 查询。

正确业务库查询结果：

| 项 | 结果 |
|---|---|
| current_database | `clientget` |
| current_schema | `public` |
| current_user | `postgres` |
| `alembic_version` | `20260507_0032` |
| 已存在关键表 | `clean_companies`, `clean_contacts`, `collection_keywords`, `collection_task_keywords`, `collection_tasks`, `keyword_master`, `lixiaoyun_raw_companies`, `tenant_companies`, `tenant_contacts`, `tenant_keyword`, `tendata_raw_companies` |
| 未存在关键表 | `collection_runs`, `lixiaoyun_raw_contacts`, `tendata_raw_contacts`, `clean_company_sources`, `clean_company_keywords` |

结论：

- `20260507_0014` 到 `20260507_0032` 已经在业务库执行。
- `20260508_0033_collection_runs.py` 尚未在业务库执行。
- 已执行的 `0014 / 0016 / 0017 / 0025 / 0031 / 0032` 不应直接改历史迁移来影响已存在库。
- 未执行的 `0033` 可以在实施前修正为当前 spec 的 `collection_runs / collection_tasks.run_id` 口径。
- 已存在表的 schema 偏差需要新增 forward migration 处理。

只读数据量核对：

| 表 | 行数 |
|---|---:|
| `clean_companies` | 0 |
| `clean_contacts` | 0 |
| `tenant_companies` | 0 |
| `tenant_contacts` | 0 |
| `keyword_master` | 2 |
| `tenant_keyword` | 4 |
| `lixiaoyun_raw_companies` | 1000 |
| `tendata_raw_companies` | 0 |
| `collection_keywords` | 6 |
| `collection_task_keywords` | 169 |
| `collection_tasks` | 155 |

迁移影响判断：

- clean / tenant 客户与联系人 4 张表当前为空，可以通过 forward migration 重建结构，但仍需处理依赖它们的 FK。
- `tenant_keyword` 有少量数据，需要保留并补 `keyword_raw / status / created_by`。
- `lixiaoyun_raw_companies` 有 1000 行，需要保留；不能 drop 后丢数据。
- `collection_tasks` 有 155 行，`0033` 添加 `run_id` 时必须保持 nullable，不得要求立即回填。

### 方案 A：修正既有未上线 migration

适用条件：

- `20260507_0014` 到 `20260508_0033` 尚未在共享/staging/生产目标库执行。
- 或当前确认的目标库没有 `alembic_version` 且没有业务表。

处理方式：

- 直接修正 `0014 / 0015 / 0016 / 0017 / 0025 / 0031 / 0033` 等迁移，使 migration 链最终产物符合当前 spec。
- 优点：历史债少，schema 干净。
- 风险：如果这些 migration 已经被某个目标库执行，改历史 migration 会导致环境不可复现。

### 方案 B：新增 forward migration

适用条件：

- `20260507_0014` 到 `20260508_0033` 已经在目标库执行。

处理方式：

- 新增下一号 migration，例如 `20260508_0034_v3_data_foundation_alignment.py`。
- 在 forward migration 中处理 uuid→bigint、删旧字段、新建缺失表、补约束索引。
- 优点：符合已执行迁移不可改原则。
- 风险：uuid→bigint 涉及多表 FK，迁移复杂度高，尤其会影响 `tenant_companies / tenant_contacts / clean_contacts / collection_tasks` 及邮件/评分相关 FK。

### 方案 C：混合策略（当前业务库推荐）

适用条件：

- 业务库已执行到 `20260507_0032`。
- repo 中 `20260508_0033` 还没执行到业务库。

处理方式：

- 修正尚未执行的 `20260508_0033_collection_runs.py`，让 `collection_runs` 和 `collection_tasks.run_id` 从一开始就符合当前 spec。
- 新增 `20260508_0034_v3_data_foundation_alignment.py`，只处理已经执行过的表与新增缺失表：
  - `tenant_keyword` 补 `keyword_raw / created_by / status`，并处理主键策略。
  - 新建 `lixiaoyun_raw_contacts / tendata_raw_contacts`。
  - 新建 `clean_company_sources / clean_company_keywords`。
  - 对 `clean_companies / clean_contacts / tenant_companies / tenant_contacts` 做 forward alignment。
- 不直接改已执行的 `0014` 到 `0032`。

优点：

- 遵守“已执行 migration 不改历史”的原则。
- 避免把尚未执行的 `0033` 也带着旧口径上线。

风险：

- 已执行表里 uuid→bigint 的字段口径冲突仍然复杂，需要 Batch 1 先写 schema introspection 测试，再决定具体迁移实现方式。

### 需要用户确认

请确认：

1. 是否确认 `clientget` 就是本次要实施的目标库？
2. 是否采用方案 C：修正未执行的 `0033` + 新增 `0034` forward alignment？

确认后才能进入 Batch 1。
