# Frontend ↔ Backend Alignment Matrix（最终版）

## 1. Admin App

| 前端页面 | 路由 | 后端 API | 数据实体 | 备注 |
|---|---|---|---|---|
| 登录 | `/login` | `POST /admin/api/v1/auth/login` | `platform_users` | 平台身份独立。 |
| 数据源管理 | `/data-sources` | `/admin/api/v1/data-sources*` | `data_sources`, `data_source_credentials` | 凭证只返回 masked。 |
| 评分模板管理 | `/scoring-templates` | `/admin/api/v1/scoring-templates*` | `platform_scoring_templates` | 只影响新租户。 |
| 情报源管理 | `/intelligence-sources` | `/admin/api/v1/intelligence-sources*` | `intelligence_sources` | tenant_id null 为平台源。 |
| 邮件模板管理 | `/email-templates` | `/admin/api/v1/email-templates*` | `platform_email_templates` | 租户可复制。 |
| 域名预热规则 | `/warmup-rules` | `/admin/api/v1/warmup-rules` | `warmup_rules`, `warmup_rule_levels` | 动态 6 档。 |
| AI 配置 | `/ai-config` | `/admin/api/v1/ai-config/*` | `ai_models`, `ai_scene_defaults` | OpenRouter 平台级。 |
| 租户列表 | `/tenants` | `/admin/api/v1/tenants` | `tenants` | 创建租户复制模板。 |
| 租户详情-域名 | `/tenants/:id` | `/tenants/{id}/domains` | `domain_warmup_status` | DNS 验证。 |
| 租户详情-团队 | `/tenants/:id` | `/tenants/{id}/users` | `users`, `user_roles` | 三角色。 |
| 租户详情-AI余额 | `/tenants/:id` | `/tenants/{id}/balance*` | `balance_transactions` | Phase 1 手动充值。 |

## 2. Tenant App

| 前端页面 | 路由 | 后端 API | 数据实体 | 备注 |
|---|---|---|---|---|
| 登录 | `/login` | `POST /t/{slug}/api/v1/auth/login` | `users`, `user_roles` | 表单输入 slug。 |
| 首次向导 | `/onboarding` | `/auth/change-password`, `/keywords`, `/scoring-templates`, `/contact-rules` | 多表 | Step1/2 必填。 |
| Dashboard | `/dashboard` | `/dashboard/overview`, `/dashboard/funnel`, `/notifications` | 聚合 | 余额只 admin 可见。 |
| 公司列表 | `/companies` | `/companies*` | `tenant_companies`, `shared_companies` | 展示 data_status。 |
| 公司详情 Drawer | drawer | `/companies/{id}`, `/companies/{id}/contacts` | company/contact/score/email | 四 tab。 |
| 优选客户 | `/curated-customers` | `/prospects*`, `/groups*` | `tenant_companies`, `groups` | 群组公司主实体。 |
| 邮件模板 | `/templates` | `/email-templates*`, `/ai-capabilities` | `email_templates` | AI 生成置灰。 |
| 发送计划列表 | `/send-plans` | `/sending-plans` | `sending_plans` | 状态标签。 |
| 创建发送计划 | `/send-plans/new` | `/sending-plans`, `/steps`, `/recipients/preview`, `/recipients/lock` | sending tables | 支持渐进保存。 |
| 计划详情 | `/send-plans/:id` | `/sending-plans/{id}`, `/pause`, `/resume` | sending/email stats | running 10s 轮询。 |
| 邮件监控 | `/email-monitor` | `/emails/stats*`, `/emails/ai-analysis` | `emails`, `email_events` | AI 分析置灰。 |
| 情报中心 | `/intelligence` | `/intelligence/articles*` | intelligence tables | 余额不足隐藏摘要。 |
| 设置-关键词 | `/settings/keywords` | `/keywords*` | `collection_keywords` | admin only。 |
| 设置-评分 | `/settings/scoring` | `/scoring-templates*` | `scoring_templates` | admin only。 |
| 设置-联系人规则 | `/settings/contact-rules` | `/contact-rules*` | `contact_rules` | admin only。 |
| 设置-AI余额 | `/settings/ai-balance` | `/billing/*` | `balance_transactions`, `ai_usage_logs` | admin only。 |
| 设置-团队 | `/settings/team` | `/team/users*` or `/users*` | `users`, `user_roles` | 可实现为 `/team/users` alias。 |

## 3. Known UI/API adjustments

1. Tenant frontend may call `/settings/team`; backend can expose `/team/users` as alias to avoid confusion.
2. AI balance component should use `/ai-capabilities` for operator/viewer and `/billing/balance` only for admin.
3. Warmup UI should render levels returned by API, not hardcode numbers.
4. Group member API should accept company IDs, not only contact IDs.
5. Company/prospect detail should include default contact state.
6. Sending wizard recipient preview should return exclusions breakdown: blacklisted/unsubscribed/bounced/incomplete/no_email.
