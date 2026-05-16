## 1. Context Review

- [x] 1.1 Review `CollectionService.mark_failed()` and `_notify_credential_expired()` to confirm the current tenant notification path.
- [x] 1.2 Review existing collection worker/service tests that cover failed collection tasks and notification insertion.
- [x] 1.3 Review tenant-visible collection task APIs/UI to confirm whether raw `collection_tasks.error_message` can be exposed to tenant users.

## 2. Core Implementation

- [x] 2.1 Remove or suppress the `CREDENTIAL_EXPIRED` path that writes tenant-visible rows into `notifications`.
- [x] 2.2 Preserve collection task failure status and `error_message` behavior for credential expiry failures.
- [x] 2.3 Ensure tenant-visible APIs/UI do not expose raw platform `CREDENTIAL_EXPIRED` credential errors.
- [x] 2.4 Keep unrelated tenant-owned notification rules unchanged.

## 3. Verification

- [x] 3.1 Add or update `backend/tests/test_collection_internal_api.py` to prove the final-failure `mark_failed(error_code="CREDENTIAL_EXPIRED")` path does not create tenant notifications.
- [x] 3.2 In that test, construct the old notification preconditions: valid lease, task linked through `collection_task_keywords`, active tenant user, and `user_roles(role='admin')`, so the regression would fail against the old `_notify_credential_expired()` behavior.
- [x] 3.3 Assert the collection task reaches `status='failed'` and preserves an error message containing `[CREDENTIAL_EXPIRED]` for platform admin diagnosis.
- [x] 3.4 Add or update a test/manual assertion proving tenant-visible APIs/UI do not expose the raw `CREDENTIAL_EXPIRED` platform credential error.
- [x] 3.5 Run `cd backend && uv run pytest -q tests/test_collection_internal_api.py -k "mark_failed"`.
- [x] 3.6 Run any broader backend tests needed if shared collection failure logic is touched.

## 4. Production Cleanup

- [x] 4.1 Run a read-only production query to count and sample legacy tenant credential-expiry notifications.
- [x] 4.2 After explicit user confirmation, delete only legacy tenant credential-expiry notifications matching the reviewed predicate.
- [x] 4.3 Re-run the read-only production query to confirm the cleanup result.
