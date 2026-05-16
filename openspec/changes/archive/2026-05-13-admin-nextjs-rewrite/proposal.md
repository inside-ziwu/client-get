## Why

Admin 端当前使用 React 19 + Vite 7 CSR SPA 架构。团队计划将整个前端统一到 Next.js 生态，Admin 端作为试点先行迁移。Admin 端体量小（~6,300 行、12 个独立页面）、用户量有限、全部是 CRUD 管理页面，是理想的低风险试验场。

迁移目标不仅是框架切换，也借此机会将 UI 组件库从 antd 6 切换到 shadcn/ui + Tailwind CSS，完成前端技术栈的全面现代化。迁移经验将直接复用到后续 Tenant 端迁移。

## What Changes

- 新建 `frontend/apps/admin-next/`，使用 Next.js 15 + App Router + TypeScript 5.5+ 搭建全新 Admin 前端。
- UI 层从 antd 6 切换到 shadcn/ui + Tailwind CSS + Radix UI。
- 12 个现有页面全部在 App Router 文件路由体系下重建（`/` 与 `/data-sources` 指向同一页面）：
  - `/login` — 登录页
  - `/` = `/data-sources` — 数据源管理
  - `/collection-tasks` — 采集关键词
  - `/collection/peers` — 同行公司
  - `/collection/peers-cleaned` — 同行数据（清洗）
  - `/collection/tendata` — Tendata 采集归档
  - `/collection/customers` — 客户采集归档
  - `/intelligence-sources` — 情报源管理
  - `/email-templates` — 邮件模板管理（含 GrapesJS 编辑器）
  - `/scoring-templates` — 评分模板
  - `/contact-classification` — 联系人分类规则
  - `/warmup-rules` — 预热规则
  - `/ai-config` — AI 模型配置
  - `/tenants` — 租户管理
- 数据层保留 TanStack Query 5 + Zustand 5，HTTP 客户端可继续使用 axios 或切换到 fetch。
- 认证机制保持 JWT sessionStorage 方案，所有页面均为 Client Components，useAuthStore 自然在客户端运行。
- GrapesJS 邮件编辑器作为 Client Component 嵌入，逻辑不变。
- 部署采用 Next.js standalone 模式，输出独立 Docker 镜像 `clientget-admin-next`，部署到 Sealos。
- 后端 API 路由前缀 `/admin/api/v1/*` 不变。开发环境继续通过 Next rewrites 代理到本地后端；生产环境不依赖 Sealos 同域名 path routing，Admin Next 构建时写入 `NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com`，浏览器直接请求 `https://api.xinanpcb.com/admin/api/v1/*`。
- 迁移完成并验证后，删除旧 `frontend/apps/admin/`，更新部署脚本。

## Non-Goals

- 不迁移 Tenant 端；Tenant 端迁移作为独立后续 change。
- 不修改后端 API；所有 Admin API 端点保持现有契约。
- 不修改数据库 schema。
- 不引入 SSR 数据获取或 React Server Components 的服务端数据模式；所有页面实质上仍为 Client Components（`'use client'`），仅利用 App Router 的文件路由和嵌套布局。
- 不改动 `@shared/types` 和 `@shared/hooks` 的任何代码。`@shared/api` 的 `createApiClient` 仅增加一个可选 `baseURL` 参数（默认值保持 `import.meta.env.VITE_API_BASE_URL`），Tenant 端不传参行为不变。
- 不在本 change 建立新的跨应用共享 UI 包；Admin 使用 shadcn/ui 组件直接放在 `admin-next/` 内部。后续 Tenant 迁移时再决定是否抽取共享 UI 层。
- 不改变现有 CI/CD 对 Tenant 端的构建和部署流程。

## Capabilities

### New Capabilities

- `admin-nextjs-app`: Admin 端 SHALL 以 Next.js 15 App Router 架构提供与现有 Vite SPA 完全一致的功能，包括全部 12 个页面、认证、权限控制、GrapesJS 邮件编辑器。

### Modified Capabilities

- 无业务功能变更。所有页面的用户可见行为、API 调用、数据展示 SHALL 与现有 Vite 版本保持一致。

## Impact

| 模块 | 影响 |
| --- | --- |
| 前端 Admin | 新建 `frontend/apps/admin-next/`（Next.js 15 + App Router + shadcn/ui + Tailwind）；完成验证后删除 `frontend/apps/admin/`（Vite + antd）。 |
| 共享包 @shared/* | `@shared/api` 的 `createApiClient` 增加可选 `baseURL` 参数（Tenant 端不传参，行为不变）。`@shared/types` 和 `@shared/hooks` 无改动。Admin 不再依赖 `@shared/ui`。 |
| 部署 | 过渡期新增 `clientget-admin-next` Docker 镜像（Next.js standalone）+ 部署脚本 `frontend/deploy/push-admin-next.sh`；迁移完成验证后，镜像名改回 `clientget-admin`，旧 `push-admin.sh` 移除。 |
| 后端 | 无改动。 |
| 数据库 | 无改动。 |
| Tenant 端 | 无改动。继续使用 Vite + antd 架构。 |
| Monorepo | pnpm workspace 添加 `frontend/apps/admin-next`；可能需要更新根 `turbo.json` 或 `pnpm-workspace.yaml`。 |

## Relationship to Other Changes

- `admin-peer-company-cleaning` 已实现 Next.js 版同行数据（清洗）页面。本 change 覆盖范围更大（全量重写），需要把该页面接入当前 `apps/admin-next` 的 App Router、侧边栏和认证布局，而不是重新基于旧 antd Admin 页面实现。
