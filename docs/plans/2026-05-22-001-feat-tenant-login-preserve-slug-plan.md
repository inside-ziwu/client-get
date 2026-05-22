---
title: "feat: 租户端登录页隐藏 slug 字段，退出后保留 slug"
status: active
created: 2026-05-22
origin: openspec/changes/tenant-login-preserve-slug/
type: feat
depth: standard
execution_posture: test-first
---

# feat: 租户端登录页隐藏 slug 字段，退出后保留 slug

## Summary

租户端登录页移除"租户标识"输入框，slug 从 URL query param `?slug=xxx` 静默读取；无 slug 时展示错误提示。同时修复 401 拦截器丢失 slug 的 bug，统一所有退出/过期路径的 slug 保留行为。

(see origin: `openspec/changes/tenant-login-preserve-slug/proposal.md`)

---

## Problem Frame

当前登录页展示 slug 输入框，对用户来说是不必要的技术细节。401 拦截器 (`shared-api/src/client.ts:37`) 直接跳转 `/login`，丢失 slug。手动退出和 RequireAuth guard 已正确保留 slug。

---

## Scope Boundaries

**In scope:**
- 登录页 UI 改造（移除 slug 字段，条件渲染）
- 401 拦截器 slug 保留修复
- 空 slug 边界处理
- vitest 测试基础设施引入（tenant 端 + shared-api 包）

**Out of scope:**
- URL 结构变更（不引入路径级 slug）
- dashboard 路由变更
- 后端 API 改动
- admin 端登录流程

### Deferred to Follow-Up Work
- 完整的 tenant 端组件测试覆盖（本次只引入基础设施 + 当前 change 的测试）

---

## Key Technical Decisions

1. **测试框架选型：vitest + @testing-library/react** — 与项目 ESM 模式兼容，配置简单，React 19 支持好。login 页是纯逻辑 + 条件渲染，testing-library 足以覆盖。

2. **401 拦截器：logout 前缓存 slug** — 与 `handleLogout` 一致的模式（先读 `payload?.slug`，再调 `logout()`）。admin 端 payload 无 slug，自然降级到 `/login`。(see origin: `openspec/changes/tenant-login-preserve-slug/design.md` D2)

3. **无 slug / 空 slug 统一处理** — `searchParams.get('slug')?.trim() || null`，null 时渲染错误提示。

---

## Implementation Units

### U1. 引入 vitest 测试基础设施（tenant 端）

**Goal:** 在 tenant app 中配置 vitest + jsdom + @testing-library/react，使组件测试能跑通。

**Requirements:** 为后续 TDD 步骤提供测试运行环境

**Dependencies:** 无

**Files:**
- `frontend/apps/tenant/vitest.config.ts`（新建）
- `frontend/apps/tenant/package.json`（添加 devDependencies + test script）
- `frontend/apps/tenant/test/setup.ts`（新建，testing-library 全局配置）

**Approach:**
- 安装 `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` 作为 devDependencies
- vitest 配置 `environment: 'jsdom'`，`setupFiles` 指向 `test/setup.ts`
- setup.ts 中导入 `@testing-library/jest-dom/vitest`
- tsconfig 路径别名需要在 vitest.config 中通过 `resolve.alias` 映射
- package.json 添加 `"test": "vitest run"`, `"test:watch": "vitest"`

**Patterns to follow:** 项目使用 ESM (`"type": "module"`)，vitest 原生支持 ESM，无额外配置。tsconfig 中的 `@/*` 和 `@shared/*` 路径别名需要映射到 vitest 的 resolve.alias。

**Test scenarios:**
- 运行 `pnpm --filter tenant test` 应能发现并执行测试文件（即使暂时无测试也应成功退出）

**Verification:** `pnpm --filter tenant test` 正常退出，无报错

---

### U2. 引入 vitest 测试基础设施（shared-api 包）

**Goal:** 在 shared-api 包中配置 vitest，使 401 拦截器的单元测试能跑通。

**Requirements:** 为 U6 的 401 拦截器测试提供运行环境

**Dependencies:** 无（可与 U1 并行）

