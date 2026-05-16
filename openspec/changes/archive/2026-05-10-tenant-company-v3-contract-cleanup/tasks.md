## 1. Backend Contract Cleanup

- [x] 1.1 Update `TenantQueryService.prospects()` to return only V3 tenant company fields.
- [x] 1.2 Remove `grade` query parameter from tenant `/companies` API and keep numeric score filters.
- [x] 1.3 Remove tenant company `deleted_at`, `grade`, `total_score`, and `is_precise_customer` references from tenant company query paths.
- [x] 1.4 Remove `/emails/stats/by-grade` route and `TenantMessagingService.email_stats_by_grade()`.
- [x] 1.5 Update `TenantMessagingService._recipients_from_filter()` to remove grade filtering and use `country_iso3`.
- [x] 1.6 Update `ScoringService._load_company_context()` to read current V3 clean company fields and remove `precise_customer` scoring branch.

## 2. Frontend And Shared Contract Cleanup

- [x] 2.1 Update tenant Companies page to remove grade, total score, precise-customer, and score-adjustment UI.
- [x] 2.2 Update tenant CuratedCustomers page to remove grade, total score, and precise-customer UI.
- [x] 2.3 Update tenant EmailMonitor page to remove by-grade request and distribution chart.
- [x] 2.4 Update shared tenant companies/prospects/emails API types to remove legacy tenant company fields and by-grade request.
- [x] 2.5 Update shared tenant company types to use `score`, `model_score`, `note`, and `tags`.

## 3. Verification

- [x] 3.1 Add or update backend tests for V3 prospects contract and scoring context fields.
- [x] 3.2 Add or update backend tests for no-grade company filtering and removed by-grade stats route.
- [x] 3.3 Run backend target tests: `cd backend && .venv/bin/python -m pytest tests/test_tenant_business_status_semantics.py tests/test_v3_data_foundation_api_contract.py`.
- [x] 3.4 Run tenant frontend type check: `cd frontend && pnpm --filter @apps/tenant type-check`.
- [x] 3.5 Run OpenSpec validation for this change.
