# 后端总体架构（从 0 实现版）

## 1. 目标架构

Phase 1 推荐一个 FastAPI 进程承载四类入口，但代码与连接池必须隔离：

```text
FastAPI app
├── admin_app      /admin/api/v1/*       platform_admin JWT, admin_pool
├── tenant_app     /t/{slug}/api/v1/*    tenant JWT, tenant_pool + RLS
├── internal_app   /internal/api/v1/*    service JWT/scope, service_pool
└── webhook_app    /webhooks/*           provider signature, service_webhook
```

未来可按入口拆成独立服务，但 Phase 1 不需要。

## 2. 推荐代码目录

```text
clientget_backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   └── pagination.py
│   ├── db/
│   │   ├── pools.py
│   │   ├── rls.py
│   │   ├── transaction.py
│   │   └── repositories/
│   ├── schemas/
│   ├── api/
│   │   ├── admin/
│   │   ├── tenant/
│   │   ├── internal/
│   │   └── webhooks/
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── tenant_service.py
│   │   ├── collection_service.py
│   │   ├── scoring_service.py
│   │   ├── ai_service.py
│   │   ├── billing_service.py
│   │   ├── sending_service.py
│   │   ├── webhook_service.py
│   │   ├── intelligence_service.py
│   │   └── notification_service.py
│   ├── integrations/
│   │   ├── openrouter.py
│   │   ├── engagelab.py
│   │   └── data_sources/
│   └── workers/
│       ├── scheduler.py
│       ├── scoring_worker.py
│       ├── sending_worker.py
│       └── intelligence_worker.py
├── collection_worker/
│   ├── main.py
│   ├── scheduler.py
│   ├── adapters/
│   └── internal_client.py
├── alembic/
├── tests/
└── pyproject.toml
```

## 3. 请求生命周期

### Tenant API

```text
request -> parse slug -> verify JWT -> tenant lookup -> tid/slug match
        -> acquire tenant_pool conn -> BEGIN
        -> SET LOCAL app.current_tenant_id = :tid
        -> handler/service/repository using same conn
        -> COMMIT/ROLLBACK -> response
```

禁止 handler 自己 acquire 新连接，因为新连接没有 RLS session variable。

### Admin API

```text
request -> verify platform JWT -> acquire admin_pool conn -> handler
```

Admin 可以跨租户查询，但所有写操作必须写 audit log。

### Internal API

```text
request -> verify service token -> verify X-Service-Name and scope
        -> idempotency check by X-Request-Id
        -> service handler
```

### Webhook

```text
request -> verify provider signature -> normalize event -> idempotency
        -> locate email -> transactionally insert event + update states
```

## 4. 服务边界

| Service | 主要职责 |
|---|---|
| AuthService | 平台/租户登录、密码、JWT、锁定。 |
| TenantService | 创建租户、复制模板、团队、域名、充值。 |
| CollectionService | 关键词聚合、任务 claim、结果入库。 |
| ScoringService | 规则评分、LLM 维度、补评。 |
| AIService | OpenRouter 调用、prompt、usage。 |
| BillingService | 余额、预授权、结算、流水。 |
| SendingService | 发送计划、收件人锁定、序列推进、额度 reserve、发信。 |
| WebhookService | EngageLab 事件幂等、状态推进。 |
| IntelligenceService | 情报源、文章、摘要、发布。 |
| NotificationService | 站内通知。 |

## 5. 数据访问模式

建议 Repository 层只接收当前事务连接：

```python
class CompanyRepository:
    def __init__(self, conn: Connection):
        self.conn = conn
```

不要在 repository 内部创建连接池连接。

## 6. 幂等设计

| 场景 | 幂等键 |
|---|---|
| Admin/Tenant 创建类 POST | `Idempotency-Key` + user/platform_user + endpoint。 |
| Internal 写接口 | `X-Request-Id` + service name + endpoint。 |
| AI 结算 | `authorization_transaction_id` 或 `idempotency_key`。 |
| 发送单步邮件 | `email_send_locks(enrollment_id, step_id)`。 |
| Webhook | `(source, provider_event_id)`。 |

## 7. 状态机概览

### Sending plan

```text
draft -> scheduled -> running -> paused -> running -> completed
       \-> cancelled
```

### Sequence enrollment

```text
active -> completed
active -> replied/bounced/unsubscribed
active -> paused -> active
active -> cancelled
```

### Collection task

```text
pending -> running -> completed
pending -> running -> failed -> pending/retry
pending/running -> cancelled
```

### AI usage

```text
authorized -> settled_exact/settled_charge/settled_release
            -> released_full
            -> settlement_failed
```

## 8. 生产安全基线

- CORS 白名单只允许 Admin/Tenant 前端域名。
- 所有密钥来自环境变量或加密存储。
- 数据源 credentials 整包 AES-256-GCM 加密。
- HTML 邮件内容 sanitize。
- Webhook raw body 签名校验。
- 登录失败锁定：5 次失败锁 15 分钟。
- 审计日志不可 UPDATE/DELETE。
- request_id 贯穿日志、错误响应、审计。
