# Acceptance Test Plan

## 1. P0 acceptance

### Auth

- Platform admin can login and access Admin API.
- Tenant admin/operator/viewer can login with slug/email/password.
- Wrong slug with valid tenant token returns 403.
- Expired token returns 401.
- 5 failed logins lock account.

### RLS

- Tenant A cannot read Tenant B companies.
- Tenant A cannot update Tenant B groups/templates/plans.
- Direct repository calls without `SET LOCAL` fail or return no rows.
- Admin API can read across tenants.

### Admin APIs

- Create tenant creates tenant, admin user, role, copied scoring template, copied email templates, contact rules.
- Manual recharge updates tenant balance and writes balance transaction.
- Data source credentials are stored encrypted and returned masked.
- Warmup rule PUT replaces levels transactionally.
- AI scene default cannot reference inactive model.

### Tenant APIs

- Onboarding requires password change and at least one keyword.
- Operator cannot access billing/team/scoring settings.
- Viewer cannot create groups/templates/plans.
- Company list returns only current tenant data.

## 2. P1 acceptance

### Collection

- Active keywords with same keyword/countries generate one task linked to multiple keyword IDs.
- Claim returns lease_id.
- Heartbeat extends lease.
- Submit with wrong/expired lease returns 409.
- Batch upsert links companies to all tenant keywords, excluding blacklisted tenants.

### Scoring

- Rule-only scoring produces grade and updates tenant_company.
- LLM dimension with insufficient balance marks pending and does not call provider.
- Recharge triggers pending scoring.
- Precise customer gets S and is_precise_customer=true.

### AI billing

- Successful call settles exact/delta/release correctly.
- Provider failure releases full hold and no usage log.
- Local settlement retry does not call provider again.
- Operator can use AI generation if capability true; viewer cannot.

### Sending

- Start plan without verified domain fails.
- Start plan without recipients fails.
- Recipient lock excludes blacklisted/unsubscribed/bounced/incomplete/no_email.
- Two workers cannot send same enrollment/step twice.
- Domain daily quota cannot be exceeded under concurrent reserve.

### Webhook

- Duplicate provider_event_id is idempotent.
- Bounce updates email/enrollment/contact.
- Reply updates email/enrollment/contact and stores reply body when provided.
- Webhook failure rolls back all state changes.

### Intelligence

- Article summary cost is charged only to successfully authorized tenants.
- Insufficient-balance tenants receive title/link without summary.
- Tenant cannot read unpublished article.

## 3. Frontend smoke tests

- Admin login -> tenants -> create tenant -> recharge.
- Tenant login -> onboarding -> companies empty state.
- Tenant create group -> create template -> create plan draft.
- Tenant email monitor loads stats empty state.

## 4. Non-functional tests

- CORS rejects unknown origin.
- API returns request_id in errors.
- HTML sanitizer removes script/event handlers.
- Partition cursor pagination returns stable order.
- Audit log written for sensitive writes.
