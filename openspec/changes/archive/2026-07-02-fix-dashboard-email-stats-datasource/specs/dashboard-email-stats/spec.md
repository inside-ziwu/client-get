# dashboard-email-stats

## ADDED Requirements

### Requirement: 仪表盘邮件统计 SHALL 基于本地 emails 表按租户聚合

仪表盘邮件统计 SHALL 基于本地 `emails` 表按租户聚合。`email_stats_by_date_range` MUST 通过 `tenant_id` 条件隔离租户数据,MUST NOT 调用 EngageLab Stats API(该 API 返回账户级汇总,无租户隔离能力)。日期过滤按 `created_at >= start_date AND created_at < end_date + 1 day`。

#### Scenario: 租户隔离

- **GIVEN** 两个租户在同一日期范围内均有邮件数据
- **WHEN** 租户 A 请求 `/dashboard/email-stats`
- **THEN** 汇总和每日明细只包含租户 A 的邮件,查询参数携带租户 A 的 `tenant_id`

#### Scenario: 每日明细按日期升序

- **GIVEN** 日期范围内多天存在发送记录
- **WHEN** 请求邮件统计
- **THEN** `daily` 数组按 `DATE(created_at)` 分组、日期升序返回,每项含 date/sent/delivered/opens

### Requirement: 百分比字段 SHALL 由后端按既定口径自算

百分比字段 SHALL 由后端自算,保留两位小数,分母为 0 时返回 0。口径(2026-05-30 提交 544820f 修订,与举报率/退订率口径一致):

- `delivered_percent` = delivered / **sent** × 100
- `total_open_percent` = total_opens / **delivered** × 100
- `open_percent` = opens / **delivered** × 100

打开率以 delivered 为分母:打开行为只可能发生在送达的邮件上。

#### Scenario: 正常计算

- **GIVEN** sent=10、delivered=8、total_opens=5、opens=3
- **WHEN** 请求邮件统计
- **THEN** `delivered_percent` = 80.0,`total_open_percent` = 62.5,`open_percent` = 37.5

#### Scenario: 分母为零不抛错

- **GIVEN** sent=0(或 sent>0 但 delivered=0)
- **WHEN** 请求邮件统计
- **THEN** 对应百分比字段返回 0,不产生除零错误
