## ADDED Requirements

### Requirement: Admin selects warmup level when adding tenant domain
The system SHALL require platform admin to select a starting warmup level when adding a tenant sending domain from the admin tenant detail domain management entry.

#### Scenario: Active warmup rule provides level options
- **WHEN** platform admin opens the add-domain dialog and an active warmup rule exists
- **THEN** the dialog MUST show warmup level options from that active rule's levels, including each level's daily limit

#### Scenario: Admin submits domain with selected level
- **WHEN** platform admin submits a domain with a selected warmup level
- **THEN** the request MUST include `domain`, `warmup_rule_id`, and `warmup_level`, and MUST NOT include `daily_limit`

#### Scenario: Domain list shows persisted quota
- **WHEN** a domain has been added successfully
- **THEN** the domain management table MUST show the domain, persisted warmup level, and persisted daily limit

### Requirement: Backend derives domain daily limit from active warmup rule
The system SHALL derive `domain_warmup_status.daily_limit` from the latest server-side active `warmup_rule_levels.daily_limit` using the submitted `warmup_rule_id` and `warmup_level` when creating a tenant domain.

#### Scenario: Rule and level are valid
- **WHEN** the submitted `warmup_rule_id` is active and contains the submitted `warmup_level`
- **THEN** the system MUST create the `domain_warmup_status` row with the matching `warmup_rule_id`, `warmup_level`, and the latest server-derived `daily_limit`

#### Scenario: Rule level daily limit changed after dialog opened
- **WHEN** the submitted `warmup_rule_id` is still active and the submitted `warmup_level` still exists but its daily limit changed after the dialog opened
- **THEN** the system MUST create the domain using the latest server-side daily limit for that level

#### Scenario: Rule is stale or level is missing
- **WHEN** the submitted `warmup_rule_id` is not active or does not contain the submitted `warmup_level`
- **THEN** the system MUST reject the request with a validation error that tells admin to refresh and reselect the warmup level

### Requirement: Domain warmup change is independent of recipient classification
The system SHALL scope this change to admin domain warmup initialization and SHALL NOT require contact classification or email recipient selection to be complete.

#### Scenario: Applying this change
- **WHEN** implementation tasks for this change are executed
- **THEN** they MUST be limited to admin domain creation UI/API behavior and MUST NOT modify contact classification, send plan recipient selection, or sending worker delivery behavior
