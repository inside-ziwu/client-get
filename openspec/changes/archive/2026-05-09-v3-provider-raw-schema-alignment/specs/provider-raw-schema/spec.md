## ADDED Requirements

### Requirement: Provider raw companies SHALL preserve collection path evidence

Provider raw company tables for sources that support both direct search and reverse lookup SHALL store `collection_type` and SHALL treat collection path as part of raw evidence identity.

#### Scenario: Same source company appears through two collection paths
- **GIVEN** a provider raw company exists for a `keyword_master_id`, `source_id`, and `collection_type = 'direct_search'`
- **WHEN** the same `keyword_master_id` and `source_id` are collected with `collection_type = 'reverse_lookup'`
- **THEN** the system SHALL persist a separate raw company row
- **AND** uniqueness SHALL be enforced by `(keyword_master_id, source_id, collection_type)`
- **AND** raw layer SHALL NOT decide which path's data is more authoritative

#### Scenario: Collection type is invalid
- **WHEN** a provider raw company is inserted with `collection_type` outside `direct_search` or `reverse_lookup`
- **THEN** the database SHALL reject the row

### Requirement: Clean layer SHALL merge provider raw evidence

The system SHALL keep provider raw rows as source evidence and SHALL merge equivalent companies only in the clean layer.

#### Scenario: Cleanup processes direct and reverse rows for one source company
- **GIVEN** two provider raw company rows share the same `keyword_master_id` and `source_id` but have different `collection_type`
- **WHEN** cleanup normalizes and links those rows
- **THEN** it SHALL be allowed to merge them into one `clean_companies` row
- **AND** it SHALL preserve source evidence for each raw row through clean source linkage

### Requirement: Provider raw companies SHALL track enrichment status per company

Provider raw company tables SHALL track detail, trade, and contacts enrichment state independently from `collection_runs` and `collection_tasks`.

#### Scenario: Search creates a raw company before enrichment
- **WHEN** a provider Search or Brief result creates a raw company row
- **THEN** `detail_status`, `trade_status`, and `contacts_status` SHALL default to `pending`
- **AND** `detail_fetched_at`, `trade_fetched_at`, and `contacts_fetched_at` SHALL remain empty

#### Scenario: Detail enrichment succeeds
- **WHEN** company detail enrichment succeeds for a raw company
- **THEN** the system SHALL set `detail_status = 'fetched'`
- **AND** it SHALL set `detail_fetched_at`
- **AND** it SHALL preserve the detail response payload when the provider exposes one

#### Scenario: Trade enrichment succeeds
- **WHEN** trade or customs enrichment succeeds for a raw company
- **THEN** the system SHALL set `trade_status = 'fetched'`
- **AND** it SHALL set `trade_fetched_at`
- **AND** it SHALL preserve the trade response payload when the provider exposes one

#### Scenario: Contact enrichment succeeds with zero contacts
- **WHEN** contact enrichment succeeds for a raw company and the provider returns zero contacts
- **THEN** the system SHALL set `contacts_status = 'fetched'`
- **AND** it SHALL set `contacts_fetched_at`
- **AND** it SHALL NOT treat zero contacts as a failed enrichment

#### Scenario: Enrichment fails
- **WHEN** detail, trade, or contact enrichment fails for a raw company
- **THEN** the system SHALL set the corresponding status to `failed`
- **AND** it SHALL record a stage-specific summary in `enrichment_error`

### Requirement: Waimaotong raw company schema SHALL expose key fields and preserve payloads

Waimaotong raw companies SHALL expose key Search, Detail, and Trade fields as columns while preserving original provider payloads.

#### Scenario: Waimaotong Search result is stored
- **WHEN** a Waimaotong Search result is persisted
- **THEN** the system SHALL store key fields including `keyword_master_id`, `collection_type`, `source_id`, `name`, `country_iso3`, `domain`, `industry`, `phone`, `emails`, and `source_tags`
- **AND** it SHALL preserve the original Search company object in `search_payload`
- **AND** it SHALL preserve an original provider object in `raw_payload` for compatibility or replay

