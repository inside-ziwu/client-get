## Why

当前发送计划收件人步骤存在两个问题：

1. 群组选择器显示"14 人"，但群组成员粒度是公司，实际是 14 家公司，显示误导用户
2. 收件人选取逻辑未接入 admin 联系人分类体系，没有按等级排序、没有按公司限数，导致收件人的优先级控制缺失

Admin 端已建好完整的联系人分类体系（等级 A/B/X + is_sendable + 职位关键词匹配），现在需要让发送计划的收件人选取和预览接入这套规则。

## What Changes

- 群组选择器计数从"X 人"改为"X 家公司"
- 收件人预览底部合计改为"合计 X 家公司，Y 位收件人"
- 收件人选取逻辑接入联系人分类等级：按 sort_order 从高到低排序，仅取 is_sendable=true 的等级，未分类联系人排最后
- 每家公司收件人上限 8 人（有邮箱）
- 收件人预览改为按公司汇总展示，可展开查看明细（联系人姓名、邮箱、分类等级）

## Non-Goals

- 不改动手动选择和筛选器两种收件人来源
- 不在 tenant 端暴露 `tenant_contacts.is_sendable` 配置界面
- 不修改 admin 联系人分类规则本身
- 不改动邮件实际发送流程

## Capabilities

### New Capabilities
- `recipient-selection-by-level`: 按联系人分类等级选取收件人，每公司上限 8 人

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 模块 | 影响范围 |
|------|---------|
| 后端 API | `tenant_messaging_service._recipients_from_group()` 需接入分类等级排序 + 每公司 8 人限制 |
| 后端 API | `tenant_ops_service.list_group_members()` 或新增预览接口需返回按等级排序的收件人 |
| 前端 tenant | `step-recipients.tsx` 群组选择器文本、预览表格结构、合计展示 |
| 前端 tenant | `step-confirmation.tsx` 同步更新群组显示文本 |
| 数据库 | 依赖现有 `v_tenant_contact_classified` 视图和 `position_classification_levels` 表，无新增表 |

依赖顺序：后端 API → 前端 UI
