# email-status-reconciliation Specification

## Purpose

EngageLab webhook 回调不可靠（批量发送时约半数 delivered/bounced 回调丢失）的自动兜底：定时主动查询 EngageLab 状态 API，补齐停留在 sent 的邮件真实投递状态并联动更新关联实体。实施形态为内联于 sending worker 主循环（约 10 分钟一轮）；历史决策见归档 change `email-status-reconciliation`。

## Requirements

### Requirement: 系统 SHALL 定时对账 sent 状态邮件的真实投递状态

系统 MUST 每 10 分钟执行一次对账，查询 `sent_at` 超过 30 分钟且 `status='sent'` 的邮件，调用 EngageLab `query_email_status` API 获取真实状态并更新数据库。

#### Scenario: 正常对账 — delivered 邮件

- **GIVEN** 一封邮件 `status='sent'`，`sent_at` 超过 30 分钟
- **WHEN** EngageLab API 返回 `status=1`（delivery）
- **THEN** 系统更新该邮件 `status='delivered'`、`delivered_at=update_time`
- **AND** 系统更新关联 `tenant_companies.business_status` 从 `in_plan` 到 `contacted`

#### Scenario: 正常对账 — Invalid Email 邮件

- **GIVEN** 一封邮件 `status='sent'`，`sent_at` 超过 30 分钟
- **WHEN** EngageLab API 返回 `status=4`（Invalid Email）
- **THEN** 系统更新该邮件 `status='bounced'`、`bounced_at=update_time`、`invalid_email=true`
- **AND** 系统更新关联 `sequence_enrollments.status='bounced'`
- **AND** 系统更新关联 `tenant_contacts.contact_status='bounced'`

#### Scenario: 正常对账 — Soft Bounce 邮件

- **GIVEN** 一封邮件 `status='sent'`，`sent_at` 超过 30 分钟
- **WHEN** EngageLab API 返回 `status=5`（Soft bounce）
- **THEN** 系统更新该邮件 `status='bounced'`、`bounced_at=update_time`、`soft_bounce=true`
- **AND** 系统更新关联 `sequence_enrollments.status='bounced'`
- **AND** 系统更新关联 `tenant_contacts.contact_status='bounced'`

#### Scenario: EngageLab 返回发送中状态

- **GIVEN** 一封邮件 `status='sent'`，`sent_at` 超过 30 分钟
- **WHEN** EngageLab API 返回 `status=18`（发送中）
- **THEN** 系统跳过该邮件，不更新状态，下一轮对账再查

#### Scenario: EngageLab API 未返回该邮件记录

- **GIVEN** 一封邮件 `status='sent'`，`sent_at` 超过 30 分钟
- **WHEN** EngageLab API 返回结果中无该邮件的 `engagelab_message_id`
- **THEN** 系统跳过该邮件，记录日志

#### Scenario: 无待对账邮件时空转

- **GIVEN** 数据库中无 `status='sent'` 且 `sent_at` 超过 30 分钟的邮件
- **WHEN** 对账任务执行
- **THEN** 系统记录日志并休眠到下一轮，不调用 EngageLab API

### Requirement: 对账 MUST 按 send_date（CST）分组查询 EngageLab API

EngageLab `query_email_status` API 要求 `send_date` 参数（北京时间日期）。系统 MUST 将邮件按 `sent_at` 转换为 CST 日期后分组查询。

#### Scenario: 跨日邮件正确分组

- **GIVEN** 一封邮件 `sent_at='2026-06-01T23:00:00+00:00'`（UTC）
- **WHEN** 转换为 CST
- **THEN** 该邮件归入 `send_date='2026-06-02'` 分组查询
