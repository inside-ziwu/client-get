# Design · tenant-nextjs-rewrite

## Context

Admin 端 Next.js 迁移（`2026-05-13-admin-nextjs-rewrite`）已归档，积累了完整的架构决策和实施经验。Tenant 端迁移沿用 Admin 的技术选型，新增 `@shared/ui` 提取和两端共享方案。

## Goals / Non-Goals

**Goals:**
- Tenant 12 个页面在 Next.js App Router 下完整重建，用户可见行为与现有版本一致
- `@shared/ui` 重构为 Tailwind + Radix 基础组件库，Admin 和 Tenant 共用
- 部署方式与 Admin 对齐（Next.js standalone Docker）

**Non-Goals:**
- 不引入 SSR / Server Components 数据模式
- 不统一表单方案（后续 change）
- 不改后端 API 或数据库

## Decisions

### D-1: 沿用 Admin 的 Next.js 架构决策

与 `admin-nextjs-rewrite` 的 D-1/D-3/D-4/D-5 保持一致：

- App Router，页面标记 `'use client'`
- TanStack Query 5 + Zustand 5 + Axios 不变
- Next.js standalone + Docker 部署
- 开发环境 rewrites 代理，生产环境 `NEXT_PUBLIC_API_BASE_URL` 直连后端

### D-2: `@shared/ui` 重构为 Tailwind + Radix 共享库

```
packages/shared-ui/
├── src/
│   ├── components/              ← 从 Admin 提取的 27 个 shadcn 基础组件
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── table.tsx
│   │   ├── ...
│   │   ├── status-tag.tsx       ← 业务标签组件（重写为 Tailwind）
│   │   ├── rating-tag.tsx
│   │   └── contact-status-tag.tsx
│   ├── lib/
│   │   └── utils.ts             ← cn() = clsx + tailwind-merge
│   ├── theme/
│   │   ├── globals.css          ← CSS 变量色彩系统（HSL）
│   │   └── tailwind-preset.ts   ← Tailwind preset（colors/radius/animate）
│   └── index.ts                 ← 统一导出
├── package.json                 ← 依赖：radix-ui, clsx, tailwind-merge, cva, lucide-react
└── tsconfig.json
```

**消费端配置**（Admin / Tenant-next 的 tailwind.config）：

```ts
import sharedPreset from '@shared/ui/theme/tailwind-preset'

export default {
  presets: [sharedPreset],
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/shared-ui/src/**/*.{ts,tsx}',
  ],
}
```

**迁移策略**：
1. 先将 Admin 本地 `src/components/ui/` 搬到 `@shared/ui`
2. Admin 改 import 路径，验证构建通过
3. Tenant-next 直接从 `@shared/ui` 导入

### D-3: 认证/权限组件 — 各 app 自建

> **Review 修订**：原方案拟将 RequireAuth 等组件抽象到 @shared/hooks 做通用化。审查发现 Admin 已有自建 RequireAuth（19 行，直接用 `next/navigation`），通用化抽象只增加一层间接调用而不减少代码量。

**最终方案**：各 app 自建 RequireAuth，@shared/ui 中的旧 RequireAuth / PermissionGate / AIAccessGuard 在 Phase 0A 重构时直接删除。

Admin 现有（参照）：
```tsx
// apps/admin/src/components/auth/require-auth.tsx — 19 行
'use client';
import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';
export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const isExpired = useAuthStore((state) => state.isExpired);
  useEffect(() => {
    if (!token || isExpired()) { router.replace('/login'); }
  }, [token, isExpired, router]);
  return <>{children}</>;
}
```

Tenant-next 在 Phase 1.4 复制同样模式。

### D-4: Ant Design → shadcn 组件映射

沿用 Admin 迁移（D-2）的映射表，Tenant 特有补充：

