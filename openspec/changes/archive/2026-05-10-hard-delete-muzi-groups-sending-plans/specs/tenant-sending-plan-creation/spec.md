## ADDED Requirements

### Requirement: Sending plan workflows SHALL tolerate hard-deleted historical plans
The tenant sending plan workflows SHALL continue to operate when previous plans for the tenant have been physically removed by an approved hard delete operation.

#### Scenario: Tenant lists plans after hard delete cleanup
- **WHEN** the target tenant's sending plans have been hard deleted by the cleanup operation
- **THEN** the sending plan list MUST return no deleted historical plans
- **AND** the dashboard plan counts MUST not include the hard-deleted plans

#### Scenario: Tenant requests hard-deleted plan detail
- **WHEN** a tenant requests the detail of a sending plan removed by the cleanup operation
- **THEN** the system MUST return the same not-found behavior used for inaccessible or deleted plans

#### Scenario: Tenant creates a new plan after cleanup
- **WHEN** a tenant creates a new valid sending plan after the hard delete cleanup
- **THEN** the system MUST create the plan using the existing sending plan creation contract
- **AND** the new plan MUST NOT depend on any hard-deleted group, recipient, step, enrollment, email, or event row