**Files:**
- `frontend/packages/shared-api/vitest.config.ts`（新建）
- `frontend/packages/shared-api/package.json`（添加 devDependencies + test script）

**Approach:**
- 安装 `vitest` 作为 devDependency
- 401 拦截器测试不需要 DOM（测试 `window.location.href` 赋值行为），使用 `environment: 'jsdom'` 模拟 window
- 需要 mock `useAuthStore` 的 `getState()` 和 `logout()`

**Patterns to follow:** shared-api 是纯 TS 包，无 React 依赖，vitest 配置最简化。

**Test scenarios:**
- `pnpm --filter @shared/api test` 正常退出

**Verification:** `pnpm --filter @shared/api test` 正常退出

---

### U3. 写测试：登录页带 slug 时只展示邮箱和密码

**Goal:** RED — 写出"带 slug 访问登录页只展示邮箱+密码"的测试用例，预期当前代码跑不过。

**Requirements:** 登录页 SHALL 隐藏租户标识输入框（spec scenario: 带 slug 的正常登录）

**Dependencies:** U1

**Files:**
- `frontend/apps/tenant/test/login-page.test.tsx`（新建）

**Execution note:** TDD RED 阶段。写测试，验证测试失败（因为当前代码仍展示 slug 字段）。

**Approach:**
- mock `next/navigation` 的 `useSearchParams` 返回 `slug=acme`
- mock `useRouter` 的 `replace`
- mock `@shared/hooks` 的 `useAuthStore`
- 渲染 `LoginForm` 组件，断言：
  - 不存在 label "租户标识"
  - 不存在 name="slug" 的 input
  - 存在 name="email" 的 input
  - 存在 name="password" 的 input

**Test scenarios:**
- 带 slug 的登录页不展示 slug 输入框
- 带 slug 的登录页展示邮箱和密码字段

**Verification:** 测试运行失败（RED），失败原因是找到了 slug 输入框

---

### U4. 写测试：无 slug 时展示错误提示

**Goal:** RED — 写出"无 slug 访问登录页展示错误提示"的测试用例。

**Requirements:** 登录页 SHALL 隐藏租户标识输入框（spec scenario: 无 slug 访问登录页）

**Dependencies:** U1

**Files:**
- `frontend/apps/tenant/test/login-page.test.tsx`（追加）

**Execution note:** TDD RED 阶段。

**Approach:**
- mock `useSearchParams` 返回空（无 slug 参数）
- 渲染组件，断言：
  - 存在"请通过正确的链接访问"或类似错误提示文案
  - 不存在登录表单（无 email/password input）
- 额外测试空 slug (`?slug=`, `?slug=  `)
  - `searchParams.get('slug')` 返回 `''`
  - 同样应展示错误提示

**Test scenarios:**
- 无 slug 参数 → 展示错误提示，不展示表单
- 空 slug (`?slug=`) → 展示错误提示，不展示表单
- 纯空格 slug (`?slug=  `) → 展示错误提示，不展示表单

**Verification:** 测试运行失败（RED），失败原因是当前代码始终展示表单

---

### U5. 实现登录页改造

**Goal:** GREEN — 修改登录页代码，使 U3 和 U4 的测试通过。

**Requirements:** 登录页 SHALL 隐藏租户标识输入框（全部场景）

**Dependencies:** U3, U4

**Files:**
- `frontend/apps/tenant/src/app/login/page.tsx`（修改）

**Execution note:** TDD GREEN 阶段。最小改动使测试通过。

**Approach:**
- 移除 `const [slug, setSlug] = useState(initialSlug)` state
- 将 slug 改为从 searchParams 静默读取：`const slug = searchParams.get('slug')?.trim() || null`
- 条件渲染：`if (!slug)` 返回错误提示 UI（Card + 提示文案），不展示表单
- 有 slug 时只展示邮箱和密码字段
- `onSubmit` 中移除 `formData.get('slug')` 逻辑，直接使用 `slug` 变量
- 移除 slug 相关的 toast.error 校验

**Patterns to follow:** 保持现有 Card + CardHeader + CardContent 的 UI 结构