| Tenant 中的 antd 组件 | shadcn/自建 对应 | 备注 |
|----------------------|-----------------|------|
| Table（排序/筛选/分页） | table.tsx + 手动状态管理 | 参照 Admin peers 页面模式 |
| Form + Form.Item | 原生 form + useState | 本次不引入 react-hook-form |
| Statistic | 自建 StatCard | 简单数字展示，Dashboard 用 |
| Progress | 自建或 Radix Progress | 发送计划进度 |
| Descriptions | 自建 dl/dt/dd 布局 | 详情展示 |
| Steps | 自建 Stepper | Onboarding 流程 |
| DatePicker | date-picker + react-day-picker | 沿用 Admin 方案 |
| Popconfirm | AlertDialog | 确认删除等场景 |
| Drawer | Sheet | 公司详情侧滑面板 |
| Menu（侧边栏） | 自建 Sidebar | 参照 Admin sidebar.tsx |
| ConfigProvider locale | 不需要 | antd 国际化随 antd 一起移除 |
| Select mode="tags" | cmdk MultiSelect（自建） | 多选 + 自由文本输入，Companies 5 个筛选字段用 |

### D-5: 渐进式开发与共存策略

```
开发期：
frontend/apps/
├── admin/           ← Phase 0 改 import 路径后继续运行
├── tenant/          ← 继续运行、继续部署，不做任何修改
└── tenant-next/     ← 新建，逐步填充页面

pnpm-workspace.yaml 增加 tenant-next

完成后：
├── admin/
├── tenant-next/ → 重命名为 tenant/
└── (旧 tenant/ 删除)
```

开发期间老 Tenant 照常部署和使用。新 Tenant-next 在所有 12 个页面完成并通过回归测试后，一次性切换部署。

### D-6: Tenant 侧边栏结构

```
┌─────────────────────────────┐
│  ClientGet    [用户头像 ▼]  │
├─────────────────────────────┤
│                             │
│  📊 工作台                   │
│                             │
│  ── 客户 ──                 │
│  🏢 公司列表                 │
│  ⭐ 优选客户                 │
│                             │
│  ── 营销 ──                 │
│  📧 邮件模板                 │
│  📬 发送计划                 │
│  📈 邮件监控                 │
│                             │
│  ── 情报 ──                 │
│  🔍 情报中心                 │
│                             │
│  ── 设置 ──                 │
│  🔑 关键词                   │
│  📊 评分配置                 │
│  🤖 AI 提供商                │
│  👥 团队管理                 │
│                             │
└─────────────────────────────┘
```

### D-7: API 访问方案

与 Admin 一致：

- 开发环境：`next.config.ts` rewrites `/t/*` → `http://localhost:8000`
- 生产环境：构建时注入 `NEXT_PUBLIC_API_BASE_URL=https://api.xinanpcb.com`，浏览器直连后端
- `@shared/api` 的 `createApiClient` 传入 `baseURL` 参数

### D-8: 页面复杂度分档与迁移顺序

| 档位 | 页面 | 原始行数 | 核心难点 |
|------|------|---------|---------|
| L | Login | ~87 | 无 |
| L | Onboarding | ~150 | Steps 组件自建 |
| L | Intelligence | ~200 | 简单列表 |
| L | Settings/Keywords | ~150 | 简单 CRUD |
| L | Settings/AIProvider | ~200 | 表单 + 统计 |
| L | Settings/Team | ~200 | 表格 + 邀请表单 |
| M | Dashboard | ~387 | StatCard 自建 + 漏斗图 |
| M | Templates | ~250 | 模板 CRUD |
| M | EmailMonitor | ~300 | 统计图表 |
| M | Settings/Scoring | ~250 | 权重调整 |
| M | CuratedCustomers | ~300 | 表格 + 筛选 |
| H | Companies | ~698 | 10 项筛选 + Drawer 详情 |
| H | SendPlans (3页) | ~700 | 列表 + 新建表单 + 详情监控 |

### D-9: cmdk MultiSelect 组件

> **Review 新增**：Tenant Companies 页面有 5 个筛选字段使用 antd `Select mode="tags"`（多选 + 自由文本输入），shadcn Select 原生不支持。

方案：基于 cmdk + Popover 自建 MultiSelect 组件，放入 `@shared/ui`。核心能力：
- 多选 checkbox 模式
- 自由文本输入创建新选项
- 已选项以 Badge 展示，可单独删除
- 支持异步搜索（筛选项可能来自后端）

在 Phase 2.0 实施，阻塞 Phase 2.2 Companies 页面。

### D-10: 开发环境 CORS 配置

> **Review 新增**：tenant-next 开发端口与 Admin 不同，后端 CORS 允许列表需添加新端口。

后端 `backend/app/main.py` 的 CORS origins 列表添加 `http://localhost:3001`（或实际使用的端口）。在 Phase 0D.10 实施。
