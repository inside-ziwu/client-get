# tenant-company-v3-contract Specification

## Purpose
TBD - created by archiving change tenant-company-v3-contract-cleanup. Update Purpose after archive.
## Requirements
### Requirement: Tenant company external contract SHALL use V3 fields only
The system SHALL expose tenant company data to tenant-facing APIs, frontend pages, and shared tenant API types using V3 fields `score`, `model_score`, `note`, `tags`, `visibility_status`, `business_status`, and `data_status`.

#### Scenario: Tenant views company list
- **WHEN** a tenant requests the company list or prospect list
- **THEN** the response MUST include current V3 scoring and private-state fields
- **AND** the response MUST NOT include `grade`, `total_score`, `notes`, `is_precise_customer`, or `score_adjustment*`

#### Scenario: Tenant views company detail
- **WHEN** a tenant opens a company detail or drawer
- **THEN** the UI MUST display `score`, `model_score`, `note`, and `tags`
- **AND** the UI MUST NOT display grade labels, total score aliases, precise-customer labels, score adjustment controls, or score adjustment reasons

### Requirement: Tenant company filters SHALL NOT accept grade semantics
The system SHALL filter tenant company scores using numeric score bounds and SHALL NOT accept or interpret `grade` as a tenant company filter.

#### Scenario: Tenant filters by score
- **WHEN** a tenant filters companies by score
- **THEN** the API MUST use numeric score range parameters
- **AND** the tenant UI MUST NOT send a `grade` filter

#### Scenario: Legacy grade query is sent
- **WHEN** a caller sends a legacy `grade` query parameter to the tenant company list
- **THEN** the system MUST NOT apply grade semantics to the query

### Requirement: Tenant messaging SHALL remove grade distribution
The system SHALL remove tenant email statistics grouped by tenant company grade.

#### Scenario: Tenant opens email monitor
- **WHEN** tenant email monitor distribution charts are loaded
- **THEN** the frontend MUST request supported distribution endpoints only
- **AND** the UI MUST NOT show a by-grade distribution chart

#### Scenario: Legacy by-grade endpoint is requested
- **WHEN** a caller requests `/emails/stats/by-grade`
- **THEN** the route MUST not be part of the active tenant API surface

### Requirement: Tenant scoring context SHALL read current clean company fields
The scoring workflow SHALL load tenant company scoring context from current `clean_companies` fields and current tenant company state fields.

#### Scenario: Scoring context is loaded
- **WHEN** scoring loads context for a visible tenant company
- **THEN** the query MUST read current V3 clean company fields such as `industry_desc`, `product_tags`, and `country_iso3`
- **AND** the query MUST NOT read `tc.is_precise_customer`, legacy clean company `domain`, or legacy clean company `product_keywords`

#### Scenario: Rule scoring evaluates current fields
- **WHEN** rule scoring evaluates company conditions
- **THEN** it MUST use current V3 field names or return a neutral fallback
- **AND** it MUST NOT include a `precise_customer` condition branch

### Requirement: Tendata raw contact rows SHALL materialize into clean contacts
The system SHALL materialize Tendata raw contact rows into current V3 clean contacts so tenant-facing company contact details can display contacts collected by Tendata.

#### Scenario: Cleanup processes Tendata raw company with raw contact rows
- **WHEN** cleanup processes a `tendata_raw_companies` row that has matching rows in `tendata_raw_contacts`
- **THEN** the system MUST create or update `clean_contacts` rows for matching raw contacts with email
- **AND** those contacts MUST be linked to the clean company through `clean_company_sources`
- **AND** tenant contacts API MUST return those contacts for visible tenant companies

#### Scenario: Historical Tendata raw contacts are backfilled
- **WHEN** a backfill is run for existing `tendata_raw_contacts`
- **THEN** the system MUST insert or update `clean_contacts` for raw contacts that have email and a `clean_company_sources` mapping
- **AND** running the backfill more than once MUST NOT create duplicate clean contacts
- **AND** the backfill MUST deduplicate candidates by clean company and case-insensitive email before upsert
- **AND** raw contacts without email MUST NOT be materialized into `clean_contacts`

#### Scenario: Tendata raw contacts are not in raw payload
- **WHEN** `tendata_raw_companies.raw_payload.contacts` is empty but `tendata_raw_contacts` contains contacts
- **THEN** cleanup and backfill MUST still materialize contacts from `tendata_raw_contacts`

#### Scenario: Cleanup uses clean company source mapping
- **WHEN** cleanup materializes contacts for a Tendata raw company
- **THEN** it MUST first ensure the `clean_company_sources` mapping exists
- **AND** it MUST use that mapping as the authority for linking `tendata_raw_contacts` to `clean_contacts`

### Requirement: Tenant company base filters align with admin customer filters
The system SHALL keep tenant company list and tenant curated customers base filters aligned with the admin customer data page base filter contract while preserving tenant visibility constraints.

#### Scenario: Tenant applies shared base filters
- **WHEN** a tenant user applies any shared base company filter on the company list or curated customers page
- **THEN** the tenant company API MUST use the same base filter semantics as the admin customer data API
- **AND** the tenant API MUST still return only companies visible to the current tenant

#### Scenario: Tenant uses private filters
- **WHEN** tenant-only filters such as score, business status, or data status remain available
- **THEN** those filters MUST be applied in addition to the shared base filters
- **AND** they MUST NOT change the meaning of the shared base filter contract
- **AND** they MUST render as flat filter operation items without a visible tenant-only category heading or key

