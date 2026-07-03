## ADDED Requirements

### Requirement: 「已发送」与「计费数」MUST 排除 failed 邮件

`email_stats_by_date_range` 的 `sent`（已发送）与 `billing`（计费数）MUST 排除 `status='failed'` 的邮件。口径依据 EngageLab 官方状态漏斗（Target → Sent → Delivered / Invalid Email，Sent 之后为 Soft Bounce / Report Spam / Open / Click，Open 之后为 Unsubscribe）：漏斗中不存在 failed；`failed` 是平台内部状态，表示发送接口调用失败、邮件从未交付给服务商，因此不属于「已发送」，也不产生计费。

`sent` 统计口径调整为 `status NOT IN ('draft','pending','queued','failed')`；`billing` 维持等于 `sent`。`targets`（目标数）维持 `COUNT(*)` 不变（failed 邮件仍是当天的发送目标）。每日明细（`daily`）中的 `sent` MUST 采用同一口径。

新口径 MUST 适用于租户仪表盘全部「已发送」展示点，防止同屏数字互相矛盾：`email_stats_by_date_range`（summary 与 daily）、`plan_overview` 的 `emails_sent`（计划级与租户级两处）、`daily_quota` 的今日已发送。口径为查询时过滤，历史日期区间自动按新口径展示，无需数据回溯。

#### Scenario: failed 不计入已发送与计费

- **GIVEN** 日期范围内某租户有 100 封邮件：60 封 delivered、20 封 bounced、15 封 failed、5 封 queued
- **WHEN** 请求 `/dashboard/email-stats`
- **THEN** `targets`=100，`sent`=80（60+20），`billing`=80，failed 与 queued 均不计入 sent

#### Scenario: 百分比分母联动新口径

- **GIVEN** 上述数据（sent=80、delivered 口径统计为 60）
- **WHEN** 请求 `/dashboard/email-stats`
- **THEN** `delivered_percent` = 60/80×100 = 75.0，以剔除 failed 后的 sent 为分母

#### Scenario: 全部失败时不除零

- **GIVEN** 日期范围内某租户所有邮件均为 `failed`
- **WHEN** 请求 `/dashboard/email-stats`
- **THEN** `sent`=0、`billing`=0，各百分比字段返回 0，不产生除零错误

#### Scenario: 同屏各卡片口径一致

- **GIVEN** 某租户存在 failed 邮件
- **WHEN** 同时请求 `/dashboard/email-stats`、`/dashboard/plan-overview` 与每日配额接口
- **THEN** 三处「已发送」均不包含 failed 邮件，数字口径一致
