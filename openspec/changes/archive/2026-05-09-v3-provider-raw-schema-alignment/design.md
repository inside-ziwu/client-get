## Context

`v3-data-foundation` established the raw/clean/tenant split and already shaped Tendata raw tables around explicit display fields plus `raw_payload`. However, Waimaotong currently remains a thinner legacy raw schema:

- `waimaotong_raw_companies` lacks `keyword_master_id`, enrichment status fields, and split payloads for Search / Detail / Trade.
- `waimaotong_raw_contacts` links to companies through `source_company_id text` instead of a `raw_company_id` FK.
- Tendata raw companies do not yet distinguish direct search from reverse lookup through `collection_type`.

Provider collection is not a single-interface operation. One company can be discovered by Search / Brief, then enriched by Detail, then enriched by Trade / BaseInfo, then associated with contacts. `collection_runs` and `collection_tasks` track run-level and batch-level execution, but they do not answer whether one raw company has completed detail, trade, or contact enrichment.

## Goals / Non-Goals

**Goals:**

- Align Waimaotong raw schema with the existing Tendata raw-table pattern.
- Preserve all original provider evidence while exposing important raw fields as columns for admin display, filtering, debugging, and cleanup input.
- Add `collection_type` to Tendata and Waimaotong company raw rows to preserve direct-search and reverse-lookup evidence separately.
- Track company-level enrichment status independently from run/task status.
- Keep raw tables free from entity-resolution decisions; clean tables merge and decide canonical values.

**Non-Goals:**

- Do not implement Waimaotong provider collection.
- Do not implement Tendata provider restoration.
- Do not redesign `collection_runs` or `collection_tasks` beyond referencing their boundaries.
- Do not add field-level permissions for raw email or phone fields.
- Do not expose provider payloads in default admin raw list/detail responses.

## Decisions

### Decision 1: Raw company rows represent provider evidence, not canonical companies

Use `(keyword_master_id, source_id, collection_type)` as the raw-company uniqueness key for provider tables that can produce both direct-search and reverse-lookup evidence.

Alternatives considered:

| Option | Decision | Rationale |
|---|---|---|
| `UNIQUE(keyword_master_id, source_id)` | Rejected | Forces raw layer to decide whether direct or reverse data wins, which belongs in cleanup / clean layers. |
| `UNIQUE(source_id)` | Rejected | Loses keyword evidence and conflicts with platform-level keyword collection semantics. |
| `UNIQUE(keyword_master_id, source_id, collection_type)` | Accepted | Preserves raw evidence for each collection path and lets clean tables merge entities. |

Raw layer SHALL not overwrite one collection path with another. Cleanup can merge multiple raw rows into one `clean_companies` row and record source evidence in `clean_company_sources`.

### Decision 2: Waimaotong remains two raw tables

Waimaotong uses:

- `waimaotong_raw_companies`
- `waimaotong_raw_contacts`

Do not split company detail into a third raw table. Search, Detail, and Trade / BaseInfo are all company-level evidence and should update the same raw company row for the same `(keyword_master_id, source_id, collection_type)`.

### Decision 3: Provider payloads are split by interface when needed

Waimaotong company raw rows use:

- `search_payload` for Search result evidence.
- `detail_payload` for Detail response evidence.
- `trade_payload` for BaseInfo / customs / trade evidence.
- `raw_payload` as compatibility or initial provider-object payload.

This avoids overwriting one interface response with another while keeping the company raw table compact.

Tendata may continue using `raw_payload` for the assembled raw company object unless provider implementation later needs split interface payloads.

### Decision 4: Raw company enrichment status belongs on raw company rows

Add company-level status pairs:

- `detail_status`, `detail_fetched_at`
- `trade_status`, `trade_fetched_at`
- `contacts_status`, `contacts_fetched_at`
- `enrichment_error`

Allowed statuses:

```text
pending / fetched / failed / skipped
```

`collection_tasks.status = completed` only means one execution batch completed. It does not mean each raw company in the batch has completed detail, trade, or contact enrichment.

### Decision 5: Raw contacts use FK linkage and source-id/email fallback uniqueness

Provider raw contact tables SHALL use:

- `raw_company_id bigint` FK to the provider raw company table.
- `source_contact_id text` when provided by the source.
- `email citext` when available.

Uniqueness follows the data-foundation raw-contact rule:

```sql
UNIQUE (raw_company_id, source_contact_id) WHERE source_contact_id IS NOT NULL
UNIQUE (raw_company_id, email) WHERE source_contact_id IS NULL AND email IS NOT NULL
```

Raw contacts may have null email. Clean layer decides whether a contact is sendable.

### Decision 6: Admin raw API defaults stay payload-light

Admin raw company/contact APIs SHALL return key fields by default and SHALL NOT include provider payloads unless a dedicated debug/detail path explicitly opts in.

## Proposed Schema Shape

### tendata_raw_companies additions

| Field | Type | Meaning |
|---|---|---|
| `collection_type` | text | `direct_search` or `reverse_lookup` |
| `detail_status` | text | Detail enrichment status |
| `detail_fetched_at` | timestamptz | Detail success time |
| `trade_status` | text | Trade enrichment status |
| `trade_fetched_at` | timestamptz | Trade success time |
| `contacts_status` | text | Contacts enrichment status |
| `contacts_fetched_at` | timestamptz | Contacts success time |
| `enrichment_error` | jsonb | Latest enrichment error summary |