**Test scenarios:** 由 U3, U4 覆盖

**Verification:** U3 和 U4 的所有测试通过（GREEN）；TypeScript 类型检查通过

---

### U6. 写测试：401 拦截器保留 slug

**Goal:** RED — 写出"401 响应时重定向保留 slug"的测试用例。

**Requirements:** 退出登录 SHALL 在重定向 URL 中保留 slug（spec scenario: API 401 响应触发重定向 + payload 无 slug 降级）

**Dependencies:** U2

**Files:**
- `frontend/packages/shared-api/test/client.test.ts`（新建）

**Execution note:** TDD RED 阶段。

**Approach:**
- mock `useAuthStore.getState()` 返回包含 `payload: { slug: 'acme' }` 的状态
- mock `useAuthStore.getState().logout` 为 spy
- 创建 tenant 类型的 apiClient
- mock axios adapter 返回 401 响应
- 断言 `window.location.href` 被设为 `/login?slug=acme`
- 断言 `logout()` 被调用
- 另一个用例：payload 为 null 时，降级到 `/login`

**Test scenarios:**
- 401 响应 + payload 有 slug → 跳转 `/login?slug=acme`，调用 logout
- 401 响应 + payload 无 slug → 跳转 `/login`，调用 logout
- 非 401 响应 → 不触发重定向，不调用 logout

**Verification:** 测试运行失败（RED），失败原因是当前代码跳转 `/login` 而非 `/login?slug=acme`

---

### U7. 实现 401 拦截器修复

**Goal:** GREEN — 修改 401 拦截器代码，使 U6 的测试通过。

**Requirements:** 退出登录 SHALL 在重定向 URL 中保留 slug（全部场景）

**Dependencies:** U6

**Files:**
- `frontend/packages/shared-api/src/client.ts`（修改）

**Execution note:** TDD GREEN 阶段。

**Approach:**
- 在 `logout()` 调用前缓存 slug：`const slug = useAuthStore.getState().payload?.slug`
- 然后调用 `useAuthStore.getState().logout()`
- 重定向改为：`window.location.href = slug ? `/login?slug=${slug}` : '/login'`

**Patterns to follow:** 与 `app-shell.tsx` 的 `handleLogout` 保持一致的模式

**Test scenarios:** 由 U6 覆盖

**Verification:** U6 的所有测试通过（GREEN）

---

### U8. 全量测试 + 类型检查 + 手动验证

**Goal:** 确认所有测试通过、类型安全、端到端行为正确。

**Requirements:** 全部 spec scenarios

**Dependencies:** U5, U7

**Files:** 无新文件

**Approach:**
- 运行 `pnpm --filter tenant test` 和 `pnpm --filter @shared/api test` 全部通过
- 运行 `pnpm --filter tenant type-check` 类型检查通过
- 启动开发服务器，手动验证：
  - `/login?slug=acme` → 只有邮箱+密码，登录成功
  - `/login` → 错误提示，无表单
  - `/login?slug=` → 错误提示，无表单
  - 登录后退出 → URL 保留 `?slug=acme`

**Test expectation:** none — 这是验证步骤，不产出新测试

**Verification:** 全部测试绿色，类型检查通过，手动验证全部场景符合预期

---

## System-Wide Impact

- **shared-api 包是共享的**：401 拦截器修改同时影响 admin 端。admin 的 JWT payload 不含 slug，`payload?.slug` 为 undefined，自然降级到 `/login`，行为不变。
- **sessionStorage 限制**：slug 存在 JWT payload 中，JWT 存在 sessionStorage 中。新标签页不继承 session，但这不影响本次改动——新标签页需要通过管理员分发的链接访问。

---

## Deferred Implementation Notes

- vitest 配置中的路径别名映射需要实际调试确认——`@shared/*` 指向 monorepo packages 的路径可能需要调整。
- `LoginForm` 是 `'use client'` 组件包在 `<Suspense>` 中，testing-library 渲染时需确认 `useSearchParams` 的 mock 方式是否正确。若标准 mock 不工作，可能需要用 `jest.mock('next/navigation')` 替代方案。
