# API Contract（最终版）

## 1. General

Base paths:

```text
/admin/api/v1
/t/{slug}/api/v1
/internal/api/v1
/webhooks
```

Headers:

```http
Authorization: Bearer <jwt>
Idempotency-Key: <uuid>          # for POST create/action when applicable
X-Request-Id: <uuid>             # always returned and logged
```

Response:

```json
{ "data": {} }
```

List:

```json
{ "data": [], "pagination": { "cursor": null, "has_more": false, "total": 0 } }
```

Error:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [{ "field": "email", "message": "邮箱格式无效" }],
    "request_id": "req_..."
  }
}
```

## 2. Admin API

### Auth

```http
POST /admin/api/v1/auth/login
GET  /admin/api/v1/auth/me
```

### Data Sources

```http
GET   /admin/api/v1/data-sources
POST  /admin/api/v1/data-sources
PATCH /admin/api/v1/data-sources/{source_type}
GET   /admin/api/v1/data-sources/{source_type}/credentials
POST  /admin/api/v1/data-sources/{source_type}/credentials
PATCH /admin/api/v1/data-sources/{source_type}/credentials/{id}
DELETE /admin/api/v1/data-sources/{source_type}/credentials/{id}
PATCH /admin/api/v1/data-sources/{source_type}/config
```

Credential responses must mask sensitive fields.

### Platform Scoring Templates

```http
GET  /admin/api/v1/scoring-templates?industry=PCB
POST /admin/api/v1/scoring-templates
GET  /admin/api/v1/scoring-templates/{id}
PUT  /admin/api/v1/scoring-templates/{id}
GET  /admin/api/v1/scoring-templates/{id}/versions
```

### Intelligence Sources

```http
GET    /admin/api/v1/intelligence-sources
POST   /admin/api/v1/intelligence-sources
POST   /admin/api/v1/intelligence-sources/batch-import
PATCH  /admin/api/v1/intelligence-sources/{id}
DELETE /admin/api/v1/intelligence-sources/{id}
```

### Platform Email Templates

```http
GET    /admin/api/v1/email-templates
POST   /admin/api/v1/email-templates
GET    /admin/api/v1/email-templates/{id}
PUT    /admin/api/v1/email-templates/{id}
DELETE /admin/api/v1/email-templates/{id}
GET    /admin/api/v1/email-templates/{id}/preview
```

### Warmup Rules

```http
GET /admin/api/v1/warmup-rules
PUT /admin/api/v1/warmup-rules
```

PUT body:

```json
{
  "name": "默认预热规则",
  "bounce_alert_rate": 0.05,
  "levels": [
    { "level": 1, "daily_limit": 50, "min_stay_days": 1, "min_delivery_rate": 0.95, "max_bounce_rate": 0.02, "max_complaint_rate": 0.001 }
  ]
}
```

### AI Config

```http
GET    /admin/api/v1/ai-config/models
POST   /admin/api/v1/ai-config/models
PATCH  /admin/api/v1/ai-config/models/{id}
DELETE /admin/api/v1/ai-config/models/{id}
GET    /admin/api/v1/ai-config/scene-defaults
PUT    /admin/api/v1/ai-config/scene-defaults
GET    /admin/api/v1/ai-config/pricing
PUT    /admin/api/v1/ai-config/pricing
```

### Tenants

```http
GET   /admin/api/v1/tenants
POST  /admin/api/v1/tenants
GET   /admin/api/v1/tenants/{id}
PATCH /admin/api/v1/tenants/{id}
POST  /admin/api/v1/tenants/{id}/suspend
POST  /admin/api/v1/tenants/{id}/activate
```

Create tenant body:

```json
{
  "name": "赵总PCB公司",
  "slug": "zhao-pcb",
  "industry": "PCB",
  "contact_name": "赵总",
  "contact_phone": "138...",
  "admin_email": "zhao@example.com",
  "admin_name": "赵总",
  "admin_password": "temporary-password"
}
```

### Tenant Users / Domains / Balance

```http
GET   /admin/api/v1/tenants/{tid}/users
POST  /admin/api/v1/tenants/{tid}/users
PATCH /admin/api/v1/tenants/{tid}/users/{uid}
DELETE /admin/api/v1/tenants/{tid}/users/{uid}