Unique key:

```sql
UNIQUE (keyword_master_id, source_id, collection_type)
```

### waimaotong_raw_companies target fields

| Field | Type | Meaning |
|---|---|---|
| `id` | bigint identity | Raw company primary key |
| `keyword_master_id` | uuid | Platform keyword ID |
| `collection_type` | text | `direct_search` or `reverse_lookup` |
| `source_id` | text | Waimaotong company ID |
| `real_id` | text | Waimaotong real company ID, if present |
| `name` | text | Company name |
| `country_iso3` | char(3) | ISO3 country |
| `domain` | text | Domain |
| `industry` | text | Industry |
| `address` | text | Address |
| `phone` | text | Company phone |
| `employee_size` | text | Source employee-size text |
| `founded_year` | int | Founded year |
| `description` | text | Company description |
| `products` | text[] | Product names |
| `source_tags` | text[] | Source tags |
| `emails` | text[] | Company-level emails |
| `trade_amount_3y_usd` | numeric | Trade amount aligned with clean/Tendata naming |
| `trade_count` | int | Trade count |
| `contacts_count` | int | Contact count |
| `has_trade_data` | boolean | Whether trade data exists |
| `customs_data` | jsonb | Customs/trade summary if useful for compatibility |
| `search_payload` | jsonb | Search result object |
| `detail_payload` | jsonb | Detail response |
| `trade_payload` | jsonb | BaseInfo / customs / trade response |
| `raw_payload` | jsonb | Compatibility initial provider payload |
| `detail_status` | text | Detail enrichment status |
| `detail_fetched_at` | timestamptz | Detail success time |
| `trade_status` | text | Trade enrichment status |
| `trade_fetched_at` | timestamptz | Trade success time |
| `contacts_status` | text | Contacts enrichment status |
| `contacts_fetched_at` | timestamptz | Contacts success time |
| `enrichment_error` | jsonb | Latest enrichment error summary |
| `created_at` | timestamptz | Insert time |
| `updated_at` | timestamptz | Last update time |

Unique key:

```sql
UNIQUE (keyword_master_id, source_id, collection_type)
```

### waimaotong_raw_contacts target fields

| Field | Type | Meaning |
|---|---|---|
| `id` | bigint identity | Raw contact primary key |
| `raw_company_id` | bigint | FK to `waimaotong_raw_companies.id` |
| `source_contact_id` | text | Source contact ID, nullable |
| `name` | text | Contact name |
| `position` | text | Position |
| `department` | text | Department |
| `email` | citext | Email, nullable |
| `email_status` | text | Email status |
| `phone` | text | Phone |
| `mobile` | text | Mobile |
| `linkedin` | text | LinkedIn URL or handle |
| `whatsapp` | text | WhatsApp |
| `source` | text | Source label |
| `confidence` | numeric | Confidence, if source provides it |
| `raw_payload` | jsonb | Original source contact object |
| `created_at` | timestamptz | Insert time |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Raw company row count increases when direct and reverse both find the same source company | Treat raw rows as evidence. Merge only in clean layer. Add `clean_company_sources` links for each raw row. |
| Additional status fields overlap with collection task status | Document boundary: tasks track batch execution; raw company statuses track per-company enrichment. |
| Payload fields increase storage | Payloads are required for replay/debugging. Admin APIs omit payloads by default. |
| Migrating `waimaotong_raw_contacts.source_company_id` to `raw_company_id` requires source-row resolution | Migration must resolve by matching `source_company_id` to `waimaotong_raw_companies.source_id`; unresolved rows require an explicit migration report. |
| Changing Tendata uniqueness may conflict with existing data | Migration should backfill `collection_type = 'reverse_lookup'` for existing rows before replacing the unique constraint. |

## Migration Plan

1. Add `collection_type` and enrichment status fields to `tendata_raw_companies`.
2. Backfill existing Tendata rows with `collection_type = 'reverse_lookup'`.
3. Replace Tendata unique constraint with `(keyword_master_id, source_id, collection_type)`.
4. Rebuild or migrate Waimaotong raw company schema to the aligned field set.
5. Add `raw_company_id` to `waimaotong_raw_contacts` and backfill from company `source_id`.
6. Replace Waimaotong contact uniqueness with raw-contact fallback uniqueness.
7. Update provider persistence and cleanup ingestion to use new fields.
8. Update admin raw APIs to expose key fields and omit payloads by default.

Rollback should restore the previous unique constraints and keep new payload/status columns nullable. Destructive rollback of captured raw payloads is not required.

## Open Questions

- Should `waimaotong_raw_companies.customs_data` remain long-term, or become a compatibility alias derived from `trade_payload`?
- Should Tendata also split `raw_payload` into brief/detail/trade payloads once stage 2 is restored, or is assembled `raw_payload` enough for that provider?
- What exact migration behavior should apply to unresolved legacy Waimaotong contacts whose `source_company_id` cannot match a company row?
