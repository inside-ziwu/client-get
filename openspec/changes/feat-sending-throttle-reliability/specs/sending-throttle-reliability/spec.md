## ADDED Requirements

### Requirement: Worker SHALL send one email at a time per selected domain

Sending worker MUST claim at most one due email for the selected domain per iteration and MUST set that domain's next send time from `send_strategy.interval_seconds`, defaulting to `[30, 120]`.

#### Scenario: Single domain throttle
- **GIVEN** a running plan on one domain has five due emails
- **WHEN** the worker processes the first email
- **THEN** the domain next send time is set to a random delay between 30 and 120 seconds
- **AND** the worker does not immediately send another email for that same domain before the delay expires

#### Scenario: Two domain rotation
- **GIVEN** domain A and domain B both have due emails
- **WHEN** domain A sends and enters cooldown
- **THEN** the worker may immediately process domain B if it is due

### Requirement: Worker SHALL discover running domains on each loop

Worker MUST query distinct running plan domains each loop and remove stopped domains from the in-memory clock set.

#### Scenario: New domain appears
- **GIVEN** a new running plan starts for domain C
- **WHEN** the worker enters the next loop
- **THEN** domain C becomes eligible for sending

### Requirement: Claiming due emails SHALL support domain filtering

`claim_due_emails` MUST accept optional `domain_id`; when present it MUST only claim enrollments from that domain and return `domain_id`, `send_strategy`, and `enrollment_id`.

#### Scenario: Domain filter
- **GIVEN** two running domains have due enrollments
- **WHEN** `claim_due_emails(domain_id=A)` is called
- **THEN** only domain A emails are returned

### Requirement: Temporary send failures SHALL retry with bounded backoff

Temporary failures MUST increment `send_attempt_count`, schedule retries at 15 minutes, 1 hour, and 4 hours, and mark the enrollment `failed` after the fourth failure.

#### Scenario: Retry exhaustion
- **GIVEN** an active enrollment has `send_attempt_count=3`
- **WHEN** a temporary send failure is recorded
- **THEN** the enrollment status becomes `failed`

### Requirement: Permanent send failures SHALL fail the enrollment immediately

Permanent provider failures MUST mark the enrollment `failed` immediately. Invalid email failures MUST mark the contact `invalid`; bounce failures MAY mark the contact `bounced`; configuration-like failures MUST NOT update contact status.

#### Scenario: Invalid email
- **GIVEN** provider returns HTTP 422
- **WHEN** the failure is recorded
- **THEN** enrollment status is `failed`
- **AND** contact status is `invalid`

#### Scenario: Provider auth failure
- **GIVEN** provider returns HTTP 401 or 403
- **WHEN** the worker classifies the error
- **THEN** it is treated as temporary
- **AND** contact status is not changed

### Requirement: Failed sends SHALL release reserved quota

Whenever a claimed email fails or a stale lock is recovered, reserved quota for that domain and current date MUST decrement by one without going below zero.

#### Scenario: Reserved quota recovery
- **GIVEN** reserved_count is 1
- **WHEN** the send is marked failed
- **THEN** reserved_count becomes 0

### Requirement: Worker SHALL recover stale locks at startup

Worker MUST release locks older than 30 minutes, mark corresponding queued emails `failed` with `STALE_LOCK`, and emit a structured recovery log.

#### Scenario: Stale lock
- **GIVEN** an email send lock has status `locked` and `locked_at` older than 30 minutes
- **WHEN** stale lock recovery runs
- **THEN** the lock is released
- **AND** the queued email is marked failed with `STALE_LOCK`

### Requirement: Worker SHALL emit structured logs

Worker MUST log key events as structured JSON-compatible records, including successful send, failed send, throttle sleep, idle domain, and stale lock recovery.

#### Scenario: Send failure log
- **GIVEN** provider returns a temporary failure
- **WHEN** the worker records the failure
- **THEN** the log contains `event`, `domain_id`, `status_code`, and `error_type`
