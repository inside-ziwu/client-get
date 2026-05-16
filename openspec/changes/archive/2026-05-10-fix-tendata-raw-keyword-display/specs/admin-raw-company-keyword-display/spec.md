## ADDED Requirements

### Requirement: Admin raw Tendata list SHALL expose display keyword from keyword master

The V3 admin raw company list endpoint for Tendata SHALL expose a display keyword by resolving `tendata_raw_companies.keyword_master_id` through `keyword_master.id`.

#### Scenario: Tendata raw row has keyword master

- **WHEN** an admin requests `/api/v1/raw/tendata/companies` and a returned `tendata_raw_companies` row has `keyword_master_id` referencing a `keyword_master` row
- **THEN** the response item SHALL include the raw row's `keyword_master_id`
- **AND** the response item SHALL include `keyword` equal to the referenced `keyword_master.keyword`

#### Scenario: Tendata raw row has null keyword master

- **WHEN** an admin requests `/api/v1/raw/tendata/companies` and a returned `tendata_raw_companies` row has `keyword_master_id IS NULL`
- **THEN** the response item SHALL still be returned
- **AND** the response item SHALL include `keyword` as `null`

### Requirement: Admin Tendata page SHALL display keyword master keyword

The admin Tendata data page SHALL render the keyword column from the API response's `keyword` value, which is sourced from `keyword_master.keyword`.

#### Scenario: API row contains keyword

- **WHEN** the admin Tendata data page receives a row with `keyword`
- **THEN** the keyword column SHALL display that `keyword` value

#### Scenario: API row contains null keyword

- **WHEN** the admin Tendata data page receives a row with `keyword` as `null`
- **THEN** the keyword column SHALL display `—`

### Requirement: Tendata raw schema SHALL remain unchanged

This change SHALL NOT add keyword display columns to `tendata_raw_companies`; keyword display data SHALL be resolved from the existing `keyword_master_id` foreign key relationship.

#### Scenario: Implementing keyword display

- **WHEN** the keyword display fix is implemented
- **THEN** no migration SHALL add `keyword_normalized`, `keyword`, or other keyword display columns to `tendata_raw_companies`
