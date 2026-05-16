# tendata-raw-auto-cleanup-enqueue Specification

## Purpose
TBD - created by archiving change auto-enqueue-tendata-raw-cleanup. Update Purpose after archive.
## Requirements
### Requirement: New Tendata raw company inserts SHALL enqueue cleanup work

The system SHALL create a cleanup queue entry for every newly inserted `tendata_raw_companies` row, regardless of which application or database write path created the row.

#### Scenario: Tendata raw row is inserted directly
- **WHEN** a new row is inserted into `tendata_raw_companies`
- **THEN** the system SHALL create a matching `cleanup_queue` row with `raw_table = 'tendata_raw_companies'`
- **AND** the queue row SHALL reference the inserted raw row id
- **AND** the queue row SHALL start with `status = 'pending'`

#### Scenario: Existing service enqueue also runs
- **WHEN** the service layer inserts a Tendata raw row and also calls its existing enqueue helper
- **THEN** the system SHALL keep exactly one cleanup queue row for that raw row
- **AND** it SHALL NOT fail because the database trigger also attempted to enqueue the same raw row

### Requirement: Tendata raw updates SHALL NOT automatically requeue cleanup work

The system SHALL avoid automatic cleanup requeue on normal `tendata_raw_companies` updates.

#### Scenario: Tendata raw row is updated
- **WHEN** an existing `tendata_raw_companies` row is updated after insertion
- **THEN** the auto-enqueue trigger SHALL NOT create a new cleanup queue row because of that update

### Requirement: Missing Tendata cleanup queue detection SHALL remain observable

The system SHALL allow operators to detect whether any Tendata raw rows still lack cleanup queue entries after the trigger is deployed.

#### Scenario: Operator checks missing queue rows
- **WHEN** an operator compares `tendata_raw_companies` against `cleanup_queue`
- **THEN** newly inserted Tendata raw rows after this change SHALL have matching cleanup queue rows

