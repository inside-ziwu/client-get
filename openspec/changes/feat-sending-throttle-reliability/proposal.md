## Why

当前 SendingWorker 一次领取多封并连续发送，会放大冷邮件域名信誉风险；失败路径也缺少有限重试、崩溃恢复、配额回收和明确的错误分类。发送规模化前需要把发送节流和可靠性补齐。

## What Changes

- Worker 改为每次按域名领取 1 封，按 `send_strategy.interval_seconds` 设置域名级随机冷却时间，并在多域名间轮转。
- `claim_due_emails` 支持 `domain_id` 过滤并返回发送节流所需字段。
- EngageLab 发送异常携带 HTTP 状态码，Worker 按 5xx/429/网络异常临时错误、422 永久无效邮箱、其余 4xx 永久失败分类。
- `sequence_enrollments` 增加 `send_attempt_count`，状态允许 `failed`，临时错误最多重试 3 次并按 15 分钟、1 小时、4 小时递增。
- 失败和 stale lock 恢复时回收 `domain_daily_usage.reserved_count`，避免配额泄漏。
- Worker 启动时释放超过 30 分钟的 stale lock，并将对应 queued email 标记为 `failed(STALE_LOCK)`。
- 关键发送、失败、节流、恢复事件输出结构化日志。

## Non-Goals

- 不引入外部消息队列。
- 不自动化预热曲线。
- 不做发送优先级排序。
- 不新增发送速度 UI 配置。
- 不执行生产部署、镜像构建或线上迁移。

## Capabilities

### New Capabilities

- `sending-throttle-reliability`: 逐封节流、有限重试、崩溃恢复、配额回收和结构化日志。

## Impact

| 模块 | 影响范围 |
| --- | --- |
| 数据库 | `sequence_enrollments.send_attempt_count` 新列，status CHECK 增加 `failed` |
| 后端 service | `claim_due_emails`、`mark_email_sent`、`mark_email_failed`、`recover_stale_locks` |
| 后端 worker | 域名轮转、节流、错误分类、结构化日志 |
| EngageLab 集成 | `EngageLabSendError.status_code` |
| 脚本 | sending worker CLI 参数调整 |
| 测试 | 新增 sending worker/service 覆盖 |
