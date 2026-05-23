---
title: Refresh Token 静默刷新认证
type: feature
status: active
date: 2026-05-23
origin: openspec/changes/refresh-token-auth/
execution_posture: tdd
---

# Refresh Token 静默刷新认证

## Summary

后端更新镜像后 admin 端用户被强制登出。根因：access_token 24h 过期 + session cookie 无 maxAge + 前端 401 直接 logout。方案：新增 refresh_token（7 天有效期，httpOnly cookie），前端 401 拦截器先尝试刷新再 logout。TDD 驱动，每个实施单元 2-5 分钟。

---

## Problem Frame

当前认证流程纯无状态 JWT，access_token 24h 有效期。前端收到 401 直接 `logout()` 跳转登录页，无重试。admin_auth_token cookie 无 maxAge（session cookie），浏览器关闭即失效。后端容器重启本身不影响 JWT 验证（JWT_SECRET 稳定），但 24h 过期窗口 + session cookie 导致用户频繁被登出。

---

## Requirements

- R1. login 成功后同时签发 access_token（body）和 refresh_token（httpOnly cookie，7 天）
- R2. `POST /admin/api/v1/auth/refresh` 端点：验证 refresh_token cookie → 签发新 access_token
- R3. `POST /admin/api/v1/auth/logout` 端点：清除 refresh_token cookie
- R4. 前端 401 拦截器：先调 refresh → 成功则重放请求 → refresh 也失败才 logout
- R5. 并发 401 只发一次 refresh，其他请求排队等待
- R6. refresh URL 自身 401 不触发循环
- R7. 网络错误时不 logout，让错误正常传播
- R8. admin_auth_token cookie 加 maxAge: 86400
- R9. admin logout 流程调用后端 logout 端点清除 refresh cookie

来源：`openspec/changes/refresh-token-auth/specs/refresh-token/spec.md`

---

## Scope Boundary

**包含：** admin 端 refresh token 完整链路（签发、刷新、登出、前端拦截器）
**不包含：** tenant 端（后续复用）、token rotation、token 黑名单、数据库 schema 变更

---

## Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| D1 refresh token 存储 | 纯 JWT，不存数据库 | 当前系统无状态，admin 用户量极小 |
| D2 withCredentials | 全局加在 `axios.create()` | 一处修改，跨域 cookie 自动发送 |
| D3 login 响应类型 | 局部用 JSONResponse | `success_response()` 返回 dict 无法 set_cookie |
| D4 cookie Path | `/admin/api/v1/auth` | 必须是实际端点 URL 的前缀 |
| D5 refresh 后同步 cookie | 调用 `/api/auth/set-token` | 保持 Next.js middleware SSR 路由保护 |
| D6 无限循环防护 | 拦截器排除 refresh URL | refresh 自身 401 直接 logout |
| D7 网络错误处理 | 不 logout，传播错误 | 后端部署期间不踢用户 |
| D8 cookie 环境切换 | `app_env` 动态判断 | 本地 Secure=false 无 Domain；生产 Secure=true Domain=.xinanpcb.com |

来源：`openspec/changes/refresh-token-auth/design.md`

---

## Existing Patterns

- JWT 签发/解码：`backend/app/security/jwt.py` — `create_access_token()` / `decode_access_token()` 模式
- 配置项：`backend/app/core/config.py` — `Field(default=..., alias="ENV_VAR")` 模式
- 路由结构：`backend/app/api/admin/auth.py` — `router = APIRouter(prefix="/auth")`
- 错误抛出：`AppError(code="UNAUTHORIZED", message="...", status_code=401)`
- 前端状态：`frontend/packages/shared-hooks/src/useAuth.ts` — Zustand + localStorage persist
- 前端 cookie 同步：`frontend/apps/admin/src/app/api/auth/set-token/route.ts`
- 前端登出：`frontend/apps/admin/src/components/layout/app-shell.tsx` — `handleLogout()`

---

## Implementation Units

### IU-1: 后端配置 + refresh token JWT 函数（TDD）

**文件：**
- `backend/app/core/config.py`（改）
- `backend/app/security/jwt.py`（改）
- `backend/tests/conftest.py`（新）
- `backend/tests/test_jwt.py`（新）

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 3min | 红 | 创建 `backend/tests/conftest.py`：设置测试环境变量 fixture。创建 `backend/tests/test_jwt.py`：编写 `test_create_refresh_token_contains_type_refresh` — 调用 `create_refresh_token({"sub": "u1", "kind": "platform"})`，断言返回的 JWT 解码后包含 `type: "refresh"` 和正确的 `sub`/`kind` |
| 2 | 3min | 绿 | `config.py` 新增 `refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")`。`jwt.py` 新增 `create_refresh_token(claims)` — 复制 `create_access_token` 结构，改 timedelta 为 days，payload 加 `"type": "refresh"` |
| 3 | 3min | 红 | `test_jwt.py` 新增 `test_decode_refresh_token_success` — 创建 refresh token 后调用 `decode_refresh_token()` 验证返回 claims。新增 `test_decode_refresh_token_rejects_access_token` — 用 `create_access_token` 创建的 token 调用 `decode_refresh_token` 应抛 AppError |
| 4 | 3min | 绿 | `jwt.py` 新增 `decode_refresh_token(token)` — 解码后校验 `payload.get("type") == "refresh"`，否则抛 `AppError(code="UNAUTHORIZED", ...)` |
| 5 | 2min | 红→绿 | `test_jwt.py` 新增 `test_decode_refresh_token_rejects_expired` — 用 freezegun 或手动设置过期时间验证过期 token 抛 AppError |
| 6 | 2min | 重构 | 运行 `python -m pytest backend/tests/test_jwt.py -v`，确认全部通过。审视代码，提取 cookie 配置常量如有必要 |

