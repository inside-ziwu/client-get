## MODIFIED Requirements

### Requirement: Tenant dashboard and client types SHALL expose current business status semantics

The tenant-facing dashboard, filters, API types, and frontend display labels SHALL use the current business status semantics and current V3 tenant company contract.

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
- **THEN** the count SHALL be derived from `score`
- **AND** it SHALL NOT depend on `business_status = scored`
- **AND** it SHALL NOT depend on tenant company `grade`
- **AND** it SHALL count only tenant companies with `visibility_status = visible`

#### Scenario: Companies filters are requested
- **WHEN** the tenant companies filters are requested
- **THEN** business status, data status, country, and other tenant-facing filter options SHALL be derived only from tenant companies with `visibility_status = visible`
- **AND** hidden tenant companies SHALL NOT contribute filter values
- **AND** tenant company grade SHALL NOT be returned as a filter option

#### Scenario: Frontend submits or filters business status
- **WHEN** the frontend submits or filters by tenant company business status
- **THEN** it SHALL use only `new`, `in_group`, `in_plan`, or `contacted`
- **AND** shared frontend types SHALL NOT list removed business status values as valid tenant company business statuses

### Requirement: Tenant company visibility SHALL remain independent of business status

The system SHALL continue to use `tenant_companies.visibility_status` as the access and display gate for tenant companies and SHALL NOT rely on `tenant_companies.deleted_at`.

#### Scenario: Visible company has any valid business stage
- **WHEN** a tenant company has `visibility_status = visible`
- **AND** its `business_status` is any allowed operational stage
- **THEN** tenant company list and allowed operating workflows SHALL treat it as visible subject to their existing filters
- **AND** tenant company queries SHALL NOT require `tenant_companies.deleted_at`

#### Scenario: Hidden company has any business stage
- **WHEN** a tenant company has `visibility_status = hidden`
- **THEN** detail, scoring, grouping, sending workflows, dashboard metrics, and filter options SHALL continue to block or omit it
- **AND** changing `business_status` SHALL NOT make the hidden company operable
