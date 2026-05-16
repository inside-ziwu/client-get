# RLS Policy Matrix（自审后补充）

本文档补齐 `schema.sql` 中“只给示例 policy”的风险点。Codex/Claude Code 实现 Alembic 时必须按此矩阵生成完整 policy，不允许只复制示例 policy。

## 1. 原则

1. 所有带 `tenant_id` 且会被 Tenant API 访问或写入的表必须启用 RLS。
2. `shared_companies`、`shared_contacts`、`company_sources` 原表不开放给 `app_user`；Tenant API 只能通过服务层 JOIN 已授权的 `tenant_companies` / `tenant_contacts` 返回。
3. `intelligence_sources` 允许 `tenant_id IS NULL` 的平台源被租户只读查看；租户自定义源仅本租户可见。
4. `audit_logs` 对 Tenant API 只允许 INSERT / SELECT，禁止 UPDATE / DELETE。
5. Internal service roles 通过独立 DB role 和 endpoint scope 控制，不使用普通 tenant JWT 权限。

## 2. 必须启用 RLS 的表

| 表 | SELECT | INSERT | UPDATE | DELETE | 说明 |
|---|---|---|---|---|---|
| `users` | tenant only | service/admin only | tenant admin limited | soft disable | 登录查询走 auth_service，不走 app_user。 |
| `user_roles` | tenant only | admin only | admin only | admin only | 三角色。 |
| `collection_keywords` | tenant only | admin role | admin role | admin role | Tenant 设置关键词。 |
| `collection_task_keywords` | tenant only/internal | internal | internal | internal | 自审补齐，避免含 tenant_id 表漏 RLS。 |
| `tenant_companies` | tenant only | service/operator | service/operator | soft delete | 公司视图。 |
| `scoring_templates` | tenant admin | tenant admin | tenant admin | no | 当前活跃模板。 |
| `scoring_template_versions` | tenant admin | system | no | no | 历史快照。 |
| `company_scores` | tenant only | scoring service | scoring service | no | 评分记录。 |
| `contact_rules` | tenant admin | tenant admin | tenant admin | no | 联系人规则。 |
| `company_blacklist` | tenant only | operator/admin | operator/admin | operator/admin | 黑名单。 |
| `competitor_companies` | tenant only | service/admin | service/admin | service/admin | 竞对库。 |
| `tenant_contacts` | tenant only | service/operator | service/operator | soft delete | 联系人视图。 |
| `groups` | tenant only | operator/admin | operator/admin | soft delete | 群组。 |
| `group_members` | tenant only | operator/admin | operator/admin | operator/admin | 群组成员。 |
| `domain_warmup_status` | tenant admin | admin/internal | internal/admin | no | 域名状态。 |
| `domain_warmup_history` | tenant admin | internal | no | no | 预热历史。 |
| `domain_daily_usage` | tenant admin | sending service | sending service | no | 额度使用。 |
| `email_templates` | tenant only | operator/admin | operator/admin | soft delete | 租户模板。 |
| `sending_plans` | tenant only | operator/admin | operator/admin | limited | 发送计划。 |
| `sending_plan_recipients` | tenant only | operator/admin | append-only | no | 收件人快照。 |
| `sequence_steps` | tenant only | operator/admin | future-only | no | 序列步骤。 |
| `sequence_enrollments` | tenant only | sending service | sending/webhook | no | 执行状态。 |
| `email_send_locks` | service only | sending service | sending service | no | 发送幂等锁。 |
| `emails` | tenant only | sending service | webhook/service | no | 分区表。 |
| `email_events` | tenant only | webhook | no | no | 事件流水。 |
| `intelligence_sources` | tenant_id null or tenant | admin/tenant future | admin/tenant future | soft delete | 自审补齐。 |
| `intelligence_subscriptions` | tenant only | tenant user | tenant user | tenant user | 订阅。 |
| `intelligence_article_publications` | tenant only | internal | tenant user state | no | 文章发布状态。 |
| `notifications` | tenant/user only | system | mark read only | no | 站内消息。 |
| `balance_transactions` | tenant admin only | admin/system | no | no | 余额流水。 |
| `ai_usage_logs` | tenant admin only | ai service | settlement only | no | AI 用量/尝试记录。 |
| `audit_logs` | tenant only | app/system | no | no | 自审补齐，审计只追加。 |

## 3. Policy 模板

普通 tenant 表：

```sql
CREATE POLICY <table>_select ON <table>
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY <table>_insert ON <table>
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY <table>_update ON <table>
  FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY <table>_delete ON <table>
  FOR DELETE USING (tenant_id = current_tenant_id());
```

审计表：

```sql
CREATE POLICY audit_insert ON audit_logs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY audit_select ON audit_logs
  FOR SELECT USING (tenant_id = current_tenant_id());
-- 不创建 UPDATE/DELETE policy。
```

平台源可读表：

```sql
CREATE POLICY intelligence_sources_select ON intelligence_sources
  FOR SELECT USING (tenant_id IS NULL OR tenant_id = current_tenant_id());
```

## 4. 验收

至少写以下测试：

1. Tenant A 创建/读取的数据 Tenant B 完全不可见。
2. 直接从 `shared_companies` 查询应被 app_user 拒绝。
3. `audit_logs` 可 INSERT/SELECT，不可 UPDATE/DELETE。
4. `balance_transactions` 和 `ai_usage_logs` 仅 admin 可读，operator/viewer 不可读。
5. `intelligence_sources` 中 `tenant_id IS NULL` 平台源可读，其他租户私有源不可读。
