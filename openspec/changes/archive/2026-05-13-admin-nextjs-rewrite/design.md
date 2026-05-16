## 架构决策

### D-1: Next.js 15 App Router

全部采用 App Router（不使用 Pages Router）。Admin 的所有页面实质上都是 Client Components（标记 `'use client'`），因为每个页面都用到 useState、useEffect、事件绑定等浏览器端能力。App Router 在本 change 中主要提供：

- 文件路由（替代 react-router 手动配置）
- 嵌套布局（`layout.tsx` 替代 `<Outlet/>`）
- 按路由自动 code splitting

不使用 Server Components 数据获取、Server Actions、ISR/SSG。

### D-2: shadcn/ui + Tailwind CSS 替代 antd

antd 组件到 shadcn/ui 组件的映射关系：

| antd 组件 | shadcn/ui 对应 | 备注 |
|-----------|--------------|------|
| Table | DataTable (TanStack Table) | 需手写列定义，但比 antd Table 更灵活 |
| Form + Form.Item | Form (react-hook-form + zod) | 验证从 antd rules 迁移到 zod schema |
| Modal | Dialog | |
| Drawer | Sheet | |
| Input / InputNumber | Input | shadcn 的 Input 更轻量 |
| Select | Select 或 Combobox | |
| Button | Button | |
| Card | Card | |
| Popconfirm | AlertDialog | |
| Switch | Switch | |
| Tag / Badge | Badge | |
| Collapse | Collapsible 或 Accordion | |
| Descriptions | 自定义 DescriptionList | shadcn 无直接对应，用简单的 dl/dt/dd 布局 |
| DatePicker / RangePicker | 社区方案 (date-picker + react-day-picker) | |
| Upload | 自定义 FileUpload | |
| Statistic | 自定义 StatCard | 简单的数字展示组件 |
| message / notification | Sonner (toast) | |

### D-3: 共享包策略

```
@shared/types  → 继续使用，无改动
@shared/api    → createApiClient 增加可选 baseURL 参数
                 Tenant 端不传参，行为不变（默认读 VITE_API_BASE_URL）
                 Admin-next 传 baseURL=''，使用相对路径
@shared/hooks  → 继续使用，无改动
@shared/ui     → admin-next 不再依赖（此包全是 antd 组件）
```

Admin-next 的 UI 组件直接放在 `admin-next/src/components/ui/` 下（shadcn/ui 的标准做法）。

### D-4: 数据层保持不变

- TanStack Query 5：queryClient 配置沿用（staleTime 30s, gcTime 5m, retry 1）
- Zustand 5：useAuthStore 保留，sessionStorage persist 不变
- API 客户端：继续使用 `@shared/api` 的 `createApiClient('admin')` + `createAdminApi(client)`
- 不引入 fetch 替代 axios，降低变量

### D-5: 部署架构

```
现有:                                   迁移后:
┌──────────────┐                       ┌──────────────┐
│ Vite build   │                       │ next build   │
│ → dist/      │                       │ → .next/     │
│   (静态文件)  │                       │  standalone/ │
└──────┬───────┘                       └──────┬───────┘
       ▼                                      ▼
┌──────────────┐                       ┌──────────────┐
│ nginx:alpine │                       │ node:20-slim │
│ 静态托管      │                       │ server.js    │
│ 端口 80      │                       │ 端口 3000     │
└──────────────┘                       └──────────────┘
```

- Dockerfile 使用多阶段构建：build 阶段 pnpm install + next build，运行阶段基于 `node:20-alpine`
- `next.config.ts` 设置 `output: 'standalone'`
- 开发环境前端使用相对路径（`/admin/api/...`）并由 Next rewrites 代理到本地后端；生产环境在构建时写入 `NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com`，浏览器直接请求后端公网 API 域名（见 D-6）
- `/admin/api/*` 请求在生产环境不经过 Admin Next 应用，也不依赖 Sealos 同域名 path routing
- 健康检查端点：Next.js 内建 `/api/healthz` route handler，替代 nginx 的 `/healthz`

### D-6: API 访问方案

