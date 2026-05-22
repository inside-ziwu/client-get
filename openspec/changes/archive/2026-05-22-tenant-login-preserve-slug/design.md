## Context

当前租户端登录页（`frontend/apps/tenant/src/app/login/page.tsx`）包含三个字段：租户标识(slug)、邮箱、密码。slug 可通过 URL query param `?slug=xxx` 预填充。

退出登录时，`app-shell.tsx` 的 `handleLogout` 和 `RequireAuth` guard 已正确携带 slug 重定向。但 `shared-api/src/client.ts` 的 401 响应拦截器直接跳转 `window.location.href = '/login'`，丢失 slug。

## Goals / Non-Goals

**Goals:**
- 登录页只展示邮箱和密码，slug 从 URL 静默读取
- 所有退出/过期路径统一保留 slug
- 无 slug 访问时给出明确错误提示

**Non-Goals:**
- 不引入路径级 slug（如 `/:slug/login`）
- 不改变 dashboard 路由结构
- 不涉及后端改动
- 不涉及 admin 端

## Decisions

### D1: slug 继续使用 query param 传递

继续用 `?slug=xxx` 而非路径 `/:slug/login`。

理由：当前 logout、RequireAuth 已用 query param 方式实现，改路径需重构整个 Next.js App Router 目录结构，收益不大。Query param 满足需求且改动最小。

### D2: 401 拦截器通过 store 快照读取 slug

在 `logout()` 调用前先从 `useAuthStore.getState().payload?.slug` 取值，拼接到重定向 URL。

理由：与 `handleLogout` 一致的模式，简单可靠。

### D3: 无 slug 时展示静态错误提示

当 URL 无 `slug` 参数时，登录页渲染一段错误提示文案，不提供 slug 输入框。

理由：实际使用中登录链接由管理员分发，用户不应自行输入 slug。展示输入框反而增加认知负担。

## Risks / Trade-offs

- **[风险] 401 拦截器在 logout 后 payload 已清空** → 在调用 `logout()` 前先缓存 slug 值，与 handleLogout 保持一致
- **[取舍] 无 slug 用户无法自助登录** → 可接受：租户登录链接始终由管理员提供，不存在自助发现 slug 的场景
