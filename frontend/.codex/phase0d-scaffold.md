# Phase 0D: Tenant-next 脚手架

> 前置：Phase 0A+0C 已完成（@shared/ui 已重构，Admin 已切换）
> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`

## 目标

在 `apps/tenant-next/` 初始化 Next.js 15 项目，配置好所有基础设施，能 `pnpm dev` 启动并代理后端 API。

## 参照

- Admin 项目结构：`apps/admin/`（已完成的 Next.js 迁移，完全参照其模式）
- Admin next.config.ts、providers.tsx、lib/api.ts 作为模板

## 执行步骤

### 1. 初始化项目

在 `apps/tenant-next/` 创建 Next.js 15 项目（App Router, TypeScript）。

**package.json** — name 设为 `@apps/tenant-next`，依赖：
- next, react, react-dom
- @tanstack/react-query, zustand, axios, dayjs, sonner, lucide-react
- @shared/api, @shared/types, @shared/hooks, @shared/ui（workspace 引用）
- devDependencies: typescript, @types/react, @types/node, tailwindcss, postcss, autoprefixer

### 2. 配置文件

**next.config.ts** — 参照 `apps/admin/next.config.ts`：
```ts
import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';
import path from 'node:path';

export default function nextConfig(phase: string): NextConfig {
  return {
    output: 'standalone',
    outputFileTracingRoot: path.join(__dirname, '../..'),
    transpilePackages: ['@shared/api', '@shared/types', '@shared/hooks', '@shared/ui'],
    async rewrites() {
      if (phase !== PHASE_DEVELOPMENT_SERVER) return [];
      return [
        { source: '/t/:path*', destination: 'http://localhost:8000/t/:path*' },
      ];
    },
  };
}
```

注意：
- transpilePackages 多了 `@shared/ui`（Admin 目前没加，因为 Admin 迁移时 shared-ui 还是 antd）
- rewrites 代理 `/t/*` 而不是 `/admin/api/*`

**tailwind.config.ts**：
```ts
import sharedPreset from '@shared/ui/theme/tailwind-preset'
import type { Config } from 'tailwindcss'

const config: Config = {
  presets: [sharedPreset],
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/shared-ui/src/**/*.{ts,tsx}',
  ],
}
export default config
```

**postcss.config.mjs**：
```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } }
```

**tsconfig.json** — 继承 `../../tsconfig.base.json`，paths:
```json
{
  "@/*": ["./src/*"],
  "@shared/api": ["../../packages/shared-api/src"],
  "@shared/types": ["../../packages/shared-types/src"],
  "@shared/hooks": ["../../packages/shared-hooks/src"],
  "@shared/ui": ["../../packages/shared-ui/src"],
  "@shared/ui/*": ["../../packages/shared-ui/src/*"]
}
```

### 3. 核心文件

**src/app/globals.css**：
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* 从 @shared/ui/theme/globals.css 复制 CSS 变量，或直接 @import */
    /* 与 Admin 使用相同的色彩系统 */
  }

  * { @apply border-border; }
  body { @apply bg-background text-foreground antialiased; }
}
```

**src/providers.tsx** — 完全参照 `apps/admin/src/providers.tsx`：
```tsx
'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';
import { Toaster } from 'sonner';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, gcTime: 5 * 60_000, retry: 1, refetchOnWindowFocus: false },
    },
  }));
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors closeButton position="top-right" />
    </QueryClientProvider>
  );
}
```

**src/lib/api.ts** — 参照 `apps/admin/src/lib/api.ts`：
```ts
import { createApiClient, createTenantApi } from '@shared/api';
const tenantBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
const client = createApiClient('tenant', { baseURL: tenantBaseURL });
export const tenantApi = createTenantApi(client);
```

**src/app/layout.tsx**（最小可用）：
```tsx
import type { Metadata } from 'next';
import { Providers } from '@/providers';
import './globals.css';

export const metadata: Metadata = { title: 'ClientGet' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
```

**src/app/page.tsx**（占位）：
```tsx
export default function Home() {
  return <div>Tenant Next - Scaffold OK</div>;
}
```

### 4. 更新 workspace

在 `pnpm-workspace.yaml` 的 packages 列表中添加 `apps/tenant-next`。

### 5. 验证

- `pnpm install`（从 monorepo 根目录）
- `pnpm --filter @apps/tenant-next dev`（应该能在 localhost:3001 启动）
- 打开浏览器访问 localhost:3001，看到 "Tenant Next - Scaffold OK"

## 约束

- 不改 @shared/api、@shared/types、@shared/hooks 的任何代码
- 不改 Admin 的任何代码
- 不改后端代码（CORS 已配好 localhost:3001）
- 端口用 3001（Admin 用 3000）
