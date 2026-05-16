## Why

Production has shown that some `tendata_raw_companies` rows can be written without a matching `cleanup_queue` row. The cleanup pipeline is now running, but automatic cleanup must be guaranteed for all raw insert paths, including paths that bypass `CollectionService._route_and_enqueue()`.

## What Changes

- Add a database-level fallback that enqueues newly inserted Tendata raw company rows into `cleanup_queue`.
- Keep the existing service-level enqueue path; the queue unique constraint prevents duplicate queue rows.
- Limit automatic enqueue to `INSERT` events so raw enrichment updates do not repeatedly requeue already seen rows.
- Add tests and production verification for missing-queue detection.

## Capabilities

### New Capabilities
- `tendata-raw-auto-cleanup-enqueue`: Guarantees new Tendata raw rows are queued for cleanup regardless of write path.

### Modified Capabilities

## Impact

- Backend Alembic migration adds a PostgreSQL trigger/function.
- Existing collection code remains compatible with the trigger.
- Production cleanup worker continues consuming `cleanup_queue`; no new worker type is introduced.
