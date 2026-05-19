## Why

发送计划创建时，公司列表显示"联系人数 > 0"（来自 `waimaotong_clean_companies.contacts_count`），但添加到群组后联系人邮箱丢失——根因是系统缺少从 `waimaotong_clean_contacts` 到 `tenant_contacts` 的自动物化机制。迁移 `20260519_0045` 清空了 `tenant_contacts`，且全系统唯一的写入路径 `_ensure_contact_from_payload` 仅在手动创建公司时触发。

## What Changes

- 新增自动物化逻辑：公司加入群组时，若 `tenant_contacts` 为空，从 `waimaotong_clean_contacts` 自动创建对应记录
- 修复 `_recipients_from_group` SQL：`tc_default` lateral fallback 只回退了 `tenant_contact_id`，但 `contact_name`/`contact_email` 仍走 `gm.tenant_contact_id` 的 JOIN 链（为 NULL 时取不到数据）
- 新增数据修复迁移：为已有 `tenant_companies`（`waimaotong_clean_contacts` 有数据但 `tenant_contacts` 为空）补建记录
- 修复 `data_status` 不一致：`20260519_0046` 修复迁移将所有公司设为 `data_status='ready'`，但实际 `tenant_contacts` 为空

## Non-Goals

- 不改变 `waimaotong_clean_contacts` 的数据结构或导入流程
- 不重构群组成员模型（`group_members` 仍以公司+联系人为维度）
- 不涉及前端 UI 变更（数据修复后现有页面自然恢复正常）
- 不处理 Admin 端的联系人管理流程

## Capabilities

### New Capabilities

- `auto-materialize-tenant-contacts`: 从 WMT 源表自动物化 `tenant_contacts`，确保公司加入群组 / 发送计划收件人解析时有可用联系人

### Modified Capabilities

（无现有 spec 变更）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 后端 Service | `tenant_ops_service.py`：`add_group_members` 增加自动物化调用 |
| 后端 Service | `tenant_messaging_service.py`：`_recipients_from_group` SQL 修复 fallback 链 |
| 数据库迁移 | 新增 Alembic revision：批量补建 `tenant_contacts` + 修正 `data_status` |
| 现有数据 | 所有 `waimaotong_clean_contacts` 有记录但 `tenant_contacts` 为空的公司将被修复 |
| 依赖顺序 | 数据库迁移 → 后端 Service 修复（无前端变更） |
