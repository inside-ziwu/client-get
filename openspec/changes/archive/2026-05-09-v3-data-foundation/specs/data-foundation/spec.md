## ADDED Requirements

### Requirement: Data foundation SHALL define the 12 confirmed schema tables

The data foundation change SHALL define only the confirmed V3 schema tables for keywords, raw data, clean customer data, and tenant views.

#### Scenario: Schema scope is reviewed

- **GIVEN** the data foundation OpenSpec change is reviewed
- **THEN** it SHALL include `keyword_master`, `tenant_keyword`, `lixiaoyun_raw_companies`, `lixiaoyun_raw_contacts`, `tendata_raw_companies`, `tendata_raw_contacts`, `clean_companies`, `clean_contacts`, `clean_company_sources`, `clean_company_keywords`, `tenant_companies`, and `tenant_contacts`
- **AND** it SHALL NOT define cleanup worker implementation, Sealos deployment, AI enrichment, or competitor table redesign as part of this change

### Requirement: Keyword master SHALL be the platform-level keyword truth

The system SHALL store platform-level keywords in `keyword_master`, with `keyword_normalized` unique globally and `created_at` recorded.

#### Scenario: Tenant enters an equivalent keyword

- **GIVEN** a tenant enters a keyword such as "P.C.B" or "PCB "
- **WHEN** the backend normalizes the keyword
- **THEN** the system SHALL upsert one `keyword_master` row for the normalized platform keyword
- **AND** the system SHALL NOT create duplicate platform keyword rows for case or punctuation variants
- **AND** normalization SHALL trim, lowercase, convert fullwidth characters to halfwidth, collapse whitespace, and remove non-semantic separators such as `.`, `_`, and spaces
- **AND** normalization SHALL preserve potentially semantic symbols, so values such as `FR-4` and `C++` are not merged with `FR4` or `C`

### Requirement: Tenant keyword SHALL store tenant-level input and subscription state

The system SHALL store tenant keyword subscriptions in `tenant_keyword`, preserving the tenant's raw input in `keyword_raw` and linking to `keyword_master`.

#### Scenario: Tenant deletes and re-adds a keyword

- **GIVEN** a tenant previously soft-deleted a keyword subscription
- **WHEN** the tenant adds the same normalized platform keyword again
- **THEN** the system SHALL restore the existing `tenant_keyword` row to `status = 'active'`
- **AND** the system SHALL update `keyword_raw` to the latest tenant input
- **AND** the system SHALL NOT refresh the original `tenant_keyword.created_at`

### Requirement: Collection runs SHALL own cross-day collection state

The system SHALL use `collection_runs` as the truth for platform keyword collection status, cursor, daily limit, stopping, and completion.

#### Scenario: Lixiaoyun reaches the daily limit

- **GIVEN** a `collection_run` for a `keyword_master` reaches the Lixiaoyun daily limit
- **WHEN** the current task finishes
- **THEN** the system SHALL mark the run as `daily_limit_reached`
- **AND** the system SHALL persist the continuation cursor on the run
- **AND** the run SHALL retain enough state for a later collection implementation to continue from the next Beijing 08:00 window

#### Scenario: Admin starts collection for a subscribed platform keyword

- **GIVEN** admin starts collection for a `keyword_master`
- **AND** the keyword has one or more active `tenant_keyword` subscriptions
- **WHEN** the system creates the `collection_run`
- **THEN** the system SHALL set `collection_runs.triggered_tenant_id` to the tenant from the earliest active subscription ordered by `tenant_keyword.created_at ASC, tenant_keyword.id ASC`
- **AND** the system SHALL leave `triggered_tenant_id` empty when the keyword has no active tenant subscription
- **AND** restored subscriptions SHALL keep their original `created_at` for earliest-subscription ordering

#### Scenario: Active run already exists

- **GIVEN** an active `collection_run` exists for the same `keyword_master_id`, `provider`, and provider-specific `stage`
- **WHEN** admin starts collection again for that same tuple
- **THEN** the system SHALL NOT create a second active run for that tuple
- **AND** the database SHALL enforce uniqueness for statuses `not_started`, `running`, and `daily_limit_reached`

#### Scenario: Provider and stage are validated together

- **GIVEN** the system creates a `collection_run`
- **WHEN** `provider = 'lixiaoyun'`
- **THEN** `stage` SHALL be `lixiaoyun_competitors`
- **AND** when `provider = 'tendata'`, `stage` SHALL be `tendata_customers`
- **AND** illegal provider/stage combinations SHALL be rejected

