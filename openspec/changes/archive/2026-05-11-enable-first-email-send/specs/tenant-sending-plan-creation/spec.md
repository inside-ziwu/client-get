## ADDED Requirements

### Requirement: Sending plan start exposes actionable first-send blockers
The system SHALL preserve the existing complete sending plan creation contract while ensuring the transition from created plan to real sending has clear blockers for first-email smoke testing.

#### Scenario: Start is blocked by unverified domain
- **WHEN** an operator starts a sending plan whose domain exists but is not verified
- **THEN** the system MUST reject the start request with a validation message that identifies the unverified sending domain as the blocker

#### Scenario: Start is blocked by missing recipients
- **WHEN** an operator starts a sending plan that has no eligible locked or lockable recipients
- **THEN** the system MUST reject the start request with a validation message that identifies the recipient problem as the blocker

#### Scenario: Start is ready for worker pickup
- **WHEN** an operator starts a sending plan with a verified domain, valid first step, and at least one eligible recipient
- **THEN** the system MUST make the plan available for sending worker pickup without requiring additional manual database edits
