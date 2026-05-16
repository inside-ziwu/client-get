## 1. Identify Legacy Skipped Tests

- [x] 1.1 List tests skipped because they depend on removed `shared_companies` schema or unimplemented Phase 2 CRM behavior.
- [x] 1.2 Confirm those skipped tests are not current V3 requirements.

## 2. Remove Tests

- [x] 2.1 Delete `backend/tests/test_sending_api.py`.
- [x] 2.2 Remove the skipped legacy test from `backend/tests/test_non_functional.py` while preserving its active CORS/request-id test.
- [x] 2.3 Delete `backend/tests/test_tenant_core_endpoints.py`.
- [x] 2.4 Delete `backend/tests/test_sending_worker.py`.
- [x] 2.5 Delete `backend/tests/test_scoring_internal_api.py`.
- [x] 2.6 Delete `backend/tests/test_rbac_and_route_ordering.py`.

## 3. Verification

- [x] 3.1 Re-run the direct `login_admin()` backend test subset that remains after deletion.
- [x] 3.2 Record pass/fail/skipped counts and any remaining skip reasons.

  2026-05-10 验证记录：
  - `cd backend && .venv/bin/python -m pytest tests/test_tenant_settings_api.py tests/test_non_functional.py tests/test_admin_config_api.py tests/test_intelligence_api.py tests/test_auth_integration.py -q -rs`
  - 结果：10 passed，0 skipped。