### Requirement: Collection tasks SHALL represent single execution batches

The system SHALL associate every V3 collection task with a `collection_run` and SHALL use tasks only for single execution batches. Scheduling, claiming, and execution behavior SHALL be defined by later collection or worker changes.

#### Scenario: Task batch is represented

- **GIVEN** a pending `collection_task` with `run_id`
- **WHEN** the task row is inspected
- **THEN** the task SHALL represent only one execution batch
- **AND** run-level cursor and platform collection status SHALL remain on `collection_runs`

### Requirement: Clean company filters SHALL be backed by explicit fields and indexes

The tenant and admin customer lists SHALL support the 10 confirmed filters through explicit schema fields and indexes.

#### Scenario: Customer list filters are mapped

- **GIVEN** the API receives filters for country, industry, incorporation date, registered capital, product tags, company size, data source, trade amount, trade count, and contact count
- **THEN** each filter SHALL map to a field in `clean_companies` or `clean_company_sources`
- **AND** the design SHALL define an index strategy for each filter
- **AND** company size SHALL use `clean_companies.employee_num` as source text in this change
- **AND** this change SHALL NOT add an employee-size normalization field

### Requirement: Raw contacts SHALL avoid duplicate rows when source contact id is missing

The system SHALL define raw contact uniqueness for sources that provide `source_contact_id` and for sources that only provide email.

#### Scenario: Source contact id exists

- **GIVEN** a raw contact has `source_contact_id`
- **WHEN** it is inserted
- **THEN** uniqueness SHALL be enforced by `(raw_company_id, source_contact_id)`

#### Scenario: Source contact id is missing but email exists

- **GIVEN** a raw contact has no `source_contact_id`
- **AND** it has an email
- **WHEN** it is inserted
- **THEN** uniqueness SHALL be enforced by `(raw_company_id, email)`

### Requirement: Legacy collection keyword tables SHALL not be V3 truth

The system SHALL treat `collection_keywords` and `collection_task_keywords` only as migration inputs or temporary compatibility artifacts.

#### Scenario: V3 resolves subscribed tenants

- **GIVEN** a V3 collection task belongs to a run
- **WHEN** the subscribed tenants for the platform keyword are resolved
- **THEN** the system SHALL resolve tenants through `collection_tasks.run_id → collection_runs.keyword_master_id → tenant_keyword`
- **AND** the system SHALL NOT use `collection_task_keywords` as the target truth source

### Requirement: API contract SHALL align with schema sources

The data foundation change SHALL define admin and tenant API contracts whose response fields can be traced to clean, raw, keyword, run/task, or tenant-view tables.

#### Scenario: Tenant requests a customer detail

- **GIVEN** a tenant requests a company detail
- **WHEN** the API receives `{id}` in `/t/{tenant_slug}/api/v1/companies/{id}`
- **THEN** company base fields SHALL come from `clean_companies`
- **AND** `{id}` SHALL mean `clean_companies.id`
- **AND** the backend SHALL verify visibility through `clean_company_keywords` joined to the current tenant's active `tenant_keyword`
- **AND** tenant private fields SHALL be overlaid from `tenant_companies` by `(tenant_id, clean_company_id)` when present
- **AND** source fields SHALL come from `clean_company_sources`
- **AND** matched tenant keywords SHALL come from `clean_company_keywords` joined through `tenant_keyword`

#### Scenario: Tenant requests company contacts

- **GIVEN** a tenant requests `/t/{tenant_slug}/api/v1/companies/{id}/contacts`
- **WHEN** the clean company is visible to the current tenant through active tenant keywords
- **THEN** the API SHALL return contacts from `clean_contacts` for that `clean_companies.id`
- **AND** it SHALL overlay tenant contact state from `tenant_contacts` when present
- **AND** it SHALL NOT require separate per-contact visibility authorization beyond company visibility

#### Scenario: Admin requests raw data

- **GIVEN** admin requests a raw company or contact list
- **WHEN** the API returns raw rows
- **THEN** the response SHALL NOT include `raw_payload` by default
- **AND** this change SHALL NOT introduce a new field-level permission model for email or phone values

#### Scenario: Clean company sources are recorded

- **GIVEN** a clean company is linked to source records in V3
- **WHEN** `clean_company_sources.source_type` is written
- **THEN** V3 SHALL allow `tendata`
- **AND** Lixiaoyun raw rows SHALL NOT be written into `clean_company_sources`
- **AND** future providers such as `waimaotong` SHALL require an explicit schema extension
