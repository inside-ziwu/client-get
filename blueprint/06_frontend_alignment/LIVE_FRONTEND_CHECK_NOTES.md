# Live Frontend Check Notes

用户提供的两个前端入口：

- Admin: `https://client-get-admin.vercel.app/`
- Tenant: `https://client-get-tenant.vercel.app/`

当前交付包以 `08_UI_SPEC.md` 和 `11_FRONTEND_ARCHITECTURE.md` 为主要前端逻辑来源，并对线上入口做了可达性级别确认。由于当前环境无法稳定执行完整浏览器自动化流程（任意值登录、逐菜单点击、读取运行时网络请求），最终对齐矩阵以文档定义的路由和 API 映射为准。

后端实现完成后，建议增加一轮真实 E2E：

1. Admin 任意 mock 登录切换真实登录。
2. Tenant 输入 slug/email/password 登录。
3. 对每个页面打开 DevTools Network，确认 API path 与 `API_CONTRACT.md` 一致。
4. 替换 mock 数据为真实 API 后跑 Playwright smoke tests。

最低 smoke test：

- Admin：登录 → 数据源 → AI 配置 → 租户详情。
- Tenant：登录 → Dashboard → 公司列表 → 优选客户 → 邮件模板 → 发送计划 → 邮件监控。
