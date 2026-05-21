## 1. Root Cause And Final Scope

- [x] 1.1 Confirm tenant list empty root cause: visible `tenant_companies.clean_company_id` pointed at stale WMT ids, so the tenant list could not join current `waimaotong_clean_companies`.
- [x] 1.2 Confirm WMT table is externally written and current `waimaotong_clean_companies.id` cannot be treated as stable across rebuilds.
- [x] 1.3 Finalize scope as B + light C: accept a short stale window and repair within minutes, without redesigning `tenant_companies` around a new stable key in this change.

## 2. Backend Repair

- [x] 2.1 Add `backend/app/workers/wmt_lineage_repair.py` with one-shot repair and background loop entrypoints.
- [x] 2.2 Repair `waimaotong_clean_companies.keyword_master_ids` using the clean lineage path: `wmt_clean.sys_company_id -> wmt_raw.sys_company_id -> source_competitor -> lixiaoyun_api_clean_companies.entname_eng -> keyword_master_ids`.
- [x] 2.3 Add raw fallback: `source_competitor -> lixiaoyun_api_companies.entname_eng -> keyword_master_id`.
- [x] 2.4 Fan out current WMT ids to `tenant_companies` for active `tenant_keyword` subscriptions.
- [x] 2.5 Hide visible stale `tenant_companies` relations that no longer join current `waimaotong_clean_companies`.
- [x] 2.6 Keep repair idempotent so repeated runs do not duplicate tenant relations.
- [x] 2.7 Use PostgreSQL advisory lock to avoid concurrent repair work across multiple backend instances.

## 3. App Integration And Migration

- [x] 3.1 Add `WMT_LINEAGE_REPAIR_ENABLED` and `WMT_LINEAGE_REPAIR_INTERVAL_SECONDS` settings.
- [x] 3.2 Start the repair loop from FastAPI lifespan when enabled.
- [x] 3.3 Add Alembic migration `20260521_0051_wmt_keyword_master_ids_not_null.py`.
- [x] 3.4 Migration normalizes `keyword_master_ids` NULL to `{}` and sets `NOT NULL DEFAULT '{}'`.

## 4. Tests And Verification

- [x] 4.1 Add repair self-healing test: after WMT id rebuild, old tenant relation is hidden and current WMT id is inserted.
- [x] 4.2 Add repair idempotency test: two consecutive repairs do not duplicate writes.
- [x] 4.3 Run backend targeted tests: `uv run pytest tests/test_fan_out_worker.py -q` passed with 15 tests.
- [x] 4.4 Run lint for changed backend files: `ruff check` passed.
- [x] 4.5 Record local Alembic caveat: empty local DB upgrade is blocked by an existing initial migration FK type mismatch, unrelated to this change.

## 5. Production Result

- [x] 5.1 Commit backend repair: `eed4ad2 fix(backend): 增加 WMT 血缘自愈 repair`.
- [x] 5.2 Trigger backend ACR build from GitHub Actions.
- [x] 5.3 Push backend image `crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:2026.05.21-r1`.
- [x] 5.4 Deploy and restart backend services.
- [x] 5.5 Verify production DB: Alembic at `20260521_0051`, WMT `keyword_master_ids` NULL count is 0, stale visible tenant relation count is 0.
- [x] 5.6 Verify tenant list recovered: tenant `019dc238...` joins 507 current WMT companies; tenant `019dc236...` joins 319 current WMT companies.
- [x] 5.7 User confirmed frontend tenant company list has recovered.
