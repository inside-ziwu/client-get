# V3 Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` or `openspec-apply-change` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `v3-data-foundation` 从“规格审查通过”推进到“数据库骨架、迁移边界、API contract 可实施且可验证”。

**Architecture:** 先做现有实现 Gap Audit，再做数据库 schema 对齐，最后做迁移映射与 API 对齐。不要把 cleanup_service、worker runtime、Sealos、AI enrichment、competitor 重构、邮件、评分、群组混入本 change。

**Tech Stack:** FastAPI + PostgreSQL + Alembic + async SQLAlchemy connection layer + pytest + OpenSpec。

---

## 0. 当前状态

| 项 | 状态 |
|---|---|
| OpenSpec 审查 | `Spec Review Passed / Ready for Implementation` |
| OpenSpec validate | `openspec validate v3-data-foundation --strict` 通过 |
| tasks 进度 | `1/30 complete` |
| 已完成任务 | `T-DF-01`，仅表示 `triggered_tenant_id` 字段语义已确认并写入 design/spec，尚未执行 migration |
| 数据库实现 | 未按本版 12 表 schema 完成 |
| API 实现 | 未按本版 API contract 完成 |

## 1. 关键风险

后端并不是空白状态，已经存在多份 V3 相关 Alembic 迁移，且部分与当前已确认 schema 冲突：

| 文件 | 现状风险 |
|---|---|
| `backend/alembic/versions/20260430_0009_phase1_collection_schema.py` | 已建旧版 raw / clean / tenant 表，含 `task_id`、`last_seen_at` 等当前 schema 已移除字段 |
| `backend/alembic/versions/20260507_0014_t_df_31_data_model_v3.py` | 重建 `clean_companies / tenant_companies` 为 uuid 主键，和当前确认的 bigint 主键冲突 |
| `backend/alembic/versions/20260507_0016_keyword_master_tables.py` | `tenant_keyword` 当前是 uuid 主键，且缺少 `keyword_raw / created_by / status` |
| `backend/alembic/versions/20260507_0017_collection_keywords_master_fk.py` | keyword 归一规则和当前 spec 不完全一致 |
| `backend/alembic/versions/20260508_0033_collection_runs.py` | `collection_runs` 当前是 uuid 主键，缺 `stage / triggered_by / triggered_tenant_id`，且 provider/stage 约束不是当前口径 |

**结论：第一步不能直接写新 migration。必须先做 Batch 0 Gap Audit。**

## 2. 实施边界

本计划包含：

- 12 张 schema 表与约束/索引对齐
- `collection_runs` 与 `collection_tasks.run_id` 数据骨架对齐
- 旧 `collection_keywords / collection_task_keywords` 的迁移映射与兼容边界
- admin / tenant API contract 的后端路由与前端类型对齐计划
- OpenSpec tasks 状态维护

本计划不包含：

- cleanup_service raw → clean 清洗实现
- worker 调度、claim、执行逻辑
- Sealos / Docker 部署
- OpenRouter AI enrichment
- competitor 同行模型重构
- 邮件计划、群组、评分调分历史实现

## 3. Batch 0：现有实现 Gap Audit

**目标：** 先确认当前代码库和当前 spec 的差异，决定是“补增量迁移”还是“修正既有未上线迁移”。

**文件：**

- 读取：`/Users/lay/Documents/Github/client_get/openspec/changes/v3-data-foundation/design.md`
- 读取：`/Users/lay/Documents/Github/client_get/openspec/changes/v3-data-foundation/specs/data-foundation/spec.md`
- 读取：`/Users/lay/Documents/Github/client_get/backend/alembic/versions/*.py`
- 输出：`/Users/lay/Documents/Github/client_get/openspec/changes/v3-data-foundation/implementation-gap-audit.md`

- [ ] **Step 0.1：列出当前 Alembic 链**

