## Why

EngageLab webhook 推送不可靠——批量发送时只有约 50% 的 delivered/bounced 回调能送达我们的 endpoint，导致大量邮件状态停留在 `sent`，送达率数据严重失真（实际 76% 显示为 50%）。已手动修复两次（5月底、6月初），需要自动化对账机制根治。

## What Changes

- 新增定时对账 worker：周期性调用 EngageLab `query_email_status` API，查询 `status='sent'` 邮件的真实投递状态
- 按 send_date 分批查询，将 delivery / Invalid Email / Soft bounce 结果写回 `emails` 表
- 联动更新 `sequence_enrollments`、`tenant_contacts`、`tenant_companies`（与现有 webhook_service 逻辑一致）
- 新增 email_events 记录（source='reconciliation'），区分 webhook 自然回调和对账补录

## Non-Goals

- 不修改 webhook 处理逻辑本身
- 不补录 open/click 等追踪事件（EngageLab status API 不提供这些数据）
- 不修改前端统计展示逻辑

## Capabilities

### New Capabilities

- `email-status-reconciliation`: 定时对账任务，主动拉取 EngageLab 投递状态补齐 webhook 丢失的 delivered/bounced 事件

### Modified Capabilities

（无）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 Worker | 新增 `backend/app/workers/reconciliation.py` |
| 后端 Service | 新增对账 service 或复用 webhook_service 逻辑 |
| EngageLab 集成 | 复用现有 `query_email_status()` 方法 |
| 数据库 | 无 schema 变更，只有数据写入 |
| 部署 | 需要在 Sealos 启动对账 worker 进程 |
| 依赖顺序 | 后端 worker → 部署配置 |
