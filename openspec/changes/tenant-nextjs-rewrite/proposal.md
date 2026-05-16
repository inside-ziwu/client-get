# Proposal · tenant-nextjs-rewrite

> 前序：`admin-nextjs-rewrite`（已归档 `2026-05-13-admin-nextjs-rewrite`）
> 关联：`@shared/ui` 重构（随本 change 一并完成）

## Why

Admin 端已完成 Next.js 15 + shadcn/ui + Tailwind CSS 迁移（归档 `2026-05-13-admin-nextjs-rewrite`）。Tenant 端仍使用 Vite 7 + React Router v7 + Ant Design v6，技术栈分裂导致：

1. **开发者心智负担** — 在两端切换时需要适应完全不同的 UI 组件 API（antd vs Radix）、路由方式（React Router vs App Router）和样式方案（antd 主题 vs Tailwind）。
2. **共享组件无法共享** — `@shared/ui` 绑定了 antd + react-router-dom，Admin 已不依赖它；两端 UI 复用实质为零。
3. **构建和部署不一致** — Admin 用 Next.js standalone + Node 运行；Tenant 用 Vite 构建 + Nginx 静态托管。两套 Dockerfile、两套部署逻辑。

本 change 将 Tenant 端迁移到与 Admin 一致的技术栈，并借此机会重构 `@shared/ui` 为 Tailwind + Radix 基础组件库，实现两端真正的 UI 共享。

## What Changes

### 引入

#### 新应用 `frontend/apps/tenant-next/`

- Next.js 15 + App Router + TypeScript
- Tailwind CSS + shadcn/ui（从 `@shared/ui` 导入基础组件）
- TanStack Query 5 + Zustand 5 + Axios（数据层不变）
- 12 个现有页面在 App Router 文件路由下全部重建：
  - `/login` — 登录页
  - `/onboarding` — 新手引导
  - `/` = `/dashboard` — 仪表盘
  - `/companies` — 公司管理
  - `/curated-customers` — 优选客户
  - `/templates` — 邮件模板
  - `/send-plans` — 发送计划列表
  - `/send-plans/new` — 新建计划
  - `/send-plans/:id` — 计划详情
  - `/email-monitor` — 邮件监控
  - `/intelligence` — 情报中心
  - `/settings/keywords` — 关键词管理
  - `/settings/scoring` — 评分配置
  - `/settings/ai-provider` — AI 提供商
  - `/settings/team` — 团队管理
- 认证：JWT sessionStorage 方案不变；Next.js middleware 做路由守卫
- 部署：Next.js standalone Docker 镜像，与 Admin 一致

#### `@shared/ui` 重构为 Tailwind + Radix 基础组件库

- 从 Admin `src/components/ui/` 提取 27 个 shadcn 基础组件到 `packages/shared-ui/src/components/`
- 业务标签组件（StatusTag / RatingTag / ContactStatusTag）从 antd 重写为 Tailwind
- 导出 Tailwind preset（色彩变量、borderRadius、animate 插件），供两端 tailwind.config 引用
- 导出 `cn()` 工具函数
- 删除所有 antd / react-router-dom 依赖

#### 认证/权限组件迁移到 `@shared/hooks`

- `RequireAuth` / `PermissionGate` / `AIAccessGuard` 从 `@shared/ui` 移到 `@shared/hooks`
- 重写为纯逻辑组件（不依赖 react-router-dom，由调用方传入 navigate/location）

### 修改

- **Admin `src/components/ui/`** — 删除本地 shadcn 组件，改为从 `@shared/ui` 导入
- **Admin tailwind.config** — 引入 `@shared/ui` 的 Tailwind preset，content 路径增加 shared-ui
- **Admin 认证/权限组件引用** — 改为从 `@shared/hooks` 导入

### 移除

- 迁移完成验证后删除 `frontend/apps/tenant/`（Vite + antd 版本）
- `@shared/ui` 中所有 antd / react-router-dom 相关代码

## Non-Goals

- ❌ 不修改后端 API；所有 Tenant API 端点保持现有契约
- ❌ 不修改数据库 schema
- ❌ 不引入 SSR 数据获取或 Server Components 服务端数据模式；页面实质上仍为 Client Components
- ❌ 不统一表单方案（react-hook-form + zod）；本次保持 useState 简单表单模式，表单统一作为后续独立 change
- ❌ 不引入 TanStack Table；表格沿用 Admin 的原生 HTML table + 手动状态管理模式
- ❌ 不改动 `@shared/types` 和 `@shared/api` 的任何代码
- ❌ 不改动 Admin 的业务页面逻辑，仅修改 UI 组件 import 路径

## Impact

| 模块 | 影响 |
|------|------|
| 前端 Tenant | 新建 `frontend/apps/tenant-next/`；完成验证后删除 `frontend/apps/tenant/` |
| 共享包 @shared/ui | 全面重构：antd → shadcn/Tailwind；Admin 和 Tenant-next 共用 |
| 共享包 @shared/hooks | 新增 RequireAuth / PermissionGate / AIAccessGuard（纯逻辑版） |
| 共享包 @shared/types, @shared/api | 无改动 |
| Admin 前端 | 改 import 路径（本地 ui → @shared/ui）；无业务逻辑改动 |
| 部署 | Tenant Docker 从 nginx 静态 → Next.js standalone；push-tenant.sh 重写 |
| 后端 | 无改动 |
| 数据库 | 无改动 |

## Relationship to Other Changes

- 前序 `2026-05-13-admin-nextjs-rewrite`（已归档）— Admin 端已完成 Next.js 迁移，本 change 复用其架构决策和组件方案
- 后续计划 — 表单方案统一（react-hook-form + zod），待本 change 完成后另开 change
