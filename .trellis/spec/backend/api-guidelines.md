# API 约定

> 事实来源：`app/core/responses.py`、`app/core/errors.py`、`app/schemas/`、`app/api/admin/config.py`（16 个端点已全量 Pydantic 化，#94）、`frontend/packages/shared-types/src/api.ts`。

## 收参：一律 Pydantic model

- 请求体用 `app/schemas/` 下的 `BaseModel` 子类，字段带 `Field(..., description=…)`；**禁止 `payload: dict` 裸收参**。存量裸 dict 端点（主要在 tenant 侧与 internal 侧）在被修改时顺手改造，逐步向 OpenAPI 契约生成过渡。
- 创建用 `payload.model_dump()`；局部更新（PATCH）用 `payload.model_dump(exclude_unset=True)`，service 只更新出现的键。参照 `IntelligenceSourceCreate` / `IntelligenceSourceUpdate` 与 `admin/config.py` 中的用法。
- 枚举取值用 `Literal[...]`，与数据库 CHECK 约束一致（例：`source_type: Literal["rss", "website", "manual"]`）。
- 查询参数用 `Query(...)`；日期字符串在 route 层解析成 `date` / `datetime` 再交给 service（参照 `api/tenant/core.py::dashboard_email_stats`）。

## 响应包装

- 单对象：`success_response(data)` → `{"data": …}`。
- 列表：`paginated_response(items, cursor=…, has_more=…, total=…)` → `{"data": [...], "pagination": {"cursor", "has_more", "total"}}`。
- 错误：由 `core/errors.py` 统一产出 `{"error": {"code", "message", "details": [{"field", "message"}], "request_id"}}`；参数校验失败固定 `422 VALIDATION_ERROR`。
- 序列化在 service 层完成：时间 `.isoformat()`，UUID 转 `str`，Decimal 转 `float`，JSON 列原样透传。

## 路由顺序

**静态路由必须放在动态 `/{id}` 路由之前**，否则被动态段吞掉。参照 `admin/config.py`：`POST /intelligence-sources/batch-import` 定义在 `PATCH /intelligence-sources/{source_id}` 之前。

## 与前端的契约同步

前端类型是手写的（`frontend/packages/shared-types`），没有编译期契约保证（已知漂移实例 #51）。因此：

- 修改任何响应结构、新增字段、改枚举取值 → **同一 PR** 内同步 `shared-types/src/models.ts`（领域模型）/ `api.ts`（`ApiResponse` / `PaginatedResponse` / 筛选参数）和 `shared-api/src/{admin,tenant}/<feature>.ts`（调用函数与返回泛型）。
- `shared-api` 的函数形如 `client.get<PaginatedResponse<T>>('/api/v1/...')`；前缀 `/admin` 或 `/t/{slug}` 由客户端拦截器拼接，**调用方路径不带前缀**。
- 前端契约细则见 [../frontend/type-safety.md](../frontend/type-safety.md)。

## internal 与 webhook 端点

- internal 端点供 worker / 外部服务回写，用 `require_service_scopes("sending:write")` 之类的 scope 保护；调用方同时带 Bearer 服务令牌与 `X-Service-Name`。
- 回写端点必须幂等：闸门放**只有该链路自己写的表**（`email_send_locks` 条件更新 + `RETURNING`），不放多写入方共享的 `emails.status`（webhook 与对账都会推进它）。重复回调返回 `{"duplicate": true}` 并跳过全部副作用。
- webhook 入口先验签（`api/webhooks/engagelab.py`），原文不得落日志。

## 常见错误

- 直接返回 `row` 映射而不经 service 序列化——字段名和类型会漂。
- JOIN 查询里别名与另一张表列同名，`.mappings()` 静默取后者（见 database-guidelines.md）。
- 改了后端字段却没改 `shared-types`：前端编译不报错，运行时取到 `undefined`。
