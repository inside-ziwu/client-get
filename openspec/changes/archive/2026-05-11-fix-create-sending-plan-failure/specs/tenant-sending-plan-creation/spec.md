## ADDED Requirements

### Requirement: Tenant can create a complete sending plan atomically
The system SHALL provide a tenant sending plan creation flow that creates the plan, required sequence steps, and optional locked recipients as one atomic operation.

#### Scenario: Tenant creates draft sending plan
- **WHEN** an admin or operator submits a valid sending plan with at least one sequence step and `lock_recipients=false`
- **THEN** the system MUST create the plan and all submitted steps
- **AND** the plan MUST be returned to the client with a durable identifier

#### Scenario: Tenant creates and locks sending plan recipients
- **WHEN** an admin or operator submits a valid sending plan with `lock_recipients=true`
- **THEN** the system MUST create the plan, create all submitted steps, lock at least one eligible recipient, and persist the recipient total
- **AND** the operation MUST fail without persisting partial plan data if recipient locking fails

#### Scenario: Tenant creates and locks with no eligible recipients
- **WHEN** an admin or operator submits a sending plan with `lock_recipients=true`
- **AND** the selected recipient source has zero eligible recipients
- **THEN** the system MUST reject the creation request with a clear validation error
- **AND** the system MUST NOT persist the plan, steps, or recipients from that request

#### Scenario: Step creation fails during plan creation
- **WHEN** any submitted step is invalid or cannot be persisted
- **THEN** the system MUST reject the creation request with a validation error
- **AND** the system MUST NOT leave a newly created plan without its required steps

### Requirement: Sending plan creation validates business inputs before persistence
The system SHALL validate all required sending plan creation inputs before writing a new plan.

#### Scenario: Required plan field is missing
- **WHEN** the request omits a required field such as name, recipient source, recipient configuration, sender identity, or domain
- **THEN** the system MUST reject the request with a clear validation error before inserting the plan

#### Scenario: First step is invalid
- **WHEN** the submitted first step is not `step_number=1`, `delay_days=0`, and `condition_type=always`
- **THEN** the system MUST reject the request with a clear validation error

#### Scenario: Step templates do not belong to tenant
- **WHEN** any submitted step references an email template outside the current tenant or a missing template
- **THEN** the system MUST reject the request with a clear validation error

#### Scenario: Sending domain is invalid
- **WHEN** the submitted domain is missing or belongs to another tenant
- **THEN** the system MUST reject the request with a clear validation error

#### Scenario: Draft is created with unverified domain
- **WHEN** the submitted domain belongs to the current tenant but is not verified
- **AND** `lock_recipients=false`
- **THEN** the system MUST allow creating a draft sending plan

#### Scenario: Lock is requested with unverified domain
- **WHEN** the submitted domain belongs to the current tenant but is not verified
- **AND** `lock_recipients=true`
- **THEN** the system MUST reject the request with a clear validation error
- **AND** the system MUST NOT persist partial plan data from that request

#### Scenario: Recipient group is invalid
- **WHEN** the submitted recipient source is `group` and the group id is missing, invalid, or outside the current tenant
- **THEN** the system MUST reject the request with a clear validation error

### Requirement: Tenant creation page shows actionable errors
The tenant sending plan creation page SHALL submit a complete creation payload and show actionable server validation errors.

#### Scenario: Server returns validation message
- **WHEN** sending plan creation fails with a server validation message
- **THEN** the page MUST show that message to the user
- **AND** the page MUST keep the current form state for correction

#### Scenario: Creation succeeds
- **WHEN** sending plan creation succeeds
- **THEN** the page MUST invalidate sending plan and dashboard data
- **AND** the page MUST navigate to the created plan detail page
