## ADDED Requirements

### Requirement: Tenant company external contract SHALL use V3 fields only
The system SHALL expose tenant company data to tenant-facing APIs, frontend pages, and shared tenant API types using V3 fields `score`, `model_score`, `note`, `tags`, `visibility_status`, `business_status`, and `data_status`.

#### Scenario: Tenant views company list
- **WHEN** a tenant requests the company list or prospect list
- **THEN** the response MUST include current V3 scoring and private-state fields
- **AND** the response MUST NOT include `grade`, `total_score`, `notes`, `is_precise_customer`, or `score_adjustment*`

#### Scenario: Tenant views company detail
- **WHEN** a tenant opens a company detail or drawer
- **THEN** the UI MUST display `score`, `model_score`, `note`, and `tags`
- **AND** the UI MUST NOT display grade labels, total score aliases, precise-customer labels, score adjustment controls, or score adjustment reasons

### Requirement: Tenant company filters SHALL NOT accept grade semantics
The system SHALL filter tenant company scores using numeric score bounds and SHALL NOT accept or interpret `grade` as a tenant company filter.

#### Scenario: Tenant filters by score
- **WHEN** a tenant filters companies by score
- **THEN** the API MUST use numeric score range parameters
- **AND** the tenant UI MUST NOT send a `grade` filter

#### Scenario: Legacy grade query is sent
- **WHEN** a caller sends a legacy `grade` query parameter to the tenant company list
- **THEN** the system MUST NOT apply grade semantics to the query

### Requirement: Tenant messaging SHALL remove grade distribution
The system SHALL remove tenant email statistics grouped by tenant company grade.

#### Scenario: Tenant opens email monitor
- **WHEN** tenant email monitor distribution charts are loaded
- **THEN** the frontend MUST request supported distribution endpoints only
- **AND** the UI MUST NOT show a by-grade distribution chart

#### Scenario: Legacy by-grade endpoint is requested
- **WHEN** a caller requests `/emails/stats/by-grade`
- **THEN** the route MUST not be part of the active tenant API surface

### Requirement: Tenant scoring context SHALL read current clean company fields
The scoring workflow SHALL load tenant company scoring context from current `clean_companies` fields and current tenant company state fields.

#### Scenario: Scoring context is loaded
- **WHEN** scoring loads context for a visible tenant company
- **THEN** the query MUST read current V3 clean company fields such as `industry_desc`, `product_tags`, and `country_iso3`
- **AND** the query MUST NOT read `tc.is_precise_customer`, legacy clean company `domain`, or legacy clean company `product_keywords`

#### Scenario: Rule scoring evaluates current fields
- **WHEN** rule scoring evaluates company conditions
- **THEN** it MUST use current V3 field names or return a neutral fallback
- **AND** it MUST NOT include a `precise_customer` condition branch
