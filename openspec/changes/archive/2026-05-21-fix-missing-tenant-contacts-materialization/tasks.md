## 1. 数据修复迁移

- [x] 1.1 新增 Alembic revision：批量补建 `tenant_contacts`（从 `waimaotong_clean_contacts` 物化所有有 email 的记录，无上限，分批 1000 家处理）
- [x] 1.2 同一迁移中：修正 `tenant_companies.data_status`（无 `tenant_contacts` 记录的公司设为 `'missing_contacts'`，有记录的保持 `'ready'`）
- [x] 1.3 本地执行迁移验证：确认 `tenant_contacts` 行数、`data_status` 分布

## 2. 后端 Service 修复

- [x] 2.1 新建 `backend/app/services/tenant_contact_utils.py`：独立异步函数 `ensure_contacts_from_wmt(conn, tenant_id, tenant_company_id)`（查 WMT 联系人 → 批量 INSERT tenant_contacts → ON CONFLICT DO NOTHING，全量物化无上限）（Eng Review v2 D2：两个 service 都需要调用，提取为零耦合的独立函数）
- [x] 2.1a `ensure_contacts_from_wmt` 物化后：用 `EXISTS(SELECT 1 FROM tenant_contacts WHERE ...)` 检查并 UPDATE `tenant_companies.data_status` 从 `'missing_contacts'` 为 `'ready'`（Eng Review v2 D6：EXISTS 替代 count > 0，确保并发安全）
- [x] 2.2 `tenant_ops_service.py`：`add_group_members` 在 `_select_default_contact_id` 之前调用 `ensure_contacts_from_wmt`（从 `tenant_contact_utils` import）
- [x] 2.3 `tenant_messaging_service.py`：重写 `_recipients_from_group` SQL — 改为 JOIN 所有 `tenant_contacts`，每个 (公司, 联系人) 对成为独立收件人，不再使用 LATERAL fallback（Design D8）
- [x] 2.4 `tenant_ops_service.py`：修复 `list_group_members` SQL — 保持 1 公司 1 行，添加 LATERAL fallback 取默认联系人 + 标量子查询取 `contacts_count`（Design D5 + D10）
- [x] 2.5 `ensure_contacts_from_wmt` 排序：`ORDER BY (position IS NOT NULL)::int DESC, id ASC`，无 LIMIT（全量物化）（Design D6）
- [x] 2.6 `tenant_messaging_service.py`：重写 `_recipients_from_manual` company_ids 分支 — JOIN 所有 `tenant_contacts`，去掉 LIMIT 1，返回所有联系人（Design D9）
- [x] 2.7 `_recipients_from_manual` company_ids 分支：查询前调用 `ensure_contacts_from_wmt` 确保联系人已物化（从 `tenant_contact_utils` import）
- [x] 2.8 `_recipients_from_group`：查询前对 group 内各公司调用 `ensure_contacts_from_wmt`（Eng Review v3 D2：发送时自愈物化）
- [x] 2.9 `lock_plan_recipients`：改为批量 INSERT + RETURNING 统计真实新增数，去掉逐行 for 循环（Design D11）
- [x] 2.10 `_recipients_from_filter`：重写 SQL 返回所有联系人，去掉 `setdefault` 去重；查询前调用 `ensure_contacts_from_wmt`（Design D12）
- [x] 2.11 `_build_recipient_candidates`：新增 `is_sendable` 检查，`is_sendable=false` 时 `excluded_reason = "not_sendable"`（Design D13）
- [x] 2.12 `_build_recipient_candidates`：修复 `str(row["tenant_contact_id"])` None 字符串问题，改为条件表达式（Design D14）
- [x] 2.13 D8/D9/D12 的 SQL 查询返回列需包含 `tco.is_sendable`，供 `_build_recipient_candidates` 使用

## 3. 前端改动

- [x] 3.1 `list_group_members` API 响应新增 `contacts_count` 字段，前端群组成员列表展示"N 个联系人"（Design D10）

## 4. 测试验证

- [x] 4.0 新建 WMT 测试 helper：向 `waimaotong_clean_companies` / `waimaotong_clean_contacts` 插入测试数据的工具函数（Eng Review v2 D8：现有 helper 写 old `clean_*` 表，业务 SQL 查 `waimaotong_clean_*` 表，新测试必须用新表）
- [x] 4.1 新增测试用例：公司有 WMT 联系人但无 `tenant_contacts` 时，加入群组后自动物化，发送计划能正确解析邮箱
- [x] 4.2 新增测试用例：`_recipients_from_group` 多联系人 — 公司有 3 个联系人时，发送计划收件人包含 3 条记录
- [x] 4.3 新增测试用例：WMT 联系人全部无 email 时，物化不执行，group_member 返回 0 个收件人
- [x] 4.4 新增测试用例：`ensure_contacts_from_wmt` 物化后 `data_status` 从 `'missing_contacts'` 更新为 `'ready'`
- [x] 4.5 新增测试用例：物化全量验证 — WMT 有 15 个有 email 的联系人时，全部 15 个都被物化
- [x] 4.6 新增测试用例：`list_group_members` — 返回 `contacts_count` 字段，且 fallback 默认联系人正确
- [x] 4.7 新增测试用例：`ensure_contacts_from_wmt` 幂等性 — 重复调用不产生重复数据
- [x] 4.8 新增测试用例：公司已有 `tenant_contacts` 时 `ensure_contacts_from_wmt` 跳过物化
- [x] 4.9 新增测试用例：`_recipients_from_manual` company_ids 多联系人 — 公司有 3 个联系人时返回 3 条记录
- [x] 4.10 新增测试用例：物化排序验证 — 有 position 的联系人的 `created_at` 早于无 position 的
- [x] 4.11 新增测试用例：`_recipients_from_manual` contact_ids 分支回归 — 修改 company_ids 后 contact_ids 仍正常（Eng Review v2 D5）
- [x] 4.12 新增测试用例：部分联系人 bounced/unsubscribed 时，`_build_recipient_candidates` 正确排除这些联系人但保留其他联系人
- [x] 4.13 新增测试用例：多公司不同联系人数量场景 — 3 家公司分别有 1/3/5 个联系人 → 总计 9 条收件人（Eng Review v3 D4）
- [x] 4.14 新增测试用例：`_recipients_from_group` 发送时自动物化 — stale 公司在发送路径触发 ensure（Eng Review v3 D4）
- [x] 4.15 新增测试用例：`_recipients_from_manual` 批量 company_ids — ANY() 返回所有公司的所有联系人（Eng Review v3 D4）
- [x] 4.16 新增测试用例：`list_group_members` 中 0 联系人公司 contacts_count = 0（Eng Review v3 D4）
- [x] 4.17 新增测试用例：端到端 — 公司有 WMT 联系人 → 加入群组 → 创建发送计划 → lock → 所有联系人成为收件人（Eng Review v3 D4）
- [x] 4.18 新增测试用例：`lock_plan_recipients` 批量 INSERT — 重复调用后 inserted_count 为真实新增数（Design D11）
- [x] 4.19 新增测试用例：`_recipients_from_filter` 多联系人 — 公司有 3 个联系人时返回 3 条记录（Design D12）
- [x] 4.20 新增测试用例：`is_sendable=false` 的联系人被排除为 `not_sendable`（Design D13）
- [x] 4.21 新增测试用例：`tenant_contact_id` 为 NULL 时不输出字符串 "None"（Design D14）
- [x] 4.22 运行全量测试套件确认无回归：`pytest backend/tests/`
