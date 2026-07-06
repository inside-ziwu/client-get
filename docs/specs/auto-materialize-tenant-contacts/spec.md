# auto-materialize-tenant-contacts Specification

## Purpose
TBD - created by archiving change fix-missing-tenant-contacts-materialization. Update Purpose after archive.
## Requirements
### Requirement: 系统 SHALL 在公司加入群组时自动物化 tenant_contacts

当公司被添加到群组（`add_group_members`），如果该公司在 `tenant_contacts` 中没有任何记录，系统 MUST 从 `waimaotong_clean_contacts` 自动物化联系人记录到 `tenant_contacts`。物化范围限定为有 email 的联系人，每家公司最多 10 条。

#### Scenario: 公司有 WMT 联系人且 tenant_contacts 为空

- **GIVEN** 公司 A 的 `waimaotong_clean_contacts` 有 3 条记录（均有 email）
- **AND** 公司 A 在 `tenant_contacts` 中没有任何记录
- **WHEN** 公司 A 被添加到群组
- **THEN** 系统自动在 `tenant_contacts` 中创建 3 条记录（`contact_status='available'`, `is_sendable=true`）
- **AND** `group_members.tenant_contact_id` 被设为其中按 `created_at ASC` 排序的第一条

#### Scenario: 公司已有 tenant_contacts 记录

- **GIVEN** 公司 B 在 `tenant_contacts` 中已有 2 条记录
- **WHEN** 公司 B 被添加到群组
- **THEN** 系统不触发物化（跳过）
- **AND** `group_members.tenant_contact_id` 从已有 `tenant_contacts` 中选取

#### Scenario: WMT 联系人无 email

- **GIVEN** 公司 C 的 `waimaotong_clean_contacts` 有 5 条记录，但全部 email 为 NULL
- **WHEN** 公司 C 被添加到群组
- **THEN** 系统不创建 `tenant_contacts`（无有效联系人）
- **AND** `group_members.tenant_contact_id` 为 NULL

#### Scenario: WMT 联系人超过上限

- **GIVEN** 公司 D 的 `waimaotong_clean_contacts` 有 50 条有 email 的记录
- **WHEN** 公司 D 被添加到群组
- **THEN** 系统只物化前 10 条（按 `waimaotong_clean_contacts.id ASC`）
- **AND** `group_members.tenant_contact_id` 被设为第一条

### Requirement: _recipients_from_group SHALL 在 tenant_contact_id 为 NULL 时正确回退联系人数据

`_recipients_from_group` 的 SQL 查询在 `gm.tenant_contact_id` 为 NULL 时，MUST 通过 lateral fallback 同时取回 `tenant_contact_id`、`contact_name`、`contact_email`、`contact_status`，而不仅仅回退 `tenant_contact_id`。

#### Scenario: group_member 有明确的 tenant_contact_id

- **GIVEN** 群组成员记录 `gm.tenant_contact_id = 42`
- **AND** `tenant_contacts(id=42)` 对应的 `waimaotong_clean_contacts.email = 'ada@acme.com'`
- **WHEN** 执行 `_recipients_from_group`
- **THEN** 结果中 `contact_email = 'ada@acme.com'`，`tenant_contact_id = 42`

#### Scenario: group_member 的 tenant_contact_id 为 NULL 但公司有 tenant_contacts

- **GIVEN** 群组成员记录 `gm.tenant_contact_id = NULL`
- **AND** 该公司在 `tenant_contacts` 中有记录，首条对应 email `'bob@acme.com'`
- **WHEN** 执行 `_recipients_from_group`
- **THEN** 结果中 `contact_email = 'bob@acme.com'`（通过 lateral fallback）
- **AND** `tenant_contact_id` 为该 fallback 记录的 id

#### Scenario: group_member 的 tenant_contact_id 为 NULL 且公司无 tenant_contacts

- **GIVEN** 群组成员记录 `gm.tenant_contact_id = NULL`
- **AND** 该公司在 `tenant_contacts` 中无任何记录
- **WHEN** 执行 `_recipients_from_group`
- **THEN** 结果中 `contact_email = NULL`，`tenant_contact_id = NULL`

### Requirement: list_group_members SHALL 与 _recipients_from_group 保持一致的 fallback 行为

`list_group_members` 查询 MUST 在 `gm.tenant_contact_id = NULL` 时也通过 fallback 取回联系人数据，确保群组成员列表预览与发送计划收件人解析结果一致。

#### Scenario: 群组成员预览显示 fallback 联系人

- **GIVEN** 群组成员 `gm.tenant_contact_id = NULL`
- **AND** 该公司在 `tenant_contacts` 中有记录
- **WHEN** 调用 `list_group_members` API
- **THEN** 返回的成员数据中包含 fallback 联系人的 `contact_name` 和 `contact_email`

#### Scenario: 群组成员预览无联系人

- **GIVEN** 群组成员 `gm.tenant_contact_id = NULL`
- **AND** 该公司在 `tenant_contacts` 中无记录
- **WHEN** 调用 `list_group_members` API
- **THEN** 返回的成员数据中 `contact_name = NULL`，`contact_email = NULL`

### Requirement: 数据修复迁移 SHALL 补建缺失的 tenant_contacts 并修正 data_status

Alembic 迁移 MUST 执行以下修复：
1. 为所有 `tenant_companies`（其关联的 `waimaotong_clean_contacts` 有 email 记录但 `tenant_contacts` 为空）批量创建 `tenant_contacts`
2. 将 `tenant_contacts` 仍为空的公司的 `data_status` 设为 `'missing_contacts'`
3. 回填 `group_members.tenant_contact_id`（NULL → 首个 `tenant_contact`）

#### Scenario: 迁移补建联系人

- **GIVEN** 公司 X 的 `tenant_contacts` 为空
- **AND** `waimaotong_clean_contacts` 中有 3 条有 email 的记录
- **WHEN** 执行迁移
- **THEN** `tenant_contacts` 新增 3 条记录
- **AND** `tenant_companies.data_status` 保持 `'ready'`

#### Scenario: 迁移修正 data_status

- **GIVEN** 公司 Y 的 `tenant_contacts` 为空
- **AND** `waimaotong_clean_contacts` 中也没有有 email 的记录
- **WHEN** 执行迁移
- **THEN** `tenant_companies.data_status` 被更新为 `'missing_contacts'`

#### Scenario: 迁移回填 group_members

- **GIVEN** 群组成员记录 `gm.tenant_contact_id = NULL`
- **AND** 该公司在迁移后有了 `tenant_contacts` 记录
- **WHEN** 执行迁移
- **THEN** `gm.tenant_contact_id` 被更新为该公司首条 `tenant_contact` 的 id

