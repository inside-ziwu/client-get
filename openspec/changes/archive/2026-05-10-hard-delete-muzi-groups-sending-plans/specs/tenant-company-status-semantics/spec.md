## ADDED Requirements

### Requirement: Hard-deleted tenant companies SHALL NOT be represented by status fields
The system SHALL treat the operational hard delete cleanup as physical removal of tenant-scoped rows, not as a tenant company status transition.

#### Scenario: Muzi tenant company is hard deleted
- **WHEN** the confirmed `muzi` tenant company is removed by the hard delete operation
- **THEN** the system MUST NOT set `business_status` to a replacement value
- **AND** the system MUST NOT set `visibility_status` to `hidden` as the deletion result
- **AND** tenant company list and detail workflows MUST omit the company because the tenant company row no longer exists

#### Scenario: Group deletion affects prior in_group companies
- **WHEN** all groups are hard deleted for a tenant
- **THEN** the system MUST NOT rely on group deletion to mutate remaining tenant companies from `in_group` to another status
- **AND** any status repair for non-deleted companies MUST be explicit, tested, and scoped to the target tenant
