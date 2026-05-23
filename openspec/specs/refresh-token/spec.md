# refresh-token Specification

## Purpose
TBD - created by archiving change refresh-token-auth. Update Purpose after archive.
## Requirements
### Requirement: 登录时 SHALL 同时签发 refresh token

`POST /admin/auth/login` 登录成功后，系统 MUST 在响应中同时：
1. 返回 `access_token`（JSON body，保持现有行为）
2. 设置 `refresh_token` httpOnly cookie（`Set-Cookie` header）

refresh_token cookie 属性：
- `HttpOnly`: true
- `Secure`: true（生产环境）
- `SameSite`: Lax
- `Domain`: `.xinanpcb.com`（生产环境）
- `Path`: `/admin/api/v1/auth`
- `Max-Age`: 604800（7 天）

refresh_token JWT payload：
- `sub`: 用户 ID
- `kind`: `"platform"`
- `type`: `"refresh"`
- `iat`: 签发时间
- `exp`: 过期时间（7 天后）

#### Scenario: 登录成功签发双 token

- **GIVEN** 有效的 admin 用户凭证
- **WHEN** 调用 `POST /admin/auth/login` 且认证通过
- **THEN** 响应 body 包含 `access_token`，且响应 header 包含 `Set-Cookie: refresh_token=<jwt>; HttpOnly; Path=/admin/auth; Max-Age=604800`

#### Scenario: 登录失败不签发任何 token

- **GIVEN** 无效的凭证（邮箱或密码错误）
- **WHEN** 调用 `POST /admin/auth/login`
- **THEN** 返回 401，不设置任何 cookie

---

### Requirement: 刷新端点 SHALL 验证 refresh token 并签发新 access token

系统 MUST 提供 `POST /admin/auth/refresh` 端点：
- 从请求的 `refresh_token` cookie 中读取 JWT
- 验证签名、过期时间、`type == "refresh"`
- 验证用户仍然存在且状态为 active
- 签发新的 access_token（与登录时相同的 claims）

请求：无 body，refresh_token 通过 cookie 自动发送
响应：`{ "code": 0, "data": { "access_token": "<jwt>" } }`

#### Scenario: 有效 refresh token 换新 access token

- **GIVEN** 用户持有未过期的 refresh_token cookie
- **WHEN** 调用 `POST /admin/auth/refresh`
- **THEN** 返回 200，body 包含新的 `access_token`

#### Scenario: refresh token 已过期

- **GIVEN** 用户持有已过期的 refresh_token cookie
- **WHEN** 调用 `POST /admin/auth/refresh`
- **THEN** 返回 401，body 包含 `code: "UNAUTHORIZED"`

#### Scenario: 无 refresh token cookie

- **GIVEN** 请求不含 refresh_token cookie
- **WHEN** 调用 `POST /admin/auth/refresh`
- **THEN** 返回 401

#### Scenario: 用户已被禁用

- **GIVEN** refresh_token 有效但对应的 platform_user 状态不是 active
- **WHEN** 调用 `POST /admin/auth/refresh`
- **THEN** 返回 401，拒绝签发新 token

---

### Requirement: 前端 SHALL 在 access token 失效时静默刷新

前端 axios 拦截器收到 401 响应时，MUST 先尝试调用 `/admin/auth/refresh` 获取新 access_token：
- 刷新成功：更新本地存储的 token，重放原请求
- 刷新失败：清除登录状态，跳转 `/login`
- 并发 401：多个请求同时 401 时只发一次 refresh，其他请求排队等待

#### Scenario: access token 过期后静默刷新

- **GIVEN** 用户已登录，access_token 已过期，refresh_token 有效
- **WHEN** 前端发起 API 请求收到 401
- **THEN** 自动调用 refresh 端点获取新 token，使用新 token 重放原请求，用户无感知

#### Scenario: refresh token 也过期

- **GIVEN** 用户已登录，access_token 和 refresh_token 都已过期
- **WHEN** 前端发起 API 请求收到 401
- **THEN** refresh 请求也返回 401，前端清除状态并跳转到登录页

#### Scenario: 并发请求同时 401

- **GIVEN** 多个 API 请求同时因 access_token 过期返回 401
- **WHEN** 第一个 401 触发 refresh
- **THEN** 其他请求等待 refresh 完成，使用新 token 统一重放，只发一次 refresh 请求

---

### Requirement: 登出时 SHALL 清除 refresh token cookie

系统 MUST 提供 `POST /admin/auth/logout` 端点：
- 清除 `refresh_token` cookie（Path 和 Domain 必须与设置时完全匹配）
- 前端 logout 流程 MUST 调用此端点

#### Scenario: 登出清除 refresh cookie

- **GIVEN** 用户已登录且持有 refresh_token cookie
- **WHEN** 用户执行登出操作
- **THEN** 前端调用 `POST /admin/auth/logout`，响应包含 `Set-Cookie: refresh_token=; Max-Age=0`，浏览器删除 cookie

#### Scenario: 登出后无法刷新

- **GIVEN** 用户已登出，refresh_token cookie 已被清除
- **WHEN** 尝试调用 `POST /admin/auth/refresh`
- **THEN** 返回 401（无 cookie）

---

### Requirement: admin 前端 cookie MUST 设置 maxAge

`set-token` API route 设置的 `admin_auth_token` cookie MUST 包含 `maxAge`（与 access_token 有效期一致），避免作为 session cookie 在浏览器关闭时丢失。

#### Scenario: cookie 持久化

- **GIVEN** 用户登录成功
- **WHEN** 前端调用 `/api/auth/set-token` 设置 cookie
- **THEN** cookie 包含 `maxAge: 86400`（24 小时），关闭浏览器后重新打开仍有效

