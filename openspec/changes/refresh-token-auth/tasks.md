## 1. 后端：refresh token 签发与验证

- [ ] 1.1 `backend/app/core/config.py` 新增 `refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")`
- [ ] 1.2 `backend/app/security/jwt.py` 新增 `create_refresh_token(claims)` — 签发带 `type: "refresh"` 的 JWT，有效期取 `settings.refresh_token_expire_days`
- [ ] 1.3 `backend/app/security/jwt.py` 新增 `decode_refresh_token(token)` — 解码并校验 `type == "refresh"`，非 refresh 类型抛 UNAUTHORIZED

## 2. 后端：login 端点改造 + refresh + logout 端点

- [ ] 2.1 `backend/app/services/auth_service.py` 的 `platform_login` 方法返回值改为 `tuple[str, str]`（access_token, refresh_token）
- [ ] 2.2 `backend/app/api/admin/auth.py` 的 `login` 路由改为返回 `JSONResponse`（不再用 `success_response()`），通过 `response.set_cookie` 设置 refresh_token。cookie 属性根据 `settings.app_env` 动态切换：
  - 生产：`HttpOnly=True, Secure=True, SameSite=Lax, Domain=.xinanpcb.com, Path=/admin/api/v1/auth, Max-Age=604800`
  - 本地：`HttpOnly=True, Secure=False, SameSite=Lax, Path=/admin/api/v1/auth, Max-Age=604800`（不设 Domain）
- [ ] 2.3 `backend/app/api/admin/auth.py` 新增 `POST /auth/refresh` 路由：从 cookie 读取 refresh_token → decode → 查用户状态 → 签发新 access_token（返回 JSONResponse）
- [ ] 2.4 `backend/app/api/admin/auth.py` 新增 `POST /auth/logout` 路由：清除 refresh_token cookie（Path/Domain 必须与设置时完全匹配），返回 `{"data": {"ok": true}}`

## 3. 前端：axios 配置 + 401 拦截器改造

- [ ] 3.1 `frontend/packages/shared-api/src/client.ts` 的 `axios.create()` 增加 `withCredentials: true`
- [ ] 3.2 401 拦截器改为：
  - 如果失败请求 URL 包含 `/auth/refresh` → 直接 logout（防止无限循环）
  - 否则 → 尝试调用 refresh 端点
  - refresh 成功 → 更新 localStorage token + 调用 `/api/auth/set-token` 同步 cookie → 重放原请求
  - refresh 返回 401 → logout
  - refresh 网络错误 → 不 logout，让原请求的错误正常传播（用户看到加载失败而非被踢出）
- [ ] 3.3 实现 refresh 请求队列：多个并发 401 只发一次 refresh，其他请求排队等待。队列需有超时释放机制防死锁。
- [ ] 3.4 `frontend/packages/shared-hooks/src/useAuth.ts` 确认 `setToken` 可被拦截器调用以更新 localStorage 中的 token

## 4. 前端：cookie maxAge + logout 适配

- [ ] 4.1 `frontend/apps/admin/src/app/api/auth/set-token/route.ts` 的 `cookies.set` 增加 `maxAge: 86400`（24 小时）
- [ ] 4.2 admin logout 流程增加调用 `POST /admin/api/v1/auth/logout` 清除后端 refresh_token cookie

## 5. 后端单元测试

- [ ] 5.1 创建 `backend/tests/` 目录和 `conftest.py` 基础设施
- [ ] 5.2 `backend/tests/test_jwt.py`：测试 create_refresh_token 签发正确 claims、decode_refresh_token 正常解码、decode 拒绝 access token、decode 拒绝过期 token
- [ ] 5.3 `backend/tests/test_auth_refresh.py`：测试 refresh 端点的正常/过期/缺失/用户禁用场景

## 6. 手动验证

- [ ] 6.1 本地启动后端，手动测试 login 返回 Set-Cookie header（refresh_token）
- [ ] 6.2 本地测试 `POST /admin/auth/refresh`：有效 cookie → 返回新 access_token
- [ ] 6.3 本地测试 refresh token 过期/缺失 → 返回 401
- [ ] 6.4 前端启动 admin dev，测试正常登录流程不受影响
- [ ] 6.5 前端模拟 access_token 过期（手动篡改 localStorage）→ 确认静默刷新成功
- [ ] 6.6 测试 logout → 确认 refresh_token cookie 被清除
- [ ] 6.7 确认前端 TypeScript 编译无错误：`pnpm --filter admin build`
- [ ] 6.8 确认后端测试通过：`cd backend && python -m pytest tests/`
