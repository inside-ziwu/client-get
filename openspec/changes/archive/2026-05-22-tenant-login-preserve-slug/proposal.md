## Why

租户端退出登录或 token 过期后，401 拦截器将用户重定向至 `/login`，丢失租户标识 slug，导致用户需要重新手动输入 slug 才能登录。同时登录页展示 slug 输入框对普通用户来说是不必要的技术细节——实际使用中登录链接总是由管理员分发、自带 slug。

## What Changes

- **移除登录页 slug 输入框**：登录页只展示邮箱和密码字段，slug 从 URL query param `?slug=xxx` 静默读取
- **无 slug 时展示错误提示**：若 URL 中没有 slug，显示"请通过正确的链接访问"提示，不提供 slug 输入框
- **修复 401 拦截器丢失 slug 的 bug**：`shared-api/src/client.ts` 的 401 响应拦截器当前直接跳转 `/login`，需改为 `/login?slug=xxx` 保留租户标识

## Non-Goals

- 不改变 URL 结构（继续使用 query param，不引入路径级 slug 如 `/:slug/login`）
- 不涉及 dashboard 内部路由变更
- 不涉及后端 API 改动
- 不涉及 admin 端登录流程

## Capabilities

### New Capabilities

- `tenant-login-slug-hidden`: 租户端登录页隐藏 slug 字段，从 URL 静默读取，无 slug 时展示错误提示

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 影响范围 | 说明 |
|---------|------|
| `frontend/apps/tenant/src/app/login/page.tsx` | 移除 slug 输入框，改为从 searchParams 读取；无 slug 时渲染错误提示 |
| `frontend/packages/shared-api/src/client.ts` | 401 拦截器修复：读取当前 slug 并拼接到重定向 URL |
| 用户体验 | 登录页更简洁；退出/过期后可直接重新输入密码登录，无需找回 slug |
