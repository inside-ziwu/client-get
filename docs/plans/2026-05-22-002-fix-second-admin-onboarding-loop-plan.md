---
title: "fix: 修复第二个管理员登录后新手引导死循环"
status: active
created: 2026-05-22
origin: openspec/changes/fix-second-admin-onboarding-loop/proposal.md
---

# fix: 修复第二个管理员登录后新手引导死循环

## 问题概述

第二个管理员每次登录后都被跳转到新手引导页，无法进入工作台。根因是 `login/page.tsx:44` 将用户级的 `must_change_pwd` 和租户级的 `needs_onboarding` 混在同一个 `||` 条件中统一跳转到 `/onboarding`，而 onboarding 页面不处理改密码也不清除该标记，形成死循环。

## 关键技术决策

1. **`mustChangePwd` 状态存 zustand store，不改 JWT payload** — 登录时已调 `/auth/me`，直接从响应取值写入 store。token 和此字段同在 sessionStorage，清空 sessionStorage 会同时丢失两者触发重新登录，不存在不一致风险。
2. **优先级链：`must_change_pwd` > `needs_onboarding` > 正常进入** — 改密码是用户级安全强制，优先于租户级引导。改密成功后若 `needs_onboarding=true` 则跳引导，否则进首页。
3. **RequireAuth 加防绕过检查** — 防止用户手动输入 dashboard URL 绕过强制改密码。

## 范围边界

**做：**
- 拆分登录跳转为三路判断
- 新建 `/force-change-password` 页面（含反向保护）
- `useAuthStore` 加 `mustChangePwd` 字段 + 清除逻辑
- `RequireAuth` 加 `mustChangePwd` 检查

**不做：**
- 不改后端 API
- 不改 JWT payload 结构
- 不改 `needs_onboarding` 的 tenant 级别语义
- 不搭建前端测试基础设施（TODOS.md 跟踪）

---

## 实施单元

### U1. useAuthStore 加 mustChangePwd 字段

**目标：** 在 auth store 中新增 `mustChangePwd` 状态字段，支持设置和清除。

**依赖：** 无

**文件：**
- `frontend/packages/shared-hooks/src/useAuth.ts`

**做法：**
- `AuthState` 接口加 `mustChangePwd: boolean`
- 新增 `setMustChangePwd(v: boolean)` action
- `logout()` 时将 `mustChangePwd` 置为 `false`
- 初始值 `false`

**执行姿态：** 测试先行。先写断言验证 store 行为，再改实现。

**测试场景：**
- 初始状态 `mustChangePwd` 为 `false`
- 调用 `setMustChangePwd(true)` 后值变为 `true`
- 调用 `logout()` 后 `mustChangePwd` 重置为 `false`
- 调用 `setMustChangePwd(true)` 再 `setMustChangePwd(false)` 后值为 `false`

**验收：** store 的 `mustChangePwd` 字段在设置、清除、登出三个场景下行为正确。

---

### U2. 登录跳转拆分为三路判断

**目标：** 登录成功后按优先级链跳转：`must_change_pwd` → `/force-change-password`，`needs_onboarding` → `/onboarding`，否则 → `/`。同时将 `must_change_pwd` 写入 store。

**依赖：** U1

**文件：**
- `frontend/apps/tenant/src/app/login/page.tsx`

**做法：**
- 登录成功取到 `me` 响应后，调用 `setMustChangePwd(me.must_change_pwd)`
- 将原来的 `router.replace(me.must_change_pwd || me.needs_onboarding ? '/onboarding' : '/')` 替换为三路 if-else：
  - `me.must_change_pwd` → `/force-change-password`
  - `me.needs_onboarding` → `/onboarding`
  - 其他 → `/`

**执行姿态：** 测试先行。先写断言描述三种跳转场景，再改跳转逻辑。

**测试场景：**
- `must_change_pwd=true, needs_onboarding=false` → 跳转到 `/force-change-password`
- `must_change_pwd=false, needs_onboarding=true` → 跳转到 `/onboarding`
- `must_change_pwd=false, needs_onboarding=false` → 跳转到 `/`
- `must_change_pwd=true, needs_onboarding=true` → 跳转到 `/force-change-password`（优先级）
- 登录成功后 store 中 `mustChangePwd` 值与 `me.must_change_pwd` 一致

