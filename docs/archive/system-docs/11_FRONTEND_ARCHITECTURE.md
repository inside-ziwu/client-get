# 11 前端架构设计

> **版本**: v1.0
> **日期**: 2026-04-17
> **输入文档**: `04_FRONTEND_MAP.md`（现有前端）、`07_REQUIREMENTS_SPEC.md`（需求规格）、`08_UI_SPEC.md`（界面规格）、`09_DATABASE_DESIGN.md`（数据库设计）、`10_API_DESIGN.md`（API设计）
> **目标读者**: 前端开发工程师、AI Agent
> **技术栈**: React 19 + TypeScript 5.5+ + Ant Design 6 + Vite 7 + react-router-dom 7

---

## 目录

1. [架构总览](#1-架构总览)
2. [Monorepo 工程结构](#2-monorepo-工程结构)
3. [双应用路由设计](#3-双应用路由设计)
4. [认证与授权](#4-认证与授权)
5. [状态管理](#5-状态管理)
6. [API 层设计](#6-api-层设计)
7. [共享组件库](#7-共享组件库)
8. [页面-API 映射](#8-页面-api-映射)
9. [RBAC 前端实现](#9-rbac-前端实现)
10. [主题与样式体系](#10-主题与样式体系)
11. [性能优化策略](#11-性能优化策略)
12. [测试策略](#12-测试策略)
13. [构建与部署](#13-构建与部署)
14. [从现有前端迁移](#14-从现有前端迁移)

---

## 1. 架构总览

### 1.1 双应用架构

系统采用两个独立 React 应用，共享一个组件库，通过 pnpm workspace monorepo 管理：

```
┌─────────────────────────────────────────────────────────┐
│                      Monorepo (pnpm workspace)          │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │   Admin App     │  │   Tenant App    │               │
│  │  admin.xxx.com  │  │  app.xxx.com    │               │
│  │                 │  │                 │               │
│  │  7 pages        │  │  14 pages       │               │
│  │  platform ops   │  │  tenant users   │               │
│  │  独立 JWT       │  │  JWT+tenant_id  │               │
│  └────────┬────────┘  └────────┬────────┘               │
│           │                    │                        │
│           └──────┬─────────────┘                        │
│                  │                                      │
│         ┌────────▼────────┐                             │
│         │  @shared/ui     │  共享组件库                   │
│         │  @shared/hooks  │  共享 Hooks                  │
│         │  @shared/api    │  API 客户端                   │
│         │  @shared/types  │  TypeScript 类型              │
│         └─────────────────┘                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Admin API: /admin/api/v1/*                     │    │
│  │  Tenant API: /t/{slug}/api/v1/*                 │    │
│  │  见 10_API_DESIGN.md                             │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术选型

| 层 | 选型 | 理由 |
|---|------|------|
| 框架 | React 19 | 延续现有技术栈，CSR SPA 架构（Vite 构建，非 Next.js/SSR） |
| 语言 | TypeScript 5.5+ | 严格模式，`noUncheckedIndexedAccess` |
| UI 库 | Ant Design 6 | 延续现有，企业级组件完备 |
| 构建 | Vite 7 | 延续现有，HMR 极快 |
| 路由 | react-router-dom 7 | 延续现有，支持 loader/action 模式 |
| 状态管理 | Zustand 5 | 轻量级，替代纯 Hooks（见 `04_FRONTEND_MAP.md` §5 产品化标注） |
| 数据请求 | TanStack Query 5 + Axios | 缓存/重试/乐观更新，Axios 拦截器复用 |
| 图表 | @ant-design/charts (G2) | 与 AntD 风格统一 |
| 富文本 | TinyMCE 7 | 邮件模板编辑，支持变量插入 |
| Monorepo | pnpm workspace | 原生支持，无额外工具 |

### 1.3 与现有系统差异

| 维度 | 现有（`04_FRONTEND_MAP.md`） | 新架构 |
|------|------|------|
| 应用数量 | 单应用 12 页面 | 双应用 21 页面（Admin 7 + Tenant 14） |
| 路由 | `/plans`, `/companies` 等 | Admin: `/data-sources` 等；Tenant: `/dashboard` 等（slug 仅存在于 API 前缀） |
| 状态管理 | 纯 React Hooks | Zustand + TanStack Query |
| API 层 | 裸 Axios，无版本化 | TanStack Query + Axios，`/api/v1/` 前缀 |
| 认证 | 单 JWT，无多租户 | Admin JWT + Tenant JWT（含 `tid`/`slug`/`roles`） |
| RBAC | 无 | 三角色（admin/operator/viewer），页面级+元素级控制 |
| 实时更新 | 10s 轮询（部分页面） | TanStack Query `refetchInterval` 统一管理 |

---

## 2. Monorepo 工程结构

```
frontend/
├── pnpm-workspace.yaml
├── package.json                    # workspace root
├── tsconfig.base.json              # 共享 TS 配置
├── .eslintrc.cjs                   # 共享 ESLint
├── .prettierrc                     # 共享格式化
│
├── packages/
│   ├── shared-types/               # @shared/types
│   │   ├── package.json
│   │   └── src/
│   │       ├── api.ts              # API 请求/响应类型
│   │       ├── models.ts           # 业务实体类型
│   │       ├── auth.ts             # JWT payload / 认证类型
│   │       └── enums.ts            # 评级/状态/角色枚举
│   │
│   ├── shared-api/                 # @shared/api
│   │   ├── package.json
│   │   └── src/
│   │       ├── client.ts           # Axios 实例工厂
│   │       ├── admin/              # Admin API endpoints
│   │       ├── tenant/             # Tenant API endpoints
│   │       └── query-keys.ts       # TanStack Query key 工厂
│   │
│   ├── shared-hooks/               # @shared/hooks
│   │   ├── package.json
│   │   └── src/
│   │       ├── useAuth.ts          # 认证状态 hook
│   │       ├── usePermission.ts    # RBAC 权限判断 hook
│   │       ├── useAIBalance.ts     # AI 余额状态 hook
│   │       └── usePagination.ts    # 游标分页 hook
│   │
│   └── shared-ui/                  # @shared/ui
│       ├── package.json
│       └── src/
│           ├── RatingTag.tsx        # S/A/B/C/D 评级标签
│           ├── StatusTag.tsx        # 状态标签
│           ├── CompanyDetailDrawer/ # 公司详情 Drawer（4 Tab）
│           ├── ScoreRadarChart.tsx  # 评分雷达图（ECharts radar）
│           ├── TemplateEditor/     # 邮件模板编辑器
│           ├── ExcelImporter/      # Excel 导入流程
│           ├── AIBalanceGuard.tsx   # AI 余额置灰包装器
│           ├── NotificationBell/   # 通知铃铛
│           └── AppLayout/          # 通用布局（侧边栏+顶栏）
│
├── apps/
│   ├── admin/                      # Admin 应用
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── router.tsx          # Admin 路由定义
│   │       ├── stores/             # Admin Zustand stores
│   │       ├── pages/              # 7 个页面
│   │       │   ├── DataSources/
│   │       │   ├── ScoringTemplates/
│   │       │   ├── IntelligenceSources/
│   │       │   ├── EmailTemplates/
│   │       │   ├── WarmupRules/
│   │       │   ├── AIConfig/
│   │       │   └── Tenants/
│   │       └── components/         # Admin 专属组件
│   │
│   └── tenant/                     # Tenant 应用
│       ├── package.json
│       ├── vite.config.ts
│       ├── index.html
│       └── src/
│           ├── main.tsx
│           ├── router.tsx          # Tenant 路由定义
│           ├── stores/             # Tenant Zustand stores
│           ├── pages/              # 14 个页面
│           │   ├── Login/
│           │   ├── Onboarding/
│           │   ├── Dashboard/
│           │   ├── Companies/
│           │   ├── CuratedCustomers/
│           │   ├── Templates/
│           │   ├── SendPlans/
│           │   ├── EmailMonitor/
│           │   ├── Intelligence/
│           │   └── Settings/
│           │       ├── Keywords/
│           │       ├── Scoring/
│           │       ├── ContactRules/
│           │       ├── AIBalance/
│           │       └── Team/
│           └── components/         # Tenant 专属组件
│               ├── OnboardingWizard/
│               └── GroupSidebar/
```

**pnpm-workspace.yaml**:

```yaml
packages:
  - 'packages/*'
  - 'apps/*'
```

---

## 3. 双应用路由设计

### 3.1 Admin 端路由

见 `08_UI_SPEC.md` §3.1 导航结构，对应 `10_API_DESIGN.md` §5 Admin API。

```typescript
// apps/admin/src/router.tsx
import { createBrowserRouter } from 'react-router-dom';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/',
    lazy: () => import('./layouts/AdminLayout'),
    children: [
      { index: true, lazy: () => import('./pages/DataSources') },
      { path: 'data-sources', lazy: () => import('./pages/DataSources') },
      { path: 'scoring-templates', lazy: () => import('./pages/ScoringTemplates') },
      { path: 'intelligence-sources', lazy: () => import('./pages/IntelligenceSources') },
      { path: 'email-templates', lazy: () => import('./pages/EmailTemplates') },
      { path: 'warmup-rules', lazy: () => import('./pages/WarmupRules') },
      { path: 'ai-config', lazy: () => import('./pages/AIConfig') },
      { path: 'tenants', lazy: () => import('./pages/Tenants') },
      { path: 'tenants/:id', lazy: () => import('./pages/TenantDetail') },
    ],
  },
]);
```

### 3.2 Tenant 端路由

见 `08_UI_SPEC.md` §4.1 导航结构 + 附录 A Tenant端页面清单。

**Slug 获取策略**: Tenant 应用部署在 `app.xxx.com`，用户登录时选择/输入租户 slug，登录成功后存入 JWT 的 `slug` 字段。后续所有 API 请求使用 `/t/{slug}/api/v1/...` 前缀。

```typescript
// apps/tenant/src/router.tsx
import { createBrowserRouter } from 'react-router-dom';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/onboarding',
    lazy: () => import('./pages/Onboarding'),
  },
  {
    path: '/',
    lazy: () => import('./layouts/TenantLayout'),
    children: [
      { index: true, lazy: () => import('./pages/Dashboard') },
      { path: 'dashboard', lazy: () => import('./pages/Dashboard') },
      { path: 'companies', lazy: () => import('./pages/Companies') },
      { path: 'curated-customers', lazy: () => import('./pages/CuratedCustomers') },
      { path: 'templates', lazy: () => import('./pages/Templates') },
      { path: 'send-plans', lazy: () => import('./pages/SendPlans') },
      { path: 'send-plans/new', lazy: () => import('./pages/SendPlanWizard') },
      { path: 'send-plans/:id', lazy: () => import('./pages/SendPlanDetail') },
      { path: 'email-monitor', lazy: () => import('./pages/EmailMonitor') },
      { path: 'intelligence', lazy: () => import('./pages/Intelligence') },
      {
        path: 'settings',
        children: [
          { path: 'keywords', lazy: () => import('./pages/Settings/Keywords') },
          { path: 'scoring', lazy: () => import('./pages/Settings/Scoring') },
          { path: 'contact-rules', lazy: () => import('./pages/Settings/ContactRules') },
          { path: 'ai-balance', lazy: () => import('./pages/Settings/AIBalance') },
          { path: 'team', lazy: () => import('./pages/Settings/Team') },
        ],
      },
    ],
  },
]);
```

### 3.3 路由守卫

```typescript
// packages/shared-hooks/src/useAuth.ts
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';

interface JWTPayload {
  sub: string;      // user_id (UUID)
  tid?: string;     // tenant_id (UUID), Admin JWT 无此字段
  slug?: string;    // tenant slug, Admin JWT 无此字段
  roles: string[];  // ['admin'] | ['operator'] | ['viewer']
  exp: number;
}

interface AuthState {
  token: string | null;
  payload: JWTPayload | null;
  setToken: (token: string) => void;
  logout: () => void;
  isExpired: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      payload: null,
      setToken: (token) => set({ token, payload: jwtDecode<JWTPayload>(token) }),
      logout: () => set({ token: null, payload: null }),
      isExpired: () => {
        const p = get().payload;
        return !p || p.exp * 1000 < Date.now();
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
```

**RequireAuth 组件**:

```typescript
// packages/shared-ui/src/RequireAuth.tsx
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, isExpired } = useAuthStore();
  const location = useLocation();

  if (!token || isExpired()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

**RequireOnboarding 组件**（Tenant 端额外守卫）:

```typescript
// apps/tenant/src/components/RequireOnboarding.tsx
function RequireOnboarding({ children }: { children: React.ReactNode }) {
  const { data: profile, isLoading } = useCurrentUser();

  // 请求进行中 — 显示加载状态，避免闪烁或错误重定向
  if (isLoading) {
    return <Spin spinning style={{ width: '100%', marginTop: 120 }} />;
  }

  // 管理员未完成首次配置 → 重定向到向导
  if (profile?.needs_onboarding) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
```

---

## 4. 认证与授权

### 4.1 登录流程

**Admin 端**:

```
用户 → POST /admin/api/v1/auth/login { email, password }
     ← { access_token, token_type: "bearer" }
     → 存入 useAuthStore → 跳转 /
```

**Tenant 端**:

```
用户 → POST /t/{slug}/api/v1/auth/login { email, password }
     ← { access_token, token_type: "bearer", must_change_pwd: boolean }
     → 存入 useAuthStore → must_change_pwd ? 强制改密 : 首次登录检测 → /onboarding 或 /dashboard
```

Tenant 端登录页统一采用**登录表单方式**：用户访问 `app.xxx.com/login`，输入 `slug + email + password`。登录成功后 slug 写入 JWT 与 auth 上下文，后续所有 API 请求自动拼接到 `/t/{slug}/api/v1/*`。

### 4.2 Token 管理

| 事项 | 实现 |
|------|------|
| 存储 | `zustand/persist` → `sessionStorage`（避免跨会话持久化） |
| 附加 | Axios 请求拦截器自动附加 `Authorization: Bearer {token}` |
| 过期 | JWT `exp` 字段检测；Axios 响应拦截器捕获 401 → 清除 token → 跳转登录 |
| 有效期 | 24h（见 `10_API_DESIGN.md` §3.2） |
| 刷新 | Phase 1 不实现 refresh token；过期后重新登录 |

### 4.3 Axios 实例

```typescript
// packages/shared-api/src/client.ts
import axios, { type AxiosInstance } from 'axios';
import { useAuthStore } from '@shared/hooks';

type AppType = 'admin' | 'tenant';

export function createApiClient(appType: AppType): AxiosInstance {
  const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  });

  // 请求拦截：附加 JWT + 构造 URL 前缀
  client.interceptors.request.use((config) => {
    const { token, payload } = useAuthStore.getState();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Tenant 应用自动添加 /t/{slug} 前缀
    if (appType === 'tenant' && payload?.slug) {
      config.baseURL = `${import.meta.env.VITE_API_BASE_URL}/t/${payload.slug}`;
    } else if (appType === 'admin') {
      config.baseURL = `${import.meta.env.VITE_API_BASE_URL}/admin`;
    }
    return config;
  });

  // 响应拦截：401 自动登出
  client.interceptors.response.use(
    (res) => res,
    (error) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return client;
}
```

---

## 5. 状态管理

### 5.1 分层策略

| 层 | 工具 | 场景 |
|---|------|------|
| 服务端状态 | TanStack Query | API 数据缓存、分页、自动刷新、乐观更新 |
| 客户端全局状态 | Zustand | 认证信息、当前用户、UI偏好（侧边栏折叠等） |
| 页面局部状态 | React useState/useReducer | 表单、Modal 开关、临时选择 |

### 5.2 TanStack Query 配置

```typescript
// apps/tenant/src/main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // 30s 内不重新请求
      gcTime: 5 * 60_000,         // 5分钟垃圾回收
      retry: 1,                   // 失败重试 1 次
      refetchOnWindowFocus: false, // 切换标签不自动刷新
    },
  },
});
```

### 5.3 Query Key 工厂

统一管理 query key，避免缓存冲突。**Tenant 端所有 key 以 slug 作为首级作用域，防止多租户缓存泄漏**：

```typescript
// packages/shared-api/src/query-keys.ts

/** 获取当前 tenant slug（从 auth store） */
function tenantScope(): string {
  const slug = useAuthStore.getState().payload?.slug;
  if (!slug) throw new Error('Tenant slug not available');
  return slug;
}

export const queryKeys = {
  // Tenant 端 — 所有 key 以 ['tenant', slug, ...] 开头
  companies: {
    all: () => ['tenant', tenantScope(), 'companies'] as const,
    list: (filters: CompanyFilters) => ['tenant', tenantScope(), 'companies', 'list', filters] as const,
    detail: (id: string) => ['tenant', tenantScope(), 'companies', 'detail', id] as const,
  },
  prospects: {
    all: () => ['tenant', tenantScope(), 'prospects'] as const,
    list: (groupId: string | null, filters: CustomerFilters) =>
      ['tenant', tenantScope(), 'prospects', 'list', groupId, filters] as const,
  },
  groups: {
    all: () => ['tenant', tenantScope(), 'groups'] as const,
    list: () => ['tenant', tenantScope(), 'groups', 'list'] as const,
  },
  sendingPlans: {
    all: () => ['tenant', tenantScope(), 'sending-plans'] as const,
    list: (filters: PlanFilters) => ['tenant', tenantScope(), 'sending-plans', 'list', filters] as const,
    detail: (id: string) => ['tenant', tenantScope(), 'sending-plans', 'detail', id] as const,
  },
  emails: {
    stats: (filters: MonitorFilters) => ['tenant', tenantScope(), 'emails', 'stats', filters] as const,
    trend: (filters: MonitorFilters) => ['tenant', tenantScope(), 'emails', 'trend', filters] as const,
  },
  intelligence: {
    list: (filters: IntelFilters) => ['tenant', tenantScope(), 'intelligence', 'list', filters] as const,
  },
  emailTemplates: {
    all: () => ['tenant', tenantScope(), 'email-templates'] as const,
    official: () => ['tenant', tenantScope(), 'email-templates', 'official'] as const,
    custom: () => ['tenant', tenantScope(), 'email-templates', 'custom'] as const,
  },
  dashboard: {
    overview: () => ['tenant', tenantScope(), 'dashboard', 'overview'] as const,
    funnel: () => ['tenant', tenantScope(), 'dashboard', 'funnel'] as const,
  },
  billing: {
    balance: () => ['tenant', tenantScope(), 'billing', 'balance'] as const,
    transactions: (period: string) => ['tenant', tenantScope(), 'billing', 'transactions', period] as const,
  },
  notifications: {
    unread: () => ['tenant', tenantScope(), 'notifications', 'unread'] as const,
  },

  // Admin 端
  admin: {
    dataSources: { all: ['admin', 'data-sources'] as const },
    scoringTemplates: { all: ['admin', 'scoring-templates'] as const },
    intelligenceSources: { all: ['admin', 'intelligence-sources'] as const },
    emailTemplates: { all: ['admin', 'email-templates'] as const },
    warmupRules: { current: () => ['admin', 'warmup-rules'] as const },
    aiConfig: { current: () => ['admin', 'ai-config'] as const },
    tenants: {
      list: (filters?: TenantFilters) => ['admin', 'tenants', 'list', filters] as const,
      detail: (id: string) => ['admin', 'tenants', 'detail', id] as const,
    },
  },
} as const;
```

### 5.4 Zustand Stores

**Tenant 端**:

```typescript
// apps/tenant/src/stores/uiStore.ts
interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    { name: 'ui-prefs' }
  )
);
```

---

## 6. API 层设计

### 6.1 请求/响应类型

所有 API 遵循 `10_API_DESIGN.md` §3 统一响应格式：

```typescript
// packages/shared-types/src/api.ts

/** 统一成功响应 — 见 10_API_DESIGN.md §4.1 */
interface ApiResponse<T> {
  data: T;            // 成功响应直接包装在 data 字段中，无 code/message 包装
}

/** 游标分页响应 — 见 10_API_DESIGN.md §4.2
 *  实际响应格式: { "data": [...], "pagination": { "cursor", "has_more", "total?" } }
 */
interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    cursor: string | null;   // 下一页游标，基于 UUID v7 时间有序性
    has_more: boolean;
    total?: number;          // 仅 include_total=true 时返回
  };
}

/** 统一错误响应 — 见 10_API_DESIGN.md §4.3 */
interface ApiError {
  error: {
    code: string;             // 如 "VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"
    message: string;
    details?: Record<string, string[]>;
  };
}
```

### 6.2 API 模块示例

```typescript
// packages/shared-api/src/tenant/companies.ts
import type { Company, CompanyFilters, PaginatedResponse } from '@shared/types';

export function companiesApi(client: AxiosInstance) {
  return {
    list: (filters: CompanyFilters) =>
      client.get<PaginatedResponse<Company>>('/api/v1/companies', {
        params: filters,
      }),

    detail: (id: string) =>
      client.get<ApiResponse<Company>>(`/api/v1/companies/${id}`),

    importExcel: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return client.post<ApiResponse<ImportResult>>('/api/v1/companies/batch-import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    blacklist: (id: string) =>
      client.post<void>(`/api/v1/companies/${id}/blacklist`),
  };
}
```

### 6.3 自定义 Hook 模式

每个 API 模块对应一组 TanStack Query hooks：

```typescript
// apps/tenant/src/hooks/useCompanies.ts
export function useCompanyList(filters: CompanyFilters) {
  const api = useTenantApi();
  return useQuery({
    queryKey: queryKeys.companies.list(filters),
    queryFn: () => api.companies.list(filters).then((r) => r.data),
  });
}

export function useCompanyDetail(id: string) {
  const api = useTenantApi();
  return useQuery({
    queryKey: queryKeys.companies.detail(id),
    queryFn: () => api.companies.detail(id).then((r) => r.data.data),
    enabled: !!id,
  });
}

export function useBlacklistCompany() {
  const api = useTenantApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.companies.blacklist(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.companies.all });
    },
  });
}
```

### 6.4 游标分页 Hook

```typescript
// packages/shared-hooks/src/useCursorPagination.ts
export function useCursorPagination<T>(
  queryKey: readonly unknown[],
  fetcher: (cursor?: string) => Promise<PaginatedResponse<T>>
) {
  return useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => fetcher(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => (last.pagination.has_more ? last.pagination.cursor : undefined),
  });
}
```

### 6.5 轮询刷新

邮件监控和发送计划执行中状态需定时刷新（见 `04_FRONTEND_MAP.md` §2.4 和 `08_UI_SPEC.md` §4.7）：

```typescript
// 发送计划详情 — 执行中时 10s 刷新
export function useSendPlanDetail(id: string) {
  const api = useTenantApi();
  const { data } = useQuery({
    queryKey: queryKeys.sendingPlans.detail(id),
    queryFn: () => api.sendingPlans.detail(id).then((r) => r.data.data),
    refetchInterval: (query) => {
      const plan = query.state.data;
      return plan?.status === 'running' ? 10_000 : false;
    },
  });
  return data;
}
```

---

## 7. 共享组件库

见 `08_UI_SPEC.md` §5 共享组件规格。

### 7.1 组件清单

| 组件 | Props 概要 | 使用位置 |
|------|-----------|---------|
| `<RatingTag grade="S" />` | `grade: 'S'|'A'|'B'|'C'|'D'` | 全局 |
| `<StatusTag status="running" />` | `status: PlanStatus` | 发送计划 |
| `<ContactStatusTag status="replied" />` | `status: ContactStatus` | 优选客户 |
| `<AIBalanceGuard>` | `children: ReactNode`，余额 ≤ 0 时 children 置灰 + tooltip | 模板 AI 生成、监控 AI 分析 |
| `<CompanyDetailDrawer id={...} open onClose />` | 宽度 65%，4 Tab（基本信息/评分明细/联系人/邮件记录） | 公司列表、优选客户 |
| `<ScoreRadarChart dimensions={...} />` | ECharts radar，3~8 维度自适应 | CompanyDetailDrawer |
| `<TemplateEditor value onChange />` | TinyMCE + 变量插入工具栏 + 预览 | 模板页、发送计划 Step 3 |
| `<ExcelImporter onComplete />` | 下载模板 → 上传 → 结果报告 Modal | 公司列表、情报源管理 |
| `<NotificationBell />` | 铃铛 + 未读数气泡 + 下拉面板（最近 20 条） | Tenant 端顶栏 |
| `<AppLayout sidebarItems />` | 暗色侧边栏 240px（可折叠 64px）+ 白色顶栏 + 内容区 | 两端通用 |

### 7.2 评级颜色编码

见 `08_UI_SPEC.md` §2.2：

```typescript
// packages/shared-ui/src/RatingTag.tsx
const RATING_COLORS: Record<string, string> = {
  S: 'gold',
  A: 'green',
  B: 'blue',
  C: 'orange',
  D: 'default',
};

export function RatingTag({ grade }: { grade: string }) {
  return <Tag color={RATING_COLORS[grade] ?? 'default'}>{grade}</Tag>;
}
```

### 7.3 AI 余额守卫

见 `08_UI_SPEC.md` §2.3：

```typescript
// packages/shared-ui/src/AIBalanceGuard.tsx
export function AIBalanceGuard({ children }: { children: React.ReactElement }) {
  const { data: balance } = useAIBalance();
  const disabled = (balance?.amount ?? 0) <= 0;

  if (disabled) {
    return (
      <Tooltip title="AI余额不足，请充值">
        {React.cloneElement(children, { disabled: true })}
      </Tooltip>
    );
  }
  return children;
}
```

---

## 8. 页面-API 映射

### 8.1 Admin 端

页面路由对应 `10_API_DESIGN.md` §5 Admin API 端点。

| 页面 | 路由 | 主要 API 端点 |
|------|------|-------------|
| 数据源管理 | `/data-sources` | `GET /admin/api/v1/data-sources`, `GET/POST/PATCH/DELETE /admin/api/v1/data-sources/{type}/credentials`, `PATCH /admin/api/v1/data-sources/{type}/config` |
| 评分模板管理 | `/scoring-templates` | `GET/POST /admin/api/v1/scoring-templates`, `GET/PUT /admin/api/v1/scoring-templates/{id}`, `GET /admin/api/v1/scoring-templates/{id}/versions` |
| 情报源管理 | `/intelligence-sources` | `GET/POST /admin/api/v1/intelligence-sources`, `PATCH/DELETE /admin/api/v1/intelligence-sources/{id}`, `POST /admin/api/v1/intelligence-sources/batch-import` |
| 邮件模板管理 | `/email-templates` | `GET/POST /admin/api/v1/email-templates`, `PUT/DELETE .../email-templates/{id}` |
| 域名预热规则 | `/warmup-rules` | `GET/PUT /admin/api/v1/warmup-rules` |
| AI 配置 | `/ai-config` | `GET/PUT /admin/api/v1/ai-config/models`, `GET/PUT .../ai-config/pricing`, `GET/PUT .../ai-config/scene-defaults` |
| 租户列表 | `/tenants` | `GET/POST /admin/api/v1/tenants` |
| 租户详情 | `/tenants/:id` | `GET/PUT .../tenants/{id}`, domains/team/balance 子资源 CRUD |

### 8.2 Tenant 端

页面路由对应 `10_API_DESIGN.md` §6 Tenant API 端点。所有端点以 `/t/{slug}/api/v1/` 为前缀（Axios 拦截器自动添加）。

| 页面 | 路由 | 主要 API 端点 | 特殊行为 |
|------|------|-------------|---------|
| 登录 | `/login` | `POST .../auth/login` | 含 slug + email 字段 |
| 首次向导 | `/onboarding` | `POST .../auth/change-password`, `POST .../keywords`, `PUT .../scoring-templates/{id}`, `PUT .../contact-rules/{id}`, `GET .../auth/me` | 5 步 Steps，完成状态以后端 `needs_onboarding=false` 为准 |
| Dashboard | `/dashboard` | `GET .../dashboard/overview`, `GET .../dashboard/funnel`, `GET .../notifications` | 概览卡片 + 漏斗图 |
| 公司列表 | `/companies` | `GET .../companies`, `POST .../companies/batch-import`, `POST .../prospects/{id}/blacklist` | 高级筛选面板，Excel 导入 |
| 优选客户 | `/curated-customers` | `GET .../prospects`, `GET/POST .../groups`, `POST .../groups/{id}/members/batch-add`, `POST .../groups/{id}/members/batch-remove` | 左右分栏，群组管理 |
| 邮件模板 | `/templates` | `GET .../email-templates` (official+custom), `POST .../email-templates`, `POST .../email-templates/ai-generate` | 双 Tab（官方/自有），AI 生成弹窗 |
| 发送计划列表 | `/send-plans` | `GET .../sending-plans` | 状态颜色标签 |
| 创建计划向导 | `/send-plans/new` | `POST .../sending-plans` 创建 draft，后续 `PATCH .../sending-plans/{id}`、`/steps`、`/recipients/preview`、`/recipients/lock` 渐进保存 | 6 步 Steps，见 `08_UI_SPEC.md` §4.7.2 |
| 计划详情 | `/send-plans/:id` | `GET .../sending-plans/{id}`, `POST .../sending-plans/{id}/pause`, `POST .../sending-plans/{id}/resume` | 执行中 10s 轮询 |
| 邮件监控 | `/email-monitor` | `GET .../emails/stats`, `GET .../emails/stats/trend`, `POST .../emails/ai-analysis` | 筛选面板 + 图表，AI 分析按钮 |
| 情报中心 | `/intelligence` | `GET .../intelligence/articles` | 信息流样式，余额 ≤ 0 时隐藏摘要 |
| 设置-关键词 | `/settings/keywords` | `GET/POST/DELETE .../keywords` | 仅 Admin 可见 |
| 设置-评分 | `/settings/scoring` | `GET/PUT .../scoring-templates/{id}` | 仅 Admin 可见，复用评分模板编辑器 |
| 设置-联系人 | `/settings/contact-rules` | `GET/PUT .../contact-rules/{id}` | 仅 Admin 可见 |
| 设置-余额 | `/settings/ai-balance` | `GET .../billing/balance`, `GET .../billing/transactions`, `GET .../billing/usage-summary`, `GET .../billing/usage-trend` | 仅 Admin 可见；Operator/Viewer 通过 `GET .../ai-capabilities` 控制按钮状态 |
| 设置-团队 | `/settings/team` | `GET/POST .../team/users`, `PATCH/DELETE .../team/users/{id}` | 仅 Admin 可见 |

---

## 9. RBAC 前端实现

### 9.1 角色映射

JWT `roles` 字段值与 UI 角色对应（见 `10_API_DESIGN.md` §3.2 + `09_DATABASE_DESIGN.md` §3.3 `tenant_users.role`）：

| JWT roles 值 | UI 显示名 | 权限等级 |
|-------------|-----------|---------|
| `admin` | 管理员 | 完整权限 |
| `operator` | 业务操作员 | 日常操作，无设置写权限 |
| `viewer` | 只读观察者 | 仅查看 |

### 9.2 权限 Hook

```typescript
// packages/shared-hooks/src/usePermission.ts
type Role = 'admin' | 'operator' | 'viewer';
type Action = 'create' | 'edit' | 'delete' | 'execute' | 'view';

const PERMISSIONS: Record<string, Role[]> = {
  // 页面级
  'settings.keywords':      ['admin'],
  'settings.scoring':       ['admin'],
  'settings.contact-rules': ['admin'],
  'settings.team':          ['admin'],
  'settings.ai-balance':    ['admin'],

  // 操作级
  'company.create':         ['admin', 'operator'],
  'company.import':         ['admin', 'operator'],
  'company.blacklist':      ['admin', 'operator'],
  'group.create':           ['admin', 'operator'],
  'template.create':        ['admin', 'operator'],
  'template.ai-generate':   ['admin', 'operator'],
  'plan.create':            ['admin', 'operator'],
  'plan.execute':           ['admin', 'operator'],
  'monitor.ai-analysis':    ['admin', 'operator'],
  'balance.recharge':       ['admin'],
};

export function usePermission() {
  const { payload } = useAuthStore();
  const role = payload?.roles[0] as Role | undefined;

  return {
    can: (permission: string): boolean => {
      if (!role) return false;
      const allowed = PERMISSIONS[permission];
      return allowed ? allowed.includes(role) : false; // 未定义的权限默认拒绝（安全优先）
    },
    role,
    isAdmin: role === 'admin',
    isOperator: role === 'operator',
    isViewer: role === 'viewer',
  };
}
```

### 9.3 权限组件

```typescript
// packages/shared-ui/src/PermissionGate.tsx

/** 无权限时隐藏子元素 */
export function PermissionGate({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { can } = usePermission();
  return can(permission) ? <>{children}</> : <>{fallback}</>;
}
```

使用示例：

```tsx
// 仅 Admin/Operator 可见的"手动添加"按钮
<PermissionGate permission="company.create">
  <Button type="primary" icon={<PlusOutlined />}>手动添加</Button>
</PermissionGate>

// AI 生成按钮：RBAC + 余额双重守卫
<PermissionGate permission="template.ai-generate">
  <AIBalanceGuard>
    <Button icon={<RobotOutlined />}>AI生成</Button>
  </AIBalanceGuard>
</PermissionGate>
```

### 9.4 路由级权限

设置子路由根据角色过滤（见 `08_UI_SPEC.md` §7.2）：

```typescript
// apps/tenant/src/layouts/TenantLayout.tsx
function TenantLayout() {
  const { can } = usePermission();

  const settingsMenuItems = [
    can('settings.keywords') && { key: 'keywords', label: '采集关键词', path: '/settings/keywords' },
    can('settings.scoring') && { key: 'scoring', label: '评分规则', path: '/settings/scoring' },
    can('settings.contact-rules') && { key: 'contact-rules', label: '联系人规则', path: '/settings/contact-rules' },
    can('settings.ai-balance') && { key: 'ai-balance', label: 'AI余额', path: '/settings/ai-balance' },
    can('settings.team') && { key: 'team', label: '团队管理', path: '/settings/team' },
  ].filter(Boolean);

  // ...
}
```

---

## 10. 主题与样式体系

### 10.1 Ant Design 6 主题定制

```typescript
// packages/shared-ui/src/theme.ts
import type { ThemeConfig } from 'antd';

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  components: {
    Layout: {
      siderBg: '#001529',           // 暗色侧边栏
    },
    Table: {
      headerBg: '#fafafa',
    },
  },
};
```

### 10.2 CSS 方案

- **Ant Design 6 内置 CSS-in-JS**（基于 @ant-design/cssinjs），组件样式无需额外引入
- **页面级自定义样式**: CSS Modules（`*.module.css`），与 Vite 原生集成
- **不引入 Tailwind / styled-components**，保持技术栈简洁

### 10.3 布局规范

见 `08_UI_SPEC.md` §1.2：

| 区域 | 尺寸 |
|------|------|
| 侧边栏 | 240px 展开 / 64px 折叠，暗色 `#001529` |
| 顶栏 | 64px 高，白色，含面包屑 + 通知铃铛 + 用户头像 |
| 内容区 | padding 24px，白色/浅灰背景 |
| Drawer 宽度 | 详情类 65%，编辑类 600px |

---

## 11. 性能优化策略

### 11.1 代码分割

所有页面使用 `lazy()` 动态导入（见 §3 路由定义），Vite 自动按路由分包。

### 11.2 数据缓存

TanStack Query `staleTime: 30s` 避免重复请求。导航返回列表页时直接使用缓存，后台静默刷新。

### 11.3 虚拟滚动

公司列表/优选客户列表如数据量 > 1000 行，引入 `@tanstack/react-virtual`。Phase 1 使用标准分页即可。

### 11.4 图片/资源

Phase 1 无图片密集场景。仅需确保 Vite 构建时资源哈希 + CDN 缓存。

---

## 12. 测试策略

| 层 | 工具 | 覆盖范围 |
|---|------|---------|
| 单元测试 | Vitest | 工具函数、权限判断、状态 store |
| 组件测试 | Vitest + Testing Library | 共享组件（RatingTag, PermissionGate, AIBalanceGuard） |
| E2E | Playwright | 关键用户流：登录→创建计划→发送→监控 |

Phase 1 优先级：**共享组件单元测试 > 权限逻辑测试 > E2E 冒烟测试**。

---

## 13. 构建与部署

### 13.1 构建命令

```bash
# 构建 Admin 应用
pnpm --filter admin build

# 构建 Tenant 应用
pnpm --filter tenant build

# 构建所有
pnpm -r build
```

### 13.2 部署架构

```
                         ┌─────────────────────┐
                         │      Nginx / CDN     │
                         ├──────────┬──────────┤
                         │          │          │
                  admin.xxx.com  app.xxx.com   │
                         │          │          │
                    ┌────▼────┐ ┌──▼─────┐    │
                    │ Admin   │ │ Tenant │    │
                    │ SPA     │ │ SPA    │    │
                    │ (静态)   │ │ (静态)  │    │
                    └─────────┘ └────────┘    │
                                              │
              /admin/api/v1/*  /t/*/api/v1/*  │
                         │          │          │
                    ┌────▼──────────▼────┐     │
                    │   FastAPI 后端      │     │
                    └───────────────────┘     │
                         └─────────────────────┘
```

两个 SPA 均为纯静态文件，Nginx 配置：

```nginx
# Admin 应用
server {
    server_name admin.xxx.com;
    root /var/www/admin/dist;
    location / { try_files $uri /index.html; }
    location /admin/api/ { proxy_pass http://backend:8000; }
}

# Tenant 应用
server {
    server_name app.xxx.com;
    root /var/www/tenant/dist;
    location / { try_files $uri /index.html; }
    location /t/ { proxy_pass http://backend:8000; }
}
```

### 13.3 环境变量

```bash
# apps/admin/.env.production
VITE_API_BASE_URL=https://admin.xxx.com

# apps/tenant/.env.production
VITE_API_BASE_URL=https://app.xxx.com
```

---

## 14. 从现有前端迁移

### 14.1 现有页面映射

现有 12 个页面（见 `04_FRONTEND_MAP.md`）到新双应用的映射关系：

| 现有页面 | 现有路由 | 迁移目标 | 新路由 | 说明 |
|---------|---------|---------|-------|------|
| Login | `/login` | Tenant App | `/login` | 增加 slug 字段 |
| Dashboard | `/` | Tenant App | `/dashboard` | 全新设计，见 `08_UI_SPEC.md` §4.3 |
| Plans | `/plans` | Tenant App | `/send-plans` | 彻底重写：6步向导，不再是 pipeline |
| PlanDetail | `/plans/:id` | Tenant App | `/send-plans/:id` | 从 4 阶段 pipeline → 序列进度 |
| Keywords | `/keywords` | Tenant App | `/settings/keywords` | 移入设置子页 |
| CompanyAssets | `/company-assets` | **废弃** | — | 合并入 `/companies` |
| Companies | `/companies` | Tenant App | `/companies` | 增加高级筛选、Excel 导入 |
| Contacts | `/contacts` | **废弃** | — | 联系人作为公司详情 Tab |
| Templates | `/templates` | Tenant App | `/templates` | 增加官方/自有双 Tab + AI 生成 |
| Drafts | `/drafts` | **废弃** | — | 草稿合并到发送计划流程 |
| CleaningRules | `/cleaning-rules` | Admin App | `/scoring-templates` | 产品配置升级为评分模板 |
| Tasks | `/tasks` | **废弃** | — | 后台任务对用户不可见 |

### 14.2 迁移策略

**不渐进迁移，直接重建**。理由：

1. 路由结构完全不同（单应用 → 双应用）
2. API 前缀变化（`/api/` → `/admin/api/v1/` + `/t/{slug}/api/v1/`）
3. 状态管理从纯 Hooks 升级到 Zustand + TanStack Query
4. RBAC 全新引入
5. 现有仅 12 页面 + 3 组件，重建成本低于渐进迁移

**可复用部分**：

| 资产 | 复用方式 |
|------|---------|
| Ant Design 组件用法模式 | 直接参考现有页面的 Table/Form/Drawer 使用方式 |
| `ScoreDimensionIndicator` | 重构为 `ScoreRadarChart`，从三维固定升级为 N 维自适应 |
| Axios 拦截器模式 | 延续请求/响应拦截器设计，增强多租户前缀逻辑 |
| 10s 自动刷新模式 | 改用 TanStack Query `refetchInterval` 实现 |

### 14.3 开发顺序建议

```
Phase 1: 基础设施（~1周）
├── Monorepo 初始化（pnpm workspace + tsconfig + eslint）
├── @shared/types — 全量类型定义
├── @shared/api — Axios 实例 + API 模块骨架
├── @shared/hooks — useAuth + usePermission
└── @shared/ui — AppLayout + RatingTag + StatusTag

Phase 2: Tenant 核心页面（~2周）
├── 登录页 + 认证流程
├── Dashboard
├── 公司列表 + CompanyDetailDrawer
├── 优选客户 + GroupSidebar
└── 首次登录向导

Phase 3: Tenant 功能页面（~2周）
├── 邮件模板 + TemplateEditor + AI 生成
├── 发送计划（列表 + 6步向导 + 详情）
├── 邮件监控 + 图表
├── 情报中心
└── 设置 5 个子页

Phase 4: Admin 端（~1.5周）
├── Admin 登录
├── 7 个管理页面
└── 租户详情（域名/团队/余额 3 Tab）

Phase 5: 集成与打磨（~0.5周）
├── E2E 测试
├── 构建优化
└── 部署配置
```

**总估时**: 约 7 周（1 前端工程师）。
