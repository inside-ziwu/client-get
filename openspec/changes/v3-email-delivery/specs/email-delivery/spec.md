## ADDED Requirements

### Requirement: Admin configures tenant sending domain during tenant creation
The system SHALL let platform admin provide a tenant sending domain and starting warmup level when creating a tenant, and SHALL persist the corresponding `domain_warmup_status` record in the same creation flow.

#### Scenario: Admin creates tenant with sending domain
- **WHEN** admin submits tenant creation with a sending domain and warmup level
- **THEN** the tenant MUST be created and a domain warmup record MUST be persisted for that tenant

### Requirement: Admin manages EngageLab domain verification
The system SHALL let platform admin add a tenant sending domain through EngageLab, store DNS records, trigger verification, poll verification status, and present copyable SPF, DKIM, and DMARC records.

#### Scenario: Admin adds and verifies domain
- **WHEN** admin adds a tenant sending domain and triggers verification
- **THEN** the system MUST call EngageLab domain APIs, persist DNS records, and update verification status through `pending`, `verifying`, `verified`, or `failed`

### Requirement: Sending worker performs real delivery with warmup limits
The system SHALL deploy and run the sending worker so it sends email through EngageLab, enforces per-domain warmup daily limits, writes `emails` records, updates delivery status, records failures, and prevents duplicate sends.

#### Scenario: Sending worker sends within daily limit
- **WHEN** a pending email is eligible and the domain daily limit is not exhausted
- **THEN** the worker MUST send through EngageLab, write or update the email record, and record delivery status

#### Scenario: Sending fails
- **WHEN** EngageLab or rendering fails for a send attempt
- **THEN** the system MUST persist `error_code` and `error_message` for diagnosis

#### Scenario: Duplicate send is attempted
- **WHEN** the same email send is picked up more than once
- **THEN** the system MUST use an idempotency mechanism to avoid duplicate delivery

### Requirement: Email plan creation uses classified recipients
The system SHALL remove tenant target-strategy selection and SHALL use contact classification to select all sendable contacts for email plans.

#### Scenario: Tenant creates send plan
- **WHEN** tenant creates an email plan for selected companies
- **THEN** the system MUST select contacts with `is_sendable=true` and support multi-step sequences that use contacts not already sent in prior steps

### Requirement: Delivery tracking records opens and delivery events
The system SHALL enable EngageLab open tracking and delivery event ingestion, persist event history in `email_events`, and update emails with first open, open count, soft bounce, invalid email, spam report, and unsubscribe indicators.

#### Scenario: EngageLab sends open event
- **WHEN** the system receives or fetches an open event for an email
- **THEN** it MUST append an email event and update first-open/open-count fields on the email

#### Scenario: EngageLab sends bounce or complaint event
- **WHEN** the system receives or fetches a soft bounce, invalid email, spam report, or unsubscribe event
- **THEN** it MUST append an email event and update the corresponding delivery indicator on the email

### Requirement: Tenant email monitor shows six delivery metrics
The system SHALL expose tenant email monitor metrics for sent volume, delivery rate, unique open rate, soft bounce, spam report, and unsubscribe, with drill-down event detail.

#### Scenario: Tenant views email monitor
- **WHEN** tenant opens the email monitor page
- **THEN** the page MUST show the six delivery metrics and allow inspecting delivery timeline details

### Requirement: Sealos E2E validates real email delivery
The system SHALL include Sealos end-to-end validation from tenant/domain setup through real collection, send plan creation, real email delivery, status writeback, failure handling, and worker retry behavior.

#### Scenario: Full production-path email test runs
- **WHEN** the Sealos E2E scenario is executed with a real tenant domain and test mailbox
- **THEN** the test mailbox MUST receive the email and the system MUST show correct delivery status and monitoring data
