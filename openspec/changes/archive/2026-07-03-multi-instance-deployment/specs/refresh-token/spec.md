## MODIFIED Requirements

### Requirement: 登录时 SHALL 同时签发 refresh token

`POST /admin/api/v1/auth/login` 登录成功后，系统 MUST 在响应中同时：
1. 返回 `access_token`（JSON body，保持现有行为）
2. 设置 `refresh_token` httpOnly cookie（`Set-Cookie` header）

refresh_token cookie 属性：
- `HttpOnly`: true
- `Secure`: true（生产环境）
- `SameSite`: Lax
- `Domain`: 通过环境变量 `COOKIE_DOMAIN` 配置（Instance A: `.xinanpcb.com`，Instance B: 对应域名）
- `Path`: `/admin/api/v1/auth`
- `Max-Age`: 604800（7 天）

refresh_token JWT payload：
- `sub`: 用户 ID
- `kind`: `"platform"`
- `type`: `"refresh"`
- `iid`: 当前实例的 instance_id
- `iat`: 签发时间
- `exp`: 过期时间（7 天后）

#### Scenario: 登录成功签发双 token

- **GIVEN** 有效的 admin 用户凭证
- **WHEN** 调用 `POST /admin/api/v1/auth/login` 且认证通过
- **THEN** 响应 body 包含 `access_token`（含 `iid` claim），且响应 header 包含 `Set-Cookie: refresh_token=<jwt>; HttpOnly; Path=/admin/auth; Max-Age=604800`，refresh_token 也含 `iid` claim

#### Scenario: 登录失败不签发任何 token

- **GIVEN** 无效的凭证（邮箱或密码错误）
- **WHEN** 调用 `POST /admin/api/v1/auth/login`
- **THEN** 返回 401，不设置任何 cookie

---

### Requirement: 刷新端点 SHALL 验证 refresh token 并签发新 access token

系统 MUST 提供 `POST /admin/api/v1/auth/refresh` 端点：
- 从请求的 `refresh_token` cookie 中读取 JWT
- 验证签名、过期时间、`type == "refresh"`
- 验证 `iid` 与当前后端 `instance_id` 一致
- 验证用户仍然存在且状态为 active
- 签发新的 access_token（与登录时相同的 claims，包含 `iid`）

请求：无 body，refresh_token 通过 cookie 自动发送
响应：`{ "code": 0, "data": { "access_token": "<jwt>" } }`

#### Scenario: 有效 refresh token 换新 access token

- **GIVEN** 用户持有未过期的 refresh_token cookie，且 `iid` 与当前实例匹配
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 200，body 包含新的 `access_token`（含 `iid` claim）

#### Scenario: refresh token 已过期

- **GIVEN** 用户持有已过期的 refresh_token cookie
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 401，body 包含 `code: "UNAUTHORIZED"`

#### Scenario: refresh token 实例不匹配

- **GIVEN** 用户持有 `iid=default` 的 refresh_token，但当前后端 `INSTANCE_ID=instance_b`
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 403，拒绝签发新 token

#### Scenario: 无 refresh token cookie

- **GIVEN** 请求不含 refresh_token cookie
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 401

#### Scenario: 用户已被禁用

- **GIVEN** refresh_token 有效但对应的 platform_user 状态不是 active
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 401，拒绝签发新 token
