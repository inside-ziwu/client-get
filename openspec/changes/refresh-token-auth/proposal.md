## Why

后端更新镜像（容器重启）后，admin 端所有已登录用户被强制登出。当前 JWT access token 有效期仅 24h，前端收到 401 立即 logout，没有任何刷新或重试机制。用户体验差，且每次后端部署都需要所有管理员重新登录。

## What Changes

- 后端新增 refresh token 签发与验证（独立于 access token，有效期 7 天）
- login 端点返回 access_token 的同时，通过 httpOnly cookie 下发 refresh_token
- 新增 `POST /admin/auth/refresh` 端点：验证 refresh_token cookie → 签发新 access_token
- 前端 axios 401 拦截器改为：先尝试 refresh → 成功则重放原请求 → refresh 也失败才 logout
- admin 前端 `set-token` route 的 cookie 增加 `maxAge`，避免 session cookie 丢失

## Non-Goals

- 本次不涉及 tenant 端（租户端可后续复用同一机制）
- 不引入 Redis 或数据库存储的 token 黑名单
- 不做 refresh token rotation（每次 refresh 换新 refresh token）
- 不改 JWT_SECRET 管理方式（Sealos 环境变量注入）

## Capabilities

### New Capabilities

- `refresh-token`: 后端签发/验证 refresh token + 前端静默刷新机制

### Modified Capabilities

（无现有 spec 的 requirement 变更）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 后端 API | 新增 `POST /admin/auth/refresh`；`POST /admin/auth/login` 响应新增 Set-Cookie |
| 后端配置 | 新增 `REFRESH_TOKEN_EXPIRE_DAYS` 环境变量（默认 7） |
| 前端共享包 | `shared-api/client.ts` 拦截器逻辑变更 |
| Admin 前端 | `set-token/route.ts` cookie 设置变更；新增 refresh 代理 route |
| 数据库 | 无变更（纯无状态 JWT） |
| 部署依赖顺序 | 后端先部署（新增 refresh 端点），前端后部署（使用新端点） |