**验收：** 登录成功后根据两个标记的组合正确跳转到三个不同目标。

---

### U3. 新建 /force-change-password 页面

**目标：** 独立的强制改密码页面，含表单、API 调用、成功后清 store 并根据 `needs_onboarding` 决定下一跳、反向保护。

**依赖：** U1

**文件：**
- `frontend/apps/tenant/src/app/force-change-password/page.tsx`

**做法：**
- 复用 onboarding 页面的布局风格（居中 Card）
- 表单：当前密码 + 新密码 + 确认新密码
- 调用 `tenantApi.auth.changePassword`
- 成功回调：`setMustChangePwd(false)`，然后判断 `needs_onboarding` 决定跳 `/onboarding` 还是 `/`
- 失败回调：toast 显示错误信息（区分 401 当前密码错误和其他错误）
- 反向保护：`mustChangePwd` 为 `false` 时自动跳走（跳 `/`）
- 页面标题"修改密码"，提示"首次登录需要修改初始密码"

**执行姿态：** 测试先行。先写断言描述反向保护和表单提交场景，再写页面实现。

**测试场景：**
- `mustChangePwd=false` 时直接访问 → 重定向到 `/`
- 提交空表单 → 不发请求（前端校验）
- 新密码和确认密码不一致 → 前端提示错误
- 新密码少于 8 字符 → 前端提示错误
- 当前密码错误 → API 返回 401 → toast "当前密码错误"
- 提交成功 → store `mustChangePwd` 变为 `false`
- 提交成功且 `needs_onboarding=true` → 跳转 `/onboarding`
- 提交成功且 `needs_onboarding=false` → 跳转 `/`
- 提交中按钮禁用，防止重复提交

**验收：** 改密码页面表单提交、错误处理、成功后的清除和跳转、反向保护均工作正确。

---

### U4. RequireAuth 加 mustChangePwd 防绕过检查

**目标：** 在 dashboard layout 的 RequireAuth 中检查 `mustChangePwd`，如果为 `true` 则重定向到 `/force-change-password`，防止用户手动输入 URL 绕过。

**依赖：** U1

**文件：**
- `frontend/apps/tenant/src/app/(dashboard)/layout.tsx`

**做法：**
- RequireAuth 中从 store 读 `mustChangePwd`
- 在 useEffect 中，如果 `hasHydrated && token && !isExpired() && mustChangePwd` → `router.replace('/force-change-password')`
- 渲染时如果 `mustChangePwd` 为 `true` 则 return null（与未登录行为一致）

**执行姿态：** 测试先行。先写断言描述防绕过行为，再改 RequireAuth。

**测试场景：**
- `mustChangePwd=true` + 有效 token → 重定向到 `/force-change-password`
- `mustChangePwd=false` + 有效 token → 正常渲染 children
- `mustChangePwd=true` + token 过期 → 重定向到 `/login`（token 检查优先于 mustChangePwd 检查）

**验收：** 已登录但 `mustChangePwd=true` 的用户无法通过手动输入 URL 进入 dashboard 任何页面。

---

### U5. 手动端到端验证

**目标：** 在浏览器中完整走通修复后的流程，确认 bug 已修复且不影响现有功能。

**依赖：** U1, U2, U3, U4

**文件：** 无（手动验证）

**做法：**
- 启动 dev server
- 用首个 admin 登录 → 应跳 `/onboarding`（如果 `needs_onboarding=true`）或 `/`
- 用第二个 admin 登录 → 应跳 `/force-change-password`
- 完成改密码 → 应跳正确的下一页
- 再次登录第二个 admin → 应直接进 `/`
- 手动输入 dashboard URL → 应被重定向
- 登出 → 重新登录 → 确认无状态污染

**测试预期：** 无 — 手动验证项。

**验收：** 所有场景在浏览器中表现正确。
