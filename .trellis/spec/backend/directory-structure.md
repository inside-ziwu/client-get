# 后端目录结构与分层

> 事实来源：`backend/app/` 实际目录（2026-08 核对）、`app/main.py` 路由挂载与 lifespan。

## 目录布局

```
backend/
├── app/
│   ├── main.py            create_app()：中间件、异常处理器、四个路由组；lifespan 做分区维护 + 客户池修复循环
│   ├── api/               路由层：admin/ tenant/ internal/ webhooks/，每个目录一个 router.py 聚合子路由
│   ├── services/          业务逻辑 + 手写 SQL（*_service.py，一个领域一个类；共享 SQL 片段单独成模块）
│   ├── schemas/           Pydantic 请求 / 响应模型（admin_config.py、tenants.py、auth.py、tenant_settings.py…）
│   ├── security/          JWT（platform / tenant / service 三种 kind）、bcrypt、鉴权依赖
│   ├── db/                pools.py（engine + get_connection）、rls.py、transaction.py、partitions.py
│   ├── core/              config.py（Settings）、errors.py、responses.py、logging.py、request_context.py、crypto.py、ids.py
│   ├── workers/           sending.py / reconciliation.py / wmt_lineage_repair.py
│   ├── integrations/      engagelab.py、openrouter.py（外部 HTTP 客户端，httpx）
│   ├── utils/             beijing_time.py、html_sanitizer.py、country.py、email_text.py
│   └── data/              静态数据（国家、节假日表）
├── alembic/               迁移链（命名 YYYYMMDD_NNNN_描述.py）
├── 03_database/           schema.sql（蓝图）、schema_snapshot.json（结构契约）、schema_docs.json、schema_notes.md
├── scripts/               运维脚本（run_sending_worker.py、maintain_partitions.py、schema_snapshot.py、init_instance.py…）
└── tests/                 pytest，全 mock 为主（见 quality-guidelines.md）
```

## 分层规则

api（路由 / 参数 / 权限）→ services（业务逻辑 + SQL，`AsyncConnection`）→ db（连接池）。

- **route 不写业务逻辑**：只做依赖注入、参数转换、调用 service、包装响应。参照 `app/api/tenant/core.py`——每个端点两三行：取 `context.connection` 与 `context.tenant_id`，调 `TenantQueryService` 方法，`success_response(data)`。
- **SQL 只出现在 services**（以及 alembic / scripts）：`sqlalchemy.text()` + 命名参数，`result.mappings()` 取行。没有 ORM 实体层，不要引入。
- service 是无状态类，方法第一个参数是 `conn: AsyncConnection`，由路由层从鉴权上下文传入。跨领域复用的 SQL 片段放独立模块（`services/company_filter_sql.py`、`services/tenant_contact_utils.py`）。
- 路由文件顶部模块级单例 `service = XxxService()`；需要替身的类用构造参数注入（参照 `SendingWorker.__init__` 的 `service / provider / clock / sleep` 注入）。

## 路由组与鉴权（`app/main.py`）

| 前缀 | 目录 | 鉴权依赖 | 上下文对象 |
|---|---|---|---|
| `/admin/api/v1` | `api/admin/` | `get_current_platform_user`（kind=platform，校验 `iid`，查 `platform_users` 带 `instance_id`） | `PlatformAuthContext(platform_user_id, email, name, roles, connection)` |
| `/t/{slug}/api/v1` | `api/tenant/` | `get_current_tenant_user`（kind=tenant，校验 `iid`、`slug` 与 URL 一致、角色与 DB 实时比对）；`require_tenant_roles("admin", "operator")` 限制角色 | `TenantAuthContext(tenant_id, tenant_slug, user_id, roles, must_change_pwd, connection)` |
| `/internal/api/v1` | `api/internal/` | `require_service_scopes("<scope>")`（kind=service，`X-Service-Name` 头必须与令牌一致） | `ServiceAuthContext(subject, service_name, scopes)` |
| `/webhooks` | `api/webhooks/` | 签名校验（`engagelab.py::_verify_signature`，MD5 / HMAC 双算法） | — |

- 租户鉴权成功后 `set_current_tenant(conn, tenant_id)` 写会话变量 `app.current_tenant_id`——这只是 RLS 的名义配合，**隔离靠 service 层 SQL 显式过滤**（见 database-guidelines.md）。
- `/health` 与 `/` 为探活端点（Sealos 周期性请求根路径），每个路由组另有自己的 `/health`。
- 新增子路由：在对应目录的 `router.py` 用 `include_router` 聚合，不在 `main.py` 散挂。

## 一次请求的生命周期

`RequestContextMiddleware` 生成 / 透传 `X-Request-Id` → 鉴权依赖通过 `get_connection()` 取连接（`engine.begin()`：**一请求一事务**，正常返回自动提交，异常自动回滚）→ 路由调用 service → `success_response` / `paginated_response` 包装 → 异常统一由 `core/errors.py` 的处理器转成 JSON。

## worker 形态

- `sending`：独立进程 `scripts/run_sending_worker.py`（常驻循环；`--once` 单轮验证），内含约每 10 分钟一轮的 `ReconciliationWorker` 对账；生产用同一 backend 镜像起独立容器。
- `wmt_lineage_repair`：在 API 进程 lifespan 内常驻（`WMT_LINEAGE_REPAIR_ENABLED`，300 秒 / 轮），用带 `instance_id` 的 advisory lock 防并发。
- 形态选择与必备模式见 [workers.md](./workers.md)。

## 命名

- Python 一律 snake_case；服务类 `XxxService`，文件 `xxx_service.py`；测试 `tests/test_<主题>.py`。
- 迁移文件 `YYYYMMDD_NNNN_描述.py`，docstring 首段写目的、考证与拍板依据。
- 注释、docstring、提交信息、文档一律中文。

## 常见错误

- 把查询或状态推进写进路由函数——route 应只有胶水代码。
- 在 service 里 `raise HTTPException`——应抛 `AppError`（见 error-handling.md）。
- 新增静态路由放在 `/{id}` 动态路由之后被吞（见 api-guidelines.md）。
