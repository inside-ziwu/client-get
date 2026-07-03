## Why

2026-07-02 晚生产事故：EngageLab 档位日配额耗尽后（当天成功发出 8,729 封，北京时间约 23:30 起被逐封拒绝），发送 worker 缺少熔断机制且失败会退还本地配额，整夜以每小时约 2,500 封的速度空转，把队列剩余 13,950 封邮件全部打成 `failed`（`sent_at` 与 `engagelab_message_id` 全为 NULL，实际一封未发出）；其中 13,913 封因错误被误判为永久失败，对应 `sequence_enrollments` 被直接终止；仪表盘又把这批 failed 计入「已发送/计费数」，显示 22,679 与实际 8,729 严重失真。

## What Changes

- **发送 worker 配额熔断**：识别到 EngageLab 日配额耗尽后，该域名当天停止发送，次日配额重置后自动恢复；被推迟的邮件由 enrollment 推迟驱动、次日重新生成发送，不产生失败记录、不终止序列。瞬时限流（429/rate limit）维持重试链不熔断，短窗内连续命中才升级；同一 enrollment 连续 defer 3 次后降级为临时失败，防误判死循环。
- **服务商错误分类修正**：`_classify_provider_error` 区分「日配额耗尽」（关键词/错误码识别，触发熔断）与「瞬时限流」（走重试链）；「未知 4xx」的默认分类从永久失败改为临时失败，防止误杀 enrollment。
- **仪表盘「已发送/计费数」口径修正**：仪表盘全部三处「已发送」（`email_stats_by_date_range`、`plan_overview.emails_sent`、`daily_quota` 今日已发送）统一剔除 `failed`，对齐 EngageLab 官方漏斗语义（Target → Sent → Delivered/Invalid Email → …，漏斗中不存在 failed；`failed` 是平台内部状态，表示邮件从未交付给服务商）。
- **本地配额窗口对齐北京自然日**：`domain_daily_usage` 读写从 UTC 日（`CURRENT_DATE`，北京 08:00 翻转）改为北京自然日，消除与熔断恢复周期的 8 小时错位（已实测生产会话时区为 UTC）。

## Non-Goals

- 不修复 2026-07-02 事故遗留数据（13,940 个被终止的 enrollment 与 failed 邮件的恢复补发），由后续单独 change 承载。
- 不修改 EngageLab webhook 处理与对账逻辑（active change `email-status-reconciliation` 负责）。
- 不调整本地域名日配额（`daily_limit`）的取值与预热策略（配额窗口的时区对齐除外，见 What Changes 第 4 条）。
- 不新增熔断的运营通知/积压监控界面（评审确认为盲区，挂起至 design 的 Open Questions，另立 change 决策）。
- 不新增数据库 schema（熔断状态优先复用现有表/内存态，见 design）。

## Capabilities

### New Capabilities

- `sending-quota-circuit-breaker`: 发送 worker 对服务商配额耗尽错误的识别、熔断（当天停发、次日自动恢复）与错误分类（配额类/未知 4xx 归为临时错误，不终止 enrollment）。

### Modified Capabilities

- `dashboard-email-stats`: 「已发送 sent」与「计费数 billing」的统计口径新增约束——MUST 排除 `status='failed'`（未交付服务商的邮件不计入发送与计费），且新口径统一适用于仪表盘全部三处「已发送」展示点。

## Impact

| 范围 | 影响 |
|------|------|
| 后端 Worker | `backend/app/workers/sending.py`：错误分类修正（配额/限流区分 + 升级计数）+ 熔断判定与跳过逻辑 |
| 后端 Service | `backend/app/services/tenant_messaging_service.py`：新增 `defer_email_for_quota`（删行 + 释放锁/配额 + enrollment 推迟）、`domain_daily_usage` 窗口对齐北京日；`backend/app/services/tenant_query_service.py`：`email_stats_by_date_range` / `plan_overview` / `daily_quota` 三处口径 |
| 前端 | 无代码改动（仪表盘读取后端返回值，口径变化自动生效） |
| 数据库 | 无 schema 变更 |
| 部署 | 后端镜像 + sending worker 重启；无迁移 |
| 依赖顺序 | 日志校准（实施前置，tasks 1.x）→ 后端（service → worker）→ 部署；仪表盘口径独立可并行 |

关联决策/能力域：项目当前无 `openspec/_control/` 目录，无可关联的 D-xxx/C-xxx 编号；口径历史决策见归档 change `fix-dashboard-email-stats-datasource`（提交 544820f）。
