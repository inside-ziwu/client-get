## ADDED Requirements

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

### Requirement: Scoring SHALL NOT mutate tenant company operational stage

The system SHALL keep scoring state separate from `tenant_companies.business_status`.

#### Scenario: Scoring completes with a final score
- **WHEN** the scoring workflow produces a final score for a visible tenant company
- **THEN** the system SHALL update scoring records and tenant company scoring summary fields
- **AND** the system SHALL NOT set `tenant_companies.business_status` to `scored`

#### Scenario: Scoring requires asynchronous LLM completion
- **WHEN** a scoring workflow creates or updates a pending LLM scoring record
- **THEN** the system SHALL represent that pending state in scoring records or scoring jobs
- **AND** the system SHALL NOT set `tenant_companies.business_status` to `pending_score` or `scoring`

#### Scenario: Company has not been scored
- **WHEN** a visible tenant company has no score or grade
- **THEN** the company SHALL remain visible according to `visibility_status`
- **AND** the lack of score SHALL NOT require a special `business_status`

### Requirement: Tenant manual company creation SHALL use current V3 tenant company schema

The system SHALL create tenant-owned manual companies using current `tenant_companies` schema and current status semantics.

#### Scenario: Tenant manually creates a company with usable operating data
- **WHEN** a tenant manually creates a company and the company has enough data for operation
- **THEN** the system SHALL create or link a clean company
- **AND** the system SHALL create a visible tenant company with `business_status = new`
- **AND** the system SHALL set `data_status` to one of `ready`, `missing_contacts`, or `insufficient_data`

#### Scenario: Tenant manually creates a company without enough data
- **WHEN** a tenant manually creates a company with insufficient profile data or missing usable contacts
- **THEN** the system SHALL still create the tenant company if the minimum identity is valid
- **AND** the system SHALL represent data readiness using `data_status`
- **AND** the system SHALL NOT use `business_status` to represent data completeness

#### Scenario: Tenant company identity is generated
- **WHEN** the system inserts a manual tenant company
- **THEN** the system SHALL use the database's current tenant company identity strategy
- **AND** the system SHALL NOT insert UUID values into bigint tenant company identity columns

### Requirement: Legacy prospect select and exclude actions SHALL be removed or disabled

The system SHALL remove or disable legacy prospect select and exclude actions because they do not have confirmed current product semantics.

#### Scenario: Prospect select action is invoked
- **WHEN** a caller invokes a legacy select action for a visible tenant company
- **THEN** the system SHALL NOT write `selected` to `tenant_companies.business_status`
- **AND** the system SHALL return a clear unsupported/not-found response or remove the route from the active API surface
- **AND** the system SHALL NOT map the action to another business stage

#### Scenario: Prospect exclude action is invoked
- **WHEN** a caller invokes a legacy exclude action for a visible tenant company
- **THEN** the system SHALL NOT write `excluded` to `tenant_companies.business_status`
- **AND** the system SHALL return a clear unsupported/not-found response or remove the route from the active API surface
- **AND** the system SHALL NOT map the action to another business stage

#### Scenario: Caller submits an invalid business status
- **WHEN** a caller attempts to update `business_status` to a value outside `new`, `in_group`, `in_plan`, or `contacted`
- **THEN** the system SHALL reject the request with a validation error before relying on a database constraint failure

### Requirement: Tenant dashboard and client types SHALL expose current business status semantics

The tenant-facing dashboard, filters, API types, and frontend display labels SHALL use the current business status semantics.

#### Scenario: Dashboard funnel is requested
- **WHEN** the tenant dashboard funnel is requested
- **THEN** the funnel SHALL return stages for `new`, `in_group`, `in_plan`, and `contacted`
- **AND** it SHALL NOT return obsolete scoring or selection stages as business stages
- **AND** it SHALL count only tenant companies with `visibility_status = visible`

#### Scenario: Dashboard overview is requested
- **WHEN** the tenant dashboard overview is requested
- **THEN** company totals and scored company counts SHALL count only tenant companies with `visibility_status = visible`
- **AND** hidden tenant companies SHALL NOT appear in tenant-facing dashboard metrics

#### Scenario: Scored company count is displayed
- **WHEN** the dashboard displays scored company counts
- **THEN** the count SHALL be derived from score or grade data
- **AND** it SHALL NOT depend on `business_status = scored`
- **AND** it SHALL count only tenant companies with `visibility_status = visible`

#### Scenario: Companies filters are requested
- **WHEN** the tenant companies filters are requested
- **THEN** business status, data status, grade, country, and other tenant-facing filter options SHALL be derived only from tenant companies with `visibility_status = visible`
- **AND** hidden tenant companies SHALL NOT contribute filter values

#### Scenario: Frontend submits or filters business status
- **WHEN** the frontend submits or filters by tenant company business status
- **THEN** it SHALL use only `new`, `in_group`, `in_plan`, or `contacted`
- **AND** shared frontend types SHALL NOT list removed business status values as valid tenant company business statuses

### Requirement: Tenant company visibility SHALL remain independent of business status

The system SHALL continue to use `tenant_companies.visibility_status` as the access and display gate for tenant companies.

#### Scenario: Visible company has any valid business stage
- **WHEN** a tenant company has `visibility_status = visible`
- **AND** its `business_status` is any allowed operational stage
- **THEN** tenant company list and allowed operating workflows SHALL treat it as visible subject to their existing filters

#### Scenario: Hidden company has any business stage
- **WHEN** a tenant company has `visibility_status = hidden`
- **THEN** detail, scoring, grouping, sending workflows, dashboard metrics, and filter options SHALL continue to block or omit it
- **AND** changing `business_status` SHALL NOT make the hidden company operable
