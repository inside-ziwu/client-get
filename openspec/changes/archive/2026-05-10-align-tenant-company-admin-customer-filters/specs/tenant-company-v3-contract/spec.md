## ADDED Requirements

### Requirement: Tenant company base filters align with admin customer filters
The system SHALL keep tenant company list and tenant curated customers base filters aligned with the admin customer data page base filter contract while preserving tenant visibility constraints.

#### Scenario: Tenant applies shared base filters
- **WHEN** a tenant user applies any shared base company filter on the company list or curated customers page
- **THEN** the tenant company API MUST use the same base filter semantics as the admin customer data API
- **AND** the tenant API MUST still return only companies visible to the current tenant

#### Scenario: Tenant uses private filters
- **WHEN** tenant-only filters such as score, business status, or data status remain available
- **THEN** those filters MUST be applied in addition to the shared base filters
- **AND** they MUST NOT change the meaning of the shared base filter contract
- **AND** they MUST render as flat filter operation items without a visible tenant-only category heading or key