开发环境和生产环境分别处理：

```
开发环境:
  next.config.ts rewrites:
    /admin/api/:path* → http://localhost:8000/admin/api/:path*

生产环境:
  NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com
  浏览器请求:
    https://api.xinanpcb.com/admin/api/v1/*
```

决策依据：线上 Admin Next 独立域名当前没有可用的 `/admin/api/*` Ingress path routing；生产构建若继续使用相对路径，浏览器会请求前端域名下的 `/admin/api/*` 并命中 Next 404。直接使用后端公网 API 域名可以保持前后端应用解耦，不需要新增同域名 Ingress，也不需要更新后端镜像。

## 项目结构

```
frontend/apps/admin-next/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── Dockerfile
├── public/
├── src/
│   ├── app/
│   │   ├── layout.tsx                  ← 根布局 (html/body + providers)
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── (dashboard)/               ← 路由组 (带侧边栏布局)
│   │       ├── layout.tsx              ← 侧边栏 + RequireAuth
│   │       ├── page.tsx                ← / → DataSources
│   │       ├── data-sources/page.tsx
│   │       ├── collection-tasks/page.tsx
│   │       ├── collection/
│   │       │   ├── peers/page.tsx
│   │       │   ├── peers-cleaned/page.tsx
│   │       │   ├── tendata/page.tsx
│   │       │   └── customers/page.tsx
│   │       ├── intelligence-sources/page.tsx
│   │       ├── email-templates/page.tsx
│   │       ├── scoring-templates/page.tsx
│   │       ├── contact-classification/page.tsx
│   │       ├── warmup-rules/page.tsx
│   │       ├── ai-config/page.tsx
│   │       └── tenants/page.tsx
│   ├── components/
│   │   ├── ui/                         ← shadcn/ui 组件 (Button, Dialog, etc.)
│   │   ├── layout/
│   │   │   ├── sidebar.tsx             ← 侧边栏导航
│   │   │   └── app-shell.tsx           ← 整体 shell
│   │   └── grapes-email-editor.tsx     ← GrapesJS 编辑器
│   ├── lib/
│   │   ├── api.ts                      ← adminApi 实例 (复用 @shared/api)
│   │   ├── format.ts                   ← 日期格式化工具
│   │   └── utils.ts                    ← cn() 等 tailwind 工具
│   └── providers.tsx                   ← QueryClientProvider 等
```

## 页面复杂度与迁移策略

按复杂度分三档，决定迁移优先级：

| 档位 | 页面 | 行数 | 核心组件 | 迁移难点 |
|------|------|------|---------|---------|
| S 高 | CollectionArchive | ~945 | 双 Tab + 多级筛选 + 嵌套表 | 筛选器表单最复杂，需 10+ 个字段 |
| S 高 | ScoringTemplates | ~741 | DimensionEditor + 分数合并 | 自定义维度编辑器需重写 |
| S 高 | Tenants | ~739 | 4 Tab 详情 + 15+ API | 最多 API 调用，多表单嵌套 |
| M 中 | DataSources | ~535 | JSON 配置编辑器 + 凭证管理 | 动态表单字段 |
| M 中 | ContactClassification | ~491 | 三列层级 UI | 层级选择同步逻辑 |
| M 中 | PeersData | ~444 | 11 列表 + 筛选 | 常规 CRUD |
| M 中 | PeersCleaned | 已有 Next.js 实现 | 清洗后同行公司池 + 健康指标 + 详情 Sheet | 接入当前 App Router/shadcn 布局 |
| M 中 | CollectionTasks | ~425 | 可展开行 + 轮询 | 状态轮询逻辑 |
| M 中 | EmailTemplates | ~351 | GrapesJS 集成 | 编辑器 ref 管理 |
| M 中 | IntelligenceSources | ~325 | 批量 JSON 导入 | 常规 CRUD |
| L 低 | AIConfig | ~277 | 双表布局 | 简单 |
| L 低 | WarmupRules | ~287 | 动态行编辑 | 简单 |
| L 低 | Login | ~72 | 登录表单 | 最简单 |
