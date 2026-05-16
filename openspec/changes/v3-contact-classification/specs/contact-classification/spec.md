## ADDED Requirements

### Requirement: Admin manages shared contact classification rules
The system SHALL provide an admin-only contact classification module where platform operators manage classification levels, categories, and keywords used by all tenants.

#### Scenario: Admin edits classification hierarchy
- **WHEN** an admin creates or updates levels, categories, or keywords
- **THEN** the system MUST persist the shared hierarchy and make it available to all tenants without tenant-specific configuration

### Requirement: Classification uses three tables and one live view
The system SHALL store contact classification rules in `position_classification_levels`, `position_classification_categories`, and `position_classification_keywords`, and SHALL expose live classification results through `v_tenant_contact_classified`.

#### Scenario: Rule changes take effect
- **WHEN** an admin updates classification rules
- **THEN** `v_tenant_contact_classified` MUST reflect the updated rules without requiring a compiled cache rebuild

### Requirement: Position classification determines sendability
The system SHALL classify a contact position by tokenizing mixed Chinese and English text, matching normalized tokens against configured keywords, selecting the highest-priority matching level, and returning whether the contact is sendable.

#### Scenario: Position matches sendable keyword
- **WHEN** a contact position matches an A or B level keyword
- **THEN** classification MUST return `is_sendable=true` with the matching highest-priority level

#### Scenario: Position matches non-sendable keyword
- **WHEN** a contact position matches an X level keyword
- **THEN** classification MUST return `is_sendable=false`

#### Scenario: Position has no matching keyword
- **WHEN** a contact position matches no configured keyword
- **THEN** classification MUST treat the contact as not sendable

### Requirement: Tenant contact-rules configuration is removed
The system SHALL remove tenant-side contact-rules configuration UI and APIs so contact classification is controlled only by platform admin.

#### Scenario: Tenant opens settings or onboarding
- **WHEN** a tenant user opens settings or onboarding
- **THEN** no contact-rules configuration entry point MUST be available

### Requirement: Email plan recipient selection can use classification
The system SHALL allow email plan creation to select all contacts whose classification is sendable, without a main-contact concept or tenant-selected target strategy.

#### Scenario: Email plan selects recipients
- **WHEN** an email plan needs recipients for a company
- **THEN** the system MUST select contacts classified with `is_sendable=true`
