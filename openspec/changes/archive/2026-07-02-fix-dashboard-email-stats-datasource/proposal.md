## Why

仪表盘 email-stats 当前调用 EngageLab Stats API（`/v1/stats_day`），该 API 返回的是**整个 EngageLab 账户级**汇总数据，没有租户隔离能力。用户实际只有 83 封邮件，但仪表盘显示 106（包含其他租户的邮件）。此外百分比字段由 EngageLab 以 delivered 为分母计算，与业务预期（以 sent 为分母）不一致。

历史背景：原设计 D1 选择本地 `emails` 表聚合查询，后因 webhook 写入的追踪数据疑似不准确而改为调 EngageLab API，但引入了更严重的租户隔离问题。

## What Changes

- **替换数据源**：`email_stats_by_date_range` 方法从调用 EngageLab Stats API 改为本地 `emails` 表聚合查询，恢复原设计 D1/D4 方案
- **租户隔离**：所有统计查询通过 RLS（`tenant_id` 条件）保证数据隔离
- **百分比自算**：`delivered_percent`、`total_open_percent`、`open_percent` 由后端根据本地数据自行计算（以 sent 为分母），不依赖外部服务
- **每日明细**：趋势图数据改为 `GROUP BY DATE(created_at)` 本地聚合
- **移除 EngageLab Stats 依赖**：删除 `get_stats_day` 方法及相关缓存逻辑（发送功能不受影响）
- **验证 webhook 数据**：对比本地追踪字段与 EngageLab 数据，确认 webhook 回写的准确性

## Non-Goals

- 不修改 webhook 处理逻辑（`WebhookService`）—— webhook 代码逻辑正确，只需验证数据
- 不修改 `emails` 表结构或新增数据库迁移
- 不修改前端展示逻辑（`StatsSection` 组件）—— 后端响应格式保持不变
- 不修改 EngageLab 邮件发送功能（`send_email`）

## Capabilities

### New Capabilities

（无新能力，修改现有实现）

### Modified Capabilities

（无 spec 级行为变更，仅数据源实现切换，API 契约不变）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 service | `tenant_query_service.py` — 重写 `email_stats_by_date_range` 方法 |
| 后端集成 | `engagelab.py` — 删除 `get_stats_day` 方法 |
| 前端 | 无变更（API 响应格式不变） |
| 数据库 | 无迁移（`emails` 表已有所有需要的字段） |
| 依赖顺序 | 仅后端变更，无跨模块依赖 |