**测试场景：**
- `create_refresh_token` 签发包含 `type: "refresh"` 的 JWT
- `decode_refresh_token` 正常解码有效 token
- `decode_refresh_token` 拒绝 access token（无 `type: "refresh"`）
- `decode_refresh_token` 拒绝过期 token

**依赖：** 无

---

### IU-2: 后端 login 端点改造（TDD）

**文件：**
- `backend/app/services/auth_service.py`（改）
- `backend/app/api/admin/auth.py`（改）
- `backend/tests/test_auth_login.py`（新）

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 3min | 红 | 创建 `backend/tests/test_auth_login.py`：编写 `test_platform_login_returns_both_tokens` — mock 数据库查询返回有效用户，调用 `platform_login()`，断言返回 `tuple[str, str]`（access_token, refresh_token） |
| 2 | 3min | 绿 | `auth_service.py` 的 `platform_login` 返回值改为 `tuple[str, str]`：同时调用 `create_access_token` 和 `create_refresh_token`，返回 `(access_token, refresh_token)` |
| 3 | 4min | 红→绿 | `test_auth_login.py` 新增 `test_login_route_sets_refresh_cookie` — 用 httpx AsyncClient 调用 `/admin/api/v1/auth/login`，断言响应包含 `Set-Cookie: refresh_token=...` 且 body 包含 `access_token`。`auth.py` 的 `login` 路由改为：解构 `access_token, refresh_token = await service.platform_login(...)`，构造 `JSONResponse(content={"data": {"access_token": access_token}})`，调用 `response.set_cookie(...)` 设置 refresh_token |
| 4 | 3min | 绿 | 实现 cookie 属性的环境动态切换：读 `settings.app_env`，生产环境 `Secure=True, Domain=".xinanpcb.com"`，本地 `Secure=False` 无 Domain |
| 5 | 2min | 重构 | 提取 `_set_refresh_cookie(response, token)` 辅助函数（供 login 和后续 refresh 端点复用） |

**测试场景：**
- `platform_login` 返回 `(access_token, refresh_token)` 二元组
- login 路由 body 包含 `access_token`
- login 路由响应包含 `Set-Cookie: refresh_token` header
- cookie 属性正确（HttpOnly, Path, Max-Age）

**依赖：** IU-1

---

### IU-3: 后端 refresh + logout 端点（TDD）

**文件：**
- `backend/app/api/admin/auth.py`（改）
- `backend/tests/test_auth_refresh.py`（新）

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 3min | 红 | 创建 `backend/tests/test_auth_refresh.py`：编写 `test_refresh_with_valid_cookie_returns_new_access_token` — 先登录拿到 refresh cookie，再用该 cookie 调用 `POST /admin/api/v1/auth/refresh`，断言返回新 access_token |
| 2 | 4min | 绿 | `auth.py` 新增 `POST /auth/refresh` 路由：从 `request.cookies.get("refresh_token")` 读 token → `decode_refresh_token` → 查 platform_users 状态 → `create_access_token` → 返回 JSONResponse |
| 3 | 3min | 红→绿 | 新增 `test_refresh_without_cookie_returns_401` — 无 cookie 请求返回 401。新增 `test_refresh_with_expired_token_returns_401` — 过期 token 返回 401 |
| 4 | 3min | 红→绿 | 新增 `test_refresh_with_disabled_user_returns_401` — token 有效但用户状态非 active 返回 401。在 refresh 路由中加入用户状态检查 |
| 5 | 3min | 红→绿 | 新增 `test_logout_clears_refresh_cookie` — 调用 `POST /admin/api/v1/auth/logout`，断言响应 `Set-Cookie: refresh_token=; Max-Age=0`。`auth.py` 新增 logout 路由：`response.delete_cookie("refresh_token", path=..., domain=...)` |
| 6 | 2min | 重构 | 运行全部后端测试 `python -m pytest backend/tests/ -v`，确认通过 |

**测试场景：**
- 有效 refresh cookie → 200 + 新 access_token
- 无 cookie → 401
- 过期 token → 401
- 用户已禁用 → 401
- logout 清除 cookie（Max-Age=0）

**依赖：** IU-2

---

### IU-4: 前端 axios withCredentials + 401 拦截器重构

