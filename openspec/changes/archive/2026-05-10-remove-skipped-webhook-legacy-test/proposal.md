## Why

Backend full-suite verification still reports one skipped test from a legacy EngageLab webhook path. The skipped test depends on removed `shared_companies` schema and unimplemented Phase 2 CRM behavior, so it no longer represents a current V3 requirement.

## What Changes

- Remove the remaining skipped legacy webhook test from the backend test suite.
- Remove any helper code that exists only to support that skipped legacy test.
- Do not change webhook runtime behavior, database schema, or Phase 2 CRM scope.
- Keep future webhook coverage tied to the current V3 schema through a separate OpenSpec change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-suite-governance`: Backend full-suite verification must not retain obsolete skipped legacy CRM/webhook tests that depend on removed schema.

## Impact

- Affected tests: `backend/tests/test_webhook_api.py`.
- Affected OpenSpec area: `test-suite-governance`.
- No API, runtime, migration, dependency, or deployment behavior changes.
