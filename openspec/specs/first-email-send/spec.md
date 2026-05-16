# first-email-send Specification

## Purpose
Define the minimum production-path smoke test for sending the first real email through EngageLab without expanding scope to the full email delivery system.

## Requirements
### Requirement: EngageLab adapter sends provider-compatible payload
The system SHALL transform internal email send payloads into the EngageLab-compatible request format inherited from the reference implementation before calling the provider.

#### Scenario: Worker sends one email through EngageLab
- **WHEN** the sending worker passes an internal payload containing sender, recipient, subject, HTML body, text body, and idempotency key to the EngageLab adapter
- **THEN** the adapter MUST call EngageLab with HTTP Basic authentication
- **AND** the request body MUST include `from`, `to`, `body.subject`, `body.content.html`, `body.content.text`, and `body.settings`
- **AND** `body.settings.open_tracking` MUST be true

#### Scenario: EngageLab returns a message identifier
- **WHEN** EngageLab accepts the send request and returns a provider message identifier
- **THEN** the adapter MUST return a normalized `engagelab_message_id` to the sending worker

#### Scenario: EngageLab rejects the send request
- **WHEN** EngageLab returns an HTTP error or malformed success response
- **THEN** the adapter MUST raise a diagnostic send error that includes provider status or response context without leaking credentials

### Requirement: First email smoke test uses the production sending path
The system SHALL validate the first real email through the same plan-start and sending-worker path used by production delivery.

#### Scenario: Plan is started for first email test
- **WHEN** a tenant operator starts a single-recipient sending plan that uses a verified domain and a valid first step
- **THEN** the system MUST create active sequence enrollment records for eligible recipients

#### Scenario: Sending worker processes one due email
- **WHEN** the sending worker runs once with a limit of one and a due active enrollment exists
- **THEN** the worker MUST create an `emails` row, attempt provider delivery for that email, and update the email to `sent` when EngageLab accepts it
- **AND** the email MUST have a non-empty `engagelab_message_id`

#### Scenario: Provider send fails during smoke test
- **WHEN** EngageLab rejects the first email smoke test request
- **THEN** the worker MUST update the email to `failed`
- **AND** the email MUST include `error_code` and `error_message` for diagnosis

### Requirement: First email smoke test protects credentials and blast radius
The system SHALL keep the first real send limited to one explicit test email and SHALL NOT persist EngageLab secrets in source-controlled files.

#### Scenario: Credentials are configured
- **WHEN** EngageLab API credentials are needed for first email delivery
- **THEN** they MUST be supplied through environment variables or deployment Secret values
- **AND** the implementation MUST NOT write real credentials to code, OpenSpec artifacts, test fixtures, or committed documentation

#### Scenario: Smoke test is executed
- **WHEN** the first real email smoke test is executed
- **THEN** it MUST send from `aoqi@xapcb.com` to `aip.lazy@gmail.com`
- **AND** it MUST use a sending worker limit of one or an equivalent guard that prevents batch sending

#### Scenario: Smoke test is accepted by provider but not received
- **WHEN** EngageLab accepts the smoke-test email but `aip.lazy@gmail.com` does not receive it
- **THEN** the smoke test MUST be recorded as not passed
- **AND** the provider message identifier MUST be retained as diagnostic evidence
