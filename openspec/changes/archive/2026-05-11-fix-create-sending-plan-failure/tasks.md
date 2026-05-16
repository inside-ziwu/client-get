## 1. Backend Creation Contract

- [x] 1.1 Inspect tenant database transaction handling for API requests and confirm rollback behavior for service exceptions.
- [x] 1.2 Add typed validation helpers or request-normalization helpers for sending plan creation payloads in `TenantMessagingService`.
- [x] 1.3 Validate required plan fields, tenant-owned group recipient config, tenant-owned domain, continuous step numbers, first-step rules, and tenant-owned email templates before persistence.
- [x] 1.4 Implement an atomic service method that creates the plan, creates all submitted steps, optionally locks recipients, and returns the created plan.
- [x] 1.5 Enforce that unverified domains can save drafts but cannot be used when `lock_recipients=true`.
- [x] 1.6 Enforce that `lock_recipients=true` requires at least one eligible recipient and rolls back the whole creation request when none exist.
- [x] 1.7 Add a tenant API route for complete sending plan creation while preserving existing plan and step routes.

## 2. Tenant Frontend Creation Flow

- [x] 2.1 Add shared API types and client method for the complete sending plan creation request.
- [x] 2.2 Update `SendPlans/New.tsx` to submit one complete payload instead of orchestrating multiple create/step/lock requests.
- [x] 2.3 Add client-side checks for missing sequence templates and keep existing form state when submission fails.
- [x] 2.4 Display the server validation message when creation fails, with the existing generic error as fallback.
- [x] 2.5 Preserve successful navigation, query invalidation, and success messages for draft and lock modes.
- [x] 2.6 Preserve selected group, first template, and domain across wizard steps so the confirm step and submit payload use the same stored form values.

## 3. Verification

- [x] 3.1 Add backend tests for successful draft creation, successful create-and-lock, missing required fields, invalid first step, invalid template, invalid domain, invalid group, draft with unverified domain, lock with unverified domain, zero eligible recipients, and rollback on step/lock failure.
- [x] 3.2 Add or update frontend tests for complete payload submission and server validation error display.
- [x] 3.3 Run the backend tests that cover tenant messaging and sending plan creation.
- [x] 3.4 Run the frontend typecheck/test command that covers tenant send plan creation.
- [x] 3.5 Manually verify the tenant new sending plan page against a local or documented test fixture if automated E2E is unavailable. Not run manually; covered by backend service/route tests, frontend static flow test, and tenant type-check because no local fixture/browser session was requested for this apply pass.
- [x] 3.6 Update this task list with completed checkboxes and record any intentionally unverified item with the reason.
