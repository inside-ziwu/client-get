## Context

`CollectionService._route_and_enqueue()` already queues Tendata raw rows written through the normal collection result path. Production evidence shows some rows still appear in `tendata_raw_companies` without matching `cleanup_queue` entries, which means at least one write path bypasses that service-level enqueue.

The cleanup worker is now deployed and successfully consumes `cleanup_queue`. The remaining gap is making enqueue automatic for every new Tendata raw insert.

## Goals / Non-Goals

**Goals:**
- Guarantee every newly inserted `tendata_raw_companies` row has a matching cleanup queue row.
- Cover service paths, scripts, admin/import paths, and future direct raw insert paths.
- Keep the operation idempotent and compatible with existing `_enqueue_cleanup()`.

**Non-Goals:**
- Do not add cleanup status columns to `tendata_raw_companies`.
- Do not automatically requeue on every raw row update.
- Do not redesign cleanup worker scheduling or clean-company merge rules.

## Decisions

### D1. Use a PostgreSQL trigger as the final enqueue guard

Add an `AFTER INSERT` trigger on `tendata_raw_companies` that inserts:

`('tendata_raw_companies', NEW.id, 'pending')`

into `cleanup_queue`.

Rationale: service-layer enqueue cannot cover paths that bypass the service. A trigger makes the guarantee local to the table receiving raw rows.

Alternative considered: move enqueue into `_upsert_tendata_raw()`. This is still useful but insufficient for direct SQL/import paths.

The trigger function and trigger names should be explicit:

- `enqueue_tendata_raw_company_cleanup()`
- `tendata_raw_companies_enqueue_cleanup_after_insert`

### D2. Trigger only on INSERT

The trigger SHALL not fire on UPDATE. Detail enrichment updates can change many columns after initial raw creation; automatically requeueing every update would create noisy or ambiguous reclean semantics.

User decision on 2026-05-11: only INSERT auto-enqueues cleanup work. Later raw-field completion through UPDATE does not automatically reclean.

If future product behavior needs reclean after enrichment, it should be introduced explicitly with a separate reclean mechanism.

### D3. Keep service-level enqueue

Existing service-level enqueue remains in place. `cleanup_queue` already has a unique constraint on `(raw_table, raw_row_id)`, so the trigger and service call can safely coexist via `ON CONFLICT DO NOTHING`.

### D4. Backfill remains separate

The trigger only guarantees new inserts after deployment. Existing rows without queue entries still require one-time backfill, already handled by `deploy-cleanup-worker-and-backfill-tendata`.

Production verification for this change should therefore focus on rows inserted after the trigger deployment time, not all historical rows.

### D5. Migration order

The Alembic revision for this change should follow the current backend head. At the time of this design, the current production/head migration is `20260510_0038`; the implementation should use the next available revision such as `20260511_0039_auto_enqueue_tendata_raw_cleanup.py`.

## Risks / Trade-offs

- Trigger hides enqueue side effects from application code -> Mitigation: add migration/schema tests and document the trigger in this change.
- Trigger can enqueue invalid raw rows that later skip cleanup -> Mitigation: this matches current cleanup behavior; invalid rows are processed and marked with cleanup issue metadata.
- If cleanup_queue schema changes later, trigger must be updated in the same migration -> Mitigation: keep trigger body small and covered by tests.
