# engagelab-email-event-ingestion Specification

## Purpose

EngageLab 邮件事件入库能力：第三方事件 ID（`provider_event_id`）过长时仍能稳定保存事件并维持幂等去重。来源：change `fix-engagelab-provider-event-id-length`（2026-07-05 OpenSpec 退役收尾时落定为主 spec）。

## Requirements

### Requirement: MUST persist EngageLab events with long provider event ids
系统 MUST 在 EngageLab 邮件事件的 `provider_event_id` 超过 100 字符时仍能成功写入 `email_events`，不得因数据库字段长度限制导致 webhook 处理失败。

#### Scenario: 保存超长 provider event id
- **GIVEN** EngageLab webhook 推送一个可匹配到本地邮件的事件
- **AND** 该事件生成的 `provider_event_id` 长度超过 100 字符
- **WHEN** 后端处理该 webhook 事件
- **THEN** 系统 MUST 成功写入 `email_events`
- **AND** webhook 处理不得因 `StringDataRightTruncationError` 返回 500

#### Scenario: 保留超长 provider event id 原值
- **GIVEN** EngageLab webhook 事件生成的 `provider_event_id` 长度超过 100 字符
- **WHEN** 系统写入 `email_events`
- **THEN** `email_events.provider_event_id` MUST 保存完整原值
- **AND** 系统不得截断、裁剪或静默替换该值

### Requirement: MUST keep EngageLab event idempotency
系统 MUST 保持 EngageLab 邮件事件现有幂等语义：同一 `source` 与同一 `provider_event_id` 的重复事件不得重复写入业务事件记录。

#### Scenario: 重复超长 provider event id 不重复入库
- **GIVEN** `email_events` 已存在一条 `source = engagelab` 且 `provider_event_id` 超过 100 字符的事件
- **WHEN** EngageLab 再次推送生成相同 `provider_event_id` 的事件
- **THEN** 系统 MUST 按现有 `ON CONFLICT DO NOTHING` 语义跳过重复写入
- **AND** webhook 处理结果 MUST 表示该事件是重复事件或等效的幂等成功状态

#### Scenario: 不同 source 的相同 provider event id 互不冲突
- **GIVEN** `email_events` 中存在一个非 EngageLab source 的事件，其 `provider_event_id` 与即将处理的 EngageLab 事件相同
- **WHEN** 后端处理该 EngageLab webhook 事件
- **THEN** 系统 MUST 允许写入 `source = engagelab` 的事件
- **AND** 幂等判断 MUST 继续基于 `source + provider_event_id`
