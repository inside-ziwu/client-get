---
title: "Alembic 迁移预清理非 CASCADE FK 链，修复租户数据源切换导致的启动 crash-loop"
date: 2026-05-19
category: database-issues
module: alembic-migration
problem_type: database_issue
component: database
severity: critical
symptoms:
  - "Sealos 后端 Pod 进入 crash-loop，无法启动"
  - "psycopg.errors.ForeignKeyViolation: sequence_enrollments_plan_recipient_id_fkey 阻塞 sending_plan_recipients 删除"
  - "group_members / company_scores 的 RESTRICT FK 阻塞 tenant_companies 删除"
  - "group_members.tenant_contact_id RESTRICT FK 阻塞 tenant_contacts 删除"
root_cause: missing_workflow_step
resolution_type: migration
tags:
  - alembic
  - foreign-key
  - cascade
  - restrict
  - migration
  - crash-loop
  - tenant-companies
---

# Alembic 迁移预清理非 CASCADE FK 链，修复租户数据源切换导致的启动 crash-loop

## Problem

Alembic 迁移 `20260519_0045`（将 tenant 端数据源从 `clean_companies` 切换到 `waimaotong_clean_companies`）在 Sealos 线上执行时，`DELETE FROM tenant_companies` 触发级联删除 `sending_plan_recipients`，但 `sequence_enrollments.plan_recipient_id` 引用 `sending_plan_recipients(id)` 而无 CASCADE，导致 `ForeignKeyViolation` 异常，后端 Pod 反复崩溃。

## Symptoms

- 后端 Pod 进入 crash-loop（`Back-off restarting failed container`）
- 容器日志报错：
  ```
  psycopg.errors.ForeignKeyViolation: update or delete on table "sending_plan_recipients"
  violates foreign key constraint "sequence_enrollments_plan_recipient_id_fkey" on table "sequence_enrollments"
  DETAIL: Key (id)=(019e14df-06f0-7c5a-97b8-aa89d457332d) is still referenced from table "sequence_enrollments".
  [SQL: DELETE FROM tenant_companies WHERE clean_company_id NOT IN (SELECT id FROM waimaotong_clean_companies);]
  ```
- CI 空库构建通过，仅在有业务数据的线上环境触发

## What Didn't Work

1. **仅添加 CTE 去重步骤**：解决了 `(tenant_id, clean_company_id)` 的 UNIQUE 冲突（多个 clean_companies 映射到同一 wmt 公司），但未触及 `sequence_enrollments.plan_recipient_id` 的 RESTRICT FK，Pod 仍然 crash-loop。
2. **依赖 CASCADE 自动清理**：`tenant_companies → sending_plan_recipients` 有 CASCADE，但链路在 `sequence_enrollments.plan_recipient_id`（无 CASCADE）处断裂，无法级联到底。

## Solution

修改迁移脚本 `backend/alembic/versions/20260519_0045_tenant_wmt_datasource_migration.py`，在任何 `DELETE FROM tenant_companies` 或 `DELETE FROM tenant_contacts` 之前，按依赖逆序显式清理子表。

**Step 1 — 清空整条发送链（后续 tenant_contacts 全表清空会使所有发送数据失效）：**

```python
conn.exec_driver_sql("DELETE FROM email_send_locks;")
conn.exec_driver_sql("DELETE FROM emails;")
conn.exec_driver_sql("DELETE FROM sequence_enrollments;")
conn.exec_driver_sql("DELETE FROM sending_plan_recipients;")
```

**Step 2 — 去重删除前，先清理有 RESTRICT FK 的子表：**

```python
_dedup_cte = """
    WITH dedup AS (
        SELECT tc.id AS tc_id,
            ROW_NUMBER() OVER (PARTITION BY tc.tenant_id, wc.id
                ORDER BY tc.score DESC NULLS LAST, tc.id) AS rn
        FROM tenant_companies tc
        JOIN clean_companies cc ON cc.id = tc.clean_company_id
        JOIN waimaotong_clean_companies wc
            ON wc.company_name = cc.name AND wc.country_iso3 = cc.country_iso3
    )
"""
conn.exec_driver_sql(_dedup_cte + "DELETE FROM group_members WHERE tenant_company_id IN (...);")
conn.exec_driver_sql(_dedup_cte + "DELETE FROM company_scores WHERE tenant_company_id IN (...);")
conn.exec_driver_sql(_dedup_cte + "DELETE FROM scoring_jobs WHERE tenant_company_id IN (...);")
conn.exec_driver_sql(_dedup_cte + "DELETE FROM tenant_companies WHERE id IN (...);")
```

**Step 3 — 删除 tenant_contacts 前 NULL 掉 RESTRICT FK：**

```python
conn.exec_driver_sql("UPDATE group_members SET tenant_contact_id = NULL WHERE tenant_contact_id IS NOT NULL;")
conn.exec_driver_sql("DELETE FROM tenant_contacts;")
```

## Why This Works

`backend/03_database/schema.sql` 中 FK 约束定义不一致：

| 表 | FK 列 | 删除行为 |
|---|---|---|
| `scoring_jobs.tenant_company_id` | `ON DELETE CASCADE` | 自动清理 |
| `group_members.tenant_company_id` | RESTRICT（默认） | 阻塞删除 |
| `company_scores.tenant_company_id` | RESTRICT（默认） | 阻塞删除 |
| `sending_plan_recipients.tenant_company_id` | CASCADE（0038 迁移追加） | 自动清理 |
| `sequence_enrollments.plan_recipient_id` | RESTRICT（默认） | **链路断裂点** |
| `email_send_locks.enrollment_id` | RESTRICT（默认） | 阻塞删除 |
| `group_members.tenant_contact_id` | RESTRICT（默认） | 阻塞删除 |

CASCADE 链在 `sequence_enrollments.plan_recipient_id` 处断裂：`tenant_companies` → CASCADE → `sending_plan_recipients` → **NO CASCADE** → `sequence_enrollments`。迁移 0014 还通过 `ADD CONSTRAINT ... EXCEPTION WHEN duplicate_object` 追加了 RESTRICT FK，可能在同列形成双重约束。

通过按依赖逆序显式删除子表，完全绕过 CASCADE/RESTRICT 混杂的歧义。

## Prevention

1. **写迁移脚本前先查 FK 依赖图**：
   ```sql
   SELECT conname, conrelid::regclass, confrelid::regclass, confdeltype
   FROM pg_constraint WHERE confrelid IS NOT NULL;
   ```
   `confdeltype` 中 `a`=NO ACTION, `c`=CASCADE, `r`=RESTRICT。

2. **用线上数据快照测试迁移**：CI 空库通过不等于线上有数据时通过。执行 `./scripts/sync_prod_db_to_local.sh` 同步后再本地跑迁移。

3. **对批量 DELETE 涉及的表，优先显式清理子表**：不要假设 CASCADE 会处理全链路，RESTRICT FK 是隐形地雷。

4. **迁移执行顺序模板**：清空叶节点表 → 逐层向上清理 → 最后操作根表。涉及 NULL-able RESTRICT FK 列，先 `UPDATE SET NULL` 再 DELETE 父表。

## Related Issues

- [tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md](../database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md) — 同为 `tenant_companies` Alembic 迁移中的 FK 链路问题（DROP CASCADE 导致类型回退）
- [fk-column-migration-null-old-values-before-constraint-2026-05-07.md](../best-practices/fk-column-migration-null-old-values-before-constraint-2026-05-07.md) — FK 列迁移模式：先 NULL 旧值再加约束
- Git commit: `eaa763a fix: 迁移脚本预清理非 CASCADE FK 链，修复启动 crash-loop`
