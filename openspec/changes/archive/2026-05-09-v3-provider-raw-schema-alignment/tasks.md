## 1. Schema Migration

- [x] 1.1 Inspect current production and local schema for `tendata_raw_companies`, `tendata_raw_contacts`, `waimaotong_raw_companies`, and `waimaotong_raw_contacts`
- [x] 1.2 Add `collection_type`, enrichment status fields, fetched-at fields, and `enrichment_error` to `tendata_raw_companies`
- [x] 1.3 Backfill existing Tendata rows with `collection_type = 'reverse_lookup'`
- [x] 1.4 Replace Tendata raw-company uniqueness with `(keyword_master_id, source_id, collection_type)`
- [x] 1.5 Migrate `waimaotong_raw_companies` to the aligned key-field and payload schema
- [x] 1.6 Migrate `waimaotong_raw_contacts` from `source_company_id` text linkage to `raw_company_id` FK linkage
- [x] 1.7 Add raw contact fallback uniqueness indexes for Waimaotong contacts
- [x] 1.8 Update canonical schema documentation after migration code is validated

## 2. Provider Persistence

- [x] 2.1 Update Tendata raw company persistence to write `collection_type`
- [x] 2.2 Update Tendata enrichment persistence to maintain detail, trade, and contacts status fields
- [x] 2.3 Update Waimaotong company persistence contract to write Search key fields and `search_payload`
- [x] 2.4 Update Waimaotong detail persistence contract to write detail key fields and `detail_payload`
- [x] 2.5 Update Waimaotong trade/BaseInfo persistence contract to write trade key fields and `trade_payload`
- [x] 2.6 Update Waimaotong contact persistence contract to write `raw_company_id`, key contact fields, and `raw_payload`
- [x] 2.7 Ensure failed enrichment attempts update the matching status field and `enrichment_error`

## 3. Cleanup Integration

- [x] 3.1 Update cleanup source loading to accept multiple raw rows for the same `(keyword_master_id, source_id)` when `collection_type` differs
- [x] 3.2 Ensure cleanup can merge direct-search and reverse-lookup raw evidence into one `clean_companies` row
- [x] 3.3 Ensure `clean_company_sources` preserves each provider raw row and its collection path evidence
- [x] 3.4 Ensure zero-contact enrichment is treated as fetched, not failed

## 4. Admin API And UI Contracts

- [x] 4.1 Update admin raw provider APIs to return new key fields for Tendata and Waimaotong
- [x] 4.2 Ensure admin raw list/detail responses omit payload fields by default
- [x] 4.3 Add explicit debug/detail behavior if provider payload inspection is required
- [x] 4.4 Update admin raw table columns to show enrichment status and collection type where relevant

## 5. Tests And Verification

- [x] 5.1 Add migration tests or schema assertions for new columns, checks, FKs, and unique indexes
- [x] 5.2 Add tests for `(keyword_master_id, source_id, collection_type)` allowing direct and reverse raw rows
- [x] 5.3 Add tests for raw contact uniqueness by source contact ID and email fallback
- [x] 5.4 Add tests for Waimaotong payload preservation across Search, Detail, Trade, and Contact persistence
- [x] 5.5 Add tests for enrichment status transitions: pending, fetched, failed, skipped
- [x] 5.6 Add admin API tests proving payloads are omitted by default
- [x] 5.7 Run backend test suite and record verification output

## Verification Notes

- Local raw schema inspect on `clientget` confirmed 0035 target columns for `tendata_raw_companies`, `waimaotong_raw_companies`, and `waimaotong_raw_contacts`.
- Remote inspect against `postgresql://postgres@dbconn.sealosbja.site:45010/postgres` returned no matching public raw tables; this appears to be a different database/schema than the local V3 test DB.
- Targeted backend regression: `uv run pytest tests/test_provider_raw_schema_alignment.py tests/test_waimaotong.py tests/test_collection_worker.py tests/test_phase1_e2e.py tests/test_admin_collection_extras.py -q` -> `39 passed`.
- Backend lint: `uv run ruff check ... --select F,E9` -> `All checks passed`.
- Admin type-check: `pnpm --filter @apps/admin type-check` -> pass.
- Full backend suite was run with `uv run pytest -q` and currently reports `97 passed, 14 failed, 10 skipped`. The failures are tied to the local `clientget` DB being stamped at `20260509_0035` while still missing v3-data-foundation schema artifacts such as `tenant_keyword.keyword_raw`, `clean_company_sources`, `clean_company_keywords`, `tendata_raw_contacts`, and `lixiaoyun_raw_contacts`, plus a legacy `waimao_tong` seed mismatch in `data_sources`.
