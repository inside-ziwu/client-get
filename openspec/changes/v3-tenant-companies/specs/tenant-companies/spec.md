## ADDED Requirements

### Requirement: Tenant can edit private company state
The system SHALL let tenant users edit tenant-private company state from the company drawer, including private note, private tags, and group membership.

#### Scenario: Tenant edits private state
- **WHEN** a tenant user updates note, tags, or group membership for a company
- **THEN** the update MUST persist only for that tenant and the company row and drawer MUST reflect the changed private state

### Requirement: Company filters support ten dimensions
The system SHALL support tenant company filtering across country, industry segment, product tags, data source, establishment age, registered capital, company size, import/export value, import/export count, and contact count.

#### Scenario: Tenant filters company list
- **WHEN** a tenant applies any supported filter combination
- **THEN** the API MUST return only matching companies visible to that tenant

#### Scenario: Tenant filters curated customers
- **WHEN** a tenant applies filters on curated customers
- **THEN** the same filter semantics MUST apply as on the main company list

### Requirement: Filter UI is reusable and stateful
The system SHALL provide a reusable tenant filter component shared by Companies and Curated Customers, including multi-select OR filters, bucket filters, selected-filter chips, clear-all behavior, and pagination/sort coordination.

#### Scenario: Tenant changes filters
- **WHEN** a tenant adds, removes, or clears filters
- **THEN** the UI MUST update selected chips and refresh the list without breaking pagination or sorting

### Requirement: Admin manages industry scoring templates
The system SHALL let admin manage scoring templates by industry, including the PCB default template with seven dimensions, dimension buckets, scores, default weights, and preview behavior.

#### Scenario: Admin updates PCB scoring template
- **WHEN** admin changes PCB scoring template dimensions, buckets, scores, or default weights
- **THEN** the system MUST persist the industry template and make it available for tenant scoring

### Requirement: Tenant only adjusts scoring weights
The system SHALL change tenant scoring settings so tenants can view the inherited industry template and adjust weights only, without editing scoring rules.

#### Scenario: Tenant opens scoring settings
- **WHEN** tenant opens scoring settings
- **THEN** the UI MUST show inherited scoring dimensions and allow weight adjustment without rule-editing controls

### Requirement: Scoring worker applies V3 scoring model
The system SHALL apply tenant weights and write V3 scoring summaries to `tenant_companies.model_score` and `tenant_companies.score`, using zero as fallback for missing or out-of-bucket data.

#### Scenario: Scoring worker computes score
- **WHEN** scoring worker scores a tenant company
- **THEN** it MUST apply the configured template, tenant weights, and fallback rules, then persist `model_score` and `score`

### Requirement: Tenant private state remains isolated
The system SHALL enforce tenant isolation so private company state such as note, tags, groups, and blacklist status is not visible or mutable by other tenants.

#### Scenario: Tenant B views same shared company
- **WHEN** tenant A has edited private state for a company and tenant B views the same shared company
- **THEN** tenant B MUST NOT see tenant A's private state