Run:

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run alembic history --verbose
```

Expected:

- 能看到 `20260430_0009` 到 `20260508_0033` 的链路
- 记录当前 head 和每个 V3 相关 migration 的职责

- [ ] **Step 0.2：逐表做 spec vs migration 对照**

输出表格，至少覆盖：

```text
keyword_master
tenant_keyword
lixiaoyun_raw_companies
lixiaoyun_raw_contacts
tendata_raw_companies
tendata_raw_contacts
clean_companies
clean_contacts
clean_company_sources
clean_company_keywords
tenant_companies
tenant_contacts
collection_runs
collection_tasks
```

每张表记录：

- 当前 migration 是否存在
- 主键类型是否匹配
- 字段缺失/多余
- FK/unique/check/index 是否匹配
- 是否需要数据迁移
- 建议处理：`rewrite_unapplied_migration` / `add_forward_migration` / `leave_as_is`

- [ ] **Step 0.3：确认 migration 策略**

规则：

- 如果这些 20260507/20260508 migration 未在任何共享/staging/生产库执行，优先修正既有 migration，减少历史债。
- 如果已经执行过，必须新增 forward migration，不改历史 migration。
- 不能凭猜测决定，必须用目标数据库 `alembic_version` 或运维记录确认。

暂停点：

- 这里必须给用户确认一次 migration 策略。

## 4. Batch 1：数据库骨架对齐

**目标：** 让数据库结构对齐当前已确认 schema。只处理表、字段、约束、索引，不做 worker/cleanup/API 业务实现。

**对应 OpenSpec tasks：**

- `T-DF-10` 到 `T-DF-23`
- `T-DF-40` 到 `T-DF-43`

**文件：**

- 修改或新增：`/Users/lay/Documents/Github/client_get/backend/alembic/versions/*.py`
- 测试：`/Users/lay/Documents/Github/client_get/backend/tests/test_v3_data_foundation_schema.py`

- [ ] **Step 1.1：写 schema introspection 测试**

测试应验证：

- 12 张表存在
- bigint 主键表确实是 bigint/identity 口径
- `tenant_keyword` 含 `keyword_raw / created_by / status`
- raw 表不含 `task_id / keyword_normalized / last_seen_at`
- raw contact 有两条去重约束：`source_contact_id` 和 `email fallback`
- `clean_company_sources.source_type` V3 只允许 `tendata`
- `collection_runs` 含 `stage / triggered_by / triggered_tenant_id`
- `collection_runs` 有 active run partial unique
- `collection_tasks` 含 `run_id / scheduled_biz_date / batch_no / page_size / cursor_snapshot`

- [ ] **Step 1.2：运行测试确认失败**

Run:

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run pytest tests/test_v3_data_foundation_schema.py -v
```

Expected:

- 在迁移未对齐前失败
- 失败信息能指向缺失字段/约束/索引

- [ ] **Step 1.3：实现 migration 对齐**

按 Batch 0 用户确认的策略执行：

- 未执行历史 migration：修正既有 `0014 / 0016 / 0017 / 0033`
- 已执行历史 migration：新增下一号 forward migration，例如 `20260508_0034_v3_data_foundation_alignment.py`

必须保持：

- 不删除用户未确认的数据
- 不动 `docs/` 和 blueprint 非 backend 历史文件
- 不引入 cleanup_service 或 worker 逻辑

- [ ] **Step 1.4：运行迁移与 schema 测试**

Run:

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run alembic upgrade head
uv run pytest tests/test_v3_data_foundation_schema.py -v
```

Expected:

- Alembic upgrade 成功
- schema introspection 测试通过

- [ ] **Step 1.5：更新 OpenSpec task 勾选**

仅在验证通过后勾选：

- `T-DF-10` 到 `T-DF-23`
- `T-DF-40` 到 `T-DF-43`

## 5. Batch 2：旧数据迁移映射与兼容边界

**目标：** 定义并验证旧表到新表的迁移映射，不实现复杂 ETL。

**对应 OpenSpec tasks：**

- `T-DF-30`
- `T-DF-31`
- `T-DF-32`

**文件：**

- 输出：`/Users/lay/Documents/Github/client_get/openspec/changes/v3-data-foundation/migration-mapping.md`
- 可能修改：Alembic migration 或独立 migration helper
- 测试：`/Users/lay/Documents/Github/client_get/backend/tests/test_v3_data_foundation_migration_mapping.py`

- [ ] **Step 2.1：写迁移映射文档**

必须写清：

- `collection_keywords.keyword` → `keyword_master.keyword`
- 归一规则 → `keyword_master.keyword_normalized`
- `collection_keywords.tenant_id` → `tenant_keyword.tenant_id`
- `collection_keywords.keyword` 原文 → `tenant_keyword.keyword_raw`
- 旧 `collection_task_keywords` 只作为历史任务归属输入，不再作为目标真源
- raw / clean 旧数据只定义映射边界，具体 ETL 后续 change 处理

- [ ] **Step 2.2：写最小迁移测试**

测试输入：

- 同一租户重复关键词
- 不同租户同一归一关键词
- `P.C.B` / `pcb` / `PCB ` 等价
- `FR-4` 不与 `FR4` 合并
- 软删恢复不刷新 `created_at`

- [ ] **Step 2.3：实现或修正迁移逻辑**

只做 keyword 迁移必要逻辑，不迁 raw → clean。

- [ ] **Step 2.4：验证并勾选任务**

Run:

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run pytest tests/test_keyword_service.py tests/test_v3_data_foundation_migration_mapping.py -v
```

通过后勾选 `T-DF-30` 到 `T-DF-32`。

## 6. Batch 3：API Contract 对齐

**目标：** 后端路由和前端 shared-api 类型对齐 schema。只做 contract，不做 worker/cleanup。

**对应 OpenSpec tasks：**

- `T-DF-50`
- `T-DF-51`
- `T-DF-52`
- `T-DF-53`

**文件：**

- 可能修改：`/Users/lay/Documents/Github/client_get/backend/app/api/admin/collection.py`
- 可能修改：`/Users/lay/Documents/Github/client_get/backend/app/api/tenant/*.py`
- 可能修改：`/Users/lay/Documents/Github/client_get/backend/app/services/admin_collection_service.py`
- 可能修改：`/Users/lay/Documents/Github/client_get/backend/app/services/tenant_query_service.py`
- 可能修改：`/Users/lay/Documents/Github/client_get/frontend/packages/shared-api/src/**/*.ts`

- [ ] **Step 3.1：输出 API route matrix**

创建或更新：

```text
openspec/changes/v3-data-foundation/api-route-matrix.md
```

必须覆盖：

- admin keywords
- admin collection runs/tasks
- admin raw lixiaoyun/tendata companies
- admin clean companies
- tenant keywords
- tenant companies list/detail
- tenant company contacts

- [ ] **Step 3.2：后端 contract 测试**

新增测试：

```text
backend/tests/test_v3_data_foundation_api_contract.py
```

验证：

- tenant company detail `{id}` 是 `clean_companies.id`
- tenant 可见性通过 `clean_company_keywords + tenant_keyword`
- raw API 默认不返回 `raw_payload`
- source filter 使用 `clean_company_sources.source_type`

- [ ] **Step 3.3：实现最小 API 对齐**

只实现 contract 必需字段和查询，不做：

- 实际采集触发 worker
- cleanup raw → clean
- 评分/群组/邮件计划逻辑

- [ ] **Step 3.4：前端 shared-api 类型对齐**

更新 shared-api 类型，使 tenant/admin 前端字段名和 API 返回一致。

- [ ] **Step 3.5：验证并勾选任务**

Run:

```bash
cd /Users/lay/Documents/Github/client_get/backend
uv run pytest tests/test_v3_data_foundation_api_contract.py -v

