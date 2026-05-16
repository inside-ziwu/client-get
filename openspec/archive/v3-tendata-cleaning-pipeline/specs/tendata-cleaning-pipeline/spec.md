## ADDED Requirements

### Requirement: Tendata raw SHALL pass minimum identity checks before entering clean companies

The system SHALL only clean Tendata raw companies into `clean_companies` when the raw row contains both a company name and `country_iso3`.

#### Scenario: Tendata raw has company name and country
- **GIVEN** a `tendata_raw_companies` row has a non-empty company name
- **AND** the row has a non-empty `country_iso3`
- **WHEN** the cleanup pipeline processes the row
- **THEN** the system SHALL allow the row to be cleaned into `clean_companies`

#### Scenario: Tendata raw has no country
- **GIVEN** a `tendata_raw_companies` row has no `country_iso3`
- **WHEN** the cleanup pipeline processes the row
- **THEN** the system SHALL NOT insert or update `clean_companies` from that row
- **AND** the system SHALL leave the raw row traceable for admin/debug review

### Requirement: Tendata clean company deduplication SHALL use normalized name and country in v1

The system SHALL use normalized company name plus `country_iso3` as the v1 primary deduplication rule for cleaning Tendata raw companies into `clean_companies`.

#### Scenario: New Tendata company identity
- **GIVEN** no clean company exists with the same normalized company name and `country_iso3`
- **WHEN** a valid Tendata raw row is processed
- **THEN** the system SHALL create one `clean_companies` row for that company

#### Scenario: Existing Tendata company identity
- **GIVEN** a clean company already exists with the same normalized company name and `country_iso3`
- **WHEN** another valid Tendata raw row for that identity is processed
- **THEN** the system SHALL update the existing clean company instead of creating a duplicate clean company

### Requirement: Tendata field merge SHALL follow v1 field-class rules

The system SHALL merge Tendata raw fields into `clean_companies` using field-class-specific rules.

#### Scenario: Empty clean field receives a non-empty raw value
- **GIVEN** an existing clean company has an empty field
- **AND** a processed Tendata raw row has a non-empty value for that field
- **WHEN** the cleanup pipeline merges the row
- **THEN** the system SHALL fill the empty clean field with the raw value

#### Scenario: Latest source summary fields are merged
- **GIVEN** a valid Tendata raw row has `trade_amount_3y_usd`, `trade_count`, `contacts_count`, `industry_desc`, or `employee_num`
- **WHEN** the cleanup pipeline merges the row into a clean company
- **THEN** the system SHALL store the latest valid source summary for those fields
- **AND** the system SHALL NOT use max-value aggregation for those fields

#### Scenario: Evidence collection fields are merged
- **GIVEN** a valid Tendata raw row has `product_tags`, `pcb_suppliers`, or `aliases`
- **WHEN** the cleanup pipeline merges the row into a clean company
- **THEN** the system SHALL append those values to the clean company evidence collection
- **AND** the system SHALL remove duplicates within the collection

### Requirement: Clean companies SHALL inherit Tendata platform keyword associations

When a Tendata raw company is cleaned successfully, the resulting clean company SHALL inherit the raw row's `keyword_master_id` association.

#### Scenario: Tendata raw has a platform keyword
- **GIVEN** a valid `tendata_raw_companies` row has `keyword_master_id`
- **WHEN** the cleanup pipeline creates or updates a clean company from the row
- **THEN** the system SHALL create or retain a clean company to platform keyword association for that `keyword_master_id`

#### Scenario: Same clean company is discovered by multiple platform keywords
- **GIVEN** a clean company is already associated with one platform keyword
- **AND** another valid Tendata raw row for the same clean company has a different `keyword_master_id`
- **WHEN** the cleanup pipeline processes the second row
- **THEN** the system SHALL add the new platform keyword association
- **AND** the system SHALL NOT remove the existing platform keyword association

#### Scenario: Tendata raw has no platform keyword
- **GIVEN** a valid `tendata_raw_companies` row has no `keyword_master_id`
- **WHEN** the cleanup pipeline creates or updates a clean company from the row
- **THEN** the system SHALL NOT create a clean company to platform keyword association from that row
- **AND** the system SHALL NOT materialize tenant companies from that row alone

#### Scenario: Tendata raw without platform keyword updates an already visible clean company
- **GIVEN** a valid `tendata_raw_companies` row has no `keyword_master_id`
- **AND** the row matches an existing clean company that is already associated with a platform keyword from another source row
- **WHEN** the cleanup pipeline merges source fields into that clean company
- **THEN** the system MAY update the clean company fields and source evidence from that row
- **AND** the system SHALL NOT add a new platform keyword association from that row

### Requirement: Tendata source evidence SHALL remain traceable after cleaning

The system SHALL preserve source evidence linking each cleaned company back to the Tendata raw row that contributed it.

#### Scenario: Tendata raw is cleaned
- **GIVEN** a valid Tendata raw row is cleaned into a clean company
- **WHEN** the cleanup pipeline completes for that row
- **THEN** the system SHALL create or retain source evidence linking the clean company to the Tendata raw row
- **AND** the source evidence SHALL include `source_type = tendata`

