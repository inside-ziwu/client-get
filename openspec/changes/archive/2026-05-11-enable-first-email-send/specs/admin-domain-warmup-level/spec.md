## ADDED Requirements

### Requirement: First email smoke test depends on an existing verified sending domain
The system SHALL require the first real email smoke test to use an existing tenant sending domain whose warmup record is verified and has available daily quota.

#### Scenario: Verified domain is selected
- **WHEN** preparing the first email smoke test
- **THEN** the selected `domain_warmup_status` record MUST belong to the tenant, have `verification_status=verified`, and have a positive `daily_limit`
- **AND** the sender email `aoqi@xapcb.com` MUST belong to the selected sending domain

#### Scenario: Domain is not verified
- **WHEN** no verified tenant sending domain is available
- **THEN** implementation MUST stop before real sending and report domain verification as the blocker instead of bypassing the domain gate

#### Scenario: Daily quota is unavailable
- **WHEN** the selected verified domain has no remaining daily quota
- **THEN** implementation MUST stop before real sending and report domain quota as the blocker instead of attempting the smoke test
