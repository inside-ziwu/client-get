## Why

V3 raw provider schema currently diverges across sources: Tendata already follows a "key display fields + raw_payload" shape, while Waimaotong remains a thin two-table schema that cannot faithfully track multi-interface collection progress. This change aligns provider raw tables so raw data preserves original collection evidence, while clean tables remain responsible for entity merging and business decisions.

## What Changes

- Define Waimaotong raw schema as two tables: `waimaotong_raw_companies` and `waimaotong_raw_contacts`.
- Expand Waimaotong raw company fields to expose key Search / Detail / Trade values for admin display and troubleshooting.
- Preserve full original provider responses through payload fields, including `search_payload`, `detail_payload`, `trade_payload`, and `raw_payload`.
- Replace Waimaotong contact weak text linkage with `raw_company_id` FK to `waimaotong_raw_companies.id`.
- Add company-level enrichment tracking fields for detail, trade, and contacts collection status.
- Add `collection_type` to Tendata raw companies and align uniqueness with provider path evidence.
- Define raw-company uniqueness as `(keyword_master_id, source_id, collection_type)` for providers that support both direct search and reverse lookup.
- Keep raw API behavior aligned with data-foundation: admin list/detail responses do not include payloads by default.
- **BREAKING**: Existing Waimaotong raw contacts keyed by `source_company_id` must migrate to `raw_company_id`.
- **BREAKING**: Existing Tendata raw company uniqueness changes from `(keyword_master_id, source_id)` to `(keyword_master_id, source_id, collection_type)`.

## Capabilities

### New Capabilities

- `provider-raw-schema`: Defines aligned raw provider table requirements for Waimaotong and Tendata, including collection type semantics, enrichment status, payload preservation, and raw contact uniqueness.

### Modified Capabilities

- None.

## Impact

- Backend migrations for `tendata_raw_companies`, `waimaotong_raw_companies`, and `waimaotong_raw_contacts`.
- Provider collection persistence logic for Tendata and Waimaotong.
- Cleanup service source ingestion and raw-to-clean source mapping.
- Admin raw provider APIs and table views.
- Tests covering raw uniqueness, enrichment status transitions, payload preservation, and raw contact dedupe.