GET  /admin/api/v1/tenants/{tid}/domains
POST /admin/api/v1/tenants/{tid}/domains
POST /admin/api/v1/tenants/{tid}/domains/{did}/verify
GET  /admin/api/v1/tenants/{tid}/domains/{did}

GET  /admin/api/v1/tenants/{tid}/balance
POST /admin/api/v1/tenants/{tid}/balance/recharge
GET  /admin/api/v1/tenants/{tid}/balance/transactions
```

## 3. Tenant API

### Auth / Onboarding

```http
POST /t/{slug}/api/v1/auth/login
POST /t/{slug}/api/v1/auth/change-password
GET  /t/{slug}/api/v1/auth/me
POST /t/{slug}/api/v1/onboarding/complete
```

Login body:

```json
{ "email": "user@example.com", "password": "..." }
```

Slug is path param and must match JWT after login for all later requests.

### Dashboard

```http
GET /t/{slug}/api/v1/dashboard/overview
GET /t/{slug}/api/v1/dashboard/funnel
```

### Companies

```http
GET  /t/{slug}/api/v1/companies
GET  /t/{slug}/api/v1/companies/filters
GET  /t/{slug}/api/v1/companies/export
POST /t/{slug}/api/v1/companies
POST /t/{slug}/api/v1/companies/batch-import
GET  /t/{slug}/api/v1/companies/{id}
POST /t/{slug}/api/v1/companies/{id}/blacklist
GET  /t/{slug}/api/v1/companies/{id}/contacts
```

Implementation note: register static paths (`/filters`, `/export`) before `/companies/{id}`; see `04_api/FASTAPI_ROUTE_ORDERING.md`.

Company list supports: `cursor, limit, business_status, data_status, grade, country, industry_tags, product_keywords, source_type, has_email, search, sort`.

### Prospects

```http
GET   /t/{slug}/api/v1/prospects
GET   /t/{slug}/api/v1/prospects/{id}
PATCH /t/{slug}/api/v1/prospects/{id}
POST  /t/{slug}/api/v1/prospects/{id}/select
POST  /t/{slug}/api/v1/prospects/{id}/exclude
POST  /t/{slug}/api/v1/prospects/{id}/blacklist
```

### Contacts

```http
PATCH /t/{slug}/api/v1/contacts/{id}/set-default
```

### Groups

```http
GET    /t/{slug}/api/v1/groups
POST   /t/{slug}/api/v1/groups
GET    /t/{slug}/api/v1/groups/{id}
PATCH  /t/{slug}/api/v1/groups/{id}
DELETE /t/{slug}/api/v1/groups/{id}
GET    /t/{slug}/api/v1/groups/{id}/members
POST   /t/{slug}/api/v1/groups/{id}/members/batch-add
POST   /t/{slug}/api/v1/groups/{id}/members/batch-remove
```

Batch add body:

```json
{ "tenant_company_ids": ["..."], "tenant_contact_overrides": { "company_id": "contact_id" } }
```

### Settings

```http
GET /t/{slug}/api/v1/keywords
POST /t/{slug}/api/v1/keywords
PATCH /t/{slug}/api/v1/keywords/{id}
DELETE /t/{slug}/api/v1/keywords/{id}

GET /t/{slug}/api/v1/scoring-templates
PUT /t/{slug}/api/v1/scoring-templates/{id}
GET /t/{slug}/api/v1/scoring-templates/{id}/versions

GET /t/{slug}/api/v1/contact-rules
PUT /t/{slug}/api/v1/contact-rules/{id}
```

### Email Templates

```http
GET    /t/{slug}/api/v1/email-templates
POST   /t/{slug}/api/v1/email-templates
POST   /t/{slug}/api/v1/email-templates/ai-generate
GET    /t/{slug}/api/v1/email-templates/{id}
PUT    /t/{slug}/api/v1/email-templates/{id}
DELETE /t/{slug}/api/v1/email-templates/{id}
POST   /t/{slug}/api/v1/email-templates/{id}/clone
GET    /t/{slug}/api/v1/email-templates/{id}/preview
```

### Sending Plans

```http
GET    /t/{slug}/api/v1/sending-plans
POST   /t/{slug}/api/v1/sending-plans
GET    /t/{slug}/api/v1/sending-plans/{id}
PATCH  /t/{slug}/api/v1/sending-plans/{id}
DELETE /t/{slug}/api/v1/sending-plans/{id}

