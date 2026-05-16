# Slice 1.B-ext — Contacts 迁移（shared_contacts → clean_contacts）

状态：**✅ 本地验证通过，已签字**

创建日期：2026-05-07

---

## 目标

将旧 shared_contacts 体系切换至 V3 clean_contacts 体系：

| 变更项 | 说明 |
|--------|------|
| `tenant_contacts.contact_id` → `clean_contact_id` | 列重命名 + FK 改指 clean_contacts(id)，nullable |
| `shared_contacts` → `clean_contacts` 写入 | `_ensure_contact_from_payload` 改写 |
| 全部 JOIN shared_contacts → JOIN clean_contacts | 2 个 service 文件，9 处引用 |
| `clean_contacts` 去重索引 | `UNIQUE (clean_company_id, lower(email)) WHERE email IS NOT NULL` |

---

## 变更范围

### 数据库迁移
- [x] `backend/alembic/versions/20260507_0015_slice2_contacts_migration.py`
  - DROP UNIQUE/FK on `tenant_contacts.contact_id`
  - NULL 旧值（shared_contacts UUID 无法映射至 clean_contacts）
  - RENAME `contact_id` → `clean_contact_id`
  - ADD FK → `clean_contacts(id) ON DELETE SET NULL`
  - CREATE partial UNIQUE INDEX `WHERE clean_contact_id IS NOT NULL`
  - CREATE `uq_clean_contacts_company_email` 去重索引

### 服务层修改
- [x] `backend/app/services/tenant_ops_service.py`
  - `company_contacts`: JOIN shared_contacts → LEFT JOIN clean_contacts；返回字段 `shared_contact_id/name_en/title/department` → `clean_contact_id/position`
  - `get_group_members` (line ~655): LEFT JOIN shared_contacts → LEFT JOIN clean_contacts
  - `_ensure_contact_from_payload` (line ~988): INSERT INTO shared_contacts → INSERT INTO clean_contacts（含 ON CONFLICT 去重）；tenant_contacts.contact_id → clean_contact_id
- [x] `backend/app/services/tenant_messaging_service.py`
  - 6 处 JOIN shared_contacts → LEFT JOIN clean_contacts（plan recipients、claim_due_emails、_recipients_from_group、_recipients_from_manual ×2、_recipients_from_filter）

### 文档同步
- [x] `backend/03_database/schema.sql`
  - tenant_contacts 列 contact_id → clean_contact_id，FK 改为 clean_contacts(id) nullable
  - shared_contacts 注释更新（保留但不再被代码引用）
  - clean_contacts 新增 uq_clean_contacts_company_email 索引

---

## 设计决策

### 为何 clean_contact_id 设为 nullable？

旧 shared_contacts 的 UUID 无法映射到 clean_contacts（公司 UUID 在 0014 已重建，无法追溯）。  
迁移时直接 NULL 化旧值；新联系人通过 `_ensure_contact_from_payload` 写入 clean_contacts 后再关联。

### 为何保留 shared_contacts？

1. 可能有历史数据（不删除避免数据丢失）
2. 无 FK 约束后成为只读历史表，不影响任何业务逻辑

### company_contacts API 字段变化

| 旧字段 | 新字段 | 说明 |
|--------|--------|------|
| `shared_contact_id` | `clean_contact_id` | 联系人 UUID |
| `name_en` | _(已删除)_ | clean_contacts 无此字段 |
| `title` + `department` | `position` | 合并为职位字段 |

---

## 延迟至 Phase 2 的事项

1. **contacts 清洗 pipeline**：waimaotong_raw_contacts → clean_contacts → tenant_contacts fan-out（类似 Phase 1 的 CleanupService，contacts 路径）
2. **Tendata raw_row_id 类型不兼容**（text PK vs bigint）→ Phase 2 清洗逻辑

---

## 本地验证

```bash
cd backend

# 1. 迁移
uv run alembic upgrade head
# 期望：Running upgrade 20260507_0014 -> 20260507_0015

# 2. 验证结构
# tenant_contacts.clean_contact_id: uuid, nullable=YES
# clean_contacts: uq_clean_contacts_company_email index 存在

# 3. Smoke test
uv run python scripts/run_cleanup_worker.py --once
# 期望：{"service_instance": "cleanup-worker-1", "recovered": 0, "processed": 0}
```

---

## 签字

- [x] 本地迁移验证通过（lay 2026-05-07）
- [x] cleanup worker smoke test 通过（lay 2026-05-07）
- [x] Sealos 生产迁移（lay 2026-05-07）
