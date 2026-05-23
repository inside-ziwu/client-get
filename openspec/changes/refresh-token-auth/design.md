## Context

当前认证流程：login → 签发 access_token（24h）→ 前端存 localStorage + httpOnly session cookie。后端纯无状态 JWT 验证。前端 axios 拦截器收到 401 直接调用 `logout()` 跳转 `/login`，没有重试。

后端容器重启后（镜像更新），如果 JWT_SECRET 不变，已签发 token 仍有效；但 24h 过期窗口 + session cookie 无 maxAge = 用户频繁被登出。需要增加 refresh token 机制实现静默续签。

## Goals / Non-Goals

**Goals:**
- 后端更新镜像后已登录 admin 用户不被强制登出
- access_token 过期后可通过 refresh token 静默换新
- refresh token 通过 httpOnly cookie 传递，不暴露给 JS

**Non-Goals:**
- 不做 tenant 端（后续复用）
- 不做 refresh token rotation
- 不引入 token 黑名单 / 吊销机制
- 不改数据库 schema

## Decisions

### D1: refresh token 也用 JWT（无状态），不存数据库

**理由**：当前系统纯无状态 JWT，引入数据库存储会增加复杂度和查询开销。admin 端用户量极小，token 泄露风险低。若未来需要吊销能力再引入数据库存储。

**替代方案**：数据库存储 refresh token → 可吊销但需新建表 + 每次 refresh 都查库。

### D2: refresh token 有效期 7 天，access token 保持 24h

**理由**：admin 端使用频率不高，7 天足以覆盖正常工作周期。access token 24h 保持不变，减少变更范围。

### D3: refresh token 通过后端直接 Set-Cookie 下发

**理由**：admin 前端部署在 `admin.xinanpcb.com`，后端在 `api.xinanpcb.com`，同属 `.xinanpcb.com`。后端可直接设置 `Domain=.xinanpcb.com` 的 cookie。无需前端中转。

**替代方案**：通过前端 Next.js API route 中转 → 多一跳，且需要前端传递 refresh token 值，增加暴露面。

### D4: 前端 401 拦截器加入 refresh 重试，使用请求队列防并发

**理由**：多个请求同时 401 时，只需发一次 refresh 请求。其他请求排队等待新 token 后重放。避免并发 refresh 竞争。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| refresh token 泄露后 7 天内可持续获取 access token | httpOnly + secure + sameSite=lax cookie 限制；admin 端用户量极小 |
| 跨域 cookie 设置可能因浏览器策略被拒绝 | 使用 `Domain=.xinanpcb.com`，前后端同根域；SameSite=lax 兼容性好 |
| 前端 refresh 失败时用户体验 | 静默失败后正常跳转登录页，与当前行为一致 |

## Migration Plan

1. **后端先部署**：新增 `/admin/auth/refresh` 端点 + login 增加 Set-Cookie。旧前端不受影响（忽略新 cookie）
2. **前端后部署**：401 拦截器开始使用 refresh 端点。新前端向下兼容（refresh 失败时 fallback 到 logout）
3. **回滚**：前端回滚到旧版即可，后端的 refresh 端点无副作用可保留
