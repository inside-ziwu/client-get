# 10 API 设计文档

> **文档版本**: v1.0
> **创建日期**: 2026-04-17
> **输入文档**: `02_API_REFERENCE.md`（现有 API）、`07_REQUIREMENTS_SPEC.md`（需求规格）、`09_DATABASE_DESIGN.md`（数据库设计）
> **目标读者**: AI Agent（可解析结构化端点定义）+ 人类开发者（可理解设计意图）

---

## 目录

1. [总体设计原则](#1-总体设计原则)
2. [双应用架构](#2-双应用架构)
3. [认证与授权](#3-认证与授权)
4. [统一响应格式](#4-统一响应格式)
5. [Admin API — 平台管理端](#5-admin-api--平台管理端)
6. [Tenant API — 租户业务端](#6-tenant-api--租户业务端)
7. [Internal API — 采集服务](#7-internal-api--采集服务)
8. [Webhook 接收端点](#8-webhook-接收端点)
9. [限流与安全策略](#9-限流与安全策略)
10. [CORS 配置](#10-cors-配置)
11. [现有 API 迁移映射](#11-现有-api-迁移映射)

---

## 1. 总体设计原则

### 1.1 设计决策

| # | 决策 | 结论 | 理由 |
|---|------|------|------|
| A1 | URL 前缀 | `/api/v1/` | 版本化，兼容未来破坏性变更 |
| A2 | 双应用路由 | Admin API (`/admin/api/v1/`) + Tenant API (`/t/{slug}/api/v1/`) | 职责分离：平台管理 vs 租户业务 |
| A3 | 认证 | JWT Bearer + slug 仅存在于 Tenant API 路径 | 延续现有 JWT，增加租户上下文且不污染前端路由 |
| A4 | 分页 | 游标分页（cursor-based） | 大数据集性能稳定，避免 offset 深翻页 |
| A5 | 命名 | kebab-case URL + snake_case JSON | RESTful 惯例 + Python 生态一致 |
| A6 | 软删除 | DELETE 返回 204，实际执行 `SET deleted_at` | 见 09_DATABASE_DESIGN.md §1.2 软删除表清单 |
| A7 | 批量操作 | POST `/resource/batch-action` | 避免超长 query string |
| A8 | 幂等性 | POST 创建类端点支持 `Idempotency-Key` header | 防止网络重试导致重复创建 |

### 1.2 Canonical 决策（跨 10-14 真源）

> 本节是 `10-14` 的唯一规范真源。`11_FRONTEND_ARCHITECTURE.md`、`12_COLLECTION_SERVICE.md`、`13_AI_INTEGRATION.md`、`14_DATA_MIGRATION.md` 如有冲突，以本节为准。

| 主题 | Canonical 决策 |
|------|----------------|
| 租户 slug 承载 | **前端路由不承载 slug**；前端统一使用 `/login`、`/dashboard` 等路由；**仅 Tenant API 承载 slug**：`/t/{slug}/api/v1/*` |
| Tenant 登录方式 | 登录表单显式输入 `slug + email + password`，登录成功后 `slug` 写入 JWT 与前端 auth 上下文 |
| 角色枚举 | 机器值统一为 `admin / operator / viewer`，禁止再使用 `sales / observer` 作为程序值 |
| Admin AI 资源名 | 统一为聚合资源 `ai-config`，其子资源包括 `/models`、`/pricing`、`/scene-defaults` |
| `source_type` 枚举 | 统一为 `waimao_tong / tengdao / lixiaoyun` |
| Internal API 授权依据 | 主系统**不得信任调用方上传的 `tenant_ids`**，跨租户归属必须由主系统基于本地任务/关键词关系重新解析 |

### 1.3 HTTP 方法语义

| 方法 | 语义 | 幂等 | 示例 |
|------|------|------|------|
| GET | 读取 | 是 | 列表、详情 |
| POST | 创建 / 操作 | 否（除非带 Idempotency-Key） | 创建资源、触发动作 |
| PUT | 全量更新 | 是 | 更新资源全部字段 |
| PATCH | 部分更新 | 是 | 更新资源部分字段 |
| DELETE | 删除 | 是 | 软删除或硬删除 |

### 1.4 URL 设计规范

```
# Admin API（平台运营后台）
/admin/api/v1/{resource}

# Tenant API（租户业务端）
/t/{slug}/api/v1/{resource}

# Internal API（服务间调用，不暴露公网）
/internal/api/v1/{resource}

# Webhook（外部回调接收）
/webhooks/{provider}
```

---

## 2. 双应用架构

### 2.1 应用拆分

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx / Load Balancer                  │
│                                                          │
│  /admin/*     → Admin FastAPI App (platform_admin 角色)   │
│  /t/{slug}/*  → Tenant FastAPI App (app_user 角色)        │
│  /internal/*  → Internal FastAPI App (service_* 角色)      │
│  /webhooks/*  → Webhook FastAPI App (webhook_service 角色) │
└─────────────────────────────────────────────────────────┘
```

> **Phase 1 简化**：四个路由前缀挂载在同一 FastAPI 进程内（`app.mount()`），共享进程但使用**独立数据库连接池**（Admin 用 `platform_admin` 角色，Tenant 用 `app_user` 角色）。未来可拆分为独立服务。

### 2.2 数据库连接池隔离

| 连接池 | DB 角色 | RLS | 用途 |
|--------|---------|-----|------|
| `admin_pool` | `platform_admin` (BYPASSRLS) | 绕过 | Admin API 全部端点 |
| `tenant_pool` | `app_user` | 启用 | Tenant API 全部端点 |
| `service_pool` | `service_*`（按服务拆分的最小权限角色） | 受控绕过 | Internal API、Webhook 处理 |

> **跨文档引用**：Internal API / Webhook 不再共享单一 `service_user`。采集、评分、发送、Webhook 至少拆成独立服务身份，分别映射最小权限 DB role；只有确需跨租户写入的受控端点才允许绕过 RLS。

### 2.3 服务身份契约

Internal / Webhook 侧统一采用“服务身份 + 短期令牌 + 最小权限 DB role”：

| 服务 | `X-Service-Name` | JWT `aud` | DB 角色 | 允许能力 |
|------|------------------|-----------|---------|---------|
| 采集服务 | `collection-service` | `internal:collection` | `service_collection` | 领取采集任务、提交公司/联系人/竞品、更新采集任务状态 |
| 评分服务 | `scoring-service` | `internal:scoring` | `service_scoring` | 拉取待评分对象、写回评分结果、触发补评 |
| 发送服务 | `sending-service` | `internal:sending` | `service_sending` | 拉取到期待发送邮件、回写发送状态、查询域名配额 |
| Webhook 接收器 | `webhook-engagelab` | `internal:webhook` | `service_webhook` | 校验回调、写入 `email_events`、推进邮件与序列状态 |

**统一请求头**：

```http
Authorization: Bearer <service-token>
X-Service-Name: collection-service
X-Service-Instance: collection-sh-01
X-Request-Id: 9aef...
```

**校验规则**：
1. `sub` = 服务实例或服务账号标识；`aud` 必须匹配目标能力域。
2. `X-Service-Name` 必须与 token claim 中的服务名一致。
3. Internal API 必须校验调用方身份是否拥有该端点 scope，禁止仅凭“能连上内网”放行。
4. 所有 Internal / Webhook 写接口必须支持 `X-Request-Id` 幂等记录，避免服务重试造成重复落库。

Tenant 连接池在每次请求时设置 session 变量（见 09_DATABASE_DESIGN.md §9.1）：

> **⚠ 安全约束**：所有 Tenant API handler 必须通过 `request.state.db` 获取数据库连接，**禁止**直接从 `tenant_pool` acquire 连接——直接获取的连接未执行 `SET LOCAL`，会绕过 RLS 隔离。建议通过 FastAPI Depends 注入而非 middleware 设置，确保连接生命周期与请求绑定。

```python
# 中间件伪代码
async def tenant_middleware(request, call_next):
    slug = request.path_params["slug"]
    tenant = await get_tenant_by_slug(slug)  # 用 admin_pool 查 tenants 表

    # JWT tenant_id 与 URL slug 交叉验证（防止篡改 URL 访问其他租户）
    jwt_tid = request.state.user.tid
    if str(tenant.id) != str(jwt_tid):
        raise HTTPException(403, detail="Tenant mismatch: JWT tid does not match URL slug")
    async with tenant_pool.acquire() as conn:
        await conn.execute("SET LOCAL app.current_tenant_id = $1", tenant.id)
        request.state.db = conn
        request.state.tenant = tenant
        response = await call_next(request)
    return response
```

---

## 3. 认证与授权

### 3.1 认证流程

```
租户用户登录流程：

1. 前端访问 `/login` → 用户输入 `slug`
2. POST /t/{slug}/api/v1/auth/login { email, password }
3. 后端：
   a. 用 admin_pool 查 tenants WHERE slug = :slug → tenant_id
   b. 用受控服务身份查询 users WHERE tenant_id = :tid AND email = :email
      （登录查询是少数允许绕过 RLS 的场景，但必须走受限服务角色而非共享高权限连接）
   c. 验证 bcrypt(password, password_hash)
   d. 检查 locked_until > NOW() → 拒绝（暴力破解防护）
   e. 检查 tenant.status = 'active'
   f. 查 user_roles → 获取角色列表
   g. 签发 JWT：{ sub: user_id, tid: tenant_id, slug, roles: ["admin"|"operator"|"viewer"], exp }
4. 返回 { access_token, token_type: "bearer", must_change_pwd }
```

平台运营登录流程：

```
1. 前端访问 /admin/login
2. POST /admin/api/v1/auth/login { email, password }
3. 后端验证平台管理员凭证（users 表中 tenant_id 关联到特殊"平台租户"）
4. 签发 JWT：{ sub: user_id, tid: platform_tenant_id, roles: ["platform_admin"], exp }
```

### 3.2 JWT Token 规格

```json
{
  "sub": "018f6b3a-...",       // user_id (UUID v7)
  "tid": "018f6b3a-...",       // tenant_id
  "slug": "acme-corp",         // tenant slug（API 前缀用）
  "roles": ["admin"],          // 用户角色列表
  "exp": 1745000000,           // 过期时间（24h）
  "iat": 1744913600
}
```

| 参数 | 值 |
|------|-----|
| 算法 | HS256（Phase 1）→ RS256（Phase 2 考虑） |
| 有效期 | 24 小时 |
| 刷新机制 | Phase 1 不实现 refresh token，过期重新登录 |
| 密钥管理 | 环境变量 `JWT_SECRET_KEY` |

### 3.3 RBAC 权限矩阵

> 角色定义见 07_REQUIREMENTS_SPEC.md §1.1，DB 枚举见 09_DATABASE_DESIGN.md §2.3。

**Tenant API 权限矩阵**（`✅` = 允许，`❌` = 拒绝）：

| 资源 | 操作 | admin | operator | viewer |
|------|------|-------|----------|--------|
| **公司列表** | 读取/筛选 | ✅ | ✅ | ✅ |
| **公司** | 手动添加/导入 | ✅ | ✅ | ❌ |
| **公司** | 加入黑名单 | ✅ | ✅ | ❌ |
| **优选客户** | 读取/筛选 | ✅ | ✅ | ✅ |
| **优选客户** | 修改标签/备注 | ✅ | ✅ | ❌ |
| **群组** | 创建/管理 | ✅ | ✅ | ❌ |
| **群组** | 读取 | ✅ | ✅ | ✅ |
| **邮件模板** | 读取 | ✅ | ✅ | ✅ |
| **邮件模板** | 创建/修改/删除 | ✅ | ✅ | ❌ |
| **邮件模板** | AI 生成 | ✅ | ✅ | ❌ |
| **发送计划** | 创建/执行/暂停 | ✅ | ✅ | ❌ |
| **发送计划** | 读取/监控 | ✅ | ✅ | ✅ |
| **邮件监控** | 查看统计 | ✅ | ✅ | ✅ |
| **邮件监控** | AI 分析 | ✅ | ✅ | ❌ |
| **情报中心** | 读取 | ✅ | ✅ | ✅ |
| **采集关键词** | 配置 | ✅ | ❌ | ❌ |
| **评分规则** | 查看/修改 | ✅ | ❌ | ❌ |
| **联系人规则** | 查看/修改 | ✅ | ❌ | ❌ |
| **AI 余额** | 查看 | ✅ | ❌ | ❌ |
| **团队管理** | 创建/管理用户 | ✅ | ❌ | ❌ |

### 3.4 权限中间件

```python
from functools import wraps

def require_roles(*allowed_roles):
    """RBAC 装饰器，检查 JWT 中的角色"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.state.user
            if not any(r in allowed_roles for r in user.roles):
                raise HTTPException(403, detail="权限不足")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 用法
@router.post("/keywords")
@require_roles("admin")
async def create_keyword(request, body: KeywordCreate):
    ...
```

---

## 4. 统一响应格式

### 4.1 成功响应 — 单资源

```json
{
  "data": {
    "id": "018f6b3a-...",
    "name": "Acme Corp",
    "created_at": "2026-04-17T08:00:00Z"
  }
}
```

### 4.2 成功响应 — 列表（游标分页）

```json
{
  "data": [
    { "id": "018f6b3a-...", "name": "Company A" },
    { "id": "018f6b3b-...", "name": "Company B" }
  ],
  "pagination": {
    "cursor": "018f6b3b-...",
    "has_more": true,
    "total": 1234
  }
}
```

| 参数 | 说明 |
|------|------|
| `cursor` | 下一页起始位置（基于 UUID v7 的时间有序性） |

> **⚠ 分区表注意**：`emails` 和 `intelligence_articles` 表使用 `PARTITION BY RANGE(created_at)` + 复合主键 `(id, created_at)`（见 09 §4.2）。对这些表的游标分页必须使用 `(created_at, id)` 双字段游标而非单 UUID 游标，否则跨分区查询无法保证排序正确性。实现时游标格式为 `cursor={created_at_iso}_{uuid}`。
| `has_more` | 是否有下一页 |
| `total` | 总数（仅在 `include_total=true` 时返回，默认不返回以避免 COUNT 开销） |
| `limit` | 请求参数，每页条数，默认 20，最大 100 |

**请求示例**：

```
GET /t/acme/api/v1/companies?limit=20&cursor=018f6b3b-...&include_total=true
```

### 4.3 错误响应

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      { "field": "email", "message": "邮箱格式无效" }
    ],
    "request_id": "req_abc123"
  }
}
```

### 4.4 错误码体系

| HTTP 状态码 | error.code | 场景 |
|-------------|-----------|------|
| 400 | `VALIDATION_ERROR` | 请求参数校验失败 |
| 400 | `BUSINESS_ERROR` | 业务规则违反（如余额不足） |
| 401 | `UNAUTHORIZED` | 未认证或 token 过期 |
| 403 | `FORBIDDEN` | 角色权限不足 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 资源冲突（如重复创建） |
| 422 | `UNPROCESSABLE` | 请求可解析但语义错误 |
| 429 | `RATE_LIMITED` | 超过限流阈值 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |

### 4.5 空响应

| 操作 | HTTP 状态码 | Body |
|------|-------------|------|
| DELETE 成功 | 204 | 无 |
| POST 操作类（无返回值） | 204 | 无 |
| POST 创建类 | 201 | `{ "data": {...} }` |

---

## 5. Admin API — 平台管理端

> 路由前缀：`/admin/api/v1`
> 认证：平台管理员 JWT（`roles: ["platform_admin"]`）
> DB 连接池：`admin_pool`（`platform_admin` 角色，BYPASSRLS）

### 5.1 租户管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/tenants` | 租户列表（分页） | — |
| POST | `/tenants` | 创建租户（含初始管理员） | 07 场景⑦ Step1 |
| GET | `/tenants/{id}` | 租户详情 | — |
| PATCH | `/tenants/{id}` | 更新租户信息 | — |
| POST | `/tenants/{id}/suspend` | 停用租户 | — |
| POST | `/tenants/{id}/activate` | 启用租户 | — |

**POST `/tenants` 请求体**：

```json
{
  "name": "赵总PCB公司",
  "slug": "zhao-pcb",
  "industry": "PCB",
  "admin_email": "zhao@example.com",
  "admin_name": "赵总",
  "admin_password": "临时密码"
}
```

**创建租户后台自动执行**（见 07 场景⑦ Step1）：
1. 创建 `tenants` 记录
2. 创建 `users` 记录（`must_change_pwd=true`）
3. 创建 `user_roles` 记录（`role='admin'`）
4. 复制当前行业默认评分模板 → `scoring_templates` + `scoring_template_versions`
5. 复制行业官方邮件模板 → `email_templates`（`source_type='platform_copy'`）

### 5.2 租户用户管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/tenants/{tid}/users` | 租户下的用户列表 | 07 场景⑦ Step3 |
| POST | `/tenants/{tid}/users` | 为租户创建用户 | 07 场景⑦ Step3 |
| PATCH | `/tenants/{tid}/users/{uid}` | 更新用户 | — |
| DELETE | `/tenants/{tid}/users/{uid}` | 禁用用户 | — |

### 5.3 租户余额管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/tenants/{tid}/balance` | 余额与消费汇总 | 07 场景⑦ Step4 |
| POST | `/tenants/{tid}/balance/recharge` | 手动充值 | 07 场景⑦ Step4 |
| GET | `/tenants/{tid}/balance/transactions` | 余额变动流水 | — |

**POST `/tenants/{tid}/balance/recharge` 请求体**：

```json
{
  "amount": 500.00,
  "description": "首次充值"
}
```

**事务处理**（见 09_DATABASE_DESIGN.md §8.6）：
1. `UPDATE tenants SET balance = balance + :amount`
2. `INSERT INTO balance_transactions (type='recharge', amount=:amount, ...)`

### 5.4 租户域名管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/tenants/{tid}/domains` | 域名列表 | 07 场景⑦ Step2 |
| POST | `/tenants/{tid}/domains` | 添加域名 | 07 场景⑦ Step2 |
| POST | `/tenants/{tid}/domains/{did}/verify` | 触发 DNS 验证 | 07 场景⑦ Step2 |
| GET | `/tenants/{tid}/domains/{did}` | 域名详情（含预热状态） | — |

### 5.5 数据源管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/data-sources` | 数据源渠道列表 | 07 场景① |
| GET | `/data-sources/{type}/credentials` | 渠道账号列表（凭证字段脱敏返回） | 07 场景① Step2 |
| POST | `/data-sources/{type}/credentials` | 添加渠道账号（凭证字段 AES-256 加密存储） | 07 场景① Step2 |
| PATCH | `/data-sources/{type}/credentials/{id}` | 更新账号 | — |
| DELETE | `/data-sources/{type}/credentials/{id}` | 删除账号 | — |
| PATCH | `/data-sources/{type}/config` | 更新爬取频率配置 | 07 场景① Step3 |

### 5.6 AI 配置管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/ai-config/models` | 模型列表 | 07 场景⑥ |
| POST | `/ai-config/models` | 注册模型 | 07 场景⑥ Step1 |
| PATCH | `/ai-config/models/{id}` | 更新模型（含价格调整） | 07 场景⑥ Step3 |
| DELETE | `/ai-config/models/{id}` | 停用模型 | — |
| GET | `/ai-config/pricing` | AI 计费参数配置 | 07 场景⑥ |
| PUT | `/ai-config/pricing` | 更新 AI 计费参数 | 07 场景⑥ |
| GET | `/ai-config/scene-defaults` | 各场景默认模型配置 | 07 场景⑥ Step2 |
| PUT | `/ai-config/scene-defaults` | 设置各场景默认模型 | 07 场景⑥ Step2 |

### 5.7 平台评分模板管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/scoring-templates` | 行业默认评分模板列表 | 07 场景② |
| POST | `/scoring-templates` | 创建行业默认模板 | 07 场景② Step1 |
| PUT | `/scoring-templates/{id}` | 更新模板 | 07 场景② Step3 |
| GET | `/scoring-templates/{id}/versions` | 版本历史 | — |

> **注意**：平台评分模板与租户评分模板不同。平台模板用于新租户入驻时的快照复制，存储在独立结构中（应用层管理，不直接对应 `scoring_templates` 表——该表仅存租户副本）。

### 5.8 平台邮件模板管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/email-templates` | 平台官方邮件模板列表 | 07 场景④ |
| POST | `/email-templates` | 创建官方模板 | 07 场景④ Step1 |
| PUT | `/email-templates/{id}` | 更新模板 | — |
| DELETE | `/email-templates/{id}` | 停用模板 | — |
| GET | `/email-templates/{id}/preview` | 预览渲染 | — |

### 5.9 情报源管理

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/intelligence-sources` | 情报源列表 | 07 场景③ |
| POST | `/intelligence-sources` | 创建情报源（平台级，`tenant_id=NULL`） | 07 场景③ Step1 |
| POST | `/intelligence-sources/batch-import` | Excel 批量导入 | 07 场景③ Step2 |
| PATCH | `/intelligence-sources/{id}` | 更新 | — |
| DELETE | `/intelligence-sources/{id}` | 删除 | — |

### 5.10 域名预热规则

| 方法 | 路径 | 说明 | 对应场景 |
|------|------|------|----------|
| GET | `/warmup-rules` | 当前预热规则 | 07 场景⑤ |
| PUT | `/warmup-rules` | 更新预热规则（6档配置） | 07 场景⑤ Step1 |

### 5.11 采集任务监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/collection-tasks` | 采集任务列表（支持按状态、租户筛选） |
| GET | `/collection-tasks/{id}` | 任务详情 |
| POST | `/collection-tasks/{id}/retry` | 重试失败的任务 |

### 5.12 平台统计仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dashboard/overview` | 全平台统计（租户数、总发送量等） |
| GET | `/dashboard/ai-usage` | AI 用量与费用汇总 |
| GET | `/dashboard/collection-stats` | 采集统计 |

---

## 6. Tenant API — 租户业务端

> 路由前缀：`/t/{slug}/api/v1`
> 认证：租户用户 JWT
> DB 连接池：`tenant_pool`（`app_user` 角色，RLS 启用）
> 中间件自动执行 `SET LOCAL app.current_tenant_id = :tenant_id`

### 6.1 认证

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/login` | 登录 | 公开 |
| POST | `/auth/change-password` | 修改密码 | 所有角色 |
| GET | `/auth/me` | 当前用户信息 | 所有角色 |
| POST | `/auth/logout` | 登出（可选，客户端清除 token） | 所有角色 |

### 6.2 公司列表

> 对应 07 场景⑨。查询底层为 `tenant_companies` JOIN `v_tenant_visible_companies`。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/companies` | 公司列表（游标分页 + 多条件筛选） | 全角色 |
| GET | `/companies/{id}` | 公司详情（含评分、联系人、邮件历史） | 全角色 |
| POST | `/companies` | 手动添加公司 | admin, operator |
| POST | `/companies/batch-import` | Excel 批量导入 | admin, operator |
| GET | `/companies/filters` | 筛选器选项（国家/行业/标签枚举） | 全角色 |
| GET | `/companies/export` | 导出 Excel | admin, operator |

**GET `/companies` 查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `cursor` | string | 游标 |
| `limit` | int | 每页条数（默认 20，最大 100） |
| `status` | string | 状态筛选（`pending_score` / `scored` / `selected` 等） |
| `grade` | string | 评级筛选（`S,A,B`，逗号分隔） |
| `country` | string | 国家（多选，逗号分隔） |
| `industry_tags` | string | 行业标签 |
| `product_keywords` | string | 产品关键词（JSONB 包含查询） |
| `source_type` | string | 数据源编码 |
| `has_email` | bool | 是否有联系人邮箱 |
| `search` | string | 公司名模糊搜索 |
| `sort` | string | 排序字段（默认 `created_at`），前缀 `-` 降序 |

### 6.3 优选客户

> 对应 07 场景⑩。优选客户 = 已评分的公司子集（`status IN ('scored','selected','in_plan','contacted','replied','converted')`）。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/prospects` | 优选客户列表（游标分页 + 筛选） | 全角色 |
| GET | `/prospects/{id}` | 优选客户详情（评分明细 + 联系人） | 全角色 |
| PATCH | `/prospects/{id}` | 修改标签/备注 | admin, operator |
| POST | `/prospects/{id}/select` | 标记为"已入选" | admin, operator |
| POST | `/prospects/{id}/exclude` | 排除 | admin, operator |
| POST | `/prospects/{id}/blacklist` | 加入黑名单 | admin, operator |

### 6.4 联系人

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/companies/{cid}/contacts` | 公司下的联系人列表 | 全角色 |
| PATCH | `/companies/{cid}/contacts/{id}/set-default` | 设为默认联系人 | admin, operator |

### 6.5 群组管理

> 对应 07 场景⑩ Step4。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/groups` | 群组列表 | 全角色 |
| POST | `/groups` | 创建群组 | admin, operator |
| GET | `/groups/{id}` | 群组详情（含成员列表） | 全角色 |
| PATCH | `/groups/{id}` | 更新群组（名称/描述/自动规则） | admin, operator |
| DELETE | `/groups/{id}` | 删除群组（软删除） | admin, operator |
| POST | `/groups/{id}/members/batch-add` | 批量添加成员 | admin, operator |
| POST | `/groups/{id}/members/batch-remove` | 批量移除成员 | admin, operator |
| GET | `/groups/{id}/members` | 群组成员列表（分页） | 全角色 |

**POST `/groups/{id}/members/batch-add` 请求体**：

```json
{
  "tenant_contact_ids": ["018f...", "018f..."]
}
```

### 6.6 评分规则

> 对应 07 场景⑧ Step3。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/scoring-templates` | 当前活跃的评分模板 | admin |
| PUT | `/scoring-templates/{id}` | 修改评分规则（自动归档旧版本） | admin |
| GET | `/scoring-templates/{id}/versions` | 版本历史 | admin |
| GET | `/scoring-templates/{id}/versions/{vid}` | 历史版本详情 | admin |

### 6.7 联系人规则

> 对应 07 场景⑧ Step4。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/contact-rules` | 当前活跃的联系人规则 | admin |
| PUT | `/contact-rules/{id}` | 修改联系人规则 | admin |

### 6.8 采集关键词

> 对应 07 场景⑧ Step2。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/keywords` | 关键词列表 | admin |
| POST | `/keywords` | 创建关键词 | admin |
| PATCH | `/keywords/{id}` | 更新关键词 | admin |
| DELETE | `/keywords/{id}` | 删除关键词 | admin |

### 6.9 邮件模板

> 对应 07 场景⑪。租户看到的模板 = 平台官方模板（只读）+ 租户自有模板。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/email-templates` | 模板列表（含平台模板 + 自有模板） | 全角色 |
| GET | `/email-templates/{id}` | 模板详情 | 全角色 |
| POST | `/email-templates` | 创建自有模板 | admin, operator |
| PUT | `/email-templates/{id}` | 更新自有模板 | admin, operator |
| DELETE | `/email-templates/{id}` | 删除自有模板 | admin, operator |
| POST | `/email-templates/{id}/clone` | 从平台模板复制为自有模板 | admin, operator |
| GET | `/email-templates/{id}/preview` | 预览（变量替换） | 全角色 |
| POST | `/email-templates/ai-generate` | AI 生成模板 | admin, operator |

**POST `/email-templates/ai-generate` 请求体**：

```json
{
  "scene": "initial_contact",
  "product_info": "多层PCB板，交期15天，UL认证",
  "tone": "formal_business",
  "model_id": "018f...",
  "count": 3
}
```

**AI 生成流程**：
1. 检查租户 AI 余额（`tenants.balance > 0`）
2. 调用 OpenRouter API
3. 原子扣费（见 09 §8.6）：`UPDATE tenants SET balance = balance - :cost WHERE balance >= :cost`
4. 记录 `ai_usage_logs` + `balance_transactions`
5. 返回生成的 2-3 个模板版本

### 6.10 发送计划

> 对应 07 场景⑫。六步向导的后端支撑。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/sending-plans` | 计划列表 | 全角色 |
| POST | `/sending-plans` | 创建计划（草稿） | admin, operator |
| GET | `/sending-plans/{id}` | 计划详情 | 全角色 |
| PATCH | `/sending-plans/{id}` | 更新计划：`draft` 可全量修改；`running/paused` 仅允许备注和未生效字段的安全更新 | admin, operator |
| DELETE | `/sending-plans/{id}` | 删除计划（仅 draft/cancelled） | admin, operator |

**计划操作**：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/sending-plans/{id}/schedule` | 定时（draft → scheduled） | admin, operator |
| POST | `/sending-plans/{id}/start` | 立即执行（draft/scheduled → running） | admin, operator |
| POST | `/sending-plans/{id}/pause` | 暂停（running → paused） | admin, operator |
| POST | `/sending-plans/{id}/resume` | 恢复（paused → running） | admin, operator |
| POST | `/sending-plans/{id}/cancel` | 取消 | admin, operator |

**收件人管理**：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/sending-plans/{id}/recipients` | 当前有效收件人列表（含启动时快照 + 运行中追加） | 全角色 |
| GET | `/sending-plans/{id}/recipients/preview` | 预览收件人（未锁定，按条件实时计算） | admin, operator |
| POST | `/sending-plans/{id}/recipients/lock` | 锁定启动时收件人快照 | admin, operator |
| POST | `/sending-plans/{id}/recipients/append` | 运行中追加收件人（仅新增，不能回改已发送对象） | admin, operator |

**序列步骤**：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/sending-plans/{id}/steps` | 序列步骤列表 | 全角色 |
| POST | `/sending-plans/{id}/steps` | 添加步骤 | admin, operator |
| PUT | `/sending-plans/{id}/steps/{sid}` | 更新步骤；`running/paused` 仅允许修改尚未执行步骤的模板与延迟 | admin, operator |
| DELETE | `/sending-plans/{id}/steps/{sid}` | 删除步骤 | admin, operator |

**发送预览**：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/sending-plans/{id}/preview` | 计划摘要（收件人数、序列封数、域名） | 全角色 |
| GET | `/sending-plans/{id}/sample-emails` | 随机预览 3-5 封实际邮件内容 | admin, operator |

**POST `/sending-plans` 请求体**（六步向导合并提交）：

```json
{
  "name": "德国 A 级客户首次触达",
  "description": "...",
  "recipient_source": "group",
  "recipient_config": { "group_id": "018f..." },
  "sender_name": "Sales Team",
  "sender_email": "sales@customer.com",
  "domain_id": "018f...",
  "send_strategy": {
    "timezone_aware": true,
    "preferred_hours": [9, 17],
    "interval_minutes": 5
  },
  "steps": [
    {
      "step_number": 1,
      "template_id": "018f...",
      "delay_days": 0,
      "condition_type": "always",
      "use_ai_personalization": false
    },
    {
      "step_number": 2,
      "template_id": "018f...",
      "delay_days": 4,
      "condition_type": "no_reply"
    }
  ]
}
```

**运行中编辑约束**：
1. 与 `07_REQUIREMENTS_SPEC.md` 保持一致，执行中计划允许两类有限变更：追加收件人、修改未来序列模板。
2. 已发送邮件、已触发步骤、发送策略、发送域名均不可在 `running/paused` 状态下回改。
3. `PATCH /sending-plans/{id}`、`PUT /steps/{sid}`、`POST /recipients/append` 的实现必须校验“仅作用于未来未执行对象”。

### 6.11 邮件监控

> 对应 07 场景⑬。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/emails` | 邮件列表（分页 + 多维筛选） | 全角色 |
| GET | `/emails/{id}` | 邮件详情（含事件时间线） | 全角色 |
| GET | `/emails/stats` | 邮件统计（送达率、打开率等） | 全角色 |
| GET | `/emails/stats/by-plan` | 按计划维度统计 | 全角色 |
| GET | `/emails/stats/by-template` | 按模板维度统计 | 全角色 |
| GET | `/emails/stats/by-grade` | 按评级维度统计 | 全角色 |
| GET | `/emails/stats/by-step` | 按序列步骤维度统计 | 全角色 |
| GET | `/emails/stats/trend` | 时间趋势（按日/周/月） | 全角色 |
| POST | `/emails/ai-analysis` | AI 分析建议 | admin, operator |

**GET `/emails` 查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `plan_id` | UUID | 按计划筛选 |
| `status` | string | 邮件状态（逗号分隔） |
| `grade` | string | 收件人评级 |
| `country` | string | 收件人国家 |
| `template_id` | UUID | 按模板筛选 |
| `step_number` | int | 按序列步骤筛选 |
| `date_from` | date | 时间范围起始 |
| `date_to` | date | 时间范围结束 |

### 6.12 情报中心

> 对应 07 场景③ 的租户侧视图。底层查 `v_tenant_articles`。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/intelligence/articles` | 情报文章列表 | 全角色 |
| GET | `/intelligence/articles/{id}` | 文章详情 | 全角色 |
| POST | `/intelligence/articles/{id}/read` | 标记已读 | 全角色 |
| POST | `/intelligence/articles/{id}/star` | 收藏/取消收藏 | 全角色 |
| POST | `/intelligence/articles/{id}/archive` | 归档 | 全角色 |
| GET | `/intelligence/subscriptions` | 当前用户的订阅配置 | 全角色 |
| PUT | `/intelligence/subscriptions` | 更新订阅配置 | 全角色 |

### 6.13 域名预热状态

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/domains` | 租户域名列表（含预热进度） | admin |
| GET | `/domains/{id}` | 域名详情（含历史趋势） | admin |
| GET | `/domains/{id}/history` | 预热历史快照 | admin |

### 6.14 AI 余额

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/ai-capabilities` | 当前用户的 AI 功能可用性快照（不返回具体余额） | 全角色 |
| GET | `/billing/balance` | 当前余额 | admin |
| GET | `/billing/transactions` | 余额变动流水（分页） | admin |
| GET | `/billing/usage-summary` | 按功能分类的消费汇总 | admin |
| GET | `/billing/usage-trend` | 消费趋势（按日/周/月） | admin |

### 6.15 团队管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/team/users` | 团队成员列表 | admin |
| POST | `/team/users` | 创建用户 | admin |
| PATCH | `/team/users/{id}` | 更新用户（角色/状态，不可提升至 admin） | admin |
| DELETE | `/team/users/{id}` | 禁用用户 | admin |

### 6.16 通知

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/notifications` | 通知列表（默认最近 20 条） | 全角色 |
| POST | `/notifications/mark-read` | 批量标记已读 | 全角色 |
| GET | `/notifications/unread-count` | 未读数量 | 全角色 |

### 6.17 仪表盘

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/dashboard/overview` | 概览数据（公司数、邮件数、回复率等） | 全角色 |
| GET | `/dashboard/funnel` | 漏斗数据（公司→评分→选择→发送→回复） | 全角色 |

### 6.18 黑名单管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/blacklist` | 黑名单列表 | admin, operator |
| POST | `/blacklist` | 添加黑名单规则 | admin, operator |
| DELETE | `/blacklist/{id}` | 移除黑名单 | admin, operator |

### 6.19 竞品公司

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/competitors` | 竞品公司列表 | admin, operator |
| POST | `/competitors` | 添加竞品公司 | admin, operator |
| DELETE | `/competitors/{id}` | 移除竞品 | admin, operator |

---

## 7. Internal API — 采集服务

> 路由前缀：`/internal/api/v1`
> 认证：按服务签发的短期签名令牌（推荐 mTLS + `Authorization: Bearer <service-token>`），不暴露公网
> DB 连接池：`service_pool`（按服务拆分最小权限角色；仅受控端点可绕过 RLS）
> 部署：独立服务器（见 07 §0.4），通过 API 调用与主系统通信

### 7.1 采集服务 → 主系统

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/collection/companies/batch-upsert` | 批量写入/更新共享公司池（单次最大 500 条） |
| POST | `/collection/contacts/batch-upsert` | 批量写入/更新共享联系人池（单次最大 500 条） |
| POST | `/collection/competitors/batch-upsert` | 批量写入竞品公司（单次最大 500 条） |
| PATCH | `/collection/tasks/{id}/status` | 更新采集任务状态 |
| POST | `/collection/tasks/{id}/result` | 提交采集任务结果统计 |
| POST | `/collection/tasks/{id}/heartbeat` | 续租当前任务 lease |

**POST `/collection/companies/batch-upsert` 请求体**：

```json
{
  "companies": [
    {
      "source_type": "waimao_tong",
      "source_id": "WT-12345",
      "name": "Acme Electronics GmbH",
      "name_en": "Acme Electronics GmbH",
      "country": "DE",
      "website": "https://acme-electronics.de",
      "industry": "Electronics",
      "employee_count": "51-200",
      "raw_data": { "...原始数据..." }
    }
  ],
  "task_id": "018f...",
  "keyword_ids": ["018f...", "018f..."]
}
```

**处理逻辑**：
1. 去重：按 `(source_type, source_id)` 查 `company_sources`
2. 已存在 → 合并更新 `shared_companies`
3. 不存在 → 创建 `shared_companies` + `company_sources`
4. 主系统根据 `task_id/keyword_ids` 回查本地任务与关键词归属，重新解析允许关联的 `tenant_ids`
5. 为每个解析出的 `tenant_id` 创建 `tenant_companies`（排除黑名单和竞品）
6. 调用方必须携带对应 `lease_id` / `X-Request-Id`；主系统只接受当前有效 lease 对应的结果回写

**POST `/collection/contacts/batch-upsert` 请求体**：

```json
{
  "task_id": "018f...",
  "contacts": [
    {
      "source_type": "waimao_tong",
      "source_contact_id": "WT-C-123",
      "company_source_type": "waimao_tong",
      "company_source_id": "WT-12345",
      "name": "John Smith",
      "email": "john@example.com",
      "title": "Purchasing Manager",
      "department": "Procurement",
      "phone": "+49-...",
      "linkedin_url": "https://linkedin.com/in/...",
      "raw_data": {}
    }
  ]
}
```

主系统必须先通过 `(company_source_type, company_source_id)` 解析到 `company_sources` / `shared_companies`，再创建 `shared_contacts` 与 `tenant_contacts`。

### 7.2 主系统 → 采集服务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/collection/tasks` | 创建采集任务 |
| POST | `/collection/tasks/claim` | 原子领取待执行任务（返回 lease） |
| GET | `/collection/credentials/{source_type}` | 获取可用的数据源凭证 |

**POST `/collection/tasks/claim` 请求体**：

```json
{
  "service_instance": "collection-sh-01",
  "limit": 10,
  "lease_seconds": 300,
  "supported_sources": ["waimao_tong", "tengdao", "lixiaoyun"]
}
```

**返回体**：

```json
{
  "lease_id": "lease-018f...",
  "lease_expires_at": "2026-04-17T05:00:00Z",
  "tasks": [
    {
      "id": "018f...",
      "normalized_keyword": "multilayer pcb",
      "display_keyword": "multilayer PCB",
      "source_type": "waimao_tong",
      "keyword_ids": ["018f...", "018f..."],
      "priority": 5
    }
  ]
}
```

**claim / lease 规则**：
1. `claim` 必须在单事务内完成“筛选 pending 任务 + 标记 running + 写入 lease_owner / lease_expires_at”。
2. 只有持有当前有效 `lease_id` 的服务实例可以调用 `/status`、`/result`、`/heartbeat`。
3. `heartbeat` 只能延长未过期 lease，建议每 60 秒续租一次，每次续租 300 秒。
4. 若 `lease_expires_at < NOW()`，任务可被其他实例重新 claim；旧实例后续回写必须返回 `409 lease_expired`。
5. `/result` 成功提交后，主系统在同一事务内落结果并将任务状态终结为 `completed` / `failed`，同时清空 lease。

**POST `/collection/tasks/{id}/heartbeat` 请求体**：

```json
{
  "lease_id": "lease-018f...",
  "service_instance": "collection-sh-01",
  "extend_seconds": 300
}
```

**POST `/collection/tasks/{id}/result` 请求体**：

```json
{
  "lease_id": "lease-018f...",
  "service_instance": "collection-sh-01",
  "status": "completed",
  "total_found": 123,
  "new_companies": 45,
  "duplicate_count": 78,
  "error_message": null
}
```

### 7.3 评分服务内部端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/scoring/trigger` | 触发 T+1 评分计算 |
| GET | `/scoring/pending` | 获取待评分公司列表（按租户） |
| POST | `/scoring/results/batch` | 批量写入评分结果 |

> `scoring-service` 只能访问评分域端点；不得复用采集服务身份调用 `/collection/*`。

### 7.4 邮件发送服务内部端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sending/due-emails` | 获取到期待发送的邮件 |
| PATCH | `/sending/emails/{id}/status` | 更新邮件发送状态 |
| GET | `/sending/domains/{id}/quota` | 查询域名剩余配额 |

> `sending-service` 只处理发送链路，不允许直接写 `tenant_companies`、`collection_tasks` 等跨域资源。

---

## 8. Webhook 接收端点

> 路由前缀：`/webhooks`
> 认证：签名验证（provider-specific）
> 数据库写入：使用 webhook 专用服务身份；仅当前事务内需要的受控更新可绕过 RLS

### 8.1 EngageLab 邮件事件回调

```
POST /webhooks/engagelab
```

**请求体**（EngageLab 推送格式）：

```json
{
  "event_id": "EVT-987654",
  "event": "delivered",
  "message_id": "EL-123456",
  "email": "buyer@example.com",
  "timestamp": 1745000000,
  "metadata": { "ip": "1.2.3.4", "user_agent": "..." }
}
```

**处理流程**（见 09_DATABASE_DESIGN.md §6.7 事务边界说明）：

```python
async def handle_engagelab_webhook(payload):
    # 1. 签名验证
    verify_engagelab_signature(payload)

    # 1.5 时间戳校验（防重放攻击）
    event_time = payload.get("timestamp", 0)
    if abs(time.time() - event_time) > 300:  # 5分钟容差
        return Response(400, "Timestamp out of tolerance")

    # 2. 幂等检查（按 provider_event_id 去重，优先查 Redis 缓存）
    provider_event_id = payload["event_id"]
    cache_key = f"webhook:{provider_event_id}"
    if await redis.get(cache_key):
        return Response(200)  # 缓存命中，跳过 DB 查询
    if await event_exists(provider_event_id):
        await redis.set(cache_key, "1", ex=86400)  # 回填缓存
        return Response(200)  # 已处理，直接返回

    # 3. 单事务内完成所有更新
    async with service_pool.acquire() as conn:
        async with conn.transaction():
            # a. 查找邮件记录
            email = await find_email_by_engagelab_id(conn, payload["message_id"])

            # b. INSERT email_events（UNIQUE(provider_event_id)）
            await insert_email_event(conn, email, payload)

            # c. UPDATE emails.status
            await update_email_status(conn, email.id, payload["event"])

            # d. UPDATE sequence_enrollments（如适用）
            if payload["event"] in ("replied", "bounced", "unsubscribed"):
                await update_enrollment_status(conn, email.enrollment_id, payload["event"])

            # e. UPDATE tenant_contacts（如适用）
            if payload["event"] in ("replied", "bounced", "unsubscribed"):
                await update_contact_status(conn, email.tenant_contact_id, payload["event"])

    return Response(200)
```

---

## 9. 限流与安全策略

### 9.1 限流配置

| 端点类别 | 限制 | 说明 |
|----------|------|------|
| Tenant API — 读取 | 100 req/min/user | 常规浏览 |
| Tenant API — 写入 | 30 req/min/user | 创建/更新操作 |
| Tenant API — AI 调用 | 10 req/min/user | AI 生成/分析 |
| Admin API | 60 req/min/user | 平台管理操作 |
| Internal API | 1000 req/min/service | 服务间调用（高吞吐） |
| Webhook | 不限流（但单 IP 上限 500 req/min 防 DoS） | EngageLab 回调需及时处理 |
| 登录 | 5 req/min/IP | 暴力破解防护 |

### 9.2 限流实现

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_user_id_from_jwt)

@router.get("/companies")
@limiter.limit("100/minute")
async def list_companies(request):
    ...
```

限流 header 返回：

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1745000060
```

### 9.3 安全措施

| 措施 | 说明 |
|------|------|
| HTTPS | 全站强制 HTTPS（Nginx 层） |
| SQL 注入 | 全部参数化查询（SQLAlchemy + asyncpg） |
| XSS | 邮件 body_html 存储前 HTML sanitize（见 09 §6.6） |
| CSRF | 无（API-only，JWT Bearer 认证，无 cookie session） |
| 请求体大小 | 默认 1MB，批量导入端点 10MB |
| 超时 | API 请求 30s 超时，AI 调用 120s 超时 |
| 日志 | 全部请求记录 request_id / user_id / tenant_id / duration |

---

## 10. CORS 配置

> 现有系统 `allow_origins=["*"]`（见 02_API_REFERENCE.md §13），需收紧。

```python
from fastapi.middleware.cors import CORSMiddleware

# Phase 1 配置
ALLOWED_ORIGINS = [
    "https://admin.example.com",     # Admin 前端
    "https://*.example.com",         # Tenant 前端（通配子域名）
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
```

---

## 11. 现有 API 迁移映射

> 02_API_REFERENCE.md 中 13 个模块到新 API 的映射。

| 现有端点 | 新端点 | 说明 |
|----------|--------|------|
| `POST /api/auth/login` | `POST /t/{slug}/api/v1/auth/login` | 增加 slug 定位租户 |
| `GET /api/plans` | **废弃** | 旧 plan = 采集+评分+发送。新系统拆分为独立资源 |
| `POST /api/plans` | **废弃** | 发送计划 → `POST /t/{slug}/api/v1/sending-plans` |
| `POST /api/plans/{id}/trigger/{flow}` | **废弃** | 采集/评分由后台任务自动执行，发送由计划状态机驱动 |
| `GET /api/dashboard/*` | `GET /t/{slug}/api/v1/dashboard/*` | 增加租户隔离 |
| `GET /api/keywords` | `GET /t/{slug}/api/v1/keywords` | 增加租户隔离 |
| `GET /api/companies` | `GET /t/{slug}/api/v1/companies` | 改为查 tenant_companies + 共享池视图 |
| `GET /api/contacts` | `GET /t/{slug}/api/v1/companies/{cid}/contacts` | 嵌套在公司下 |
| `GET /api/drafts` | **废弃** | 邮件草稿概念不再存在；邮件状态由 `emails.status` 管理 |
| `POST /api/drafts/{id}/rewrite` | `POST /t/{slug}/api/v1/email-templates/ai-generate` | AI 生成移到模板层 |
| `GET /api/templates` | `GET /t/{slug}/api/v1/email-templates` | 增加平台模板 + 租户模板双层 |
| `GET /api/product-config` | `GET /t/{slug}/api/v1/scoring-templates` | 评分规则改为租户级 |
| `GET /api/task-runs` | `GET /admin/api/v1/collection-tasks` | 移到 Admin API |
| `GET /api/company-assets` | **废弃** | 原始公司数据 → `shared_companies`（Admin 内部） |
| `GET /health` | `GET /health` | 保持不变 |
| `GET /metrics` | `GET /metrics` | 保持不变 |

---

## 附录

### A. 完整端点汇总

**Admin API**：约 51 个端点（§5）
**Tenant API**：约 101 个端点（§6）
**Internal API**：约 14 个端点（§7）
**Webhook**：1 个端点（§8）

**总计**：约 167 个端点

### B. 请求 ID 追踪

每个请求自动生成 `X-Request-ID`（UUID v4），贯穿日志链路：

```python
@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### C. 健康检查端点

```
GET /health          → { "status": "ok", "db": "connected", "version": "1.0.0" }
GET /health/ready    → 就绪探针（DB + Redis 连通性）
GET /health/live     → 存活探针（进程存活即可）
```
