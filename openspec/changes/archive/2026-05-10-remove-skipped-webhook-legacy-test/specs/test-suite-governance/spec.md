## MODIFIED Requirements

### Requirement: Current test suite SHALL not retain obsolete skipped legacy CRM tests

The backend test suite SHALL not keep tests that are explicitly skipped because they depend on removed `shared_companies` schema or unimplemented Phase 2 CRM behavior, when those tests no longer represent current V3 requirements.

#### Scenario: Backend full test suite is executed

- **WHEN** the backend full test suite is executed with skip reporting
- **THEN** the result SHALL not include skipped tests from removed Phase 2 / `shared_companies` legacy CRM or webhook coverage
- **AND** remaining failures, if any, SHALL represent active current-code issues rather than known obsolete test dependencies

#### Scenario: Future webhook CRM behavior is reintroduced

- **WHEN** EngageLab webhook reply handling or equivalent CRM behavior is reintroduced under the current V3 schema
- **THEN** new tests SHALL be written against current tables, current fixtures, and current OpenSpec authority
- **AND** removed legacy skipped webhook tests SHALL NOT be treated as current requirements without a new OpenSpec change
