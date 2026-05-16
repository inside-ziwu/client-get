## 1. Schema

- [x] 1.1 Add an Alembic migration that creates a PostgreSQL trigger function for Tendata raw cleanup enqueue.
- [x] 1.2 Add an `AFTER INSERT` trigger on `tendata_raw_companies` that inserts one pending `cleanup_queue` row.
- [x] 1.3 Ensure the trigger uses `ON CONFLICT (raw_table, raw_row_id) DO NOTHING`.
- [x] 1.4 Add downgrade logic that drops the trigger and trigger function.
- [x] 1.5 Use explicit trigger names: `enqueue_tendata_raw_company_cleanup()` and `tendata_raw_companies_enqueue_cleanup_after_insert`.
- [x] 1.6 Place the migration after the current Alembic head, using the next available revision after `20260510_0038`.

## 2. Tests

- [x] 2.1 Add a migration/schema test proving direct insert into `tendata_raw_companies` creates a pending `cleanup_queue` row against migrated schema, not by invoking the trigger function directly.
- [x] 2.2 Add a test proving duplicate service-level enqueue does not create duplicate queue rows.
- [x] 2.3 Add a test proving UPDATE on an existing Tendata raw row does not create another queue row.

## 3. Verification

- [x] 3.1 Run the targeted backend test covering the trigger behavior.
- [x] 3.2 Run `openspec validate auto-enqueue-tendata-raw-cleanup --strict`.
- [x] 3.3 After deploy, verify production `tendata_raw_companies` rows inserted after the migration have matching `cleanup_queue` rows.
- [x] 3.4 Verify production missing-queue count for rows created after trigger deployment is `0`; do not use historical all-time missing rows as the success criterion.
- [x] 3.5 If historical rows without queue entries remain, handle them through the existing backfill operation, not through this trigger change.
- [x] 3.6 Before or after deploy, run the existing idempotent backfill for any pre-trigger Tendata raw rows that still lack cleanup queue rows.
- [x] 3.7 Verify at least one post-deploy Tendata raw insert sample has a matching `cleanup_queue` row.
