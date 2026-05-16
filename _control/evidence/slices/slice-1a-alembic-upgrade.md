# Slice 1.A — alembic 0006 → 0013 升级

> **状态**：✅ 已签字（2026-05-07）
> **能力域**：C8-G3
> **针对缺口**：C8-G3（alembic 升级）+ F1（ORM 层文档化）+ F2（schema.sql 对齐）
> **验收标准**：Sealos 真实 DB `alembic current` = `20260501_0013_drop_ai_fallback`；schema.sql 与实际库结构完全对齐

---

## 0. 前置状态

| 环境 | alembic head | 备注 |
|---|---|---|
| 本地 docker-compose | `20260501_0013_drop_ai_fallback` ✅ | Slice 0 已验证 |
| Sealos 生产 DB | `20260423_0006_email_template_design` 🔴 | 落后 7 个迁移 |

**Slice 1.A 目标**：将 Sealos 生产 DB 从 0006 升级到 0013，并修复 F1/F2 文档缺口。

---

## 1. 迁移风险矩阵（0007～0013）

| 迁移 | 内容摘要 | 风险等级 | 说明 |
|---|---|:-:|---|
| **0007** `collection_task_type` | `collection_tasks` ADD COLUMN task_type/context（有 DEFAULT）| 🟢 低 | ADD COLUMN WITH DEFAULT，无锁风险；不影响存量行 |
| **0008** `competitor_enrichment` | `competitor_companies` ADD COLUMN IF NOT EXISTS ×11（有 DEFAULT）；CREATE TABLE `competitor_contacts` + 索引 | 🟢 低 | 全部用 IF NOT EXISTS；ADD COLUMN WITH DEFAULT；新表无依赖 |
| **0009** `phase1_collection_schema` | **DROP TABLE tenant_companies CASCADE**；CREATE TABLE tenant_companies (id **bigserial**)；CREATE TABLE clean_companies / lixiaoyun_raw_companies / waimaotong_raw_companies / cleanup_queue | 🔴 **高风险** | 见下方 §1.1 |
| **0010** `add_default_partitions` | 为 audit_logs / emails / intelligence_articles 创建 DEFAULT 分区 | 🟢 低 | CREATE TABLE IF NOT EXISTS；仅追加分区，无破坏性 |
| **0011** `drop_ai_model_pricing_columns` | `ai_models` DROP COLUMN input_price / output_price | 🟡 中 | 确认 admin_config_service.py 的 put_ai_pricing 已是 no-op 后安全；本地已验证通过 |
| **0012** `waimaotong_raw_contacts` | CREATE TABLE waimaotong_raw_contacts + 索引 | 🟢 低 | 新表，D-035 已决策 V3 期间空表保留 |
| **0013** `drop_ai_fallback` | `ai_models` DROP COLUMN model_type；`ai_scene_defaults` DROP COLUMN fallback_model_ids | 🟡 中 | 确认无代码读写这两列后安全；本地已验证通过 |

### 1.1 迁移 0009 高风险说明

**问题**：`DROP TABLE tenant_companies CASCADE` 会删除所有引用 `tenant_companies(id)` 的 FK 约束（包括 `sending_plan_recipients.tenant_company_id uuid`），然后以 `id bigserial` 重建。JOIN 时出现 `bigint = uuid` 类型不匹配，sending worker 崩溃。

**影响范围**：
- `sending_plan_recipients.tenant_company_id`（uuid）→ 引用 `tenant_companies.id`（bigint）→ **JOIN 崩溃**
- `scoring_jobs.tenant_company_id`（uuid）→ 可能受影响
- `company_scores.tenant_company_id`（uuid）→ 可能受影响

**处置决策**（已在 Slice 0 §2.3.1 记录）**：
- 该迁移在本地已成功应用（未报 DDL 错误）
- sending worker crash 是运行时错误，不阻塞迁移本身
- **修复归 Slice 1.B T-DF-31**：新建修复迁移，将 `tenant_companies.id` 改回 `uuid`，重建 FK

