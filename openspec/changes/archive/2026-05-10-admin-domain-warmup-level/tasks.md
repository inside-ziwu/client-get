## 1. Backend Contract

- [x] 1.1 Add backend test coverage for creating tenant domain with `warmup_rule_id + warmup_level`, asserting derived `daily_limit` is written to both `domain_warmup_status` and `domain_warmup_history`
- [x] 1.2 Add backend validation test for stale/non-active rule or missing level
- [x] 1.3 Add backend test coverage showing changed rule-level daily limit uses the latest server-side value at submit time
- [x] 1.4 Update admin tenant domain creation service to require `warmup_rule_id + warmup_level` and derive `daily_limit` from the latest active `warmup_rule_levels`
- [x] 1.5 Write the derived `daily_limit` consistently to `domain_warmup_status` and `domain_warmup_history`
- [x] 1.6 Return a clear validation error when no active matching warmup level exists

## 2. Frontend Admin UI

- [x] 2.1 Update shared admin tenant domain API types to send `warmup_rule_id + warmup_level` and never send `daily_limit`
- [x] 2.2 Update `TenantDomain` response type to include `warmup_level` and `daily_limit`
- [x] 2.3 Load active warmup rule levels in admin tenant detail domain management
- [x] 2.4 Add “起始预热档位” Select to the “添加域名” modal with labels showing level and daily limit
- [x] 2.5 Show “预热档位 / 每日上限” columns in the domain management table after adding a domain
- [x] 2.6 Disable or validate submit when active warmup rule levels are unavailable
- [x] 2.7 Show backend validation errors as an operator-readable refresh/reselect prompt

## 3. Verification

- [x] 3.1 Run focused backend tests for tenant domain creation
- [x] 3.2 Run focused frontend typecheck/build validation for admin tenant page
- [x] 3.3 Verify `openspec validate admin-domain-warmup-level --strict`

## 4. Production Constraint Fix

- [x] 4.1 Add regression coverage for active warmup rule levels above 6 when creating a tenant domain
- [x] 4.2 Align `domain_warmup_status.warmup_level` database constraint with active warmup rule levels instead of hard-coding 1-6
- [x] 4.3 Re-run focused backend tests, admin build, and OpenSpec strict validation
