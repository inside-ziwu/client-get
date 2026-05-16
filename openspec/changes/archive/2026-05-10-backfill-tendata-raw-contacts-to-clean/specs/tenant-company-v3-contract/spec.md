## ADDED Requirements

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
