## ADDED Requirements

### Requirement: Admin keyword collection SHALL be platform-level

The admin keyword page SHALL manage platform-level keyword collection, with tenants represented only as subscribers.

#### Scenario: Tenant subscribes to an existing keyword

- **GIVEN** a `keyword_master` already exists for a normalized keyword
- **WHEN** a tenant adds the same keyword
- **THEN** the system SHALL create or retain only the tenant subscription relation
- **AND** the system SHALL NOT create, restart, stop, or otherwise mutate the keyword's active collection run

#### Scenario: Admin views keyword status

- **GIVEN** multiple tenants subscribe to the same keyword
- **WHEN** admin views the keyword page
- **THEN** the row status SHALL come from the platform-level keyword collection run
- **AND** tenant subscription status SHALL NOT be treated as the collection status

### Requirement: Collection runs SHALL represent cross-day collection plans

The system SHALL distinguish a cross-day `collection_run` from single-execution `collection_task` records.

#### Scenario: Admin starts collection for a keyword

- **GIVEN** a keyword is not actively collecting
- **WHEN** admin clicks "采集"
- **THEN** the system SHALL create or reuse a platform-level `collection_run`
- **AND** the system SHALL create the first `collection_task` under that run

#### Scenario: Worker executes a task

- **GIVEN** a pending `collection_task`
- **WHEN** the collection worker claims it
- **THEN** the task SHALL represent only that single execution batch
- **AND** cursor/progress updates SHALL be persisted back to its parent `collection_run`

### Requirement: Lixiaoyun daily limit SHALL continue the same run on the next day

For Lixiaoyun stage 1, each keyword SHALL collect at most 1000 records per Beijing calendar day, then continue the same run after 08:00 Beijing time on the next day.

#### Scenario: Keyword reaches the daily limit

- **GIVEN** a Lixiaoyun collection run reaches 1000 records for the current Beijing calendar day
- **WHEN** the current batch finishes
- **THEN** the current `collection_task` SHALL complete
- **AND** the `collection_run` status SHALL become `daily_limit_reached`
- **AND** admin SHALL see "今日已达上限"
- **AND** the system SHALL create a pending continuation task scheduled for the next day at 08:00 Asia/Shanghai

#### Scenario: Scheduler resumes after 08:00

- **GIVEN** a continuation task is pending for a run that previously reached the daily limit
- **WHEN** the time is after its scheduled Beijing 08:00 time
- **THEN** the scheduler SHALL execute that pending task
- **AND** the worker SHALL continue from the parent run's cursor instead of starting from the first page
- **AND** the resumed execution SHALL still collect no more than 1000 records for that Beijing calendar day

#### Scenario: Lixiaoyun has no more data

- **GIVEN** a collection task receives a no-more-data result from Lixiaoyun
- **WHEN** the task completes
- **THEN** the parent `collection_run` SHALL become `completed`
- **AND** admin SHALL see "已采完"

### Requirement: Admin stop SHALL cancel the current run and future continuation tasks

Admin stop SHALL stop the whole collection run rather than only the currently running task.

#### Scenario: Admin stops a running collection

- **GIVEN** a keyword has a running collection run
- **WHEN** admin clicks "停止"
- **THEN** the system SHALL mark the run as `stopped`
- **AND** the system SHALL cancel the current running task if present
- **AND** the system SHALL cancel all future pending or scheduled continuation tasks for that run
- **AND** the stopped run SHALL NOT automatically continue on the next day
- **AND** admin SHALL see "未开始"

### Requirement: Admin status labels SHALL match run status

The admin keyword page SHALL map run status to the agreed Chinese labels.

#### Scenario: Status label mapping

- **GIVEN** a keyword run has status `not_started` or `stopped`
- **THEN** admin SHALL see "未开始"
- **GIVEN** a keyword run has status `running`
- **THEN** admin SHALL see "采集中"
- **GIVEN** a keyword run has status `daily_limit_reached`
- **THEN** admin SHALL see "今日已达上限"
- **GIVEN** a keyword run has status `completed`
- **THEN** admin SHALL see "已采完"

### Requirement: Keyword normalization SHALL allow Chinese keywords

Keyword normalization SHALL support both English and Chinese keywords without rejecting Chinese input.

#### Scenario: Chinese keyword is added

- **GIVEN** a tenant or admin enters the keyword "线路板"
- **WHEN** the system normalizes and stores the keyword
- **THEN** the keyword SHALL be accepted
- **AND** a corresponding `keyword_master` record SHALL be available for subscription and collection

### Requirement: Lixiaoyun request size SHALL default to 10 and cap at 100

Lixiaoyun collection SHALL keep a default request page size of 10 and SHALL NOT request more than 100 items in one request.

#### Scenario: Default request size

- **GIVEN** no explicit page size override is configured
- **WHEN** the collection worker requests Lixiaoyun data
- **THEN** it SHALL request 10 items for the batch

#### Scenario: Request size cap

- **GIVEN** a configured page size is greater than 100
- **WHEN** the collection worker prepares a Lixiaoyun request
- **THEN** it SHALL cap the request page size at 100

### Requirement: Tendata stage 2 SHALL not block Lixiaoyun stage 1

Until Tendata cookie-session collection is restored, Tendata stage 2 SHALL not block the Lixiaoyun stage 1 run/task lifecycle.

#### Scenario: Tendata credentials are expired

- **GIVEN** Lixiaoyun stage 1 has completed a batch successfully
- **AND** Tendata cookie credentials are expired
- **WHEN** the system evaluates the stage 1 run/task status
- **THEN** the system SHALL NOT mark the Lixiaoyun run as failed solely because Tendata stage 2 cannot execute
