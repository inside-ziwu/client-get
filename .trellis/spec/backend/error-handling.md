# 错误处理

> 事实来源：`app/core/errors.py`、`app/main.py` 异常处理器注册、`app/security/*.py`、`app/services/intelligence_service.py` 等。

## 错误模型

- 业务错误一律抛 `AppError(code=..., message=..., status_code=..., details=...)`；`code` 用大写蛇形常量（`NOT_FOUND`、`VALIDATION_ERROR`、`UNAUTHORIZED`、`FORBIDDEN`、`INSUFFICIENT_BALANCE`、`OPENROUTER_NOT_CONFIGURED` …），`message` 是面向用户的中文句子。
- 子类表达特定语义：`CredentialExpiredError`（503，凭证过期）。新增子类只在需要被 `except` 精确捕获时才做。
- 处理器链（`create_app`）：`AppError` → 按 code / status 输出；`HTTPException` → `HTTP_ERROR`；`RequestValidationError` → `422 VALIDATION_ERROR` + 逐字段 `details`；其余 `Exception` → `500 INTERNAL_SERVER_ERROR`（`details` 里带 `str(exc)`，因此异常文本不得携带凭证）。
- 响应体固定 `{"error": {"code", "message", "details", "request_id"}}`，`request_id` 来自 `X-Request-Id`。

## 分层职责

- **service 抛 `AppError`**，不 `raise HTTPException`，不返回 `None` 让上层猜。
- **route 不 try / except** 包装业务异常，交给全局处理器。
- 鉴权依赖抛 `UNAUTHORIZED`（401：缺 / 无效令牌、用户禁用）或 `FORBIDDEN`（403：kind / iid / slug / 角色不符）。
- 租户不可见的资源返回 `NOT_FOUND`（404），消息形如"文章不存在或未发布给当前租户"，不暴露存在性。
- 可预期的外部依赖失败转成带 code 的 `AppError`，调用方按 code 集合分支（参照 `intelligence_service.publish_article` 对 `OPENROUTER_*` / `INSUFFICIENT_BALANCE` 的白名单处理：命中则降级，其他继续抛）。

## 外部服务与 worker

- 集成层抛自定义异常（`EngageLabSendError`、`OpenRouterError`）并携带 `status_code`，由 worker 做分类与熔断（见 workers.md）。
- 循环型任务对单条失败 `logger.exception("<任务>: <定位键>=%s 失败", key)` 后继续，不让整轮或进程崩溃；整轮失败在循环层兜底。
- AI 调用配 `AiUsageLogService.create_pending → complete / fail`，失败路径必须调 `fail()` 记录 `error_code`。

## 常见错误

- 吞异常：`except Exception: pass` 或只 `logger.info`——必须 `logger.exception` 保留堆栈。
- 在 service 里捕获 `AppError` 再抛新的通用错误，丢失原 code。
- 把数据库约束错误（`IntegrityError`）直接透传为 500——可预期的冲突应先查询或用 `ON CONFLICT`。
