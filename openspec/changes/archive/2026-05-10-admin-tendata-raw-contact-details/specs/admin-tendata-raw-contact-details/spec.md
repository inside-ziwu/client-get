## ADDED Requirements

### Requirement: Tendata raw table SHALL hide internal enrichment status columns

The admin Tendata raw company table SHALL NOT show company-level enrichment status columns as default main-table columns.

#### Scenario: Admin views Tendata raw company table
- **WHEN** platform admin opens the Tendata raw company table
- **THEN** the table SHALL NOT include `补详情`
- **AND** the table SHALL NOT include `贸易`
- **AND** the table SHALL NOT include the status column named `联系人`
- **AND** the underlying status fields MAY remain available to backend/debug paths

### Requirement: Tendata raw table SHALL not show hard-coded provider as collection method

The admin Tendata raw company table SHALL NOT show a `采集方式` column whose value is hard-coded to `tendata`.

#### Scenario: Admin views Tendata raw company table columns
- **WHEN** platform admin opens the Tendata raw company table
- **THEN** the table SHALL NOT include the hard-coded `采集方式` column
- **AND** the table SHALL NOT render repeated `tendata` tags in each row

### Requirement: Tendata raw detail SHALL display raw contact details

The admin Tendata raw company detail drawer SHALL display contact rows linked to the selected `tendata_raw_companies` row.

#### Scenario: Selected Tendata raw company has contacts
- **GIVEN** a Tendata raw company has rows in `tendata_raw_contacts`
- **WHEN** platform admin opens that raw company detail drawer
- **THEN** the drawer SHALL display a contacts table
- **AND** each contact row SHALL show available name, position, email, phone or mobile fields
- **AND** empty contact fields SHALL render as an empty-state placeholder instead of breaking the table

#### Scenario: Selected Tendata raw company has no contacts
- **GIVEN** a Tendata raw company has no rows in `tendata_raw_contacts`
- **WHEN** platform admin opens that raw company detail drawer
- **THEN** the drawer SHALL show a clear empty state for raw contacts
- **AND** the drawer SHALL NOT claim that raw Tendata detail cannot display contact details

### Requirement: Tendata raw contacts API SHALL return display fields

The admin raw contacts API SHALL support `provider=tendata` and SHALL return payload-light contact display fields from `tendata_raw_contacts`.

#### Scenario: Admin requests Tendata raw contacts
- **GIVEN** a Tendata raw company id exists
- **WHEN** platform admin requests `/api/v1/raw/tendata/companies/{raw_company_id}/contacts`
- **THEN** the API SHALL return contacts linked by `raw_company_id`
- **AND** each returned contact SHALL include id, raw_company_id, source_contact_id, name, position, email, phone, mobile when available, and created_at
- **AND** the default response SHALL NOT include `raw_payload`

#### Scenario: Admin requests contacts for unsupported provider
- **WHEN** platform admin requests raw contacts for a provider that is not supported by the raw contacts API
- **THEN** the API SHALL preserve the existing unsupported-provider behavior
- **AND** the Tendata support SHALL NOT regress existing Lixiaoyun contact responses

### Requirement: Raw and clean contact semantics SHALL be distinguishable

The admin UI SHALL distinguish provider raw contacts from cleaned tenant/customer contacts.

#### Scenario: Admin reads Tendata raw contact section
- **WHEN** platform admin views the Tendata raw company detail contact section
- **THEN** the UI SHALL communicate that these are provider raw contacts
- **AND** it SHALL NOT use the old statement that raw details only return contact counts
- **AND** it SHALL NOT imply these rows have already been clean-layer deduplicated or tenant-classified
