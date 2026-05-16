## Why

Tendata raw rows exist in production, but no cleanup worker was consuming `cleanup_queue`, and existing Tendata rows were not queued for cleanup. Without a production backfill, the implemented Tendata raw-to-clean-company pipeline remains unused for existing data.

## What Changes

- Deploy a production cleanup worker using the existing backend image and worker entrypoint.
- Backfill existing `tendata_raw_companies` rows into `cleanup_queue` with an idempotent insert.
- Verify production queue and clean-company evidence after the worker consumes the backfilled rows.

## Capabilities

### New Capabilities
- `cleanup-worker-backfill-operations`: Operational requirements for running cleanup workers and backfilling existing raw rows into `cleanup_queue`.

### Modified Capabilities

## Impact

- Production deployment: adds or configures a cleanup worker application/process.
- Production database: inserts missing `cleanup_queue` rows for existing Tendata raw companies.
- Existing code behavior: no application code change is required for this change.
