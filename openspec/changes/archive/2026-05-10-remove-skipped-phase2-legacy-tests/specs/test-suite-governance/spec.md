## ADDED Requirements

### Requirement: Current test suite SHALL not retain obsolete skipped legacy CRM tests

The backend test suite SHALL not keep tests that are explicitly skipped because they depend on removed `shared_companies` schema or unimplemented Phase 2 CRM behavior, when those tests no longer represent current V3 requirements.

#### Scenario: Admin-login test subset is executed

- **WHEN** the admin-login related backend test subset is executed after removing obsolete legacy skipped tests
- **THEN** the result SHALL not include skipped tests from the removed Phase 2 / `shared_companies` legacy files
- **AND** remaining failures, if any, SHALL represent active current-code issues rather than known obsolete test dependencies

#### Scenario: Future Phase 2 CRM behavior is reintroduced

- **WHEN** Phase 2 CRM or equivalent behavior is reintroduced under the current V3 schema
- **THEN** new tests SHALL be written against the current schema and OpenSpec authority
- **AND** the removed legacy skipped tests SHALL NOT be treated as current requirements without a new OpenSpec change
