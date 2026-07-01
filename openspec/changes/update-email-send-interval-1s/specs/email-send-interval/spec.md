## ADDED Requirements

### Requirement: Email sending interval SHALL default to one second

The system SHALL use `send_strategy.interval_seconds = [1, 1]` as the default single-email sending interval for new sending plans.

#### Scenario: New sending plan uses one-second interval
- **WHEN** a sending plan is created without an explicit `send_strategy`
- **THEN** the saved plan MUST contain `send_strategy.interval_seconds = [1, 1]`

#### Scenario: Explicit send strategy is not silently replaced
- **WHEN** a sending plan is created with an explicit valid `send_strategy`
- **THEN** the system MUST preserve the explicit strategy supplied by the caller

### Requirement: Worker fallback interval SHALL be one second

The sending worker SHALL fall back to a fixed one-second interval when a claimed email has no valid `send_strategy.interval_seconds`.

#### Scenario: Missing send strategy falls back to one second
- **WHEN** the sending worker calculates delay for an email with missing `send_strategy`
- **THEN** the calculated delay MUST be 1 second

#### Scenario: Invalid interval falls back to one second
- **WHEN** the sending worker calculates delay for an email with malformed `interval_seconds`
- **THEN** the calculated delay MUST be 1 second

### Requirement: Existing sending plans MUST be migrated to one-second interval

The database migration MUST update existing `sending_plans.send_strategy.interval_seconds` values to `[1, 1]` and set the column default to `{"interval_seconds":[1,1]}`.

#### Scenario: Existing plans are backfilled
- **WHEN** the migration is applied
- **THEN** existing sending plans MUST have `send_strategy.interval_seconds = [1, 1]`

#### Scenario: Future inserts without service default use one-second interval
- **WHEN** a row is inserted into `sending_plans` without an explicit `send_strategy`
- **THEN** PostgreSQL MUST apply `{"interval_seconds":[1,1]}` as the default value
