# 安全、认证与 RLS 架构

## 1. 认证类型

### Platform JWT

```json
{
  "sub": "platform_user_uuid",
  "kind": "platform",
  "roles": ["platform_admin"],
  "exp": 1745000000,
  "iat": 1744913600
}
```

### Tenant JWT

```json
{
  "sub": "user_uuid",
  "kind": "tenant",
  "tid": "tenant_uuid",
  "slug": "tenant_slug",
  "roles": ["admin"],
  "exp": 1745000000,
  "iat": 1744913600
}
```

### Service JWT

```json
{
  "sub": "collection-sh-01",
  "kind": "service",
  "service_name": "collection-service",
  "aud": "internal:collection",
  "scopes": ["collection:claim", "collection:write"],
  "exp": 1745000000
}
```

## 2. 登录流程

### Tenant login

1. 前端提交 slug/email/password。
2. auth_service 使用 `auth_pool` 查 tenant。
3. auth_service 查 user by tenant_id + email。
4. 校验密码、locked_until、tenant.status、user.status。
5. 查 user_roles。
6. 签发 tenant JWT。
7. 成功后重置 failed_login_count。
8. 失败后增加 failed_login_count，超过阈值设置 locked_until。

## 3. RLS session variable

```sql
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid AS $$
  SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;
```

Tenant request 必须在事务内执行：

```sql
SET LOCAL app.current_tenant_id = '<tenant_id>';
```

`SET LOCAL` 只在当前事务生效，避免连接池泄漏。

## 4. RLS 策略模板

```sql
ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_companies FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_companies_select ON tenant_companies
FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_companies_insert ON tenant_companies
FOR INSERT WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_companies_update ON tenant_companies
FOR UPDATE USING (tenant_id = current_tenant_id())
WITH CHECK (tenant_id = current_tenant_id());
```

## 5. RBAC

Tenant role matrix is implemented at API/service layer, not only frontend.

| Resource | admin | operator | viewer |
|---|---|---|---|
| companies read | yes | yes | yes |
| companies mutate/import/blacklist | yes | yes | no |
| groups mutate | yes | yes | no |
| templates mutate/AI generate | yes | yes | no |
| sending plans mutate/start | yes | yes | no |
| email monitor read | yes | yes | yes |
| AI analysis | yes | yes | no |
| keywords/scoring/contact rules/billing/team/domains | yes | no | no |

## 6. Sensitive data

- `password_hash` 使用 bcrypt/argon2id。
- `credentials_encrypted` 使用 AES-256-GCM。
- API 不返回密钥明文。
- `email_events.metadata` 中 IP/UA 仅 admin 可见，90 天后脱敏。
- `reply_body_text` 作为敏感内容，viewer 只读可见但需审计访问。

## 7. CORS

只允许：

- `https://client-get-admin.vercel.app`
- `https://client-get-tenant.vercel.app`
- 本地开发域名通过环境变量配置。

禁止 `allow_origins=["*"]`。

## 8. 审计

写审计的场景：

- 登录/登出。
- 租户/用户/域名/余额修改。
- 关键词/评分/联系人规则修改。
- 模板/群组/计划修改。
- 导出。
- 黑名单。
- AI 充值/退款/扣费调整。

审计日志只允许 INSERT/SELECT，不允许 UPDATE/DELETE。
