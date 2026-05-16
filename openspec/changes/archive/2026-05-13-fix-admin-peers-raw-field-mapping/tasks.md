## 1. Root Cause

- [x] 1.1 Confirm legacy `/collection/raw/lixiaoyun` does not expose the fields the page renders.
- [x] 1.2 Confirm V3 `/raw/lixiaoyun/companies` exposes top-level company fields needed by the page.

## 2. Frontend Fix

- [x] 2.1 Add a typed shared API method for V3 raw Lixiaoyun companies.
- [x] 2.2 Update `/collection/peers` to call the V3 raw API and render top-level fields.
- [x] 2.3 Update details Sheet to show available V3 raw fields without relying on `raw_payload`.
- [x] 2.4 Update contract tests to reject the legacy API path and assert V3 field mapping.

## 3. Verification

- [x] 3.1 Run affected contract test.
- [x] 3.2 Run Admin Next type-check.
- [x] 3.3 Run production build or record why it is deferred.
- [x] 3.4 Build and push the updated Admin image to ACR.

## 4. Backend Fallback Correction

- [x] 4.1 Confirm live symptom maps to V3 Lixiaoyun raw API missing payload fallbacks.
- [x] 4.2 Add backend regression coverage for payload fallback `english_name` and `contacts_count`.
- [x] 4.3 Update V3 Lixiaoyun raw list query to normalize payload fallback fields.
- [x] 4.4 Run backend regression test plus affected Admin Next checks.