### Requirement: Tenant company visibility SHALL be materialized from active tenant keyword subscriptions

The system SHALL materialize tenant-visible company rows for tenants that actively subscribe to the platform keyword associated with a clean company. The materialized tenant company state SHALL include `visibility_status` with allowed values `visible` and `hidden`.

#### Scenario: Existing tenant subscribes to the platform keyword
- **GIVEN** a clean company is associated with a platform keyword
- **AND** a tenant has an active `tenant_keyword` subscription to that platform keyword
- **WHEN** the visibility materialization runs
- **THEN** the system SHALL create or update that tenant's private company state for the clean company
- **AND** the tenant company state SHALL have `visibility_status = visible`
- **AND** the tenant company state SHALL be visible in the tenant company list

#### Scenario: New clean company is associated with an already subscribed platform keyword
- **GIVEN** a tenant already has an active `tenant_keyword` subscription to a platform keyword
- **WHEN** a new clean company becomes associated with that platform keyword
- **THEN** the system SHALL materialize the clean company into that tenant's company list

#### Scenario: Tenant adds a keyword that already has clean companies
- **GIVEN** clean companies already exist for a platform keyword
- **WHEN** a tenant adds an active `tenant_keyword` subscription to that platform keyword
- **THEN** the system SHALL materialize those existing clean companies into that tenant's company list

#### Scenario: Existing tenant company visibility is backfilled
- **GIVEN** an existing `tenant_companies` row is migrated to include `visibility_status`
- **WHEN** the migration or backfill runs
- **THEN** the system SHALL set `visibility_status = visible` only if the tenant has at least one active tenant keyword covering the clean company
- **AND** the system SHALL set `visibility_status = hidden` when no active tenant keyword covers the clean company

#### Scenario: Tenant company materialization is idempotent
- **GIVEN** a tenant company row already exists for the same tenant and clean company
- **WHEN** visibility materialization runs again
- **THEN** the system SHALL update the existing tenant company row
- **AND** the system SHALL NOT create a duplicate tenant company row

### Requirement: Tenant company business status SHALL represent operational stage only

The system SHALL use `tenant_companies.business_status` to represent the tenant's durable operational stage for a company, not transient frontend selection state.

#### Scenario: Tenant company business status values
- **GIVEN** a tenant company exists
- **WHEN** the system stores `business_status`
- **THEN** the value SHALL be one of `new`, `in_group`, `in_plan`, `contacted`, or `archived`
- **AND** the system SHALL NOT store `selected` as a `business_status`

#### Scenario: Existing selected business status is migrated
- **GIVEN** an existing tenant company has `business_status = selected`
- **WHEN** the schema migrates away from selected
- **THEN** the system SHALL migrate that value to `new`
- **AND** the system MAY later set `business_status = in_group` if valid group membership exists

#### Scenario: Tenant company is added to a group
- **GIVEN** a tenant company is added to an operational group
- **WHEN** the system updates durable operational state
- **THEN** the system MAY set `business_status = in_group`
- **AND** the actual group membership SHALL be represented by `group_members`

### Requirement: Tenant company data status SHALL be system-derived and SHALL NOT control visibility

The system SHALL derive `tenant_companies.data_status` from data readiness signals rather than tenant manual operation. `data_status` SHALL NOT determine whether a tenant company appears in the tenant company list.

#### Scenario: Tenant company data status values
- **GIVEN** a tenant company exists
- **WHEN** the system stores `data_status`
- **THEN** the value SHALL be one of `ready`, `missing_contacts`, or `insufficient_data`

#### Scenario: Tenant company lacks usable contacts
- **GIVEN** a visible tenant company has no usable clean or tenant contact
- **WHEN** the system evaluates data readiness
- **THEN** the system SHALL set `data_status = missing_contacts`

#### Scenario: Tenant company has insufficient core data
- **GIVEN** a visible tenant company has insufficient company profile data for operation
- **AND** it does not qualify as `missing_contacts`
- **WHEN** the system evaluates data readiness
- **THEN** the system SHALL set `data_status = insufficient_data`

#### Scenario: Tenant company has enough data to operate
- **GIVEN** a visible tenant company does not qualify as `missing_contacts`
- **AND** it does not qualify as `insufficient_data`
- **WHEN** the system evaluates data readiness
- **THEN** the system SHALL set `data_status = ready`

#### Scenario: Data status differs from visibility
- **GIVEN** a tenant company has `visibility_status = visible`
- **AND** the tenant company has `data_status = missing_contacts`
- **WHEN** the tenant opens the company list
- **THEN** the company SHALL remain visible
- **AND** the data status SHALL only describe operational readiness

### Requirement: Tenant keyword cancellation SHALL hide only companies with no remaining active keyword coverage

When a tenant cancels a keyword subscription, the system SHALL hide affected tenant companies only if the tenant has no other active keyword subscription covering those clean companies.

