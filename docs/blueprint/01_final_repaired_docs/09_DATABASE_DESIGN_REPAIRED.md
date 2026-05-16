# 09 数据库设计文档（修复版）

完整 DDL 草案见：`../03_database/schema.sql`。

## 1. 修复目标

原 `09_DATABASE_DESIGN.md` 已具备多租户分层思路，但存在以下会阻断从 0 实现的问题：

1. Admin 页面需要的平台配置表缺失或不完整。
2. 平台管理员身份与租户角色 enum 混用风险。
3. 采集任务缺少 countries、countries_hash、lease_id、task-keyword 关系。
4. 群组只能绑定联系人，无法表达“公司入组，发送时使用默认联系人”。
5. 默认联系人无字段。
6. AI 计费缺少预授权/结算状态机字段。
7. 发送幂等不能依赖分区表 unique。
8. Webhook 事件缺少全局幂等索引与分区定位字段。
9. `ai_models.model_type` 与 AI 场景命名不一致。
10. 分区表游标分页未完整落入 API 与 DB 设计。

本修复版已将这些问题固化为最终 Schema。

## 2. 表分层

| 层 | 表 |
|---|---|
| Platform | `platform_users`, `tenants`, `data_sources`, `data_source_credentials`, `platform_scoring_templates`, `platform_email_templates`, `warmup_rules`, `ai_models`, `ai_scene_defaults` |
| Tenant auth | `users`, `user_roles` |
| Shared pool | `shared_companies`, `company_sources`, `shared_contacts` |
| Tenant company | `tenant_companies`, `company_scores`, `scoring_templates`, `contact_rules`, `company_blacklist`, `competitor_companies` |
| Tenant contacts/groups | `tenant_contacts`, `groups`, `group_members` |
| Collection | `collection_keywords`, `collection_tasks`, `collection_task_keywords` |
| Email | `email_templates`, `domain_warmup_status`, `domain_daily_usage`, `sending_plans`, `sending_plan_recipients`, `sequence_steps`, `sequence_enrollments`, `email_send_locks`, `emails`, `email_events` |
| Intelligence | `intelligence_sources`, `intelligence_articles`, `intelligence_subscriptions`, `intelligence_article_publications` |
| Billing/AI | `balance_transactions`, `ai_usage_logs` |
| System | `audit_logs`, `notifications`, `service_idempotency_keys` |

## 3. 关键字段修复

### 3.1 平台用户

新增 `platform_users`，避免将 `platform_admin` 塞入 tenant `user_roles`。

### 3.2 数据源

新增：

- `data_sources`：渠道基本信息、别名编码、采集配置、落库规则。
- `data_source_credentials.credentials_encrypted`：整包凭证密文。

### 3.3 采集

`collection_keywords` 必须包含：

- `keyword_normalized`
- `countries`
- `countries_hash`
- `source_types`

`collection_tasks` 必须包含：

- `keyword_normalized`
- `countries`
- `countries_hash`
- `source_types`
- `lease_id`
- `lease_owner`
- `lease_expires_at`

`collection_task_keywords` 关联任务与租户关键词，主系统据此解析 tenant 归属。

### 3.4 公司状态拆分

`tenant_companies` 拆成：

- `business_status`：业务流程状态。
- `data_status`：数据完整度/富集状态。

发送资格取决于两者与联系人状态。

### 3.5 群组以公司为主

`group_members`：

- 必填 `tenant_company_id`。
- 可选 `tenant_contact_id` 作为联系人覆盖。

### 3.6 默认联系人

`tenant_contacts.is_default` + partial unique：同一租户同一公司最多一个默认联系人。

### 3.7 发送幂等

新增 `email_send_locks(enrollment_id, step_id)`，发送服务先抢锁再调用 EngageLab。

### 3.8 域名额度

新增 `domain_daily_usage`，用原子 UPDATE/INSERT reserve 当日额度，避免多计划并发超发。

### 3.9 AI 计费

`ai_usage_logs` 增加：

- `estimated_cost`
- `actual_cost`
- `authorization_transaction_id`
- `settlement_status`
- `idempotency_key`
- `provider_request_id`

`balance_transactions` 增加：

- `reference_type`
- `reference_id`
- `idempotency_key`
- `operated_by_platform_user_id`

### 3.10 Webhook 幂等

`email_events` 增加：

- `email_created_at`
- `provider_event_id`
- unique `(source, provider_event_id)` where provider_event_id is not null

## 4. RLS 策略

Tenant 表启用 RLS。典型策略：

```sql
USING (tenant_id = current_tenant_id())
WITH CHECK (tenant_id = current_tenant_id())
```

服务表按最小权限拆分 DB role：

- `service_collection`
- `service_scoring`
- `service_sending`
- `service_webhook`

Phase 1 可先用一个 service role，但代码结构必须按 service name/scope 校验。

## 5. 分区策略

按月分区：

- `emails`
- `audit_logs`
- `intelligence_articles`

分页游标必须使用：

```text
cursor=<created_at_iso>_<uuid>
ORDER BY created_at DESC, id DESC
```

## 6. Alembic 执行建议

不要一次性裸跑 `schema.sql` 到生产。建议拆成：

1. Extensions + helper functions。
2. Platform/auth。
3. Shared pool。
4. Tenant company/contact/group。
5. Collection。
6. Email/domain。
7. Intelligence。
8. AI/billing。
9. System/notifications/audit。
10. RLS policies。
11. Indexes。
12. Initial seed data。
