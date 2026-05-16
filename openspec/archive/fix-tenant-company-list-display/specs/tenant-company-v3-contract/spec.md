## ADDED Requirements

### Requirement: Tenant company list SHALL display current contact facts
The system SHALL expose and display tenant company contact facts from current V3 clean company and clean contact data. Tenant-facing list and detail views MUST use `contacts_count` and current clean contact fields, and MUST NOT rely on legacy prospect aliases for these values.

#### Scenario: Tenant views company list with zero contacts
- **WHEN** a visible tenant company is linked to a clean company with `contacts_count = 0`
- **THEN** the tenant company list API MUST return `contacts_count = 0`
- **AND** the tenant company list UI MUST display `0` rather than an empty placeholder

#### Scenario: Tenant views company list with contacts
- **WHEN** a visible tenant company is linked to a clean company with `contacts_count > 0`
- **THEN** the tenant company list API MUST return the current `contacts_count`
- **AND** the tenant company list UI MUST display that count in the contacts column

#### Scenario: Tenant views contact details
- **WHEN** a tenant opens contacts for a visible tenant company
- **THEN** the tenant contacts API MUST return current clean contact `name`, `position`, `email`, and `phone` fields
- **AND** the tenant company detail UI MUST render those fields without swapping name, position, email, or phone

#### Scenario: Legacy contact aliases are absent
- **WHEN** the tenant contacts API returns only current V3 clean contact fields
- **THEN** the tenant company detail UI MUST still render contact name, position, email, and phone correctly
- **AND** it MUST NOT require legacy fields such as `contact_name`, `contact_title`, or `full_name`

#### Scenario: Tendata collection includes contact details
- **WHEN** a Tendata company collection result includes current contact detail rows in `contacts`
- **THEN** raw company persistence MUST retain those contact detail rows in `raw_payload.contacts`
- **AND** cleanup MUST materialize contact rows with email into `clean_contacts`
- **AND** the tenant contacts API MUST return those materialized contacts for the visible tenant company
