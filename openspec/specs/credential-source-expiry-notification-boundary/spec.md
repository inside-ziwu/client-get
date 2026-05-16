## Requirements

### Requirement: Admin credential-source expiry MUST NOT notify tenant users

The system MUST NOT create tenant-visible notifications when a platform-admin-managed collection credential source reports `CREDENTIAL_EXPIRED`.

#### Scenario: Collection credential expires during worker execution

- **WHEN** a collection provider reports `CREDENTIAL_EXPIRED` for a platform-admin-managed credential source
- **THEN** the system MUST NOT insert a tenant-visible notification for any tenant user, including tenant admin users

#### Scenario: Collection task records credential expiry

- **WHEN** a collection task reaches final failure because a platform-admin-managed credential source reported `CREDENTIAL_EXPIRED`
- **THEN** the system MUST preserve the failed task status and credential expiry error message for platform admin-side diagnosis

#### Scenario: Tenant-visible surfaces do not expose platform credential errors

- **WHEN** a collection task fails because a platform-admin-managed credential source reported `CREDENTIAL_EXPIRED`
- **THEN** tenant-visible APIs, UI, notifications, and exported task views MUST NOT expose the raw `CREDENTIAL_EXPIRED` platform credential error message

### Requirement: Tenant-owned notification rules MUST remain unchanged

The system MUST keep tenant-visible notifications for tenant-owned issues outside the admin collection credential-source expiry boundary.

#### Scenario: Tenant-owned issue occurs

- **WHEN** a tenant-owned configuration or workflow issue triggers an existing tenant notification rule
- **THEN** the system MUST continue to create the tenant-visible notification according to that existing rule
