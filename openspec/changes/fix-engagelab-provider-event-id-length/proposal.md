## Why

Sales 平台最近出现少量 `500+` 错误。后端日志显示 EngageLab 邮件事件 webhook 在写入 `email_events` 时触发 PostgreSQL 截断错误：`value too long for type character varying(100)`，导致部分 `open` 等事件无法入库。

根因是第三方事件标识可能包含 message id、邮箱、事件类型和时间戳，长度会超过当前 `provider_event_id varchar(100)` 限制。第三方 provider event id 不应依赖我们假设的固定短长度。

## What Changes

- 将 `email_events.provider_event_id` 的数据库字段类型从当前 100 字符限制调整为不限制业务长度的文本类型
- 同步后端数据库模型或 schema 定义，确保代码层与迁移后的数据库结构一致
- 增加或补充 webhook 入库验证，覆盖超过 100 字符的 EngageLab `provider_event_id`
- 保持现有事件去重逻辑不变，重复事件仍按现有唯一约束与 `ON CONFLICT DO NOTHING` 处理

## Non-Goals

- 不重构 EngageLab webhook 整体处理流程
- 不修改邮件事件统计口径或前端展示
- 不处理 Sales 平台 `400+` 错误；该问题与本次数据库截断错误不直接等同
- 不把 VictoriaLogs 的 `missing _msg field` 日志格式提示纳入本次核心修复

## Capabilities

### New Capabilities

- `engagelab-email-event-ingestion`: EngageLab 邮件事件入库能力，要求第三方事件 ID 过长时仍能稳定保存事件并维持幂等去重

### Modified Capabilities

（无）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 API | 影响 `/webhooks` 下 EngageLab 邮件事件处理入库路径 |
| 数据库 | 新增 Alembic migration，将 `email_events.provider_event_id` 从长度受限字段调整为文本类型；保留现有数据、索引和唯一约束语义 |
| 邮件事件 | 超长 `provider_event_id` 的 `open` / `click` / delivery 类事件不再因字段长度失败 |
| 测试 | 需要覆盖超长 provider event id 入库和重复事件幂等 |
| 部署 | 后端镜像启动时执行 Alembic 迁移；生产执行前需确认迁移可安全运行 |
| 依赖顺序 | 数据库迁移 → 后端 schema/模型同步 → webhook 验证 |

## Control Mapping

- 决策编号：暂无 `_control/` 目录或 D-xxx 决策编号可关联；本 change 以用户在 2026-07-01 提供的线上日志为输入依据。
- 能力域：暂无 `_control/` 目录或 C-xxx 能力域编号可关联；本 change 新增 OpenSpec capability `engagelab-email-event-ingestion`。
