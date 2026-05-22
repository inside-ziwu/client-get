## ADDED Requirements

### Requirement: 登录页 SHALL 隐藏租户标识输入框
登录页 MUST 从 URL query param `?slug=xxx` 静默读取租户标识，不展示 slug 输入框。登录表单只展示邮箱和密码两个字段。

#### Scenario: 带 slug 的正常登录
- **GIVEN** 用户访问 `/login?slug=acme`
- **WHEN** 页面加载完成
- **THEN** 登录表单只展示邮箱和密码字段，不展示租户标识输入框
- **AND** 提交登录时使用 URL 中的 `acme` 作为 slug 调用 `/t/acme/api/v1/auth/login`

#### Scenario: 无 slug 访问登录页
- **GIVEN** 用户访问 `/login`（URL 中无 slug 参数）
- **WHEN** 页面加载完成
- **THEN** 页面展示错误提示，引导用户通过正确的链接访问
- **AND** 不展示登录表单

### Requirement: 退出登录 SHALL 在重定向 URL 中保留 slug
所有导致用户退出登录的场景 MUST 在重定向到登录页时保留租户标识 slug。

#### Scenario: 手动退出登录
- **GIVEN** 用户已登录租户 `acme`
- **WHEN** 用户点击退出登录
- **THEN** 浏览器跳转至 `/login?slug=acme`

#### Scenario: Token 过期触发 RequireAuth 重定向
- **GIVEN** 用户的 token 已过期，当前租户为 `acme`
- **WHEN** RequireAuth guard 检测到 token 无效
- **THEN** 浏览器跳转至 `/login?slug=acme`

#### Scenario: API 401 响应触发重定向
- **GIVEN** 用户当前租户为 `acme`，payload 中包含 slug
- **WHEN** 任意 API 请求返回 401
- **THEN** 浏览器跳转至 `/login?slug=acme`（而非当前的 `/login`）

#### Scenario: API 401 响应但 payload 无 slug
- **GIVEN** store 中 payload 为空（异常情况）
- **WHEN** API 请求返回 401
- **THEN** 浏览器跳转至 `/login`（降级处理）
