## MODIFIED Requirements

### Requirement: Tenant manual company creation SHALL use current V3 tenant company schema

The system SHALL create tenant-owned manual companies using current `tenant_companies` schema, ISO3 country keys or the existing `UNK` fallback for empty country, and current status semantics, and SHALL expose predictable validation or business errors for rejected create requests.

#### Scenario: Tenant manually creates a company with usable operating data
- **WHEN** a tenant manually creates a company and the company has enough data for operation
- **THEN** the system SHALL create or link a clean company
- **AND** the system SHALL create a visible tenant company with `business_status = new`
- **AND** the system SHALL set `data_status` to one of `ready`, `missing_contacts`, or `insufficient_data`
- **AND** the create request SHALL return the created tenant company using the current tenant company API contract

#### Scenario: Tenant manually creates a company without enough data
- **WHEN** a tenant manually creates a company with insufficient profile data or missing usable contacts
- **THEN** the system SHALL still create the tenant company if the minimum identity is valid
- **AND** the system SHALL represent data readiness using `data_status`
- **AND** the system SHALL NOT use `business_status` to represent data completeness

#### Scenario: Tenant company identity is generated
- **WHEN** the system inserts a manual tenant company
- **THEN** the system SHALL use the database's current tenant company identity strategy
- **AND** the system SHALL NOT insert UUID values into bigint tenant company identity columns

#### Scenario: Manual company create payload is submitted from the frontend
- **WHEN** a tenant admin or operator submits the new company form with valid minimum identity data
- **THEN** the frontend SHALL send only fields supported by the tenant company create API
- **AND** any selected country SHALL be submitted as an ISO3 country key
- **AND** the backend SHALL accept the payload without relying on legacy company fields
- **AND** the frontend SHALL refresh the company list after the create request succeeds

#### Scenario: Manual company create payload uses a supported ISO2 country input
- **WHEN** a create request supplies a supported ISO2 country value such as `US`, `DE`, `CN`, or `JP`
- **THEN** the system SHALL normalize the value to the corresponding ISO3 key before writing `clean_companies.country_iso3`
- **AND** the operation SHALL NOT fail because of the `clean_companies.country_iso3` database check constraint

#### Scenario: Manual company create payload omits country
- **WHEN** a create request omits country
- **THEN** the system SHALL preserve the existing empty-country fallback behavior
- **AND** the operation SHALL NOT fail because `UNK` is not an official ISO3 country code

#### Scenario: Manual company create payload uses an unsupported country input
- **WHEN** a create request supplies a country value that cannot be reliably normalized to an ISO3 key
- **THEN** the system SHALL reject the request with a validation error before writing `clean_companies`
- **AND** the system SHALL NOT guess by truncating the country value to its first three characters

#### Scenario: Tenant manually creates a company with a contact email
- **WHEN** a tenant manually creates a company with a valid contact email
- **THEN** the system SHALL create or link the tenant company
- **AND** the system SHALL create or link the contact records using the tenant company's database identity without type mismatch errors
- **AND** the operation SHALL return the created tenant company successfully

#### Scenario: Manual company create payload is invalid
- **WHEN** a create request is missing required company identity data or contains invalid field types
- **THEN** the system SHALL reject the request with a validation error before database writes
- **AND** the response SHALL include a clear error code and user-facing message
- **AND** the system SHALL NOT expose a raw database constraint or unhandled server error for this input

#### Scenario: Tenant manually creates a company that already exists for the tenant
- **WHEN** a tenant creates a company whose normalized company identity already maps to an existing visible tenant company for that tenant
- **THEN** the system SHALL return or preserve the existing tenant company without creating a duplicate tenant company row
- **AND** the operation SHALL NOT fail because of the `(tenant_id, clean_company_id)` uniqueness constraint
