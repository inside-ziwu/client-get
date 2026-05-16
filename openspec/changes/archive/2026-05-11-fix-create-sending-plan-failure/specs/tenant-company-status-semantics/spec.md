## MODIFIED Requirements

### Requirement: Tenant company business status SHALL represent operational stage only

The system SHALL use `tenant_companies.business_status` only for the tenant company's durable operational stage. The active business stages for this change SHALL be `new`, `in_group`, `in_plan`, and `contacted`.

#### Scenario: New tenant company is materialized
- **WHEN** a tenant company is created from cleanup, fan-out, keyword materialization, or manual tenant creation
- **THEN** the tenant company SHALL use `business_status = new` unless it is immediately entering a later operational stage
- **AND** the system SHALL NOT store `pending_score`, `scoring`, `scored`, `selected`, `excluded`, `replied`, or `converted` in `tenant_companies.business_status`

#### Scenario: Company enters a tenant group
- **WHEN** a visible tenant company is added to an operational group
- **THEN** the system SHALL set `business_status = in_group`
- **AND** the actual group membership SHALL remain represented by `group_members`

#### Scenario: Company leaves tenant groups
- **WHEN** a visible tenant company is removed from one operational group
- **AND** the company still belongs to at least one other operational group
- **THEN** the system SHALL keep `business_status = in_group`
- **WHEN** the company is removed from its last operational group
- **AND** its current `business_status` is `in_group`
- **THEN** the system SHALL set `business_status = new`
- **AND** the system SHALL NOT move a company from `in_plan` or `contacted` back to `new` because of group removal

#### Scenario: Draft sending plan is created
- **WHEN** a tenant creates a draft sending plan without locking recipients or starting the plan
- **THEN** the system SHALL NOT change any tenant company's `business_status`

#### Scenario: Company enters a sending plan
- **WHEN** a visible tenant company is enrolled into a sending plan
- **THEN** the system SHALL set `business_status = in_plan` only if the current status is compatible with moving into a plan

#### Scenario: Company is contacted
- **WHEN** a visible tenant company's email is confirmed `delivered` through the sending provider webhook
- **AND** the tenant company currently has `business_status = in_plan`
- **THEN** the system SHALL set `business_status = contacted`

#### Scenario: Company email is sent but not delivered
- **WHEN** a visible tenant company's email is marked `sent`
- **AND** the sending provider has not confirmed `delivered`
- **THEN** the system SHALL NOT set `business_status = contacted`

#### Scenario: Existing archived value is migrated away
- **WHEN** existing data or schema contains `business_status = archived`
- **THEN** the system SHALL migrate existing tenant companies with that value to `business_status = new`
- **AND** the system SHALL remove `archived` from the allowed `tenant_companies.business_status` values
- **AND** the system SHALL NOT map legacy select or exclude actions to `archived`
