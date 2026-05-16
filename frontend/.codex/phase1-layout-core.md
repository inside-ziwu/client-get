# Phase 1: 布局与核心路径

> 前置：Phase 0 已完成（@shared/ui 可用，tenant-next 脚手架就绪）
> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`

## 目标

建立 Tenant-next 的完整布局框架（侧边栏 + 顶部导航 + 认证守卫），并实现登录、Dashboard、Onboarding 三个核心页面。完成后应能：登录 → 看到 Dashboard → 侧边栏导航 → 登出。

## 路由结构

参照现有 Tenant 路由（见 `apps/tenant/src/router.tsx`），在 App Router 下：

```
src/app/
├── layout.tsx          ← 已有（Phase 0D）
├── login/page.tsx      ← 登录页（不需要 RequireAuth）
├── onboarding/page.tsx ← 引导页（不需要 RequireAuth）
├── (dashboard)/
│   ├── layout.tsx      ← RequireAuth + AppShell 包装
│   ├── page.tsx        ← Dashboard（首页）
│   ├── companies/page.tsx        ← 后续 Phase
│   ├── curated-customers/page.tsx
│   ├── templates/page.tsx
│   ├── send-plans/
│   │   ├── page.tsx
│   │   ├── new/page.tsx
│   │   └── [id]/page.tsx
│   ├── email-monitor/page.tsx
│   ├── intelligence/page.tsx
│   └── settings/
│       ├── keywords/page.tsx
│       ├── scoring/page.tsx
│       ├── ai-provider/page.tsx
│       └── team/page.tsx
```

## 执行步骤

### 1. RequireAuth 组件

创建 `src/components/auth/require-auth.tsx`，参照 Admin 版本（`apps/admin/src/components/auth/require-auth.tsx`）：

```tsx
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
  if (!token || isExpired()) return null;
  return <>{children}</>;
}
```

### 2. 侧边栏

创建 `src/components/layout/sidebar.tsx`。参照 Admin 的 sidebar（`apps/admin/src/components/layout/sidebar.tsx`），但菜单结构不同：

```
菜单分组：
- 工作台（/dashboard 或 /）— LayoutDashboard 图标
- 客户
  - 公司列表（/companies）— Building2 图标
  - 优选客户（/curated-customers）— Star 图标
- 营销
  - 邮件模板（/templates）— FileText 图标
  - 发送计划（/send-plans）— Send 图标
  - 邮件监控（/email-monitor）— BarChart3 图标
- 情报
  - 情报中心（/intelligence）— Search 图标
- 设置
  - 关键词（/settings/keywords）— Key 图标
  - 评分配置（/settings/scoring）— BarChart3 图标
  - AI 提供商（/settings/ai-provider）— Bot 图标
  - 团队管理（/settings/team）— Users 图标
```

用 `next/link` + `usePathname()` 做高亮。所有图标用 lucide-react。

### 3. AppShell

创建 `src/components/layout/app-shell.tsx`。包含：
- 顶部导航条：左侧显示面包屑或标题，右侧显示用户信息 + 登出按钮
- 侧边栏（上一步创建的）
- 主内容区

参照 Admin 的 `apps/admin/src/components/layout/`。

### 4. Dashboard 布局

创建 `src/app/(dashboard)/layout.tsx`：
```tsx
'use client';
import { RequireAuth } from '@/components/auth/require-auth';
import { AppShell } from '@/components/layout/app-shell';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
```

### 5. 登录页

创建 `src/app/login/page.tsx`。参照现有 `apps/tenant/src/pages/Login/index.tsx`（约 87 行）。

核心功能：
- 输入公司 slug、邮箱、密码
- 调用 `tenantApi.login({ slug, email, password })`
- 成功后 JWT 存入 sessionStorage（通过 useAuthStore）
- 跳转到 `/`（Dashboard）

用 @shared/ui 的 Input、Button、Card 组件。

### 6. Dashboard 页

创建 `src/app/(dashboard)/page.tsx`。参照现有 `apps/tenant/src/pages/Dashboard/index.tsx`（约 387 行）。

核心功能：
- 自建 StatCard 组件（简单的数字展示卡片：标题 + 数值 + 变化趋势）
- 概览卡片（公司数、联系人数等统计）
- 漏斗图（简单的 div 进度条即可）
- AI 能力状态
- 快速链接

用 @shared/ui 的 Card 组件。

### 7. Onboarding 页

创建 `src/app/onboarding/page.tsx`。参照现有 `apps/tenant/src/pages/Onboarding/index.tsx`（约 150 行）。

核心功能：
- 自建 Stepper 组件（步骤指示器）
- 引导步骤流程
- 完成后跳转到 Dashboard

### 8. 端到端验证

- 启动 `pnpm dev`，在浏览器中：
  - 访问 `/` → 未登录应跳转到 `/login`
  - 登录 → 跳转到 Dashboard，看到统计数据
  - 侧边栏可点击，菜单高亮正确
  - 点登出 → 返回登录页

## 约束

- 所有页面文件顶部加 `'use client'`
- 不改后端 API
- 表单用 useState，不引入 react-hook-form
- 数据获取用 TanStack Query（useQuery / useMutation）
- 图表不引入 recharts 等重库，用简单的 div + CSS 实现
