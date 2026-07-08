# email-send-interval Specification

## Purpose

发送计划单封邮件间隔统一为固定 3 秒，覆盖新建计划默认、worker fallback、数据库默认值与既有计划数据四条路径。来源：2026-07-08 用户要求从原 1 秒调整为 3 秒。

## Requirements

### Requirement: Email sending interval SHALL default to three seconds

The system SHALL use `send_strategy.interval_seconds = [3, 3]` as the default single-email sending interval for new sending plans.

#### Scenario: New sending plan uses three-second interval
- **WHEN** a sending plan is created without an explicit `send_strategy`
- **THEN** the saved plan MUST contain `send_strategy.interval_seconds = [3, 3]`

#### Scenario: Explicit send strategy is not silently replaced
- **WHEN** a sending plan is created with an explicit valid `send_strategy`
- **THEN** the system MUST preserve the explicit strategy supplied by the caller

### Requirement: Worker fallback interval SHALL be three seconds

The sending worker SHALL fall back to a fixed three-second interval when a claimed email has no valid `send_strategy.interval_seconds`.

#### Scenario: Missing send strategy falls back to three seconds
- **WHEN** the sending worker calculates delay for an email with missing `send_strategy`
- **THEN** the calculated delay MUST be 3 seconds

#### Scenario: Invalid interval falls back to three seconds
- **WHEN** the sending worker calculates delay for an email with malformed `interval_seconds`
- **THEN** the calculated delay MUST be 3 seconds

### Requirement: Existing sending plans MUST be migrated to three-second interval

The database migration MUST update existing `sending_plans.send_strategy.interval_seconds` values to `[3, 3]` and set the column default to `{"interval_seconds":[3,3]}`.

#### Scenario: Existing plans are backfilled
- **WHEN** the migration is applied
- **THEN** existing sending plans MUST have `send_strategy.interval_seconds = [3, 3]`

#### Scenario: Future inserts without service default use three-second interval
- **WHEN** a row is inserted into `sending_plans` without an explicit `send_strategy`
- **THEN** PostgreSQL MUST apply `{"interval_seconds":[3,3]}` as the default value
