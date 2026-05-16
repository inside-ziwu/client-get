## 1. OpenSpec Alignment

- [x] 1.1 Confirm this change is scoped to first real email smoke test and does not replace the broader `v3-email-delivery` change.
- [x] 1.2 Record the selected test tenant and verified sending domain without storing secrets; sender email is `aoqi@xapcb.com`, recipient is `aip.lazy@gmail.com`.
- [x] 1.3 Configure and record non-secret EngageLab send URL/path for the provided account; default candidate is `ENGAGELAB_BASE_URL=https://email.api.engagelab.cc` and `ENGAGELAB_SEND_PATH=/v1/mail/send`.
- [x] 1.4 Verify `aoqi@xapcb.com` belongs to the selected verified domain.
- [x] 1.5 Verify the selected domain has positive `daily_limit` and remaining daily quota before real sending.

Evidence: local smoke-test tenant `first-email-smoke-3a1958ab` used verified domain `xapcb.com`; sender `aoqi@xapcb.com` belongs to that domain. Daily limit was `1`, remaining quota was `1` before the worker run.

## 2. EngageLab Adapter

- [x] 2.1 Add or update tests for Basic Auth header generation using `ENGAGELAB_API_USER` and `ENGAGELAB_CREDENTIAL`.
- [x] 2.2 Add or update tests proving `EngageLabClient.send_email` emits the reference payload shape: `from`, `to`, `body.subject`, `body.content.html`, `body.content.text`, and `body.settings`.
- [x] 2.3 Add or update tests proving the adapter posts to the configured base URL and send path, not the legacy `/v1/email/send` default.
- [x] 2.4 Update `backend/app/integrations/engagelab.py` to transform the current internal payload into the reference EngageLab request shape.
- [x] 2.5 Ensure response parsing accepts provider identifiers from likely fields and returns normalized `engagelab_message_id`.
- [x] 2.6 Ensure provider failures raise diagnostic errors without exposing credentials.

## 3. Sending Path Verification

- [x] 3.1 Verify `start_plan` rejects unverified domains with a specific validation message and accepts a verified-domain plan with eligible recipients.
- [x] 3.2 Add or update sending worker tests so one claimed email attempts provider delivery and marks `emails.status='sent'` with `engagelab_message_id`.
- [x] 3.3 Add or update failure-path tests so provider rejection marks `emails.status='failed'` with `error_code` and `error_message`.
- [x] 3.4 Add or update quota reserve failure coverage so a quota failure after lock acquisition does not leave a blocking `email_send_locks` state; if current behavior is unsafe, record it as a blocker before real sending.
- [x] 3.5 Run the focused backend tests covering EngageLab adapter, sending plan start, quota failure, and sending worker.

## 4. First Real Email Smoke Test

- [x] 4.1 Configure EngageLab credentials through environment variables or deployment Secret values only.
- [x] 4.2 Create or select a single-recipient sending plan using a verified tenant domain and valid first-step template.
- [x] 4.3 Start the plan through the tenant API/UI and confirm active enrollment exists.
- [x] 4.4 Run `python scripts/run_sending_worker.py --once --limit 1` against the smoke-test environment.
- [x] 4.5 Verify the smoke-test plan produced exactly one `emails` row for the selected recipient, with `status='sent'` and non-empty `engagelab_message_id`.
- [x] 4.6 Confirm `aip.lazy@gmail.com` received the message; if provider accepted but inbox did not receive it, mark the smoke test as not passed and record the provider message id for diagnosis.
- [x] 4.7 If provider accepted but inbox did not receive the message, check Gmail spam/promotions folders, EngageLab provider events, provider response payload, and SPF/DKIM/DMARC status before deciding the next blocker.

Evidence: worker command was run with process-only EngageLab environment variables and `--once --limit 1`. EngageLab status API returned `status_desc=delivery` and `response_message=Successfully Delivered` for recipient `aip.lazy@gmail.com`. User confirmed the Gmail inbox received the message, so the non-receipt diagnostic branch was not needed.

## 5. Documentation And Handoff

- [x] 5.1 Update non-secret EngageLab configuration docs, including `.env.example` and deployment docs, so they no longer point smoke-test setup at the legacy `/v1/email/send` path.
- [x] 5.2 Document the final non-secret environment variable names and URL/path used for EngageLab.
- [x] 5.3 Document that production Sealos Secret changes are out of scope for automatic apply and require explicit user confirmation.
- [x] 5.4 Record the smoke-test evidence: plan id, email id, provider message id presence, worker command, sender email, recipient email, and inbox result.
- [x] 5.5 Update this task list with completed and intentionally unverified items before reporting completion.

Smoke-test evidence:
- tenant slug: `first-email-smoke-3a1958ab`
- plan id: `019e13d4-9e0b-7cdd-a719-4f9350a9be1c`
- email id: `019e13d5-97ba-7ac6-8f85-6b3acb456c31`
- provider email id: `1778449227443_131594_24226_727.sc-10_43_4_215-inbound0$aip.lazy@gmail.com`
- worker command: `python scripts/run_sending_worker.py --once --limit 1 --service-instance first-email-smoke`
- sender email: `aoqi@xapcb.com`
- recipient email: `aip.lazy@gmail.com`
- local email result: `status='sent'`, non-empty `engagelab_message_id`
- EngageLab status result: `delivery`, `Successfully Delivered`
- inbox result: user confirmed Gmail received the message
