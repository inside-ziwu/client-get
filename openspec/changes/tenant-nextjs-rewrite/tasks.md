# Tasks · tenant-nextjs-rewrite

## Phase 0: 基础设施 — @shared/ui 提取与脚手架

### 0A: @shared/ui 重构

- [ ] 0A.1 重写 `packages/shared-ui/package.json`：移除 antd / react-router-dom 依赖，新增 @radix-ui/* / clsx / tailwind-merge / class-variance-authority / lucide-react
- [ ] 0A.2 将 Admin `src/components/ui/` 27 个 shadcn 组件复制到 `packages/shared-ui/src/components/`
- [ ] 0A.3 创建 `packages/shared-ui/src/lib/utils.ts`（cn 函数）
- [ ] 0A.4 创建 `packages/shared-ui/src/theme/tailwind-preset.ts`（共享 Tailwind preset：colors / borderRadius / animate）
- [ ] 0A.5 创建 `packages/shared-ui/src/theme/globals.css`（CSS 变量色彩系统，从 Admin globals.css 提取）
- [ ] 0A.6 重写 StatusTag / RatingTag / ContactStatusTag 为 Tailwind + Badge 组件
- [ ] 0A.7 创建 `packages/shared-ui/src/index.ts` 统一导出
- [ ] 0A.8 更新 `packages/shared-ui/tsconfig.json`

### ~~0B: @shared/hooks 迁移权限组件~~ — 已删除

> **Review D3 决策**：RequireAuth / PermissionGate / AIAccessGuard 不做通用化抽象。Admin 已有自建 RequireAuth（19 行），Tenant-next 在 Phase 1.4 自建。老 @shared/ui 中的权限组件在 0A 重构时直接删除。

### 0C: Admin 切换到 @shared/ui

- [ ] 0C.1 Admin tailwind.config 引入 sharedPreset，content 增加 shared-ui 路径
- [ ] 0C.2 批量替换 Admin 中 `@/components/ui/xxx` 为 `@shared/ui` 导入
- [ ] 0C.3 删除 Admin `src/components/ui/` 目录（基础组件已在 @shared/ui）
- [ ] 0C.4 验证 Admin `pnpm dev` 正常运行，所有页面功能不变
- [ ] 0C.5 验证 Admin `pnpm build` 构建通过

### 0D: Tenant-next 脚手架

- [ ] 0D.1 在 `frontend/apps/tenant-next/` 初始化 Next.js 15 项目（App Router, TypeScript）
- [ ] 0D.2 配置 tailwind.config：引入 sharedPreset，content 包含 shared-ui
- [ ] 0D.3 创建 globals.css（导入 @shared/ui 的 CSS 变量，或复用 Admin 的）
- [ ] 0D.4 配置 tsconfig.json path alias 指向 @shared/* 包
- [ ] 0D.5 配置 next.config.ts：rewrites 代理 `/t/*` 到后端、output standalone、transpilePackages
- [ ] 0D.6 安装依赖：@tanstack/react-query, zustand, axios, dayjs, sonner, lucide-react
- [ ] 0D.7 创建 src/providers.tsx（QueryClientProvider + Sonner）
- [ ] 0D.8 创建 src/lib/api.ts（调用 createApiClient + createTenantApi）
- [ ] 0D.9 更新 pnpm-workspace.yaml 增加 tenant-next
- [ ] 0D.10 后端 CORS 允许列表添加 tenant-next 开发端口（如 3001）
- [ ] 0D.11 验证 `pnpm dev` 能启动且代理到本地后端正常

## Phase 1: 布局与核心路径

- [ ] 1.1 创建根布局 `src/app/layout.tsx`（html/body + providers）
- [ ] 1.2 创建侧边栏 `src/components/layout/sidebar.tsx`（Tenant 菜单结构：工作台/客户/营销/情报/设置）
- [ ] 1.3 创建 AppShell `src/components/layout/app-shell.tsx`（顶部导航 + 用户信息 + 登出）
- [ ] 1.4 创建 `(dashboard)/layout.tsx`（自建 RequireAuth + AppShell 包装）
- [ ] 1.5 创建登录页 `/login/page.tsx`（slug + email + password 表单 → JWT → 跳转）
- [ ] 1.6 创建 Dashboard `/page.tsx`（StatCard 自建 + 概览卡片 + 漏斗图 + AI 能力状态 + 快速链接）
- [ ] 1.7 创建 Onboarding `/onboarding/page.tsx`（引导步骤流程）
- [ ] 1.8 端到端验证：登录 → Dashboard → 侧边栏导航 → 登出

## Phase 2: 数据密集页面

- [ ] 2.0 自建 cmdk MultiSelect 组件到 `@shared/ui`（替代 antd Select mode="tags"，支持多选 + 自由输入）
- [ ] 2.1 自建缺失组件：StatCard / Progress / DescriptionList（如 Phase 1 未覆盖）
- [ ] 2.2 Companies `/companies/page.tsx`（10 项筛选 + 表格 + Drawer 详情 + 私有操作）
- [ ] 2.3 CuratedCustomers `/curated-customers/page.tsx`（共用筛选组件 + 表格）
- [ ] 2.4 SendPlans 列表 `/send-plans/page.tsx`（状态切换 + 表格）
- [ ] 2.5 SendPlans 新建 `/send-plans/new/page.tsx`（多步表单）
- [ ] 2.6 SendPlans 详情 `/send-plans/[id]/page.tsx`（详情 + 监控数据）

## Phase 3: 功能页面

- [ ] 3.1 Templates `/templates/page.tsx`（模板 CRUD + 预览）
- [ ] 3.2 EmailMonitor `/email-monitor/page.tsx`（邮件统计 + 趋势 + AI 分析）
- [ ] 3.3 Intelligence `/intelligence/page.tsx`（情报文章列表 + 订阅管理）

## Phase 4: 设置页面

- [ ] 4.1 Settings/Keywords `/settings/keywords/page.tsx`（关键词 CRUD）
- [ ] 4.2 Settings/Scoring `/settings/scoring/page.tsx`（评分权重调整）
- [ ] 4.3 Settings/AIProvider `/settings/ai-provider/page.tsx`（OpenRouter 配置 + 用量统计）
- [ ] 4.4 Settings/Team `/settings/team/page.tsx`（团队成员管理 + 邀请）

## Phase 5: 部署与收尾

- [ ] 5.1 创建 Tenant-next Dockerfile（多阶段构建：pnpm install → next build → node standalone）
- [ ] 5.2 重写 `frontend/deploy/push-tenant.sh`（适配 Next.js standalone 镜像）
- [ ] 5.3 创建 `/api/healthz` route handler（替代 nginx /healthz）
- [ ] 5.4 更新 Sealos 健康检查路径配置（从 nginx /healthz 到 Next.js /api/healthz）
- [ ] 5.5 创建 `tenant-next/test/foundation-contract.test.mjs`（参照 Admin contract test，覆盖 15 条断言）
- [ ] 5.6 全量回归测试：12 个页面逐一验证功能与现有版本一致
- [ ] 5.7 验证 Tenant 老版本 `pnpm dev` 和 `pnpm build` 不受影响
- [ ] 5.8 删除 `frontend/apps/tenant/`（旧 Vite 版本）
- [ ] 5.9 将 `frontend/apps/tenant-next/` 重命名为 `frontend/apps/tenant/`
- [ ] 5.10 清理 @shared/ui 中残留的 antd 相关代码（如有）
- [ ] 5.11 更新 monorepo 根 package.json 的 dev:tenant / build:tenant 脚本
