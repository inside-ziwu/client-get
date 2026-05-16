## 1. Preparation

- [x] 1.1 Confirm production cleanup worker deployment command and required database environment variables.
- [x] 1.2 Confirm current production counts for Tendata raw rows, cleanup queue rows, and Tendata clean source evidence.

## 2. Backfill

- [x] 2.1 Insert missing `tendata_raw_companies` rows into `cleanup_queue` with an idempotent `INSERT ... SELECT ... ON CONFLICT DO NOTHING`.
- [x] 2.2 Verify inserted row count and queue status distribution.

## 3. Verification

- [x] 3.1 Verify cleanup worker consumes queued rows by checking `cleanup_queue` status counts.
- [x] 3.2 Verify Tendata clean-company evidence via `clean_company_sources(source_type = 'tendata')`.
- [x] 3.3 Record any remaining pending, failed, skipped, or not-queued rows.
