# 前端目录结构与页面模式

> 事实来源：`frontend/package.json`、各包 `package.json`、`apps/*/tsconfig.json` paths、`apps/admin/src/lib/`、`packages/shared-api/src/client.ts`。

## Workspace 布局

```
frontend/                     pnpm 10 workspace（Node ≥ 20）
├── apps/admin/               @apps/admin   Next.js 15 + React 19，端口 3000，SSR 预取壳 + 客户端页
├── apps/tenant/              @apps/tenant  Next.js 15 + React 19，端口 3001，纯客户端渲染（'use client'）
└── packages/
    ├── shared-ui/            @shared/ui     Radix 封装 + 设计令牌 + 列表页五件套（src/components/*，根入口统一导出）
    ├── shared-api/           @shared/api    axios 客户端（client.ts）、admin/ 与 tenant/ 按领域分文件的 API 函数、query-keys.ts
    ├── shared-hooks/         @shared/hooks  useAuth（Zustand）、usePermission、useCursorPagination
    └── shared-types/         @shared/types  api.ts / models.ts / enums.ts / auth.ts（手写类型）
```

- 路径别名：`@/*` → 当前 app 的 `src/*`；`@shared/<pkg>` → `packages/<pkg>/src`。tsconfig `paths` 与 `vitest.config.ts` alias **两处都要维护**。
- 根脚本：`pnpm dev:admin` / `dev:tenant` / `build:admin` / `build:tenant` / `type-check`（`pnpm -r type-check`）。

## 页面模式

**tenant**：`src/app/(dashboard)/<feature>/page.tsx` 首行 `'use client'`，页面内 `useQuery` 取数、`useMutation` 写操作，UI 由 `ListPage` / `DataTable` 等组合（参照 `industry-news/page.tsx`、`companies/page.tsx`）。复杂表单拆到同目录组件文件（如 `companies/add-company-sheet.tsx`）。

**admin**：每个页面两个文件——
- `page.tsx`（服务端）：`createPrefetchPage({ queryKey, fetchFn: (token) => serverApi.get('/api/v1/...', { token }), Component })`，用 `HydrationBoundary` 把预取结果交给客户端；
- `client-page.tsx`（`'use client'`）：与预取**相同的 queryKey** 做 `useQuery`，否则命中不了缓存。

`serverApi`（`lib/server-api.ts`）走 `BACKEND_INTERNAL_URL`（默认 `http://localhost:8000`）、3 秒超时、`cache: 'no-store'`；SSR 令牌由 `app/api/auth/set-token | clear-token` 路由写入 / 清除 cookie。

## API 前缀与环境变量

- `createApiClient(appType)`：请求拦截器注入 Bearer token，并按 app 设置 baseURL——admin → `/admin`，tenant → `/t/{slug}`（slug 取自 JWT payload）。**tenant 前端路由本身不带 slug，slug 只来自登录输入与 JWT**；调用 `shared-api` 函数时路径从 `/api/v1/...` 起。
- 401 自动刷新：单飞（`isRefreshing` + 队列，10 秒超时）；刷新端点本身 401 → 登出并跳 `/login?slug=…`。
- 环境变量：tenant `NEXT_PUBLIC_API_BASE_URL`；admin `NEXT_PUBLIC_ADMIN_API_BASE_URL`（浏览器侧）+ `BACKEND_INTERNAL_URL`（SSR 侧）。本地都指向 `http://localhost:8000`；生产地址在镜像构建时 `--build-arg` 注入，前端代码无实例概念。

## 命名

- 变量 / 函数 camelCase，组件 PascalCase，文件 kebab-case（`client-page.tsx`、`add-company-sheet.tsx`）；hooks `useXxx`。
- 多个 app 共用的 hook 放 `packages/shared-hooks`，只在一个 app 用的放该 app 内。

## 常见错误

- admin 预取 key 与客户端 key 不一致 → 每次都重新请求、SSR 白做。
- 在 app 内新写表格 / 分页 / 筛选布局而不用五件套（component-guidelines.md）。
- 新增 `@shared/*` 包只改 tsconfig 不改 vitest alias，测试解析失败。
