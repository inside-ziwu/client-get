## 1. 登录页改造

- [ ] 1.1 移除 `frontend/apps/tenant/src/app/login/page.tsx` 中的 slug 输入框，改为从 `searchParams.get('slug')` 静默读取
- [ ] 1.2 当 URL 无 slug 参数时，渲染错误提示（不展示登录表单），引导用户通过正确链接访问
- [ ] 1.3 登录提交逻辑适配：移除 `formData.get('slug')` 相关代码，直接使用从 URL 读取的 slug 值

## 2. 401 拦截器修复

- [ ] 2.1 修改 `frontend/packages/shared-api/src/client.ts` 的 401 响应拦截器：在 `logout()` 前缓存 `payload?.slug`，重定向至 `/login?slug=xxx`

## 3. 验证

- [ ] 3.1 启动开发服务器，验证带 slug 的登录流程（`/login?slug=xxx` → 输入邮箱密码 → 登录成功）
- [ ] 3.2 验证无 slug 访问 `/login` 时展示错误提示
- [ ] 3.3 验证退出登录后 URL 保留 slug 参数
- [ ] 3.4 TypeScript 类型检查通过（`pnpm --filter tenant type-check`）
