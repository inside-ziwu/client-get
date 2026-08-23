# 前端质量与验证

> 事实来源：`apps/tenant/vitest.config.ts`、`apps/tenant/test/`（7 文件 / 33 用例，2026-07 基线）、`frontend/package.json`、部署联调的历史记录（`docs/solutions/`，已冻结为档案）。

## 门禁

- `cd frontend && pnpm type-check`（全 workspace）。
- tenant：`pnpm --filter @apps/tenant test`（Vitest + jsdom + Testing Library，`test/**/*.test.tsx`，`setup.ts` 引入 jest-dom）。
- admin：无单元测试，以 type-check + production build（`pnpm build:admin`）为门禁。
- 失效命令（修复前不得作为门禁）：根 `pnpm lint`（未装 eslint，#50）、tenant `test:contract`（指向不存在文件，#56）。

## 测试模式

- `vi.mock('@/lib/api', () => ({ tenantApi: { <feature>: { list: vi.fn(), ... } } }))` 替身 API 层；`QueryClient` 关闭 retry 后用 `QueryClientProvider` 包裹渲染（参照 `test/intelligence/intelligence-page.test.tsx`）。
- 断言用户可见行为（文案、按钮状态、表格行），不断言实现细节；`beforeEach` 设默认 resolved 值。
- 测试按功能目录放（`test/companies/`、`test/intelligence/`），文件名描述场景（`companies-pagination-continuity.test.tsx`）。

## UI 规则（设计契约摘要，全文见 design-system.md）

- 原语只从 `@shared/ui` 引入；列表页用五件套（ListPage / FilterBar / DataTable / TableState / Pagination），新页面不手写布局与分页。
- loading / refresh / empty / 筛选无结果 / error 五态可区分，不能合并成 `items.length === 0`。
- 语义色经 Badge tone（success / warning / info / danger / neutral），不散写 Tailwind 颜色 class；不存在的 class 不报错只是静默失效——对照既有页面写。
- `focus-visible` 不得移除；图标按钮必须有 `aria-label` 和 Tooltip。
- 不借 UI 迁移改 API 行为、删业务选项或重做信息架构。

## 部署与联调的坑

- **本地 admin 对接生产实例**（仅限用户授权的只读验收，不写 `.env`）必须同时配浏览器代理与 SSR 地址：`NEXT_PUBLIC_ADMIN_API_BASE_URL=`（空，走同源）+ `ADMIN_API_REWRITE_TARGET=<生产 API>` + `BACKEND_INTERNAL_URL=<生产 API>`；开发日志里 SSR 仍打 `localhost:8000` 就是漏了 `BACKEND_INTERNAL_URL`。
- Sealos 域名（`*.sealosbja.site`）不在 Public Suffix List：两个随机子域名视为同站，`SameSite=Lax` 的 refresh cookie 可跨前后端子域；但 `COOKIE_DOMAIN` **必须写后端完整主机名**，严禁写 `.sealosbja.site`（会把凭证发给该后缀下所有站点）；CORS 仍要显式列前端 origin（https、无尾斜杠）。
- 前端镜像在构建时写死 API 地址：两实例各需一套 admin / tenant 镜像（发布矩阵见 README §7）。
- 框架迁移后清理 Dockerfile 的 COPY 残留——本地不跑 `docker build`，问题只在 CI 暴露。

## 评审清单

- [ ] type-check / test / build 通过并附输出
- [ ] 用了五件套与 `@shared/ui`，无散写像素列宽与颜色 class
- [ ] 五态可区分；refetch 保留旧行；mutation pending 有反馈
- [ ] 客户端页面用 `queryKeys` 工厂；admin 预取页（server-only，不能引用依赖 zustand 的 `query-keys.ts`）用字面量 key，且 `page.tsx` 与 `client-page.tsx` 两处完全一致
- [ ] 契约同步（type-safety.md）
