## Context

The Tendata cleaning implementation already exists in backend code. `CollectionService._route_and_enqueue()` enqueues newly collected Tendata rows, and `CleanupWorker` consumes `cleanup_queue` to write `clean_companies`, `clean_company_sources`, `clean_company_keywords`, and matching `tenant_companies`.

Production currently has Tendata raw rows but no Tendata cleanup queue rows. The immediate issue is operational: deploy the cleanup worker and enqueue existing raw rows once.

## Decisions

### D1. Use the existing backend image

The cleanup worker uses the same backend image as the API and other workers:

`crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:2026.05.10-r7`

The worker command is:

`cd /app && python scripts/run_cleanup_worker.py --sleep-seconds 5`

The worker must receive the same production database environment variables as existing backend workers, especially `DATABASE_URL` using `postgresql+asyncpg://.../clientget` without `directConnection`.

### D2. Backfill is queue-only and idempotent

The production compensation inserts missing Tendata raw rows into `cleanup_queue`. It does not update raw rows directly and does not write clean-company tables directly.

The insert uses `ON CONFLICT (raw_table, raw_row_id) DO NOTHING`, so rerunning it is safe.

### D3. Verification relies on queue and source evidence

A Tendata raw row is considered actually cleaned only when `clean_company_sources` has `source_type = 'tendata'` and `source_company_id = tendata_raw_companies.id`. Queue status alone is not enough because a row can be processed but skipped by identity rules.

## Risks

- If the cleanup worker lacks production `DATABASE_URL`, it will attempt to connect to localhost and log connection failures.
- If some raw rows lack company name or `country_iso3`, the worker should process them but skip clean-company creation and record cleanup issue metadata.
- If the worker is not running, backfilled queue rows will remain pending.
