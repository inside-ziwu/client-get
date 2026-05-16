## ADDED Requirements

### Requirement: Admin customer country display MUST use Chinese country names

The system MUST display admin customer data country values as Chinese country names when the country can be deterministically identified from the supported ISO3-to-Chinese frontend mapping. Chinese country names MUST remain unchanged, and unknown values MUST remain traceable instead of being guessed.

#### Scenario: Admin list displays ISO3 country as Chinese

- **WHEN** an admin customer row has `country_iso3` value `USA`
- **THEN** the admin customer list displays country value `美国`

#### Scenario: Admin detail displays ISO3 country as Chinese

- **WHEN** an admin customer detail has `country_iso3` value `DEU`
- **THEN** the admin customer detail displays country value `德国`

#### Scenario: Chinese country name remains Chinese in display mapping

- **WHEN** the country display mapper receives country value `日本`
- **THEN** the display value remains `日本`

### Requirement: Unknown country values MUST remain traceable

The system MUST NOT guess a Chinese country name when an admin or tenant customer country value cannot be mapped by the supported frontend ISO3-to-Chinese mapping.

#### Scenario: Unknown country value is encountered

- **WHEN** an admin or tenant customer country value is unrecognized
- **THEN** the display preserves the original value without showing a guessed Chinese country name

### Requirement: Admin and tenant country localization MUST share one frontend mapping

The system MUST use one frontend shared country localization helper for admin and tenant country display/filter behavior, without adding a backend display field, database country table, or large i18n/country library for this change.

#### Scenario: Shared mapping is used by admin and tenant

- **WHEN** admin and tenant customer pages display `country_iso3` value `USA`
- **THEN** both pages display the Chinese country name `美国` using the shared frontend helper

#### Scenario: Tenant company list displays ISO3 country as Chinese

- **WHEN** a tenant company list row has `country_iso3` value `USA`
- **THEN** the tenant company list displays country value `美国`

#### Scenario: Tenant company detail displays ISO3 country as Chinese

- **WHEN** a tenant company detail has `country_iso3` value `USA`
- **THEN** the tenant company detail displays country value `美国`

#### Scenario: Tenant curated customer displays ISO3 country as Chinese

- **WHEN** a tenant curated customer row has `country_iso3` value `USA`
- **THEN** the tenant curated customer list displays country value `美国`

#### Scenario: Shared filter options keep ISO3 values

- **WHEN** admin and tenant country filters render Chinese country options
- **THEN** option labels are Chinese country names
- **AND** option values remain ISO3 keys

#### Scenario: Tenant country filter does not submit Chinese display text

- **WHEN** the tenant country filter displays option label `美国`
- **AND** the user selects that option
- **THEN** the tenant frontend sends the ISO3 value `USA` to the backend filter
- **AND** it does not send `美国` as the country filter value

#### Scenario: Tenant selected country filter summary displays Chinese

- **WHEN** the tenant country filter has selected ISO3 value `USA`
- **THEN** the tenant selected filter summary or chip displays country value `美国`
- **AND** the backend filter request still uses `USA`

### Requirement: Executable country keys MUST remain machine-readable

The system MUST keep machine-executable country keys separate from Chinese display values when admin customer country values are used for filtering, deduplication, provider calls, or worker execution.

#### Scenario: User selects a Chinese country for filtering

- **WHEN** the admin customer country filter displays country value `中国`
- **THEN** the backend execution path uses the corresponding machine key `CHN` where ISO3 is required

#### Scenario: Chinese display value does not replace provider parameter

- **WHEN** a provider call requires an ISO3 or provider-specific country parameter
- **THEN** the system does not send the Chinese display value as the executable provider parameter

### Requirement: Internal ISO3 country keys MUST remain unchanged

The system MUST keep existing internal `country_iso3` semantics for raw company cleaning, clean company deduplication, filtering, and relational joins.

#### Scenario: Clean company deduplication still uses ISO3

- **WHEN** raw company data is cleaned into `clean_companies`
- **THEN** deduplication continues to use normalized company name plus `country_iso3`

### Requirement: Clean company country storage MUST remain ISO3

The system MUST NOT update clean company country storage from ISO3 machine keys to Chinese display names for this change.

#### Scenario: Clean company country value remains machine-readable

- **WHEN** a clean company is stored with `country_iso3` value `USA`
- **THEN** the clean company storage remains `USA`
- **AND** the human-facing display may show `美国`

#### Scenario: Chinese filter maps to ISO3 data

- **WHEN** admin customer data persists only machine country keys such as `country_iso3`
- **AND** the frontend displays Chinese country names such as `美国`
- **AND** selecting `美国` filters the corresponding `USA` records
- **THEN** the system does not update the clean company library for country localization
