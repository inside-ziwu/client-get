## Context

`/collection/peers` was migrated from the old Vite Admin page as the raw Lixiaoyun company view. The current Next.js implementation calls `adminApi.collection.listRawCompanies('lixiaoyun')`, which maps to `/admin/api/v1/collection/raw/lixiaoyun`.

Backend evidence:

- `list_raw_companies(..., table='lixiaoyun', include_payload=false)` selects only `id/source_id/name/domain/task_id/created_at`.
- The fields the UI needs (`english_name`, `esdate`, `reg_capital`, `employee_scale`, `reg_address`, `contacts_count`, `keyword_normalized`) are exposed by `list_v3_raw_companies(..., provider='lixiaoyun')`, mapped to `/admin/api/v1/raw/lixiaoyun/companies`.

## Goals / Non-Goals

**Goals:**

- Display real Lixiaoyun raw company fields on `/collection/peers`.
- Keep the page as a raw company page, separate from `/collection/peers-cleaned`.
- Preserve existing filters and pagination.
- Keep backend changes limited to the existing V3 raw list API contract; no schema or worker changes.

**Non-Goals:**

- Do not add API routes.
- Do not change database schema.
- Do not merge the raw page and cleaned peer-company page.
- Do not change collection workers or database schema.

## Decisions

### D-1: Use `/raw/lixiaoyun/companies`

The page SHALL call the V3 raw company API instead of adding `include_payload=true` to the legacy collection raw API.

Rationale: the V3 raw API already exposes typed top-level fields and contact counts. Using payload would keep the UI coupled to raw vendor JSON and still miss joined fields such as keyword and contact count.

### D-2: Keep display mapping explicit

The page SHALL render fields from a `LixiaoyunRawCompanyRow` type rather than generic `raw_payload` lookups.

Rationale: the bug came from an implicit payload contract. A typed top-level row makes future API/page mismatch easier to catch.

### D-3: Contract tests guard the endpoint and fields

The existing medium page contract test SHALL assert that `/collection/peers` uses the V3 raw API client method and references the top-level field names.

Rationale: this prevents accidentally reverting the page to the legacy `listRawCompanies('lixiaoyun')` path.

### D-4: V3 raw API falls back to Lixiaoyun payload fields

The V3 raw Lixiaoyun list API SHALL derive `english_name` from `c.english_name`, then normalized payload aliases such as `company_name_en`, `name_en`, and vendor field `entNameEng`.

The same API SHALL derive `contacts_count` from split contact rows first, then payload contact arrays (`lx_contacts`, `contacts`), then numeric payload counts (`contacts_count`, `contact_num`).

Rationale: historical and live rows may contain enriched data in `raw_payload` without a backfilled top-level column or split contact rows. The page consumes the typed V3 contract, so the contract should normalize these variants at the API boundary.

## Risks / Trade-offs

- V3 raw API response type is broader than this page needs → Mitigation: define a narrow TypeScript interface for the fields rendered by the page.
- Contact detail rows are not included in the list API → Mitigation: keep the current behavior of showing contact count only; do not invent a new detail API call in this fix.
- The old contract test expected the legacy API → Mitigation: update the test to document the corrected contract.
