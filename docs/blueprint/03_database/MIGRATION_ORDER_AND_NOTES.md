# 数据库迁移执行顺序与注意事项

## 1. 从 0 初始化顺序

1. Extensions + helper functions。
2. Platform/auth 基础表：`platform_users`, `tenants`, `users`, `user_roles`。
3. 平台配置表：`data_sources`, `data_source_credentials`, `platform_scoring_templates`, `platform_email_templates`, `warmup_rules`, `ai_models`, `ai_scene_defaults`。
4. Billing/AI：`balance_transactions`, `ai_usage_logs`。
5. Shared pool：`shared_companies`, `company_sources`, `shared_contacts`。
6. Collection：`collection_keywords`, `collection_tasks`, `collection_task_keywords`。
7. Tenant company/scoring：`tenant_companies`, `scoring_templates`, `scoring_template_versions`, `company_scores`, `contact_rules`, `company_blacklist`, `competitor_companies`。
8. Contacts/groups：`tenant_contacts`, `groups`, `group_members`。
9. Domain/email：`domain_warmup_status`, `domain_warmup_history`, `domain_daily_usage`, `email_templates`, `sending_plans`, `sending_plan_recipients`, `sequence_steps`, `sequence_enrollments`, `email_send_locks`, `emails`, `email_events`。
10. Intelligence：`intelligence_sources`, `intelligence_articles`, `intelligence_subscriptions`, `intelligence_article_publications`。
11. System：`notifications`, `audit_logs`, `service_idempotency_keys`。
12. Indexes。
13. RLS policies。
14. Seed data。

## 2. Alembic 建议

不要把所有 DDL 放入一个 migration。推荐：

- `0001_extensions_helpers.py`
- `0002_auth_platform.py`
- `0003_ai_billing.py`
- `0004_shared_pool.py`
- `0005_collection.py`
- `0006_tenant_company_scoring.py`
- `0007_contacts_groups.py`
- `0008_email_domain.py`
- `0009_intelligence.py`
- `0010_system_audit_notifications.py`
- `0011_rls_policies.py`
- `0012_seed_defaults.py`

## 3. 分区

初始化至少创建当前月、上月、下月分区。后台任务每月提前创建下下月分区。

分区表：

- `emails`
- `audit_logs`
- `intelligence_articles`

## 4. Seed 数据

最小 seed：

1. `platform_users` 初始平台管理员。
2. `data_sources` 三个默认渠道：A01/B01/C01。
3. `warmup_rules` 默认动态 6 档。
4. `ai_models` 可为空，但 Admin UI 应提示配置。
5. `platform_scoring_templates` 至少一个行业模板，便于创建租户。
6. `platform_email_templates` 可为空，但 Tenant 模板页应有空态。

## 5. 旧数据迁移

如需要迁移旧库，先跑新 Schema，再执行 `14_DATA_MIGRATION_REPAIRED.md` 的分批脚本。迁移期间生成 `_migration` schema 存 id mapping，不要污染业务表。