POST /t/{slug}/api/v1/sending-plans/{id}/schedule
POST /t/{slug}/api/v1/sending-plans/{id}/start
POST /t/{slug}/api/v1/sending-plans/{id}/pause
POST /t/{slug}/api/v1/sending-plans/{id}/resume
POST /t/{slug}/api/v1/sending-plans/{id}/cancel

GET  /t/{slug}/api/v1/sending-plans/{id}/recipients
GET  /t/{slug}/api/v1/sending-plans/{id}/recipients/preview
POST /t/{slug}/api/v1/sending-plans/{id}/recipients/lock
POST /t/{slug}/api/v1/sending-plans/{id}/recipients/append

GET    /t/{slug}/api/v1/sending-plans/{id}/steps
POST   /t/{slug}/api/v1/sending-plans/{id}/steps
PUT    /t/{slug}/api/v1/sending-plans/{id}/steps/{sid}
DELETE /t/{slug}/api/v1/sending-plans/{id}/steps/{sid}

GET /t/{slug}/api/v1/sending-plans/{id}/preview
GET /t/{slug}/api/v1/sending-plans/{id}/sample-emails
```

### Emails / Monitor

```http
GET  /t/{slug}/api/v1/emails
GET  /t/{slug}/api/v1/emails/stats
GET  /t/{slug}/api/v1/emails/stats/by-plan
GET  /t/{slug}/api/v1/emails/stats/by-template
GET  /t/{slug}/api/v1/emails/stats/by-grade
GET  /t/{slug}/api/v1/emails/stats/by-step
GET  /t/{slug}/api/v1/emails/stats/trend
POST /t/{slug}/api/v1/emails/ai-analysis
GET  /t/{slug}/api/v1/emails/{id}
```

Implementation note: register `/emails/stats*` before `/emails/{id}`; see `04_api/FASTAPI_ROUTE_ORDERING.md`.

### Intelligence

```http
GET  /t/{slug}/api/v1/intelligence/articles
GET  /t/{slug}/api/v1/intelligence/articles/{id}
POST /t/{slug}/api/v1/intelligence/articles/{id}/read
POST /t/{slug}/api/v1/intelligence/articles/{id}/star
POST /t/{slug}/api/v1/intelligence/articles/{id}/archive
GET  /t/{slug}/api/v1/intelligence/subscriptions
PUT  /t/{slug}/api/v1/intelligence/subscriptions
```

### Domains / Billing / Notifications

```http
GET /t/{slug}/api/v1/domains
GET /t/{slug}/api/v1/domains/{id}
GET /t/{slug}/api/v1/domains/{id}/history

GET /t/{slug}/api/v1/ai-capabilities
GET /t/{slug}/api/v1/billing/balance
GET /t/{slug}/api/v1/billing/transactions
GET /t/{slug}/api/v1/billing/usage-summary
GET /t/{slug}/api/v1/billing/usage-trend

GET  /t/{slug}/api/v1/notifications
POST /t/{slug}/api/v1/notifications/{id}/read
POST /t/{slug}/api/v1/notifications/mark-all-read
```

## 4. Internal API

```http
POST /internal/api/v1/collection/tasks/claim
POST /internal/api/v1/collection/tasks/{id}/heartbeat
POST /internal/api/v1/collection/tasks/{id}/submit-result
GET  /internal/api/v1/collection/credentials/{source_type}
POST /internal/api/v1/collection/companies/batch-upsert
POST /internal/api/v1/collection/contacts/batch-upsert
POST /internal/api/v1/collection/competitors/batch-upsert

POST /internal/api/v1/scoring/jobs/claim
POST /internal/api/v1/scoring/jobs/{id}/submit-result
POST /internal/api/v1/scoring/trigger

POST /internal/api/v1/sending/due-emails/claim
POST /internal/api/v1/sending/emails/{id}/mark-sent
POST /internal/api/v1/sending/emails/{id}/mark-failed
POST /internal/api/v1/sending/domain-quota/reserve

POST /internal/api/v1/intelligence/articles/publish
```

## 5. Webhooks

```http
POST /webhooks/engagelab
```

Return 2xx for duplicates. Return 5xx only when retry is desired.
