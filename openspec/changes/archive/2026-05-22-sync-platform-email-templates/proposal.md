## Why

平台邮件模板只在创建租户时按行业复制一次。若平台后续新增模板，已有同行业租户不会自动获得副本，导致运营需要手动补写线上数据，既低效也容易漏。

## What Changes

- Admin 端平台邮件模板列表新增“同步到租户”动作。
- 平台管理员可将某个启用的平台邮件模板同步给所有同行业租户。
- 同步只补齐缺失副本：若租户已经有该平台模板副本，则跳过，不覆盖租户已有内容。
- 同步完成后返回并展示结果摘要，包括新增副本数与跳过副本数。
- 保留现有创建租户时自动复制同行业平台模板的行为。

## Non-Goals

- 不做 Tenant 端自助导入平台模板。
- 不做跨行业强制同步或租户多选同步。
- 不覆盖、更新或回滚租户已有模板副本。
- 不做定时自动同步、后台任务或平台模板更新后的自动下发。
- 不改变邮件发送、发送计划或 EngageLab 发送链路。

## Capabilities

### New Capabilities

- `platform-email-template-sync`: 平台邮件模板同步到同行业租户的 Admin 运营能力。

### Modified Capabilities

- 无。

## Impact

| 路径 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/api/admin/config.py` | 修改 | 增加平台邮件模板同步接口 |
| `backend/app/services/admin_config_service.py` | 修改 | 增加同步业务逻辑、结果摘要与审计 |
| `frontend/packages/shared-api/src/admin/email-templates.ts` | 修改 | 增加同步 API 封装与结果类型 |
| `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx` | 修改 | 平台模板列表增加同步操作与结果反馈 |
| `backend/tests/` | 修改 | 增加同步逻辑与接口测试 |
| `frontend/apps/admin/test/` | 修改 | 覆盖 Admin 模板页操作契约 |

- 数据库：不新增表、字段或索引；复用现有 `platform_email_templates` 与 `email_templates`。
- API：新增 Admin 端接口，不破坏现有接口。
- 前后端依赖顺序：先实现后端同步接口与测试，再接入 shared-api，最后接入 Admin UI。
- `_control/` 决策编号与能力域：当前仓库未发现 `_control/` 目录；本 change 暂无可关联 D-xxx / C-xxx。
