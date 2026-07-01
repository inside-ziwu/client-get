## Context

EngageLab webhook 由 `backend/app/api/webhooks/engagelab.py` 接收，并调用 `backend/app/services/webhook_service.py` 写入 `email_events`。当前服务在 EngageLab 未提供独立 event id 时，使用 `message_id + raw_event + occurred_at` 生成 `provider_event_id`，用于 `idx_email_events_provider_unique` 幂等去重。

数据库基线 `backend/03_database/schema.sql` 中 `email_events.provider_event_id` 当前定义为 `varchar(100)`。生产日志里的 provider event id 包含较长 message id 和收件人邮箱，已经超过 100 字符，导致 PostgreSQL 抛出 `StringDataRightTruncationError`，事件入库失败并触发 webhook 500。

## Goals / Non-Goals

**Goals:**

- 允许 EngageLab webhook 保存超过 100 字符的 `provider_event_id`
- 保留现有 `source + provider_event_id` 幂等去重语义
- 通过 Alembic migration 安全迁移现有数据库
- 保持实现简单，不引入新的 provider id 生成策略

**Non-Goals:**

- 不改造 EngageLab webhook 认证、payload 解析或状态联动逻辑
- 不修改邮件事件统计查询口径
- 不处理 VictoriaLogs `_msg` 字段提示
- 不处理 Sales 平台大量 `400+` 错误

## Decisions

### Decision: 将 provider_event_id 调整为 text

选择：将 `email_events.provider_event_id` 从 `varchar(100)` 改为 PostgreSQL `text`。

理由：

- 第三方事件标识由外部 message id、邮箱、事件类型、时间戳等组成，业务上不应假设 100 字符上限
- PostgreSQL 的 `text` 与 `varchar(n)` 在常规查询和索引使用上没有本质性能劣势；本场景需要的是取消人为长度限制
- 继续保持原值入库，便于排查第三方事件与本地记录的对应关系

备选方案：

- 改为 `varchar(255)`：能修复当前样例，但仍然是在猜上限，未来长地址或 provider 格式变化仍可能失败
- 对 provider id 做 hash：可控制长度，但会降低排障可读性，并需要额外处理冲突概率和历史数据一致性

### Decision: 保持唯一索引和 ON CONFLICT 逻辑不变

选择：保留 `idx_email_events_provider_unique ON email_events(source, provider_event_id) WHERE provider_event_id IS NOT NULL`，不改 `ON CONFLICT DO NOTHING`。

理由：

- 当前失败点是字段长度，不是幂等策略
- 调整字段类型不会改变 `source + provider_event_id` 的业务唯一含义
- 最小变更可以降低对邮件状态联动逻辑的影响

## Risks / Trade-offs

- [Risk] 生产环境存在同名索引，字段类型变更可能需要短暂锁表 → Mitigation：使用单字段 `ALTER COLUMN TYPE text`，不重建业务数据；上线前在开发库执行迁移验证
- [Risk] 超长 provider id 继续进入唯一索引，索引项可能变大 → Mitigation：当前 provider id 是事件标识级别数据，长度有限且写入频率可控；若未来出现极端长度，再单独评估 hash 辅助列
- [Risk] 只改数据库不改基线 schema，后续新环境仍会带旧限制 → Mitigation：同时更新 `backend/03_database/schema.sql` 中字段定义

## Migration Plan

1. 新增 Alembic revision，将 `email_events.provider_event_id` 类型改为 `text`
2. 同步更新 `backend/03_database/schema.sql`
3. 运行后端测试或最小 webhook 入库验证，覆盖超过 100 字符的 provider id
4. 部署后端镜像时由 `/start.sh` 执行 `alembic upgrade head`

Rollback：

- 若必须回滚代码，可保留数据库字段为 `text`，它兼容原有短 provider id，不影响旧代码读取
- 不建议自动 downgrade 回 `varchar(100)`，因为生产中可能已经写入超过 100 字符的数据；如需 downgrade，必须先审计并处理超长数据

## Open Questions

（无）