cd /Users/lay/Documents/Github/client_get/frontend
pnpm -r typecheck
```

通过后勾选 `T-DF-50` 到 `T-DF-53`。

## 7. Batch 4：最终验证与交接

**目标：** 确认本 change 可以作为后续 collection / cleanup / tenant companies 实现基准。

**对应 OpenSpec tasks：**

- `T-DF-90`
- `T-DF-91`
- `T-DF-92`

- [ ] **Step 4.1：OpenSpec strict validate**

Run:

```bash
cd /Users/lay/Documents/Github/client_get
openspec validate v3-data-foundation --strict
```

Expected:

- `Change 'v3-data-foundation' is valid`

- [ ] **Step 4.2：范围残留检查**

Run:

```bash
cd /Users/lay/Documents/Github/client_get
rg -n "cleanup_service|worker base|Sealos|OpenRouter|AI 回填|competitor 重构" openspec/changes/v3-data-foundation
```

Expected:

- 只允许出现在“Non-Goals / Scope Boundary / 不包含”语境

- [ ] **Step 4.3：任务清单核对**

Run:

```bash
cd /Users/lay/Documents/Github/client_get
openspec instructions apply --change "v3-data-foundation" --json
```

Expected:

- 已完成任务和实际验证证据一致
- 没有把“文档确认”误标为“migration 已执行”

- [ ] **Step 4.4：用户签字**

用户确认：

```text
v3-data-foundation implementation accepted
```

确认后再勾选 `T-DF-92`。

## 8. 推荐执行顺序

1. 先做 Batch 0，不写代码，只产出 `implementation-gap-audit.md`。
2. 用户确认 migration 策略。
3. 再进入 Batch 1 数据库骨架。
4. Batch 1 验证通过后，再决定是否马上进入 Batch 2。

## 9. 不变量

- 不在本 change 实现 cleanup_service。
- 不在本 change 实现 worker 调度/领取/执行。
- 不在本 change 实现 AI enrichment。
- 不再把 `collection_keywords / collection_task_keywords` 当 V3 真源。
- 租户侧 company detail `{id}` 是 `clean_companies.id`。
- 租户可见性通过 `clean_company_keywords + tenant_keyword` 判断。
- 励销云 raw 不进入 `clean_company_sources`。
- `source_type` V3 只允许 `tendata`。
