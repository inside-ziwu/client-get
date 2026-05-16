---
title: "tenant_companies.id bigint/uuid 类型不匹配导致 sending worker 崩溃"
date: 2026-05-07
category: database-issues
module: blueprint
problem_type: database_issue
component: database
symptoms:
  - "sending worker --once 立即崩溃，退出码非零"
  - "asyncpg.exceptions.UndefinedFunctionError: operator does not exist: bigint = uuid"
  - "堆栈指向 tenant_messaging_service.py:1205 claim_due_emails() 中的 JOIN 语句"
root_cause: config_error
resolution_type: migration
severity: high
tags: [schema-mismatch, type-mismatch, alembic, postgresql, sending-worker, v3-migration]
---

# tenant_companies.id bigint/uuid 类型不匹配导致 sending worker 崩溃

## Problem

migration `20260430_0009_phase1_collection_schema.py` 用 `DROP TABLE tenant_companies CASCADE` + `CREATE TABLE tenant_companies (id bigserial PRIMARY KEY, ...)` 重建了表，导致 `tenant_companies.id` 从 uuid 变为 bigint，而 `sending_plan_recipients.tenant_company_id uuid` 未被修改，sending worker 在执行 JOIN 查询时抛出 `operator does not exist: bigint = uuid` 并崩溃。

## Symptoms

- 运行 `python scripts/run_sending_worker.py --once` 立即崩溃，退出码非零
- 错误信息：`asyncpg.exceptions.UndefinedFunctionError: operator does not exist: bigint = uuid`
- 堆栈顶层指向 `app/services/tenant_messaging_service.py:1205`，函数 `claim_due_emails()`
- 崩溃位于 `JOIN tenant_companies tc ON tc.id = pr.tenant_company_id` 这一行
- PostgreSQL 不会在运行时自动转换 bigint 与 uuid，直接报"operator does not exist"
- `alembic current` 显示迁移链已完整应用，表面上看没有异常

## What Didn't Work

- 检查 ORM 模型目录（`models/`）无收获——目录为空，所有 SQL 均为原始文本，无 SQLAlchemy 类型注解可对照
- 错误发生在 JOIN 而非 WHERE 子句，排查重点曾短暂偏向过滤参数，方向有误
- `alembic history` 显示迁移链完整，未能直接暴露 DROP+recreate 引入的类型回退问题
- 单看 migration 0009 的 DDL 语句本身是合法的，Alembic 不会在应用时报错

## Solution

**第一步：用 psql 确认诊断**

```sql
-- 查 tenant_companies 实际主键类型
\d tenant_companies
-- 实际结果：id | bigint not null default nextval('tenant_companies_id_seq')
-- 设计目标：id | uuid PRIMARY KEY

-- 查 sending_plan_recipients 外键列类型
\d sending_plan_recipients
-- 结果：tenant_company_id | uuid not null（无 FK 约束）
```

两列类型不一致，JOIN 时 PostgreSQL 找不到 `bigint = uuid` 的运算符。

**第二步：定位根因（migration 0009 问题片段）**

```python
# 20260430_0009_phase1_collection_schema.py
op.execute("DROP TABLE IF EXISTS tenant_companies CASCADE")
op.execute("""
    CREATE TABLE tenant_companies (
        id bigserial PRIMARY KEY,   -- ← 与早期迁移定义的 uuid 不符
        ...
    )
""")
```

**第三步：修复路径（已登记为 Slice 1.B — T-DF-31，尚未实施）**

```python
# 修复迁移（待实施）
op.execute("DROP TABLE IF EXISTS tenant_companies CASCADE")
op.execute("""
    CREATE TABLE tenant_companies (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),  -- ← 与设计目标一致
        ...
    )
""")
# 重建 sending_plan_recipients 的外键约束
op.execute("""
    ALTER TABLE sending_plan_recipients
        ADD CONSTRAINT fk_spr_tenant_company
        FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id)
""")
```

修复后验证：`\d tenant_companies` 的 id 列应为 `uuid`；`\d sending_plan_recipients` 中外键约束应重新出现。

## Why This Works

