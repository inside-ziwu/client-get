## 1. Reproduce And Locate

- [x] 1.1 Read the current change artifacts and confirm the implementation scope stays within manual tenant company creation.
- [x] 1.2 Preserve the evidence that ISO2 country values (`US`, `DE`, `CN`) currently violate `clean_companies_country_iso3_check`.
- [x] 1.3 Preserve the evidence that creating a company with contact email currently fails in `_ensure_contact_from_payload` because a bigint tenant company id is passed as a string.
- [x] 1.4 Inspect frontend form payload mapping, country options helper, backend route, service write path, contact creation helper, and company detail return path.

## 2. Backend Save Path

- [x] 2.1 Add a small country normalization helper for manual company creation that accepts empty values, valid ISO3, and ISO2 values via `pycountry`, and rejects unsupported values without first-three-character guessing.
- [x] 2.2 Use the normalized ISO3 value in the clean company upsert so `US` / `DE` / `CN` style inputs no longer reach the database constraint unchanged.
- [x] 2.3 Fix the contact creation path so `_ensure_contact_from_payload` receives or casts the tenant company bigint id correctly.
- [x] 2.4 Preserve idempotent behavior when the same tenant creates an already-linked visible company, without exposing uniqueness constraint errors.
- [x] 2.5 Preserve current V3 state writes: `business_status = new`, `visibility_status = visible`, and valid `data_status`.
- [x] 2.6 Optionally add or reuse a lightweight create request schema only if it directly improves validation for the evidence-backed failure cases.

## 3. Frontend Payload And Feedback

- [x] 3.1 Replace the new-company country free-text input with the existing shared Chinese country options, submitting ISO3 values.
- [x] 3.2 Update the tenant Companies new-company form submit path to send only supported, trimmed, non-empty fields.
- [x] 3.3 Update create failure handling to display the backend validation or business error message when available.
- [x] 3.4 Confirm successful save closes the modal, resets the form, and refreshes tenant company list data.
- [x] 3.5 Optionally add a typed tenant company create request in the shared tenant companies API client if it stays scoped to the create payload.

## 4. Verification

- [x] 4.1 Add or update backend tests for ISO2-to-ISO3 country normalization using `US` / `DE` / `JP` / `CN`, empty-country `UNK` fallback, unsupported country rejection, ISO3 creation success, contact-email creation success, and duplicate create/link behavior.
- [x] 4.2 Add or update frontend tests for create payload country mapping and error-message display where the project test setup supports it.
- [x] 4.3 Run targeted backend tests for tenant company status/manual creation behavior.
- [x] 4.4 Run targeted frontend typecheck or tests for the tenant company page/shared API changes.
- [x] 4.5 Perform a browser or API-level end-to-end check as tenant admin/operator: create a company with a selected country and contact email, confirm success, modal close/list refresh or API response, and visible company record.
- [x] 4.6 Record any unverified end-to-end path or environment blocker in this task list before completion. No blockers remain; browser UI smoke was covered by source-level frontend assertions plus API-level E2E for the create request/response path.