#### Scenario: Waimaotong Detail result is stored
- **WHEN** a Waimaotong Detail response is persisted
- **THEN** the system SHALL store key fields including `address`, `employee_size`, `founded_year`, `description`, and `products`
- **AND** it SHALL preserve the original Detail response in `detail_payload`

#### Scenario: Waimaotong Trade result is stored
- **WHEN** a Waimaotong BaseInfo, customs, or trade response is persisted
- **THEN** the system SHALL store key fields including `trade_amount_3y_usd`, `trade_count`, `contacts_count`, and `has_trade_data` when available
- **AND** it SHALL preserve the original trade response in `trade_payload`

### Requirement: Provider raw contacts SHALL link to raw companies by foreign key

Provider raw contact tables SHALL use `raw_company_id` to reference their provider raw company table instead of text-only source-company linkage.

#### Scenario: Waimaotong contact is inserted
- **WHEN** a Waimaotong raw contact is inserted
- **THEN** it SHALL reference `waimaotong_raw_companies.id` through `raw_company_id`
- **AND** it SHALL NOT rely on `source_company_id` as the canonical relationship

#### Scenario: Raw company is deleted
- **WHEN** a provider raw company row is deleted
- **THEN** provider raw contacts linked by `raw_company_id` SHALL be deleted or otherwise prevented from becoming orphan rows

### Requirement: Provider raw contacts SHALL preserve contact fields and original payload

Provider raw contacts SHALL expose important contact fields and preserve the original contact object.

#### Scenario: Waimaotong contact payload is stored
- **WHEN** a Waimaotong contact object is persisted
- **THEN** the system SHALL store key fields including `source_contact_id`, `name`, `position`, `department`, `email`, `email_status`, `phone`, `mobile`, `linkedin`, `whatsapp`, `source`, and `confidence` when present
- **AND** it SHALL preserve the original contact object in `raw_payload`

#### Scenario: Raw contact has no email
- **WHEN** a provider returns a raw contact without email
- **THEN** the raw contact schema SHALL allow the row to be preserved
- **AND** sendability SHALL be decided by the clean/contact classification layer, not the raw layer

### Requirement: Provider raw contact uniqueness SHALL support source ID and email fallback

Provider raw contact uniqueness SHALL first use source contact ID when available and SHALL use email fallback when source contact ID is missing.

#### Scenario: Source contact id exists
- **GIVEN** a raw contact has `source_contact_id`
- **WHEN** it is inserted
- **THEN** uniqueness SHALL be enforced by `(raw_company_id, source_contact_id)`

#### Scenario: Source contact id is missing but email exists
- **GIVEN** a raw contact has no `source_contact_id`
- **AND** it has an email
- **WHEN** it is inserted
- **THEN** uniqueness SHALL be enforced by `(raw_company_id, email)`

### Requirement: Tendata raw companies SHALL include collection type

Tendata raw companies SHALL include `collection_type` so direct search and reverse lookup evidence can be preserved separately.

#### Scenario: Existing Tendata row is migrated
- **WHEN** existing Tendata raw company rows are migrated
- **THEN** the system SHALL backfill `collection_type = 'reverse_lookup'` unless a more specific historical path is known
- **AND** the row SHALL satisfy `(keyword_master_id, source_id, collection_type)` uniqueness

#### Scenario: Future Tendata direct search row is inserted
- **GIVEN** a Tendata raw company exists for `keyword_master_id`, `source_id`, and `collection_type = 'reverse_lookup'`
- **WHEN** a future Tendata direct-search path inserts the same `keyword_master_id` and `source_id` with `collection_type = 'direct_search'`
- **THEN** the system SHALL preserve a separate raw company row

### Requirement: Admin raw APIs SHALL omit payloads by default

Admin raw provider APIs SHALL return key columns for raw list and detail views and SHALL omit payload fields by default.

#### Scenario: Admin requests provider raw list
- **WHEN** admin requests a provider raw company or contact list
- **THEN** the response SHALL include key display fields
- **AND** the response SHALL NOT include `raw_payload`, `search_payload`, `detail_payload`, or `trade_payload` by default

#### Scenario: Payload is needed for debugging
- **WHEN** provider payload inspection is required
- **THEN** the system SHALL use an explicit debug/detail path or explicit opt-in behavior
- **AND** the default list response SHALL remain payload-light
