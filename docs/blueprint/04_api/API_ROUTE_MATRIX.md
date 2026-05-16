# API Route Matrix

See `API_CONTRACT.md` for full details. This file is optimized for implementation planning.

| App | Page/Worker | Endpoint group | Required service |
|---|---|---|---|
| Admin | Login | `/admin/api/v1/auth/*` | AuthService |
| Admin | DataSources | `/data-sources*` | DataSourceService |
| Admin | ScoringTemplates | `/scoring-templates*` | PlatformTemplateService |
| Admin | IntelligenceSources | `/intelligence-sources*` | IntelligenceService |
| Admin | EmailTemplates | `/email-templates*` | PlatformTemplateService |
| Admin | WarmupRules | `/warmup-rules` | WarmupService |
| Admin | AIConfig | `/ai-config/*` | AIConfigService |
| Admin | Tenants | `/tenants*` | TenantService |
| Tenant | Login/Onboarding | `/auth/*`, `/onboarding/*` | AuthService / TenantService |
| Tenant | Dashboard | `/dashboard/*` | DashboardService |
| Tenant | Companies | `/companies*` | CompanyService |
| Tenant | Prospects | `/prospects*` | ProspectService |
| Tenant | Groups | `/groups*` | GroupService |
| Tenant | Templates | `/email-templates*` | EmailTemplateService / AIService |
| Tenant | SendingPlans | `/sending-plans*` | SendingPlanService |
| Tenant | EmailMonitor | `/emails*` | EmailMonitorService / AIService |
| Tenant | Intelligence | `/intelligence*` | IntelligenceService |
| Tenant | Settings | `/keywords`, `/scoring-templates`, `/contact-rules`, `/billing`, `/domains` | Settings services |
| Worker | Collection | `/internal/api/v1/collection/*` | CollectionService |
| Worker | Scoring | `/internal/api/v1/scoring/*` | ScoringService |
| Worker | Sending | `/internal/api/v1/sending/*` | SendingService |
| External | EngageLab | `/webhooks/engagelab` | WebhookService |
