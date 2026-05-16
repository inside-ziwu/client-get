# Next.js 全栈迁移方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ClientGet 从 Vite React + FastAPI 架构逐步迁移到 Next.js 全栈架构，过渡期两套系统共享数据库并行运行，用户无感知。

**Architecture:** Next.js 做唯一前端入口，已迁移模块由 Next.js Server Actions / Route Handlers 直接访问 PostgreSQL，未迁移模块通过 `next.config.js` rewrites 代理到 FastAPI。两端共享 JWT secret 实现认证互通。Worker 过渡期保留 Python，后期按需迁移到 Node。

**Tech Stack:**
- 框架：Next.js 15（App Router）
- 数据库：Prisma（introspect 现有 schema，只读 client；迁移仍由 Alembic 管理）
- 认证：自定义 JWT 中间件（与 FastAPI 共享 HS256 secret）
- UI：Ant Design 6（与现有前端一致）+ @ant-design/nextjs-registry（SSR 支持）
- 状态：React Query（Server State）+ Zustand（Client State）
- 部署：Sealos 容器，与现有后端并行

---

## ⚠️ 审查决策记录（2026-05-12 Autoplan CEO Review）

**D1 迁移路径 → 方案 A（修订版）：AI 加速全栈迁移**

经三轮审查（Claude 初评 → Codex 反方 → 共识），最终决策：

核心前提：代码由 Codex/Claude 编写，翻译成本大幅下降；用户不熟悉 Python，长期维护 FastAPI 是硬伤。
决策：全栈迁移 API + 页面 + service，Workers 暂留 Python。过渡期尽量短，每个模块用新旧对比测试切真源。

关键机制（Codex 提出，Claude 采纳）：
- **「AI 能写」≠「AI 写完就可信」**：每个模块迁移后必须有新旧接口自动对比测试
- **模块真源切换**：对比测试通过 → 宣布该模块 FastAPI API 冻结/废弃 → Next.js 成为真源
- **短过渡期**：双系统并存时间越短越好，长期并存会放大「判断真源」的决策成本

影响：
- Phase 0-4：全部为硬目标，按模块逐步迁移
- Workers（采集/评分/发送/调度）：暂留 Python，独立决策是否迁移
- D3 RLS 安全网：纳入 Phase 0（Task 0.9）

**CEO Review 技术修正（同日）：**
发现 12 处计划与 Spike 结果不一致，已修正：
1. Prisma 7 driver adapter 模式（@prisma/adapter-pg + pg）
2. Ant Design 6 + @ant-design/nextjs-registry
3. withTenant() 传递 tx 参数
4. httpOnly Set-Cookie（非 document.cookie）
5. Phase 1 Task 1.2-1.4 补充完整实现步骤

---

## 迁移总览

```
Phase 0  基础设施        ← Next.js 项目 + 认证 + 布局 + 代理
Phase 1  租户端只读页面   ← Dashboard、精选客户、情报、邮件监控
Phase 2  租户端 CRUD 页面 ← 公司、模板、设置（关键词/评分/AI/团队）
Phase 3  租户端复杂页面   ← 发送计划（列表/新建/详情）、Onboarding
Phase 4  管理端全部页面   ← Admin 14 个页面
Phase 5  下线旧系统      ← 移除 FastAPI API 层 + Vite 前端
```

Worker（采集/评分/发送/清洗/调度/FanOut）过渡期全部保留 Python，它们只依赖数据库和 Internal API，与前端无关。迁移到 Node 是独立决策，不阻塞本方案。

---

## 现有模块清单与迁移排期

### 租户端（15 个页面）

| 页面 | 路由 | 复杂度 | Phase | 说明 |
|------|------|--------|-------|------|
| Login | `/login` | 低 | 0 | 认证基础 |
| Dashboard | `/` `/dashboard` | 中 | 1 | 只读，funnel + 统计 |
| 精选客户 | `/curated-customers` | 低 | 1 | 只读列表 |
| 情报 | `/intelligence` | 中 | 1 | 只读，订阅 + 文章 |
| 邮件监控 | `/email-monitor` | 中 | 1 | 只读，邮件事件统计 |
| 公司管理 | `/companies` | 高 | 2 | CRUD + 筛选 + 导出 |
| 邮件模板 | `/templates` | 中 | 2 | CRUD + AI 生成 |
| 设置-关键词 | `/settings/keywords` | 低 | 2 | CRUD |
| 设置-评分 | `/settings/scoring` | 低 | 2 | 读写权重 |
| 设置-AI | `/settings/ai-provider` | 低 | 2 | 配置 + 余额查询 |
| 设置-团队 | `/settings/team` | 中 | 2 | 用户 CRUD + 角色 |
| 发送计划列表 | `/send-plans` | 中 | 3 | 列表 + 状态流转 |
| 发送计划新建 | `/send-plans/new` | 高 | 3 | 多步骤表单 |
| 发送计划详情 | `/send-plans/:id` | 高 | 3 | 步骤编辑 + 收件人 |
| Onboarding | `/onboarding` | 中 | 3 | 引导流程 |

### 管理端（14 个页面）

| 页面 | 路由 | 复杂度 | Phase |
|------|------|--------|-------|
| Login | `/login` | 低 | 4 |
| 数据源 | `/data-sources` | 中 | 4 |
| 评分模板 | `/scoring-templates` | 中 | 4 |
| 情报源 | `/intelligence-sources` | 低 | 4 |
| 邮件模板 | `/email-templates` | 高 | 4（含 GrapeJS） |
| 预热规则 | `/warmup-rules` | 低 | 4 |
| AI 配置 | `/ai-config` | 中 | 4 |
| 租户管理 | `/tenants` | 高 | 4 |
| 采集任务 | `/collection-tasks` | 中 | 4 |
| 采集-Tendata | `/collection/tendata` | 低 | 4 |
| 采集-客户 | `/collection/customers` | 低 | 4 |
| 采集-同行 | `/collection/peers` | 低 | 4 |
| 联系人分类 | `/contact-classification` | 中 | 4 |

---

## Phase 0：基础设施（Next.js 项目 + 认证 + 布局 + 全量代理）

> Phase 0 完成后：用户访问 Next.js，所有请求代理到 FastAPI，功能完全不变。这是零风险上线点。

### Task 0.1：创建 Next.js 项目

**Files:**
- Create: `nextjs/package.json`
- Create: `nextjs/next.config.ts`
- Create: `nextjs/tsconfig.json`
- Create: `nextjs/.env.local`
- Create: `nextjs/app/layout.tsx`
- Create: `nextjs/app/page.tsx`

