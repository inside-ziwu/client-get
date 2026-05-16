## ADDED Requirements

### Requirement: Cleanup worker SHALL consume queued raw-company cleanup work in production

Production SHALL run a cleanup worker process that consumes `cleanup_queue` rows and invokes the existing cleanup service.

#### Scenario: Cleanup worker starts in production
- **WHEN** the cleanup worker application starts
- **THEN** it SHALL use the backend image and run `scripts/run_cleanup_worker.py`
- **AND** it SHALL use the production async `DATABASE_URL`
- **AND** it SHALL NOT rely on the default API `/start.sh` command

#### Scenario: Cleanup worker has no pending work
- **WHEN** no `cleanup_queue` rows are pending
- **THEN** the worker SHALL remain running and continue polling instead of exiting

### Requirement: Existing Tendata raw rows SHALL be backfilled into cleanup queue idempotently

Existing `tendata_raw_companies` rows without cleanup queue records SHALL be inserted into `cleanup_queue` as pending work using an idempotent operation.

#### Scenario: Missing Tendata queue rows are backfilled
- **WHEN** a `tendata_raw_companies` row has no matching `cleanup_queue` row for `raw_table = 'tendata_raw_companies'`
- **THEN** the backfill SHALL insert one pending queue row for that raw row

#### Scenario: Backfill is rerun
- **WHEN** the backfill is executed more than once
- **THEN** existing queue rows SHALL NOT be duplicated

### Requirement: Tendata cleanup completion SHALL be verified from queue and source evidence

The system SHALL distinguish queued, processed, skipped, and cleaned Tendata rows using existing queue and source tables.

#### Scenario: Tendata row is cleaned into clean company
- **WHEN** a Tendata raw row has a matching `clean_company_sources` row with `source_type = 'tendata'`
- **THEN** the row SHALL be treated as cleaned into the clean-company layer

#### Scenario: Tendata row has not entered cleanup
- **WHEN** a Tendata raw row has no matching `cleanup_queue` row
- **THEN** the row SHALL be treated as not queued