#### Scenario: Cancelled keyword is the tenant's only coverage for a company
- **GIVEN** a tenant company is visible because of one active tenant keyword
- **WHEN** that tenant keyword is cancelled
- **AND** no other active tenant keyword for the tenant covers the same clean company
- **THEN** the system SHALL set the tenant company's `visibility_status` to `hidden`
- **AND** the tenant company SHALL NOT appear in the tenant company list

#### Scenario: Cancelled keyword removes the tenant's last coverage and clears private operational state
- **GIVEN** a tenant company has private operational state such as score, note, tags, group, stage, or priority
- **AND** the tenant company is visible only because of one active tenant keyword
- **WHEN** that tenant keyword is cancelled
- **AND** no other active tenant keyword for the tenant covers the same clean company
- **THEN** the system SHALL set the tenant company's `visibility_status` to `hidden`
- **AND** the system SHALL clear the tenant company's `model_score`, `score`, `note`, and `tags`
- **AND** the system SHALL reset the tenant company's `business_status` to `new`
- **AND** the system SHALL remove the tenant company from tenant groups
- **AND** the system SHALL delete or cancel pending scoring jobs for the tenant company
- **AND** the system SHALL delete or archive company score records for the tenant company
- **AND** the system SHALL recompute `data_status` if the tenant company becomes visible again later
- **AND** the system SHALL NOT delete the platform clean company, source evidence, or platform keyword association

#### Scenario: Another active tenant keyword still covers the company
- **GIVEN** a tenant company is visible through multiple active tenant keywords
- **WHEN** one of those tenant keywords is cancelled
- **AND** at least one other active tenant keyword still covers the same clean company
- **THEN** the system SHALL keep the tenant company's `visibility_status = visible`
- **AND** the tenant company SHALL remain visible in the tenant company list
- **AND** the system SHALL keep that tenant's private operational state for the clean company

### Requirement: Scoring SHALL NOT be required for basic tenant company visibility

Tenant company visibility SHALL be determined by active tenant keyword coverage and materialized visibility state, not by scoring.

#### Scenario: Tenant company has no score
- **GIVEN** a tenant company is materialized from an active tenant keyword subscription
- **AND** the tenant has not scored the company
- **WHEN** the tenant opens the company list
- **THEN** the company SHALL still be visible
- **AND** score-related fields MAY remain empty until the tenant performs scoring or another scoring process updates them

### Requirement: Tenant company list SHALL use materialized visibility state as the display gate

The tenant company list SHALL use `tenant_companies.visibility_status = visible` as the display gate instead of dynamically deriving display eligibility from `clean_company_keywords` and active `tenant_keyword` joins.

#### Scenario: Tenant company is hidden after keyword cancellation
- **GIVEN** a tenant company has `visibility_status = hidden`
- **WHEN** the tenant opens the company list
- **THEN** the hidden tenant company SHALL NOT appear in the company list

#### Scenario: Platform keyword relation still exists for a hidden tenant company
- **GIVEN** a clean company remains associated with a platform keyword
- **AND** the tenant company has `visibility_status = hidden`
- **WHEN** the tenant opens the company list
- **THEN** the system SHALL NOT show the company only because the platform keyword relation still exists

#### Scenario: Hidden tenant company cannot be operated through other tenant entry points
- **GIVEN** a tenant company has `visibility_status = hidden`
- **WHEN** the tenant attempts to access detail, scoring, grouping, or sending workflows for that tenant company
- **THEN** the system SHALL block the operation or behave as not found for the tenant

### Requirement: Tenant operational reference tables SHALL align tenant company identifiers

Tables that reference tenant company records SHALL use the same identifier type as `tenant_companies.id`.

#### Scenario: Tenant company reference columns are aligned
- **GIVEN** `tenant_companies.id` is `bigint`
- **WHEN** the schema defines `company_scores.tenant_company_id`, `group_members.tenant_company_id`, or `scoring_jobs.tenant_company_id`
- **THEN** those columns SHALL be `bigint`
- **AND** those columns SHALL reference `tenant_companies(id)`
- **AND** existing data SHALL be migrated only through a verified mapping or otherwise archived/deleted before the foreign key is added

#### Scenario: Tenant contact reference column is aligned
- **GIVEN** `tenant_contacts.id` is `bigint`
- **WHEN** the schema defines `group_members.tenant_contact_id` as a reference to tenant contacts
- **THEN** that column SHALL be `bigint`
- **AND** it SHALL reference `tenant_contacts(id)`

### Requirement: Tendata source summary freshness SHALL be deterministic

The system SHALL determine the latest Tendata source summary using a stable timestamp.

#### Scenario: Multiple Tendata raw rows contribute source summary fields
- **GIVEN** multiple valid Tendata raw rows match the same clean company
- **AND** those rows have source summary fields such as `trade_amount_3y_usd`, `trade_count`, `contacts_count`, `industry_desc`, or `employee_num`
- **WHEN** the cleanup pipeline merges those rows
- **THEN** the system SHALL keep the source summary from the row with the latest `created_at`
- **AND** reprocessing the same rows in a different order SHALL NOT change the final source summary