`DROP TABLE ... CASCADE` 会级联删除所有引用该表的外键约束（FK），但**不会修改引用方列的数据类型**。这导致了跨迁移的静默类型回退：

1. 早期迁移创建 `sending_plan_recipients.tenant_company_id uuid`，并建立 FK 指向 `tenant_companies(id uuid)`
2. migration 0009 执行 `DROP TABLE tenant_companies CASCADE`——FK 约束被删除，但 `sending_plan_recipients.tenant_company_id` 列仍是 `uuid`
3. migration 0009 随即以 `id bigserial` 重建 `tenant_companies`——新表主键是 bigint
4. 此时两张表之间不存在 FK 约束（已被 CASCADE 删除），PostgreSQL 不会在 DDL 层面报错
5. 直到 JOIN 执行时，查询优化器尝试匹配 `bigint = uuid`，找不到对应运算符，抛出运行时错误

本质上，`DROP CASCADE` + 类型变更重建是一种**静默的跨迁移类型回退**，Alembic 的迁移链检查无法捕捉，因为每一步单独看都是合法的 DDL。

## Prevention

**1. DROP CASCADE 前先扫描所有引用方**

在执行 `DROP TABLE ... CASCADE` 前，运行以下查询记录所有引用方表和列类型，迁移后逐一验证：

```sql
SELECT conrelid::regclass AS referencing_table,
       conname AS constraint_name,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE confrelid = 'tenant_companies'::regclass
  AND contype = 'f';
```

迁移后对照确认每个 `referencing_table` 的外键列类型与新主键类型一致。

**2. 同迁移内修复引用方列类型**

若必须用 DROP+类型变更重建，应在同一迁移中显式修复所有引用方列类型：

```python
# 先修改引用方列类型，再 DROP + 重建
op.execute("ALTER TABLE sending_plan_recipients ALTER COLUMN tenant_company_id TYPE uuid USING tenant_company_id::uuid")
op.execute("DROP TABLE IF EXISTS tenant_companies CASCADE")
op.execute("CREATE TABLE tenant_companies (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), ...)")
op.execute("ALTER TABLE sending_plan_recipients ADD CONSTRAINT fk_spr_tenant_company FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id)")
```

**3. Worker `--once` 冒烟测试纳入每次迁移后的验证清单**

四个 worker 均应在每次 `alembic upgrade head` 后以 `--once` 验证一次，可暴露 SQL 运行时类型错误：

```bash
uv run python scripts/run_collection_worker.py --once
uv run python scripts/run_collection_scheduler_worker.py --once
uv run python scripts/run_scoring_worker.py --once
uv run python scripts/run_sending_worker.py --once
```

**4. 不要把 `alembic check` 等同于 schema 健康**

`alembic check` 仅验证迁移是否已应用，不验证 schema 正确性。DROP+类型变更引入的静默漂移不会被它捕捉。

**5. 可选：用 migra 做 schema diff**

每次迁移后用 `migra` 对比目标 schema（`schema.sql`）与实际数据库，类型差异作为阻塞错误处理：

```bash
pip install migra
migra postgresql://user:pass@localhost/target_db postgresql://user:pass@localhost/actual_db
# 输出为空 = schema 一致；有输出 = 存在漂移
```

**6. 同类风险排查**

任何在 migration 0009 之前建立了指向 `tenant_companies(id)` 的 uuid 外键的表，均可能存在相同的类型漂移，建议用以下查询扫描：

```sql
SELECT c.table_name, c.column_name, c.data_type
FROM information_schema.columns c
WHERE c.column_name LIKE '%tenant_company_id%'
   OR (c.column_name = 'tenant_company_id');
```

## Related Issues

- **T-DF-31**（Slice 1.B）：计划迁移，将 `tenant_companies.id` 修复回 `uuid`，并重建相关外键约束
- **`_control/v3/slices/slice-0-dev-runtime-baseline.md` §2.3.1**：本 bug 的实测发现记录（2026-05-07），含影响范围与修复时机
- **`_control/inputs/database/README.md`**：数据库设计目标，`schema.sql` 中 `tenant_companies.id uuid PRIMARY KEY` 是签字确认的目标状态
