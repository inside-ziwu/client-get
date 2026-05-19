---
title: "Alembic FK 列迁移：旧 UUID 无法映射到新目标表时的 NULL 置空模式"
date: 2026-05-07
category: best-practices
module: database-migrations
problem_type: best_practice
component: database
severity: high
applies_when:
  - "需要将 FK 列指向新目标表，且旧数据 UUID 无法映射到新表记录时"
  - "旧被引用表已被中间迁移删除，新表使用 gen_random_uuid() 全新主键"
  - "新旧表之间无主键对应关系，无法做 UPDATE JOIN 数据迁移"
symptoms:
  - "直接 RENAME + ADD FK 导致 foreign key constraint violation（旧 UUID 不在新目标表中）"
  - "旧列带 NOT NULL 约束，UPDATE SET NULL 时报 not-null constraint 错误"
resolution_type: migration
related_components:
  - service_object
tags:
  - alembic
  - foreign-key
  - rename-column
  - null-safe-migration
  - partial-unique-index
  - on-delete-set-null
  - postgresql
  - database-migrations
---

# Alembic FK 列迁移：旧 UUID 无法映射到新目标表时的 NULL 置空模式

## Context

在 Alembic 迁移链中，当一张表的 FK 列需要改为指向新目标表，但旧列中的 UUID 值与新目标表的主键之间**不存在任何可靠映射**时，常规的 RENAME + ADD CONSTRAINT 方式会直接失败。

**ClientGet 具体场景（migration 0015）**

`tenant_contacts.contact_id uuid NOT NULL REFERENCES shared_contacts(id)` 需要改为
`clean_contact_id uuid REFERENCES clean_contacts(id)`。

- Migration 0009 删除了 `shared_companies`，断开了 `shared_contacts.company_id` 与公司记录的关联
- Migration 0014 创建了 `clean_companies` 和 `clean_contacts`，两者均使用 `gen_random_uuid()` 生成全新主键
- 因此 `shared_contacts.id`（旧 FK 值来源）与 `clean_contacts.id`（新目标）之间**不存在任何行级映射路径**

直接 rename + add FK 会因现有行的旧 UUID 值在 `clean_contacts` 中不存在而违反约束，迁移回滚。

## Guidance

以下 **8 步原子 SQL 块**是处理"旧 FK 值无法映射到新目标表"场景的标准模式。**步骤顺序至关重要**——必须先消除约束再 NULL 化，再 rename，最后建新约束。

```python
def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 步骤 1：删除旧 UNIQUE 约束（若存在）
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_tenant_id_contact_id_key;

        -- 步骤 2：删除旧 FK 约束
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_contact_id_fkey;

        -- 步骤 3：先去掉 NOT NULL，否则步骤 4 的 UPDATE 会报约束错误
        ALTER TABLE tenant_contacts
            ALTER COLUMN contact_id DROP NOT NULL;

        -- 步骤 4：将无法映射的旧值置 NULL（WHERE 是性能优化，非语义必须）
        UPDATE tenant_contacts SET contact_id = NULL WHERE contact_id IS NOT NULL;

        -- 步骤 5：重命名列
        ALTER TABLE tenant_contacts RENAME COLUMN contact_id TO clean_contact_id;

        -- 步骤 6：添加新 FK，使用 ON DELETE SET NULL 而非 CASCADE
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT fk_tenant_contacts_clean_contact
            FOREIGN KEY (clean_contact_id) REFERENCES clean_contacts(id) ON DELETE SET NULL;

        -- 步骤 7：用部分唯一索引替代表级 UNIQUE（NULL 行不参与唯一性检查）
        CREATE UNIQUE INDEX uq_tenant_contacts_clean_contact
            ON tenant_contacts(tenant_id, clean_contact_id)
            WHERE clean_contact_id IS NOT NULL;

        -- 步骤 8（可选）：在目标表添加业务键去重索引，供 upsert 使用
        CREATE UNIQUE INDEX uq_clean_contacts_company_email
            ON clean_contacts(clean_company_id, lower(email))
            WHERE email IS NOT NULL;
        """
    )
```

**关键设计决策**

| 决策 | 原因 |
|------|------|
| `clean_contact_id` 设为 nullable | 现有行旧值无法映射，必须允许 NULL，否则迁移无法完成 |
| 部分唯一索引（`WHERE clean_contact_id IS NOT NULL`）| PostgreSQL 中 NULL 不参与唯一性比较；表级 UNIQUE 约束无法表达此语义 |
| `ON DELETE SET NULL` | 级联删除（CASCADE）过于破坏性；被引用记录删除后保留主表行更安全 |
| 旧值先 NULL 再 rename | 不能先 rename 再 NULL——PostgreSQL 可能在同一事务中提前检查 FK，触发约束违反 |
| 使用 `exec_driver_sql` 而非 Alembic 高级 API | Alembic 的 `op.drop_constraint()` 等方法会隐式反射表状态，中间步骤可能触发约束检查；单个原生 SQL 字符串在一个事务中按顺序执行，更可预测。项目使用 `alembic>=1.16.0`，`op.get_bind().exec_driver_sql()` 经实测可用；Alembic 2.x 后续版本如有兼容性问题可改为 `op.execute(sa.text(...))`|

**服务层同步**

迁移完成后，所有引用旧列名和旧表的查询必须同步更新：