**生产操作建议**：升级前做 `pg_dump` 全量备份（见 §3.1）。

---

## 2. F1 缺口（文档化，无代码变更）

**F1**：`backend/app/models/` 目录为空——后端不使用 SQLAlchemy ORM，所有数据访问通过 `repositories/` 中的原始 SQL（asyncpg）。

| 影响 | 说明 |
|---|---|
| ORM 生成工具 | 不适用（无 ORM layer，无法用 sqlacodegen / alembic autogenerate）|
| 数据访问模式 | 所有 SQL 写在 repositories/*.py 中，手动维护 |
| 类型检查 | 依赖 Python 类型注解 + 运行时验证，无 ORM 类型映射保障 |
| V3 实施影响 | 所有新表的数据访问均需手写 repository 函数，无 ORM 自动生成 |

**结论**：F1 不是需要修复的 Bug，是架构选型（原始 SQL）。已在 `_control/v3/slices/slice-0-dev-runtime-baseline.md` §2.3.1 记录。

---

## 3. F2 缺口修复——schema.sql 对齐（已完成）

`backend/03_database/schema.sql` 代表初始 schema（alembic 0001 加载点）+ V3 设计目标，但迁移 0003～0013 的增量变更从未回写。Slice 1.A 已完成以下修复：

### 3.1 新增表

| 表 | 来源迁移 | 说明 |
|---|---|---|
| `scoring_jobs` | 0003 | 评分任务队列，含 RLS 策略 |
| `competitor_contacts` | 0008 | 竞品联系人，含唯一索引 |
| `waimaotong_raw_contacts` | 0012 | 外贸通原始联系人（V3 期间空表，D-035）|

### 3.2 补全列

| 表 | 新增列（来源） |
|---|---|
| `collection_tasks` | `task_type varchar(50)`, `context jsonb`（0007）|
| `competitor_companies` | `source_id`, `company_name_en`, `esdate`, `legalperson`, `reg_capital`, `paid_capital`, `reg_address`, `contact_address`, `employee_scale`, `uncid`, `updated_at`（0008）|

### 3.3 删除已废弃列

| 表 | 删除列（来源） |
|---|---|
| `ai_models` | `model_type`（0013）、`input_price`（0011）、`output_price`（0011）|
| `ai_scene_defaults` | `fallback_model_ids`（0013）|

### 3.4 未修复（Slice 1.B 处理）

| 项 | 实际 DB（post-0009）| schema.sql（V3 目标）| 处理 |
|---|---|---|---|
| `tenant_companies.id` 类型 | `bigserial` | `uuid` | T-DF-31 修复迁移 |
| 新增表 | `clean_companies`, `lixiaoyun_raw_companies`, `waimaotong_raw_companies`, `cleanup_queue` | 缺失 | Slice 1.B D-008=B 重构时补入 |

---

## 4. Sealos 升级操作手册（用户执行）

### 4.1 Step 1：备份（必须）

```bash
# 连接到 Sealos 数据库（替换实际连接信息）
pg_dump \
  --host <sealos-db-host> \
  --port 5432 \
  --username postgres \
  --dbname clientget \
  --format custom \
  --file clientget-pre-0013-$(date +%Y%m%d%H%M%S).dump

# 验证备份完整性
pg_restore --list clientget-pre-0013-*.dump | tail -5
```

> ⚠️ **备份文件不要进 git**，保存到本地或 Sealos 对象存储（加密）。参见 D-017-B.2。

### 4.2 Step 2：确认 Sealos backend pod 名称

```bash
kubectl get pods -n <your-namespace> | grep backend
# 示例输出：
# clientget-backend-7d9f5b-xxxx   1/1   Running   0   2d
```

### 4.3 Step 3：在 backend pod 内执行 alembic 升级

```bash
# 方法 A：kubectl exec（推荐）
kubectl exec -it <backend-pod-name> -n <your-namespace> \
  -- python -m alembic upgrade head

# 方法 B：单次 Job（如 pod 不稳定时用）
kubectl run alembic-upgrade \
  --image=<your-backend-image> \
  --restart=Never \
  --env="DATABASE_URL=<db-url>" \
  --command -- python -m alembic upgrade head
```

### 4.4 Step 4：验证

```sql
-- ① 确认 alembic head
SELECT version_num, is_current FROM alembic_version;
-- 期望：20260501_0013_drop_ai_fallback

-- ② 确认新表存在
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'clean_companies', 'lixiaoyun_raw_companies',
    'waimaotong_raw_companies', 'cleanup_queue',
    'waimaotong_raw_contacts', 'scoring_jobs',
    'competitor_contacts'
  )
ORDER BY table_name;

-- ③ 确认 0009 的已知类型漂移（预期：bigint，Slice 1.B 修复）
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenant_companies' AND column_name = 'id';

-- ④ 确认 0011/0013 的列删除生效
SELECT column_name FROM information_schema.columns
WHERE table_name = 'ai_models'
  AND column_name IN ('model_type', 'input_price', 'output_price');
-- 期望：0 行

SELECT column_name FROM information_schema.columns
WHERE table_name = 'ai_scene_defaults'
  AND column_name = 'fallback_model_ids';
-- 期望：0 行

-- ⑤ 确认 collection_tasks 有新列
SELECT column_name FROM information_schema.columns
WHERE table_name = 'collection_tasks'
  AND column_name IN ('task_type', 'context');
-- 期望：2 行
```

---

## 5. 回滚预案

### 5.1 快速回滚（alembic downgrade）

```bash
# 回滚到 0006（需按迁移倒序，各迁移均有 downgrade()）
kubectl exec -it <backend-pod-name> -n <your-namespace> \
  -- python -m alembic downgrade 20260423_0006

# ⚠️ 注意：0009 的 downgrade() 会 DROP clean_companies 等表（有 CASCADE）
# 如已有生产数据写入，需先备份这些表
```

### 5.2 从备份恢复（全量还原）

```bash
# 恢复备份（将覆盖当前整个 clientget 数据库）
pg_restore \
  --host <sealos-db-host> \
  --port 5432 \
  --username postgres \
  --dbname clientget \
  --clean \
  --if-exists \
  clientget-pre-0013-<timestamp>.dump
```

### 5.3 回滚决策树

```
升级失败？
  ├─ DDL 错误（非 0009 相关）→ 立即 pg_restore 全量还原
  ├─ 0009 相关 DDL 错误（极少）→ pg_restore 全量还原
  └─ 升级成功但 backend crash
       ├─ sending worker crash（bigint=uuid）→ 已知，Slice 1.B 修复，不回滚
       └─ 其他 crash → 检查日志 → 视情况决定
```

---

## 6. 已知升级后问题（不阻塞 Slice 1.A 验收）

| 问题 | 原因 | 修复 Slice |
|---|---|---|
| sending worker crash（bigint = uuid）| migration 0009 把 tenant_companies.id 改为 bigserial | Slice 1.B T-DF-31 |

---

## 7. 验收标准检查表

- [x] Sealos `alembic current` = `20260501_0013_drop_ai_fallback` ✅ 2026-05-07
- [x] `scoring_jobs` 表存在 ✅
- [x] `competitor_contacts` 表存在 ✅
- [x] `waimaotong_raw_contacts` 表存在 ✅
- [x] `clean_companies` / `cleanup_queue` 表存在（0009 创建）✅
- [x] `ai_models` 无 `model_type` / `input_price` / `output_price` 列 ✅
- [x] `collection_tasks` 有 `task_type` 和 `context` 列 ✅
- [x] F2 fix：`backend/03_database/schema.sql` 已更新并提交（commit `044decd`）✅
- [x] pg_dump 备份已留档：`clientget-pre-0013-20260507050729.dump`（4.3 MB）✅

已知升级后问题（不阻塞）：
- sending worker crash（bigint = uuid）← Slice 1.B T-DF-31 修复

签字行：

- [x] lay · 2026-05-07
