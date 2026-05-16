# 后端开发计划（Codex / Claude Code 执行版）

## Phase P0 — 可启动、可登录、可隔离

### P0.1 Project scaffold

- FastAPI app with four routers: admin/tenant/internal/webhooks.
- Pydantic settings from env.
- Structured logging with request_id.
- Error response middleware.
- CORS whitelist.
- Health endpoints.

### P0.2 Database

- Alembic migrations from `03_database/schema.sql`.
- RLS helper functions and policies.
- Seed platform admin, data sources, warmup rule.
- Test partition creation.

### P0.3 Auth/RBAC

- Platform login.
- Tenant login with slug/email/password.
- JWT signing/verification.
- Tenant slug/tid match middleware.
- RBAC dependency.
- Password change and failed login lock.

### P0.4 Admin core APIs

- Tenants CRUD + create tenant workflow.
- Tenant users.
- Tenant domains.
- Manual recharge.
- Data sources and credentials.
- AI models/defaults.
- Warmup rules.
- Platform scoring/email templates.

### P0.5 Tenant core APIs

- Auth me/onboarding.
- Keywords.
- Scoring/contact rules.
- Companies/prospects read list/detail.
- Groups.
- Email templates.
- AI capabilities.
- Billing read for admin.

## Phase P1 — 业务闭环

### P1.1 Collection

- Main system task scheduler.
- Internal claim/heartbeat/submit.
- Shared company/contact upsert.
- Tenant company linking.
- Collection worker skeleton with adapters.

### P1.2 Scoring

- Rule engine.
- AI LLM dimension integration.
- Company score writeback.
- Recharge-triggered pending scoring.

### P1.3 Sending

- Sending plan wizard APIs.
- Recipient preview/lock.
- Sequence steps/enrollments.
- Domain quota reserve.
- Due email worker.
- EngageLab send integration.

### P1.4 Webhook

- EngageLab webhook receiver.
- Event idempotency.
- Email/enrollment/contact state updates.
- Reply placeholder or inbound parse if confirmed.

### P1.5 Intelligence

- Admin source CRUD/import.
- Fetch worker skeleton.
- AI summary + tenant publication.
- Tenant article APIs.

## Phase P2 — hardening and migration

- Old data migration scripts.
- Audit coverage.
- Metrics dashboards.
- PII retention jobs.
- Rate limiting.
- Playwright E2E with deployed frontend.
- Load tests for list APIs and sending worker.

## Suggested implementation order for code Agent

1. Scaffold backend and tests.
2. Implement DB migrations and seed.
3. Implement auth/RLS test suite.
4. Implement Admin API.
5. Implement Tenant settings/company/group/template APIs.
6. Implement AI billing service.
7. Implement collection internal API and worker.
8. Implement scoring.
9. Implement sending plan and worker.
10. Implement webhook.
11. Implement intelligence.
12. Implement migration scripts.
13. Run acceptance tests.