```sql
-- 变更前（INNER JOIN，clean_contact_id 为 NULL 时行消失）
JOIN shared_contacts shc ON shc.id = tc.contact_id

-- 变更后（LEFT JOIN，保留 clean_contact_id IS NULL 的行）
LEFT JOIN clean_contacts shc ON shc.id = tc.clean_contact_id
```

INSERT 模式同步（加入幂等 upsert）：

```sql
-- 变更前
INSERT INTO shared_contacts (id, company_id, name, email, title, source_type, ...)
VALUES (:id, :company_id, :name, :email, :title, 'lixiaoyun', ...)

-- 变更后（以 (company, email) 为去重键的 upsert）
INSERT INTO clean_contacts (id, clean_company_id, name, email, position, is_valid_email, sources)
VALUES (:id, :clean_company_id, :name, :email, :position, :is_valid_email, ARRAY['lixiaoyun'])
ON CONFLICT (clean_company_id, lower(email)) WHERE email IS NOT NULL DO UPDATE
SET name = COALESCE(EXCLUDED.name, clean_contacts.name),
    position = COALESCE(EXCLUDED.position, clean_contacts.position),
    last_updated = now()
RETURNING id
```

## Why This Matters

不按正确顺序操作会产生以下错误，导致迁移在生产数据库上失败并回滚：

**若跳过步骤 3（不删 NOT NULL 直接 UPDATE NULL）**
```
ERROR: null value in column "contact_id" of relation "tenant_contacts"
       violates not-null constraint
```

**若跳过步骤 4（直接 rename 后加新 FK）**
```
ERROR: insert or update on table "tenant_contacts" violates foreign key constraint
DETAIL: Key (clean_contact_id)=(xxxxxxxx-...) is not present in table "clean_contacts".
```

**若服务层 JOIN 未从 INNER 改为 LEFT**

所有 `clean_contact_id IS NULL` 的行（迁移后的全部现有行）将从查询结果中消失——功能表面正常，实则数据大量缺失，难以察觉。

**若使用表级 UNIQUE 约束而非部分索引**

当 `clean_contact_id` 全为 NULL 时，`UNIQUE (tenant_id, clean_contact_id)` 在某些情况下行为不一致（多个 NULL 是否违反唯一性取决于实现）。部分索引 `WHERE clean_contact_id IS NOT NULL` 是唯一语义明确的表达。

## When to Apply

满足以下全部条件时，使用此模式：

1. **FK 目标表已重建**：旧被引用表被删除或全量重建，新表以全新 UUID 填充，无行级映射
2. **中间迁移断链**：存在一个或多个中间迁移删除了可作为映射桥梁的关联表
3. **列需同时 rename**：列名需变更以反映新语义（不只是换 FK 目标）
4. **历史关联可丢弃**：业务上接受现有关联关系归零，由应用层后续重建

不适用场景：若旧表与新表之间存在稳定的业务键（如 email、source_id），应优先在迁移中做数据迁移（INSERT INTO new_table SELECT ... FROM old_table），而非置 NULL。

## Examples

**完整 migration 文件骨架**（SQL 步骤详见 Guidance 区块）

```python
"""Slice 2: tenant_contacts.contact_id → clean_contact_id

Revision ID: 20260507_0015
Revises: 20260507_0014
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0015"
down_revision = "20260507_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 8 步 DDL 原子块——见 Guidance 区块获取带注释的完整版本
    op.get_bind().exec_driver_sql("""
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_tenant_id_contact_id_key;
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_contact_id_fkey;
        ALTER TABLE tenant_contacts ALTER COLUMN contact_id DROP NOT NULL;
        UPDATE tenant_contacts SET contact_id = NULL WHERE contact_id IS NOT NULL;
        ALTER TABLE tenant_contacts RENAME COLUMN contact_id TO clean_contact_id;
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT fk_tenant_contacts_clean_contact
            FOREIGN KEY (clean_contact_id) REFERENCES clean_contacts(id) ON DELETE SET NULL;
        CREATE UNIQUE INDEX uq_tenant_contacts_clean_contact
            ON tenant_contacts(tenant_id, clean_contact_id)
            WHERE clean_contact_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_clean_contacts_company_email
            ON clean_contacts(clean_company_id, lower(email))
            WHERE email IS NOT NULL;
    """)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("""
        DROP INDEX IF EXISTS uq_clean_contacts_company_email;
        DROP INDEX IF EXISTS uq_tenant_contacts_clean_contact;
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS fk_tenant_contacts_clean_contact;
        ALTER TABLE tenant_contacts RENAME COLUMN clean_contact_id TO contact_id;
        -- 注：downgrade 仅恢复列名结构骨架。
        --     旧 UUID 数据已不可恢复；NOT NULL 约束亦未还原（列数据全为 NULL）。
        --     如需完整回滚，须从数据库备份恢复。
    """)
```

## Related

- 同项目另一 Alembic + PostgreSQL FK 迁移风险文档（类型漂移场景，`DROP TABLE CASCADE` 引起）：`docs/solutions/database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md`
- Slice 1.B-ext 签字文档：`_control/v3/slices/slice-1b-ext-contacts-migration.md`
- 非 CASCADE FK 预清理模式（批量 DELETE 前需显式清理 RESTRICT 子表）：`docs/solutions/database-issues/alembic-non-cascade-fk-chain-blocks-tenant-delete-2026-05-19.md`