**文件：**
- `frontend/packages/shared-api/src/client.ts`（改）

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 2min | 改 | `axios.create()` 加 `withCredentials: true` |
| 2 | 5min | 改 | 重写 401 拦截器：(1) 如果失败请求 URL 包含 `/auth/refresh` → 直接 `logout()` 跳转 `/login`（防循环）。(2) 否则检查 `isRefreshing` flag → 首个 401 发起 `POST /admin/api/v1/auth/refresh` 请求。(3) refresh 成功 → `setToken(data.access_token)` + `fetch('/api/auth/set-token', ...)` 同步 cookie → 用新 token 重放原请求。(4) refresh 返回 401 → logout。(5) refresh 网络错误 → 不 logout，reject 原 error |
| 3 | 4min | 改 | 实现并发队列：模块级 `let isRefreshing = false` + `let failedQueue: {resolve, reject}[]`。首个 401 设 `isRefreshing = true`，后续 401 入队。refresh 完成后依次 resolve/reject 队列中的请求 |
| 4 | 2min | 验证 | TypeScript 编译检查 `pnpm --filter shared-api build`（或 `tsc --noEmit`） |

**测试场景（手动验证，IU-6）：**
- access_token 过期 → 静默刷新 → 请求成功
- refresh 也过期 → 跳转 /login
- 并发请求 → 只发一次 refresh
- 后端停机 → 显示加载失败，不 logout

**依赖：** IU-3（后端端点需存在）

---

### IU-5: 前端 cookie maxAge + logout 适配

**文件：**
- `frontend/apps/admin/src/app/api/auth/set-token/route.ts`（改）
- `frontend/apps/admin/src/components/layout/app-shell.tsx`（改）

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 2min | 改 | `set-token/route.ts` 的 `cookies.set` 加 `maxAge: 86400`（24h） |
| 2 | 3min | 改 | `app-shell.tsx` 的 `handleLogout`：在现有 `clear-token` 调用前，先 `fetch` 调用后端 `POST /admin/api/v1/auth/logout`（withCredentials）清除 refresh cookie |
| 3 | 2min | 验证 | TypeScript 编译检查 `pnpm --filter admin build` |

**测试场景（手动验证，IU-6）：**
- 登录后关闭浏览器再打开 → cookie 仍在（maxAge 生效）
- 登出 → refresh_token cookie 被清除 → 无法刷新

**依赖：** IU-4

---

### IU-6: 端到端手动验证

**文件：** 无新增

**步骤：**

| # | 时间 | 动作 | 详情 |
|---|------|------|------|
| 1 | 3min | 验证 | 启动后端 `uvicorn`，curl 测试 login → 确认 `Set-Cookie: refresh_token` header |
| 2 | 3min | 验证 | curl 带 cookie 测试 refresh → 确认返回新 access_token |
| 3 | 2min | 验证 | curl 测试 refresh 无 cookie / 过期 → 确认 401 |
| 4 | 3min | 验证 | 启动前端 admin dev，浏览器登录 → DevTools 确认 refresh_token cookie 存在且属性正确 |
| 5 | 3min | 验证 | DevTools 手动删除 localStorage access_token（或篡改为过期值）→ 刷新页面 → 确认静默刷新成功，用户无感知 |
| 6 | 2min | 验证 | 登出 → DevTools 确认 refresh_token cookie 已清除 |
| 7 | 2min | 验证 | 运行 `python -m pytest backend/tests/ -v` + `pnpm --filter admin build` 最终确认 |

**依赖：** IU-5

---

## Execution Sequence

```
IU-1 → IU-2 → IU-3 → IU-4 → IU-5 → IU-6
 │      │       │       │       │       │
 │      │       │       │       │       └ 端到端验证
 │      │       │       │       └ cookie maxAge + logout 适配
 │      │       │       └ axios 拦截器重构
 │      │       └ refresh + logout 端点
 │      └ login 端点改造
 └ JWT 函数 + 配置 + 测试基础设施
```

严格线性依赖：每个 IU 依赖前一个的产出。后端先行（IU-1 ~ IU-3），前端跟进（IU-4 ~ IU-5），最后集成验证（IU-6）。

---

## Risks

| 风险 | 影响 | 缓解 |
|------|------|------|
| 跨域 cookie 被浏览器拒绝 | refresh 机制完全失效 | IU-6 步骤 4 验证；同根域 `.xinanpcb.com` + SameSite=Lax 兼容性好 |
| 并发 refresh 队列死锁 | 请求永远挂起 | 队列加 10s 超时释放机制 |
| refresh 端点本身性能 | 每次 refresh 查库 | admin 用户量极小（<10），不构成问题 |
| 前端 set-token 同步失败 | Next.js middleware 误判未登录 | refresh 成功后 await set-token，失败不影响 API 调用（只影响 SSR 路由保护） |

---

## Deployment

1. **后端先部署**：新增 refresh/logout 端点 + login 加 Set-Cookie。旧前端忽略新 cookie，行为不变
2. **前端后部署**：401 拦截器启用 refresh。向下兼容：refresh 失败时 fallback 到 logout
3. **回滚**：前端回滚即可。后端 refresh 端点无副作用可保留