- [ ] **Step 1: 初始化 Next.js 项目**

```bash
cd /Users/lay/Documents/Github/client_get
pnpm create next-app nextjs --typescript --app --eslint --tailwind --src-dir=false --import-alias="@/*" --use-pnpm
```

- [ ] **Step 2: 安装核心依赖**

```bash
cd nextjs
pnpm add antd @ant-design/icons @ant-design/nextjs-registry
pnpm add @tanstack/react-query zustand axios
pnpm add prisma -D
pnpm add @prisma/client @prisma/adapter-pg pg
pnpm add -D @types/pg
pnpm add jose  # JWT 解码，Edge Runtime 兼容
```

> **Spike 验证**：Prisma 7 不再内置数据库驱动，必须安装 `@prisma/adapter-pg` + `pg` 并通过 driver adapter 模式初始化。

- [ ] **Step 3: 配置环境变量**

创建 `nextjs/.env.local`：

```env
# 数据库（与 FastAPI 共享同一个 PostgreSQL）
DATABASE_URL="postgresql://clientget:password@localhost:5432/clientget"

# 认证（与 FastAPI 共享同一套 JWT）
JWT_SECRET="与 FastAPI 的 JWT_SECRET 相同"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_HOURS=24

# FastAPI 代理地址（未迁移模块转发到这里）
FASTAPI_URL="http://localhost:8000"

# Internal Service Secret（调用 Worker Internal API）
INTERNAL_SERVICE_SECRET="与 FastAPI 的 INTERNAL_SERVICE_SECRET 相同"
```

- [ ] **Step 4: 配置 next.config.ts 全量代理**

此时所有 API 请求都代理到 FastAPI，前端只是一个空壳：

```typescript
// nextjs/next.config.ts
import type { NextConfig } from 'next'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

const nextConfig: NextConfig = {
  transpilePackages: ['antd', '@ant-design/icons'],

  async rewrites() {
    return [
      // 租户端 API 全量代理
      {
        source: '/t/:slug/api/v1/:path*',
        destination: `${FASTAPI_URL}/t/:slug/api/v1/:path*`,
      },
      // 管理端 API 全量代理
      {
        source: '/admin/api/v1/:path*',
        destination: `${FASTAPI_URL}/admin/api/v1/:path*`,
      },
      // 内部 API 全量代理
      {
        source: '/internal/api/v1/:path*',
        destination: `${FASTAPI_URL}/internal/api/v1/:path*`,
      },
      // Webhook 全量代理
      {
        source: '/webhooks/:path*',
        destination: `${FASTAPI_URL}/webhooks/:path*`,
      },
    ]
  },
}

export default nextConfig
```

- [ ] **Step 5: 验证项目启动**

```bash
cd nextjs && pnpm dev
# 访问 http://localhost:3000 应看到 Next.js 默认页面
```

- [ ] **Step 6: 提交**

```bash
git add nextjs/
git commit -m "feat: 初始化 Next.js 项目，配置全量 API 代理到 FastAPI"
```

---

### Task 0.2：Prisma Introspect 现有数据库

**Files:**
- Create: `nextjs/prisma/schema.prisma`

> Prisma 只做读取现有 schema，不管迁移。迁移继续由 Alembic 负责，避免两套迁移工具冲突。

- [ ] **Step 1: 初始化 Prisma**

```bash
cd nextjs
npx prisma init --datasource-provider postgresql
```

- [ ] **Step 2: Introspect 现有数据库**

```bash
npx prisma db pull
```

这会从 PostgreSQL 反向生成 `prisma/schema.prisma`，包含所有表、字段、关系。

- [ ] **Step 3: 生成 Prisma Client**

```bash
npx prisma generate
```

- [ ] **Step 4: 创建数据库工具模块**

创建 `nextjs/lib/db.ts`：

```typescript
import pg from "pg"
import { PrismaPg } from "@prisma/adapter-pg"
import { PrismaClient } from "@prisma/client"

/**
 * Prisma 7 driver adapter 模式（Spike 验证通过）
 * 必须显式创建 pg.Pool + PrismaPg adapter
 */
function createPrismaClient() {
  const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL,
    max: 10, // 生产环境连接池上限，按需调整
  })
  const adapter = new PrismaPg(pool)
  return new PrismaClient({ adapter })
}

const globalForPrisma = globalThis as unknown as {
  prisma: ReturnType<typeof createPrismaClient> | undefined
}

export const prisma = globalForPrisma.prisma ?? createPrismaClient()

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma
```

> **Spike 验证**：`new PrismaClient()` 无参会报 `PrismaClientInitializationError`，必须传 adapter。连接池配置（`max`）在生产环境中重要。

- [ ] **Step 5: 创建 RLS 上下文设置函数**

创建 `nextjs/lib/rls.ts`：

```typescript
import { prisma } from "./db"

type TransactionClient = Parameters<Parameters<typeof prisma.$transaction>[0]>[0]

/**
 * 在事务中设置 RLS tenant 上下文，并将 tx 传递给回调
 * 与 FastAPI 的 set_current_tenant() 行为一致
 *
 * 用法：
 *   const result = await withTenant(tenantId, async (tx) => {
 *     return tx.tenant_companies.findMany({ where: { visibility_status: "visible" } })
 *   })
 */
export async function withTenant<T>(
  tenantId: string,
  fn: (tx: TransactionClient) => Promise<T>
): Promise<T> {
  return prisma.$transaction(async (tx) => {
    await tx.$executeRaw`SELECT set_config('app.current_tenant_id', ${tenantId}, true)`
    return fn(tx)
  })
}
```

> **Spike 验证**：回调必须接收 `tx` 参数并在 tx 上执行查询，否则查询不在事务内，RLS 上下文无效。

- [ ] **Step 6: 验证数据库连接**

创建临时测试文件 `nextjs/scripts/test-db.ts`：

```typescript
import { prisma } from '../lib/db'

async function main() {
  const count = await prisma.tenants.count()
  console.log(`租户数量: ${count}`)
}

main().then(() => process.exit(0))
```

```bash
npx tsx scripts/test-db.ts
# 应输出 "租户数量: N"
```

删除测试文件后提交：

- [ ] **Step 7: 提交**

```bash
rm nextjs/scripts/test-db.ts
git add nextjs/prisma/ nextjs/lib/db.ts nextjs/lib/rls.ts
git commit -m "feat: Prisma introspect 现有数据库，添加 RLS 上下文工具"
```

---

### Task 0.3：JWT 认证中间件

**Files:**
- Create: `nextjs/lib/auth.ts`
- Create: `nextjs/middleware.ts`

