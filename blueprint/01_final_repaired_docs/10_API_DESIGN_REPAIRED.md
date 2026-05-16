# 10 API 设计文档（修复版）

完整合同见：`../04_api/API_CONTRACT.md` 与 `../04_api/API_ROUTE_MATRIX.md`。

## 1. 统一入口

| 类型 | 前缀 | 认证 | 用途 |
|---|---|---|---|
| Admin | `/admin/api/v1` | `platform_admin` JWT | 平台运营后台。 |
| Tenant | `/t/{slug}/api/v1` | Tenant JWT + slug/tid 校验 | 租户业务后台。 |
| Internal | `/internal/api/v1` | Service JWT + scope | 采集/评分/发送等服务。 |
| Webhook | `/webhooks` | Provider signature / service secret | EngageLab 回调。 |

## 2. 响应格式

单资源：

```json
{ "data": { "id": "..." } }
```

列表：

```json
{
  "data": [],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total": 123
  }
}
```

错误：

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

## 3. 修复后的关键 API 决策

1. `details` 使用 array of objects，便于前端 Form 映射。
2. 创建类 POST 支持 `Idempotency-Key`。
3. Internal/Webhook 写接口支持 `X-Request-Id` 幂等。
4. 分区表列表接口使用双字段 cursor。
5. AI 功能按钮不直接读余额，统一读 `GET /ai-capabilities`。
6. `GET /billing/balance` 仅 tenant admin 可见。
7. Phase 1 自助充值接口不开放，Admin 手动充值。

## 4. Admin API 必备资源

- Auth：`POST /auth/login`, `GET /auth/me`
- Data sources：`/data-sources`, `/data-sources/{type}/credentials`, `/data-sources/{type}/config`
- Platform scoring templates：`/scoring-templates`
- Intelligence sources：`/intelligence-sources`
- Platform email templates：`/email-templates`
- Warmup rules：`/warmup-rules`
- AI config：`/ai-config/models`, `/ai-config/scene-defaults`, `/ai-config/pricing`
- Tenants：`/tenants`, `/tenants/{id}/users`, `/tenants/{id}/domains`, `/tenants/{id}/balance`
- Collection monitor：`/collection-tasks`
- Dashboard：`/dashboard/overview`, `/dashboard/ai-usage`, `/dashboard/collection-stats`

## 5. Tenant API 必备资源

- Auth/onboarding：`/auth/login`, `/auth/me`, `/auth/change-password`, `/onboarding/complete`
- Dashboard：`/dashboard/overview`, `/dashboard/funnel`
- Companies：`/companies`, `/companies/{id}`, `/companies/batch-import`, `/companies/{id}/blacklist`
- Prospects：`/prospects`, `/prospects/{id}`
- Contacts：`/companies/{cid}/contacts`, `/contacts/{id}/set-default`
- Groups：`/groups`, `/groups/{id}/members/batch-add`, `/groups/{id}/members/batch-remove`
- Scoring settings：`/scoring-templates`
- Contact rules：`/contact-rules`
- Keywords：`/keywords`
- Email templates：`/email-templates`, `/email-templates/ai-generate`
- Sending plans：`/sending-plans`, `/sending-plans/{id}/steps`, `/sending-plans/{id}/recipients/*`, `/sending-plans/{id}/start|pause|resume|cancel`
- Email monitor：`/emails`, `/emails/stats`, `/emails/stats/trend`, `/emails/ai-analysis`
- Intelligence：`/intelligence/articles`, `/intelligence/subscriptions`
- Domains：`/domains`
- Billing/AI capability：`/ai-capabilities`, `/billing/balance`, `/billing/transactions`, `/billing/usage-summary`
- Notifications：`/notifications`, `/notifications/mark-all-read`

## 6. Internal API 必备资源

- Collection：claim tasks, heartbeat, submit result, batch upsert companies/contacts/competitors, credentials。
- Scoring：claim pending score jobs, write results, trigger pending scoring。
- Sending：claim due emails, reserve quota, mark sent/failed。
- Intelligence worker：publish articles, settle summaries。

## 7. Webhook

`POST /webhooks/engagelab`

要求：

1. 校验签名或 shared secret。
2. 幂等插入 event。
3. 定位 email。
4. 同事务更新 email、enrollment、contact。
5. 重复事件返回 200/204。
6. 非幂等失败返回 5xx 让 provider 重试。