> 与 FastAPI 共享同一个 JWT_SECRET，两端签发的 token 互认。

- [ ] **Step 1: 创建 JWT 工具函数**

创建 `nextjs/lib/auth.ts`：

```typescript
import { jwtVerify, SignJWT } from 'jose'
import { cookies } from 'next/headers'

const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!)
const JWT_ALGORITHM = 'HS256'
const JWT_EXPIRE_HOURS = Number(process.env.JWT_EXPIRE_HOURS || 24)

// 与 FastAPI 的 JWT payload 结构完全一致
export interface JWTPayload {
  sub: string           // user_id
  kind: 'platform' | 'tenant'
  iat: number
  exp: number
  tid?: string          // tenant_id（仅 tenant token）
  slug?: string         // tenant_slug（仅 tenant token）
  roles?: string[]      // 角色列表（仅 tenant token）
}

/** 验证 JWT（与 FastAPI decode_access_token 逻辑一致） */
export async function verifyToken(token: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, JWT_SECRET, {
    algorithms: [JWT_ALGORITHM],
  })
  return payload as unknown as JWTPayload
}

/** 签发 JWT（与 FastAPI create_access_token 逻辑一致） */
export async function signToken(payload: Omit<JWTPayload, 'iat' | 'exp'>): Promise<string> {
  return new SignJWT(payload as Record<string, unknown>)
    .setProtectedHeader({ alg: JWT_ALGORITHM })
    .setIssuedAt()
    .setExpirationTime(`${JWT_EXPIRE_HOURS}h`)
    .sign(JWT_SECRET)
}

/** 从请求头或 cookie 中提取 token */
export function extractToken(request: Request): string | null {
  // 优先从 Authorization header 提取（API 调用）
  const authHeader = request.headers.get('Authorization')
  if (authHeader?.startsWith('Bearer ')) {
    return authHeader.slice(7)
  }
  return null
}

/** Server Component / Server Action 中获取当前用户 */
export async function getCurrentUser(): Promise<JWTPayload | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('token')?.value
  if (!token) return null
  try {
    return await verifyToken(token)
  } catch {
    return null
  }
}
```

- [ ] **Step 2: 创建 Next.js middleware**

创建 `nextjs/middleware.ts`：

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { verifyToken, extractToken } from '@/lib/auth'

// 不需要认证的路径
const PUBLIC_PATHS = ['/login', '/admin/login']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 公开路径直接放行
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // API 代理路径不经过 middleware（由 rewrites 处理）
  if (pathname.startsWith('/t/') && pathname.includes('/api/')) {
    return NextResponse.next()
  }
  if (pathname.startsWith('/admin/api/')) {
    return NextResponse.next()
  }

  // 检查 token
  const token = extractToken(request) || request.cookies.get('token')?.value
  if (!token) {
    // 根据路径判断重定向到哪个登录页
    const loginUrl = pathname.startsWith('/admin')
      ? new URL('/admin/login', request.url)
      : new URL('/login', request.url)
    return NextResponse.redirect(loginUrl)
  }

  try {
    await verifyToken(token)
    return NextResponse.next()
  } catch {
    const loginUrl = pathname.startsWith('/admin')
      ? new URL('/admin/login', request.url)
      : new URL('/login', request.url)
    return NextResponse.redirect(loginUrl)
  }
}

export const config = {
  matcher: [
    // 匹配所有页面路径，排除静态资源
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
```

- [ ] **Step 3: 验证 middleware 工作**

```bash
cd nextjs && pnpm dev
# 访问 http://localhost:3000 应重定向到 /login
# 访问 http://localhost:3000/login 应正常显示
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/lib/auth.ts nextjs/middleware.ts
git commit -m "feat: JWT 认证中间件，与 FastAPI 共享 token 验证"
```

---

### Task 0.4：租户端登录页

**Files:**
- Create: `nextjs/app/login/page.tsx`
- Create: `nextjs/lib/store/auth.ts`

> 登录请求仍然发到 FastAPI（通过 rewrites 代理），拿到 token 后存到 Zustand + cookie。

- [ ] **Step 1: 创建 Zustand auth store**

创建 `nextjs/lib/store/auth.ts`：

```typescript
import { create } from 'zustand'

interface AuthState {
  slug: string | null
  setSlug: (slug: string) => void
  logout: () => void
}

/**
 * 客户端状态只存 slug（用于 API 路径拼接）。
 * token 由服务端通过 httpOnly Set-Cookie 管理，客户端无法读取（更安全）。
 */
export const useAuthStore = create<AuthState>((set) => ({
  slug: typeof window !== 'undefined' ? localStorage.getItem('slug') : null,
  setSlug: (slug) => {
    localStorage.setItem('slug', slug)
    set({ slug })
  },
  logout: () => {
    localStorage.removeItem('slug')
    set({ slug: null })
    // token cookie 由服务端 /api/auth/logout 清除
    window.location.href = '/login'
  },
}))
```

> **安全修正**：token 不再通过 `document.cookie` 设置（无法设 httpOnly）。改为登录 API Route 用 `response.cookies.set()` 设置 httpOnly cookie（参考 Spike 的 login route 实现）。

- [ ] **Step 2: 创建登录 API Route（httpOnly cookie）**

创建 `nextjs/app/api/auth/login/route.ts`：

```typescript
/**
 * 登录 API Route — 代理到 FastAPI，然后在响应中设置 httpOnly cookie
 * 参考 Spike 验证的实现
 */
import { NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const { email, password, slug } = await request.json()

  if (!email || !password || !slug) {
    return NextResponse.json({ error: "邮箱、密码和企业标识不能为空" }, { status: 400 })
  }

  const fastapiUrl = process.env.FASTAPI_URL
  try {
    const resp = await fetch(`${fastapiUrl}/t/${slug}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "登录失败" }))
      return NextResponse.json({ error: err.detail || "登录失败" }, { status: resp.status })
    }

    const data = await resp.json()
    const response = NextResponse.json({ success: true, user: data.data?.user })

    // httpOnly cookie — 客户端 JS 无法读取，防 XSS 窃取
    response.cookies.set("token", data.data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24,
      path: "/",
    })

    return response
  } catch {
    return NextResponse.json({ error: "服务暂不可用" }, { status: 503 })
  }
}
```

- [ ] **Step 3: 创建登录页**

创建 `nextjs/app/login/page.tsx`：

```tsx
'use client'

import { useState } from 'react'
import { Form, Input, Button, Card, App } from 'antd'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'

interface LoginForm {
  email: string
  password: string
  slug: string
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const setSlug = useAuthStore((s) => s.setSlug)
  const { message } = App.useApp()

  const onFinish = async (values: LoginForm) => {
    setLoading(true)
    try {
      // 调用 Next.js API Route（设置 httpOnly cookie）
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      const data = await res.json()

      if (!res.ok) {
        message.error(data.error || '登录失败')
        return
      }

      setSlug(values.slug)
      message.success('登录成功')
      router.push('/')
    } catch {
      message.error('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <App>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Card title="ClientGet 登录" style={{ width: 400 }}>
          <Form layout="vertical" onFinish={onFinish}>
            <Form.Item name="slug" label="企业标识" rules={[{ required: true }]}>
              <Input placeholder="输入企业 slug" />
            </Form.Item>
            <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
              <Input placeholder="输入邮箱" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true }]}>
              <Input.Password placeholder="输入密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </App>
  )
}
```

> **Spike 验证**：Ant Design 6 的 `message` API 需要通过 `App.useApp()` 获取，页面需包裹在 `<App>` 内。

- [ ] **Step 3: 验证登录流程**

```bash
cd nextjs && pnpm dev
# 1. 访问 http://localhost:3000 → 重定向到 /login
# 2. 输入正确的 slug/email/password → 登录成功，跳转到 /
# 3. 检查 cookie 中有 token
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/app/login/ nextjs/lib/store/
git commit -m "feat: 租户端登录页，通过代理调用 FastAPI 认证"
```

---

### Task 0.5：租户端主布局

**Files:**
- Create: `nextjs/app/(tenant)/layout.tsx`
- Create: `nextjs/components/TenantSidebar.tsx`
- Create: `nextjs/app/(tenant)/page.tsx`

- [ ] **Step 1: 更新根 layout 注入 Ant Design 6**

修改 `nextjs/app/layout.tsx`：

```tsx
import type { Metadata } from 'next'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import './globals.css'

// 与现有 shared-ui/theme.ts 保持一致的主题配置
const theme = {
  token: {
    colorPrimary: '#1677ff',
  },
}

export const metadata: Metadata = {
  title: 'ClientGet',
  description: 'B2B 外贸客户智能平台',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <AntdRegistry>
          <ConfigProvider locale={zhCN} theme={theme}>
            {children}
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  )
}
```

> **Spike 验证**：Ant Design 6 直接用 `@ant-design/nextjs-registry` 的 `AntdRegistry`，无需自己手写 cssinjs 提取逻辑。不再需要 `nextjs/lib/antd-registry.tsx` 文件。

- [ ] **Step 3: 创建租户端侧边栏**

创建 `nextjs/components/TenantSidebar.tsx`：

```tsx
'use client'

import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  BankOutlined,
  StarOutlined,
  MailOutlined,
  SendOutlined,
  MonitorOutlined,
  BulbOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { usePathname, useRouter } from 'next/navigation'

const { Sider } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/companies', icon: <BankOutlined />, label: '公司管理' },
  { key: '/curated-customers', icon: <StarOutlined />, label: '精选客户' },
  { key: '/templates', icon: <MailOutlined />, label: '邮件模板' },
  { key: '/send-plans', icon: <SendOutlined />, label: '发送计划' },
  { key: '/email-monitor', icon: <MonitorOutlined />, label: '邮件监控' },
  { key: '/intelligence', icon: <BulbOutlined />, label: '智能资讯' },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '设置',
    children: [
      { key: '/settings/keywords', label: '关键词' },
      { key: '/settings/scoring', label: '评分规则' },
      { key: '/settings/ai-provider', label: 'AI 配置' },
      { key: '/settings/team', label: '团队管理' },
    ],
  },
]

export default function TenantSidebar() {
  const pathname = usePathname()
  const router = useRouter()

  return (
    <Sider width={220} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
      <div style={{ padding: '16px', fontWeight: 700, fontSize: 18 }}>ClientGet</div>
      <Menu
        mode="inline"
        selectedKeys={[pathname]}
        items={menuItems}
        onClick={({ key }) => router.push(key)}
      />
    </Sider>
  )
}
```

- [ ] **Step 4: 创建租户端主布局**

创建 `nextjs/app/(tenant)/layout.tsx`：

```tsx
import { Layout } from 'antd'
import TenantSidebar from '@/components/TenantSidebar'

const { Content } = Layout

export default function TenantLayout({ children }: { children: React.ReactNode }) {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <TenantSidebar />
      <Layout>
        <Content style={{ padding: 24 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}
```

- [ ] **Step 5: 创建首页占位**

创建 `nextjs/app/(tenant)/page.tsx`：

```tsx
export default function TenantHome() {
  return <div>仪表盘（Phase 1 迁移）</div>
}
```

- [ ] **Step 6: 验证布局渲染**

```bash
cd nextjs && pnpm dev
# 登录后访问 / 应看到侧边栏 + 内容区 + "仪表盘（Phase 1 迁移）"
```

- [ ] **Step 7: 提交**

```bash
git add nextjs/app/ nextjs/components/
git commit -m "feat: 租户端主布局和侧边栏导航"
```

---

### Task 0.6：创建 API 工具层

**Files:**
- Create: `nextjs/lib/api/client.ts`
- Create: `nextjs/lib/api/tenant.ts`

> 封装前端 API 调用。Phase 0 阶段所有请求都通过 rewrites 代理到 FastAPI；后续 Phase 迁移时，逐步替换为 Server Actions。

- [ ] **Step 1: 创建 axios 客户端**

创建 `nextjs/lib/api/client.ts`：

```typescript
import axios from 'axios'
import { useAuthStore } from '@/lib/store/auth'

export function createTenantClient() {
  const { token, slug } = useAuthStore.getState()
  const instance = axios.create({
    baseURL: `/t/${slug}/api/v1`,
  })

  instance.interceptors.request.use((config) => {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
  )

  return instance
}

export function createAdminClient() {
  const { token } = useAuthStore.getState()
  const instance = axios.create({
    baseURL: '/admin/api/v1',
  })

  instance.interceptors.request.use((config) => {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  return instance
}
```

- [ ] **Step 2: 创建租户端 API wrapper 示例**

创建 `nextjs/lib/api/tenant.ts`：

```typescript
import { createTenantClient } from './client'

// 以 dashboard 为例，其他模块迁移时按同样模式添加
export const dashboardApi = {
  overview: () => createTenantClient().get('/dashboard/overview'),
  funnel: () => createTenantClient().get('/dashboard/funnel'),
}

export const companiesApi = {
  list: (params: Record<string, unknown>) => createTenantClient().get('/companies', { params }),
  get: (id: string) => createTenantClient().get(`/companies/${id}`),
  create: (data: Record<string, unknown>) => createTenantClient().post('/companies', data),
  filters: () => createTenantClient().get('/companies/filters'),
}

// Phase 1-3 迁移时逐步添加其他模块...
```

- [ ] **Step 3: 提交**

```bash
git add nextjs/lib/api/
git commit -m "feat: API 工具层，当前全量代理到 FastAPI"
```

---

### Task 0.7：为所有租户端路由创建占位页面

**Files:**
- Create: `nextjs/app/(tenant)/companies/page.tsx`
- Create: `nextjs/app/(tenant)/curated-customers/page.tsx`
- Create: `nextjs/app/(tenant)/templates/page.tsx`
- Create: `nextjs/app/(tenant)/send-plans/page.tsx`
- Create: `nextjs/app/(tenant)/send-plans/new/page.tsx`
- Create: `nextjs/app/(tenant)/send-plans/[id]/page.tsx`
- Create: `nextjs/app/(tenant)/email-monitor/page.tsx`
- Create: `nextjs/app/(tenant)/intelligence/page.tsx`
- Create: `nextjs/app/(tenant)/settings/keywords/page.tsx`
- Create: `nextjs/app/(tenant)/settings/scoring/page.tsx`
- Create: `nextjs/app/(tenant)/settings/ai-provider/page.tsx`
- Create: `nextjs/app/(tenant)/settings/team/page.tsx`
- Create: `nextjs/app/(tenant)/onboarding/page.tsx`

> 每个页面暂时只是 "即将迁移" 占位符。Phase 1-3 逐步替换为真实实现。

- [ ] **Step 1: 批量创建占位页面**

为每个路由创建最小 page.tsx：

```tsx
// 以 companies 为例，其他页面结构相同，只改标题
export default function CompaniesPage() {
  return <div>公司管理（即将迁移）</div>
}
```

每个文件按上述 Files 列表创建。

- [ ] **Step 2: 验证所有路由可访问**

```bash
cd nextjs && pnpm dev
# 逐个点击侧边栏菜单项，确认每个页面都能正常渲染占位内容
```

- [ ] **Step 3: 提交**

```bash
git add nextjs/app/
git commit -m "feat: 所有租户端路由占位页面"
```

---

### Task 0.8：Dockerfile 和部署配置

**Files:**
- Create: `nextjs/Dockerfile`

- [ ] **Step 1: 创建 Dockerfile**

创建 `nextjs/Dockerfile`：

```dockerfile
FROM node:20-alpine AS base

# 安装 pnpm
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 构建参数
ARG FASTAPI_URL=https://api.xinanpcb.com
ENV FASTAPI_URL=$FASTAPI_URL

RUN npx prisma generate
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 2: 更新 next.config.ts 开启 standalone 输出**

在 `nextConfig` 中添加：

```typescript
output: 'standalone',
```

- [ ] **Step 3: 本地构建验证**

```bash
cd nextjs
docker build -t clientget-nextjs .
docker run -p 3000:3000 --env-file .env.local clientget-nextjs
# 访问 http://localhost:3000 应正常工作
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/Dockerfile nextjs/next.config.ts
git commit -m "feat: Next.js Dockerfile，standalone 模式构建"
```

---

### Task 0.9：RLS 安全网（数据库层强制）

**Files:**
- Create: `nextjs/scripts/enforce-rls.sql`

> **审查补充项**：Spike 发现 postgres owner 角色会绕过 RLS（`relforcerowsecurity: false`）。
> 必须在数据库层面强制 RLS，防止代码遗漏 `withTenant()` 导致数据泄漏。

- [ ] **Step 1: 创建 RLS 强制 SQL 脚本**

创建 `nextjs/scripts/enforce-rls.sql`：

```sql
-- 方案：对所有租户相关表强制 RLS，即使 table owner 也不能绕过
-- 需要 superuser 或 table owner 执行

-- 租户公司表
ALTER TABLE tenant_companies FORCE ROW LEVEL SECURITY;

-- 租户联系人表
ALTER TABLE tenant_contacts FORCE ROW LEVEL SECURITY;

-- 邮件表
ALTER TABLE emails FORCE ROW LEVEL SECURITY;

-- 情报订阅表（如果存在 RLS 策略）
-- ALTER TABLE intelligence_subscriptions FORCE ROW LEVEL SECURITY;

-- 其他租户相关表按需添加...
-- 完整列表参考：SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

- [ ] **Step 2: 创建应用专用数据库角色（非 owner）**

```sql
-- 创建一个非 owner 角色给 Next.js 应用使用
-- 这个角色受 RLS 策略约束，不会绕过
CREATE ROLE nextjs_app LOGIN PASSWORD 'secure_password';
GRANT USAGE ON SCHEMA public TO nextjs_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nextjs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nextjs_app;
```

- [ ] **Step 3: 更新 .env.local 使用新角色**

```env
# 使用非 owner 角色连接，确保 RLS 生效
DATABASE_URL="postgresql://nextjs_app:secure_password@localhost:5432/clientget"
```

- [ ] **Step 4: 验证 RLS 强制生效**

```bash
# 用新角色连接，不设置 app.current_tenant_id 时查询应返回空结果
npx tsx -e "
import { prisma } from './lib/db.js'
// 不调用 withTenant，直接查询 — 应该返回 0 条
const count = await prisma.tenant_companies.count()
console.log('无 tenant 上下文查询结果:', count, '(应为 0)')
await prisma.\$disconnect()
"
```

- [ ] **Step 5: 提交**

```bash
git add nextjs/scripts/enforce-rls.sql
git commit -m "feat: RLS 安全网 — 数据库层强制行级安全 + 非 owner 角色"
```

---

## Phase 0 完成标志

- [ ] Next.js 项目启动正常
- [ ] Prisma 7 (driver adapter 模式) 可读取现有数据库
- [ ] JWT 认证与 FastAPI 互通（httpOnly cookie）
- [ ] 登录流程完整（Next.js API Route → FastAPI 代理 → httpOnly cookie）
- [ ] 侧边栏导航所有页面可访问
- [ ] 全量 API 代理到 FastAPI，功能无变化
- [ ] RLS 安全网生效（FORCE RLS + 非 owner 角色）
- [ ] Docker 构建成功

**此时可以上线 Next.js 替代 Vite 前端，用户体验完全不变。这是零风险切换点。**

---

## Phase 1：租户端只读页面 + 建立迁移流水线

> Phase 1 的核心目标不是「观望」，而是建立可复用的迁移流水线：
>
> **每个模块的迁移流程：**
> 1. AI 读 Python service 代码 → 翻译为 TypeScript Server Action（通过 Prisma + RLS）
> 2. 编写新旧接口自动对比测试（同租户同参数，对比 FastAPI 和 Next.js 返回值）
> 3. 对比测试通过 → 前端切到 Next.js API → 从 rewrites 移除对应路径
> 4. 宣布该模块 FastAPI API 冻结/废弃
>
> Phase 1 用只读页面建立这条流水线，Phase 2-3 用同样流程迁写操作。

### Task 1.1：Dashboard 仪表盘

**Files:**
- Create: `nextjs/app/(tenant)/actions/dashboard.ts`
- Modify: `nextjs/app/(tenant)/page.tsx`

- [ ] **Step 1: 创建 Server Action**

创建 `nextjs/app/(tenant)/actions/dashboard.ts`：

```typescript
'use server'

import { getCurrentUser } from '@/lib/auth'
import { withTenant } from '@/lib/rls'

export async function getDashboardOverview() {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    const [companyCount, contactCount, emailStats] = await Promise.all([
      tx.tenant_companies.count({
        where: { visibility_status: 'visible' },
      }),
      tx.tenant_contacts.count(),
      tx.$queryRaw`
        SELECT
          count(*) FILTER (WHERE status = 'sent') AS sent,
          count(*) FILTER (WHERE status = 'opened') AS opened,
          count(*) FILTER (WHERE status = 'bounced') AS bounced
        FROM emails
        WHERE created_at > now() - interval '30 days'
      `,
    ])

    return { companyCount, contactCount, emailStats }
  })
}

export async function getDashboardFunnel() {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    const rows = await tx.$queryRaw`
      SELECT business_status, count(*)::int AS total
      FROM tenant_companies
      WHERE visibility_status = 'visible'
      GROUP BY business_status
    `
    return rows
  })
}
```

> **Spike 验证**：使用 `withTenant(tenantId, async (tx) => { ... })` 模式，RLS 已设置 `app.current_tenant_id`，查询中不需要显式传 `tenant_id` 条件（RLS 策略自动过滤）。

- [ ] **Step 2: 实现 Dashboard 页面**

修改 `nextjs/app/(tenant)/page.tsx`：

```tsx
'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import { BankOutlined, TeamOutlined, MailOutlined } from '@ant-design/icons'
import { getDashboardOverview, getDashboardFunnel } from './actions/dashboard'

export default function DashboardPage() {
  const [overview, setOverview] = useState<{
    companyCount: number
    contactCount: number
    emailStats: Array<{ sent: number; opened: number; bounced: number }>
  } | null>(null)

  useEffect(() => {
    getDashboardOverview().then(setOverview)
  }, [])

  if (!overview) return <Card loading />

  const stats = overview.emailStats?.[0] || { sent: 0, opened: 0, bounced: 0 }

  return (
    <div>
      <h2>仪表盘</h2>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="公司总数" value={overview.companyCount} prefix={<BankOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="联系人总数" value={overview.contactCount} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="30天已发邮件" value={stats.sent} prefix={<MailOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="30天已打开" value={stats.opened} prefix={<MailOutlined />} />
          </Card>
        </Col>
      </Row>
      {/* funnel 图表在此补充 */}
    </div>
  )
}
```

- [ ] **Step 3: 验证 Dashboard 数据正确**

```bash
cd nextjs && pnpm dev
# 登录后访问 /，应看到公司数、联系人数、邮件统计
# 对比旧版 Vite 前端的数据是否一致
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/app/\(tenant\)/
git commit -m "feat: 迁移 Dashboard 仪表盘到 Next.js Server Action"
```

---

### Task 1.2：精选客户页面

> 结构与 Dashboard 类似：Server Action 查库 → 页面渲染表格。
> 参考 `backend/app/services/tenant_query_service.py` 中的 curated_customers 查询逻辑。

**Files:**
- Create: `nextjs/app/(tenant)/curated-customers/actions.ts`
- Modify: `nextjs/app/(tenant)/curated-customers/page.tsx`

- [ ] **Step 1: 创建 Server Action — 精选客户列表**

```typescript
'use server'

import { getCurrentUser } from '@/lib/auth'
import { withTenant } from '@/lib/rls'

interface CuratedCustomersParams {
  page: number
  pageSize: number
  keyword?: string
}

export async function getCuratedCustomers(params: CuratedCustomersParams) {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    // 精选客户 = score >= 阈值 且 visibility_status = 'visible'
    const where: Record<string, unknown> = {
      visibility_status: 'visible',
      score: { not: null },
    }

    // 关键词搜索需要关联 clean_companies（与公司列表 Spike 验证的模式一致）
    if (params.keyword) {
      where.clean_companies = {
        name_normalized: { contains: params.keyword.toLowerCase() },
      }
    }

    const [total, companies] = await Promise.all([
      tx.tenant_companies.count({ where }),
      tx.tenant_companies.findMany({
        where,
        skip: (params.page - 1) * params.pageSize,
        take: params.pageSize,
        orderBy: { score: 'desc' },
        include: {
          clean_companies: {
            select: { name: true, country_iso3: true, website: true, industry_tags: true },
          },
        },
      }),
    ])

    return {
      total,
      data: companies.map((tc) => ({
        id: tc.id.toString(),
        companyName: tc.clean_companies.name,
        country: tc.clean_companies.country_iso3,
        website: tc.clean_companies.website,
        industryTags: tc.clean_companies.industry_tags,
        score: tc.score ? Number(tc.score) : null,
        businessStatus: tc.business_status,
      })),
    }
  })
}
```

- [ ] **Step 2: 实现页面（Ant Design Table + 分页 + 搜索）**

参考公司列表 Spike 的页面结构（`nextjs-spike/app/dashboard/companies/page.tsx`），复用相同的 Table + Search + Pagination 模式。

- [ ] **Step 3: 验证数据与旧版一致**

```bash
cd nextjs && pnpm dev
# 登录后访问 /curated-customers
# 对比旧版 Vite 前端同一页面的数据条数和排序
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/app/\(tenant\)/curated-customers/
git commit -m "feat: 迁移精选客户页面到 Next.js Server Action"
```

---

### Task 1.3：情报页面

**Files:**
- Create: `nextjs/app/(tenant)/intelligence/actions.ts`
- Modify: `nextjs/app/(tenant)/intelligence/page.tsx`

> 包含订阅管理（读写）和文章列表（只读）。订阅更新是 PUT 操作，在 Server Action 中实现。

- [ ] **Step 1: 创建 Server Actions**

```typescript
'use server'

import { getCurrentUser } from '@/lib/auth'
import { withTenant } from '@/lib/rls'

/** 获取情报订阅列表 */
export async function getIntelligenceSubscriptions() {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    return tx.intelligence_subscriptions.findMany({
      orderBy: { created_at: 'desc' },
    })
  })
}

/** 更新订阅状态（启用/禁用） */
export async function updateSubscription(id: string, enabled: boolean) {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    return tx.intelligence_subscriptions.update({
      where: { id: BigInt(id) },
      data: { enabled },
    })
  })
}

/** 获取情报文章列表（分页） */
export async function getIntelligenceArticles(params: { page: number; pageSize: number }) {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    const [total, articles] = await Promise.all([
      tx.intelligence_articles.count(),
      tx.intelligence_articles.findMany({
        skip: (params.page - 1) * params.pageSize,
        take: params.pageSize,
        orderBy: { published_at: 'desc' },
      }),
    ])
    return { total, data: articles }
  })
}
```

> **注意**：表名需根据 Prisma introspect 生成的实际 schema 调整。上述代码为示意结构。

- [ ] **Step 2: 实现页面（Tab 切换：订阅配置 / 文章列表）**

使用 Ant Design `Tabs` 组件，两个 tab：
- 订阅配置：Table + Switch 控件（启用/禁用）
- 文章列表：Table + 分页

- [ ] **Step 3: 验证**

```bash
cd nextjs && pnpm dev
# 登录后访问 /intelligence
# Tab 1: 订阅列表显示正常，切换开关触发更新
# Tab 2: 文章列表分页正常
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/app/\(tenant\)/intelligence/
git commit -m "feat: 迁移情报页面到 Next.js Server Action"
```

---

### Task 1.4：邮件监控页面

**Files:**
- Create: `nextjs/app/(tenant)/email-monitor/actions.ts`
- Modify: `nextjs/app/(tenant)/email-monitor/page.tsx`

> 包含邮件统计（多维度）和邮件列表（游标分页）。
> 参考 `backend/app/services/tenant_messaging_service.py` 中的统计和列表 SQL。

- [ ] **Step 1: 创建 Server Actions**

```typescript
'use server'

import { getCurrentUser } from '@/lib/auth'
import { withTenant } from '@/lib/rls'

/** 邮件统计概览（30天） */
export async function getEmailStats() {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    const stats = await tx.$queryRaw`
      SELECT
        count(*) FILTER (WHERE status = 'sent')::int AS sent,
        count(*) FILTER (WHERE status = 'delivered')::int AS delivered,
        count(*) FILTER (WHERE status = 'opened')::int AS opened,
        count(*) FILTER (WHERE status = 'clicked')::int AS clicked,
        count(*) FILTER (WHERE status = 'bounced')::int AS bounced,
        count(*) FILTER (WHERE status = 'complained')::int AS complained
      FROM emails
      WHERE created_at > now() - interval '30 days'
    `
    return (stats as Array<Record<string, number>>)[0]
  })
}

/** 邮件趋势数据（按天聚合，最近 30 天） */
export async function getEmailTrend() {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    return tx.$queryRaw`
      SELECT
        date_trunc('day', created_at)::date AS date,
        count(*) FILTER (WHERE status = 'sent')::int AS sent,
        count(*) FILTER (WHERE status = 'opened')::int AS opened
      FROM emails
      WHERE created_at > now() - interval '30 days'
      GROUP BY 1
      ORDER BY 1
    `
  })
}

/** 邮件列表（offset 分页） */
export async function getEmails(params: { page: number; pageSize: number; status?: string }) {
  const user = await getCurrentUser()
  if (!user || !user.tid) throw new Error('未认证')

  return withTenant(user.tid, async (tx) => {
    const where: Record<string, unknown> = {}
    if (params.status) where.status = params.status

    const [total, emails] = await Promise.all([
      tx.emails.count({ where }),
      tx.emails.findMany({
        where,
        skip: (params.page - 1) * params.pageSize,
        take: params.pageSize,
        orderBy: { created_at: 'desc' },
        select: {
          id: true, to_email: true, subject: true, status: true,
          sent_at: true, opened_at: true, created_at: true,
        },
      }),
    ])
    return { total, data: emails }
  })
}
```

> **注意**：raw SQL 中的表名和字段需根据实际 schema 调整。趋势数据按天聚合，前端用 Ant Design Charts 或简单列表展示。

- [ ] **Step 2: 实现页面（统计卡片 + 趋势 + 邮件表格）**

页面结构：
- 顶部：6 个 `Statistic` 卡片（已发送/已送达/已打开/已点击/退信/投诉）
- 中部：趋势（可先用简单表格代替图表，后续补 Chart）
- 底部：邮件列表 `Table`，支持按状态筛选 + 分页

- [ ] **Step 3: 验证**

```bash
cd nextjs && pnpm dev
# 登录后访问 /email-monitor
# 统计卡片数字与旧版一致
# 邮件列表分页和筛选正常
```

- [ ] **Step 4: 提交**

```bash
git add nextjs/app/\(tenant\)/email-monitor/
git commit -m "feat: 迁移邮件监控页面到 Next.js Server Action"
```

---

### Phase 1 完成标志

- [ ] Dashboard、精选客户、情报、邮件监控 4 个页面全部通过 Next.js Server Action 直接查库
- [ ] 对应的 FastAPI API 路由仍保留（未迁移的页面可能仍依赖）
- [ ] 数据与旧版完全一致

---

## Phase 2：租户端 CRUD 页面（写操作 + 真源切换）

> Phase 2 使用 Phase 1 建立的迁移流水线，但涉及写操作，风险更高。
>
> **每迁一个模块必须：**
> 1. AI 翻译 Python service → TypeScript（包含完整业务校验逻辑）
> 2. 新旧接口对比测试（写操作需对比：输入校验、状态变更、错误码）
> 3. 对比通过 → 切真源 → 冻结该模块的 FastAPI API
>
> 参考对应的 `*_service.py` 中的 SQL 和校验逻辑。

### Task 2.1：公司管理（最复杂的 CRUD 页面）

**Files:**
- Create: `nextjs/app/(tenant)/companies/actions.ts`
- Modify: `nextjs/app/(tenant)/companies/page.tsx`
- Create: `nextjs/app/(tenant)/companies/[id]/page.tsx`
- Create: `nextjs/app/(tenant)/companies/[id]/actions.ts`

包含：
- 公司列表（10+ 筛选参数、排序、分页）
- 公司详情（联系人列表、评分、活动历史）
- 创建公司
- 批量导入
- 导出
- 加黑名单

参考：
- `tenant_query_service.py` → `companies_page()`（列表查询，动态 SQL 拼接）
- `tenant_ops_service.py` → `create_company()`（创建逻辑，国家规范化 + 去重 + 落库）
- `company_filter_sql.py`（筛选条件构建工具函数）

- [ ] **Step 1-N: 按子功能逐步实现（列表 → 筛选 → 详情 → 创建 → 导入 → 导出）**

---

### Task 2.2：邮件模板

**Files:**
- Create: `nextjs/app/(tenant)/templates/actions.ts`
- Modify: `nextjs/app/(tenant)/templates/page.tsx`

包含：CRUD + AI 生成 + 克隆 + 预览

参考：`tenant_messaging_service.py` 中模板相关方法

---

### Task 2.3：设置 - 关键词

参考：`tenant_settings_service.py`

---

### Task 2.4：设置 - 评分规则

参考：`tenant_scoring_weights_service.py`

---

### Task 2.5：设置 - AI 配置

参考：`tenant_ai_provider_service.py`

---

### Task 2.6：设置 - 团队管理

参考：`tenant_team_service.py`

---

### Phase 2 完成标志

- [ ] 公司管理全功能可用（列表、详情、创建、导入、导出、黑名单）
- [ ] 邮件模板 CRUD + AI 生成
- [ ] 4 个设置页面全部可用
- [ ] 所有写操作通过 Server Action 直接落库

---

## Phase 3：租户端复杂页面

### Task 3.1：发送计划列表

参考：`tenant_messaging_service.py` 中 sending_plans 相关方法

---

### Task 3.2：发送计划新建（多步骤表单）

这是最复杂的页面，包含：
- 选择收件人（从公司/分组/筛选条件）
- 配置发送步骤（模板 + 延迟 + 条件）
- 预览和确认

参考：`tenant_messaging_service.py` 中 `create_sending_plan()`、`complete_create_sending_plan()`

---

### Task 3.3：发送计划详情

包含：步骤编辑、收件人管理、状态流转（启动/暂停/恢复/取消）

---

### Task 3.4：Onboarding 引导页

参考：`tenant_settings_service.py` 中 onboarding 相关方法

---

### Phase 3 完成标志

- [ ] 发送计划全流程可用（创建 → 配置步骤 → 选择收件人 → 启动 → 监控）
- [ ] Onboarding 流程正常
- [ ] **租户端全部 15 个页面迁移完成**

---

## Phase 4：管理端全部页面

### Task 4.0：管理端基础设施

**Files:**
- Create: `nextjs/app/admin/login/page.tsx`
- Create: `nextjs/app/admin/(dashboard)/layout.tsx`
- Create: `nextjs/components/AdminSidebar.tsx`

与租户端类似，创建 Admin 登录 + 布局 + 侧边栏。

---

### Task 4.1 - 4.13：逐页迁移

按以下顺序（从简单到复杂）：

| Task | 页面 | 复杂度 | 参考 Service |
|------|------|--------|-------------|
| 4.1 | 预热规则 | 低 | `admin_config_service.py` |
| 4.2 | 情报源 | 低 | `admin_config_service.py` |
| 4.3 | AI 配置 | 中 | `admin_config_service.py` |
| 4.4 | 评分模板 | 中 | `admin_config_service.py` |
| 4.5 | 数据源 | 中 | `admin_config_service.py` |
| 4.6 | 联系人分类 | 中 | `contact_classification_service.py` |
| 4.7 | 采集-Tendata | 低 | `admin_collection_service.py` |
| 4.8 | 采集-客户 | 低 | `admin_collection_service.py` |
| 4.9 | 采集-同行 | 低 | `admin_collection_service.py` |
| 4.10 | 采集任务 | 中 | `admin_collection_service.py` |
| 4.11 | 邮件模板 | 高 | `admin_config_service.py` + GrapeJS |
| 4.12 | 租户管理 | 高 | `tenant_service.py` + `tenant_team_service.py` |

---

### Phase 4 完成标志

- [ ] 管理端全部 14 个页面迁移完成
- [ ] GrapeJS 邮件编辑器正常工作
- [ ] 租户管理全功能可用
- [ ] **前端 + 后端 API 层全部迁移到 Next.js**

---

## Phase 5：下线旧系统

### Task 5.1：移除 FastAPI API 层

- [ ] 从 `next.config.ts` 中移除所有 rewrites 规则
- [ ] 验证没有任何请求还在走 FastAPI
- [ ] 保留 FastAPI 的 `/internal/api/v1` 和 `/webhooks`（Worker 依赖）
- [ ] 或将 Internal API 和 Webhook 也迁移到 Next.js Route Handler

### Task 5.2：清理旧前端

- [ ] 删除 `frontend/` 目录（Vite React monorepo）
- [ ] 更新部署脚本，不再构建和推送旧前端镜像
- [ ] 更新 CI/CD 配置

### Task 5.3：评估 Worker 迁移

Worker 当前是 Python，通过 Internal API 和直接数据库访问工作。两个选择：

**选项 A：保留 Python Worker**
- 优点：零工作量，已经稳定运行
- 缺点：维护两套语言栈

**选项 B：迁移到 Node**
- 使用 BullMQ 或类似队列替代当前的 lease-based 轮询
- 使用 Prisma 访问数据库
- 逐个 Worker 迁移

**建议：Phase 5 只做 API 层和前端清理，Worker 迁移作为独立项目评估。**

---

## 关键风险和缓解措施

| 风险 | 缓解 |
|------|------|
| Prisma introspect 结果与手写 SQL 不一致 | Phase 0 验证所有表可读；复杂查询继续用 `$queryRaw` |
| RLS 在 Prisma 中不生效 | 每次查询前 `$executeRaw` 设置 tenant 上下文，封装为 `withTenant()` |
| Server Action 中复杂 SQL 迁移遗漏 | 每个页面迁移后对比旧版数据，写自动化对比脚本 |
| 两套系统并行时数据一致性 | 同一模块的前端 + API 整块切，不拆分 |
| Alembic 迁移 + Prisma 冲突 | Prisma 只做 introspect（`db pull`），不做 migrate；每次 Alembic 迁移后重新 `db pull` + `generate` |

---

## 迁移检查清单（每个页面通用）

每迁移一个页面，完成以下检查：

- [ ] Server Action 实现所有业务逻辑（参考对应 `*_service.py`）
- [ ] RLS 上下文正确设置
- [ ] 前端页面渲染正确
- [ ] 数据与旧版一致（手动对比或自动化脚本）
- [ ] 错误处理和 loading 状态
- [ ] 移动端适配（如有需要）
- [ ] 提交代码
