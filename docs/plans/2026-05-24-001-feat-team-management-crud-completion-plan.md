---
title: "feat: 团队管理页面 CRUD 完善"
status: active
origin: docs/brainstorms/2026-05-24-team-management-crud-completion-requirements.md
change: openspec/changes/team-management-crud-completion/
created: 2026-05-24
depth: lightweight
---

# feat: 团队管理页面 CRUD 完善

## Problem Frame

租户端团队管理页面目前只有创建和列表功能，管理员无法编辑成员角色、删除离职人员或切换成员状态。角色和状态以英文原值展示，最近登录只显示日期。后端 CRUD 四个接口和前端 API 客户端均已就绪，只需补齐前端 UI。

---

## Scope Boundaries

**In scope:**
- 表格增加操作列（编辑、禁用/启用、删除）+ 自保护逻辑
- 编辑弹窗（修改姓名和角色）
- 删除确认对话框
- 角色/状态中文化显示
- 最近登录时间格式改为 `YYYY-MM-DD HH:mm` 本地时间
- 创建表单增加角色选择
- 每个行为切片的单元测试

**Out of scope:**
- 后端接口改动（已完备）
- 表格整体布局和列结构变更
- 用户头像、角色权限说明卡片
- 批量操作
- 响应式优化（内部管理页面主要桌面端使用）

### Deferred to Follow-Up Work

- 搭建前端测试基础设施的系统性覆盖（当前 TODOS.md backlog 项）

---

## Key Technical Decisions

**D1 编辑交互** — 使用 shadcn/ui `Dialog` 组件，与 `curated-customers/page.tsx` 的 `GroupFormDialog` 模式一致。弹窗内编辑失败时在弹窗内展示错误信息，不关闭弹窗。(see origin: openspec/changes/team-management-crud-completion/design.md D1, D7)

**D2 删除交互** — 使用 `AlertDialog`，与 `send-plans/page.tsx` 的删除确认模式一致。失败用 toast.error。(see origin: design.md D2)

**D3 自保护** — 在 TeamPage 组件顶层调用 `useAuthStore(s => s.payload)`，render 通过闭包引用 `payload?.sub` 与 `row.id` 对比，当前用户行显示「当前账号」，不显示操作按钮。(see origin: design.md D3; eng-review D2: 不可在 DataTable render 回调内调用 hook)

**D4 按钮视觉层次** — 编辑=link 样式，禁用/启用=outline 样式，删除=destructive 样式，三级区分操作危险程度。(see origin: design.md D6)

**D5 时间格式化** — 用 `new Date(iso)` 解析后格式化本地时间，解决 UTC vs 本地时间的矛盾。(see origin: design.md D5)

**D6 Loading 状态** — 所有提交按钮在请求期间利用 `mutation.isPending` 禁用。(see origin: design.md D8)

---

## Patterns to Follow

| 模式 | 参考文件 |
|------|---------|
| AlertDialog 删除确认 | `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx` (`DeleteGroupDialog`) |
| Dialog 编辑表单 | `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx` (`GroupFormDialog`) |
| Select 下拉组件 | `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-basic-info.tsx` |
| DataTable 操作列 | `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx` |
| Toast 反馈 | 各页面 mutation 回调：`toast.success('XXX已更新')` / `toast.error('XXX失败')` |
| Auth 取当前用户 | `frontend/apps/tenant/src/app/(dashboard)/layout.tsx` — `useAuthStore(s => s.payload)` |
| Query Key 体系 | `frontend/packages/shared-api/src/query-keys.ts` — `queryKeys.team.list()` / `queryKeys.team.all()` |

---

## Implementation Units

> 执行姿态：TDD 驱动。每个 Unit 先写失败测试，再实现使其通过。测试文件统一放在 `frontend/apps/tenant/test/settings/team/` 目录下。
>
> 全局：所有 queryKey 使用 `queryKeys.team.list()` / `queryKeys.team.all()`（from `@shared/api`），不使用裸字符串数组。(eng-review D6: 与项目 query key 体系保持一致)

### U1. 角色/状态常量映射与中文化显示

**Goal:** 定义 `ROLE_LABELS` 和 `STATUS_LABELS` 常量，替换表格中角色列和状态列的英文显示。

**Requirements:** R4 角色中文化、R5 状态中文化

**Dependencies:** 无

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-labels.test.tsx`

**Approach:** 在页面文件顶部定义两个 `Record<string, string>` 常量映射。角色列的 render 函数改为 `row.roles?.map(r => ROLE_LABELS[r] ?? r).join('、')`（中文顿号分隔）。状态列的 Badge 文本改为 `STATUS_LABELS[row.status]`。

**Patterns to follow:** 现有 Badge variant 用法（`variant={row.status === 'active' ? 'default' : 'secondary'}`）

**Execution note:** 先写测试验证映射函数输出正确中文，再改 render 函数。

**Test scenarios:**
- 单角色 `admin` 渲染为「管理员」
- 多角色 `['admin', 'operator']` 渲染为「管理员、运营」
- 状态 `active` 渲染为「已激活」
- 状态 `disabled` 渲染为「已禁用」

**Verification:** 列表中角色和状态列全部显示中文。

### U2. 最近登录时间格式化

**Goal:** 最近登录列显示 `YYYY-MM-DD HH:mm` 本地时间，未登录显示 `-`。

**Requirements:** R6 最近登录时间格式

**Dependencies:** 无

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-time-format.test.ts`

**Approach:** 提取一个 `formatLoginTime(iso: string | null | undefined): string` 纯函数。内部用 `new Date(iso)` 解析，检查 `isNaN(date.getTime())` 后再格式化；无效日期返回 `-`。用 `getFullYear/getMonth/getDate/getHours/getMinutes` 加 pad 格式化。替换原来的 `row.last_login_at?.slice(0, 10)`。

**Execution note:** 先写纯函数测试，再替换 render。UTC 时区测试不硬编码预期时间，改为验证输出格式匹配 `YYYY-MM-DD HH:mm`（避免 CI 时区差异导致 flaky test）。

**Test scenarios:**
- ISO 字符串 `2026-05-23T14:30:00+08:00` 格式化为 `2026-05-23 14:30`
- UTC 字符串格式化后匹配 `YYYY-MM-DD HH:mm` 格式（不硬编码时区结果）
- `null` 返回 `-`
- `undefined` 返回 `-`
- 无效字符串 `"invalid"` 返回 `-`（NaN 守卫）

**Verification:** 最近登录列显示完整日期+时间。

### U3. 创建表单增加角色选择

**Goal:** 创建表单增加角色 Select 下拉，默认「运营」，替换硬编码。

**Requirements:** R7 创建表单角色选择

**Dependencies:** U1（复用 ROLE_LABELS）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-create-form.test.tsx`

**Approach:** 添加 `const [role, setRole] = useState('operator')` 状态。表单内增加 `Select` 组件，options 使用 `ROLE_LABELS` 映射。mutation 的 `roles` 参数改为 `[role]`。同时补充 `createMutation` 缺失的 `onError` 处理：`onError: () => toast.error('创建失败')`。(eng-review D3)

**Patterns to follow:** `send-plans/new/step-basic-info.tsx` 的 Select 用法

**Execution note:** 测试组件渲染出 Select 且默认值为 operator，提交时携带选中的角色。

**Test scenarios:**
- 表单渲染包含角色 Select，默认选中「运营」
- 选择「管理员」后提交，mutation 参数 roles 为 `['admin']`
- 提交成功后角色 Select 重置为默认值「运营」
- 创建失败时显示 toast.error（eng-review D3 补充）

**Verification:** 创建成员时可选择角色。

### U4. 操作列与自保护逻辑

**Goal:** 表格增加操作列，当前用户行显示「当前账号」，其他行显示编辑/禁用/删除按钮。

**Requirements:** R1-R3 的自保护部分

**Dependencies:** U1

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-actions-column.test.tsx`

**Approach:** 在 TeamPage 组件顶层调用 `const payload = useAuthStore(s => s.payload)`。在 DataTable columns 末尾增加 `{ key: 'actions', title: '操作', render }` 列。render 通过闭包引用 `payload?.sub`，与 `row.id` 对比。当前用户行渲染 `<span className="text-sm text-muted-foreground">当前账号</span>`；其他行渲染三个按钮：编辑（`variant="link"`）、禁用/启用（`variant="outline" size="sm"`）、删除（`variant="destructive" size="sm"`）。按钮的 onClick 先设为占位（后续 Unit 接入 mutation）。(eng-review D2: hook 必须在组件顶层调用，不可在 render 回调内)

**Patterns to follow:** `templates/page.tsx` 的 DataTable 操作列

**Execution note:** 测试当前用户行和非当前用户行的渲染差异。

**Test scenarios:**
- 当前用户行渲染「当前账号」文本，不渲染任何操作按钮
- 非当前用户行渲染编辑、禁用/启用、删除三个按钮
- 已激活成员行的按钮文案为「禁用」
- 已禁用成员行的按钮文案为「启用」

**Verification:** 操作列正确渲染，当前用户受保护。

### U5. 编辑弹窗

**Goal:** 实现编辑弹窗，可修改姓名和角色，提交调用 update API。

**Requirements:** R1 编辑成员

**Dependencies:** U4（点击编辑按钮触发）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-edit-dialog.test.tsx`

**Approach:** 添加 `const [editTarget, setEditTarget] = useState<TeamUser | null>(null)` 状态。提取 `EditMemberDialog` 组件（同文件内），接收 `open/target/onClose` props。弹窗内包含姓名 Input 和角色 Select，通过 `useEffect` 在 target 变化时预填值。添加 update mutation，`onSuccess` 时 toast.success + invalidateQueries + onClose；`onError` 时在弹窗内展示错误信息（添加 error state）。保存按钮在 `isPending` 时禁用并显示「保存中...」。

**Patterns to follow:** `curated-customers/page.tsx` 的 `GroupFormDialog` 模式

**Execution note:** 先测试弹窗打开时预填当前值，再测试提交行为。

**Test scenarios:**
- 点击编辑后弹窗打开，姓名和角色预填当前值
- 修改姓名后点击保存，调用 update API 传入新姓名
- 修改角色后点击保存，调用 update API 传入新角色
- 保存成功后弹窗关闭，显示 toast.success
- 保存期间按钮禁用，文案显示「保存中...」
- 保存失败时弹窗不关闭，弹窗内显示错误信息

**Verification:** 编辑成员后列表刷新显示更新值。

### U6. 删除确认

**Goal:** 实现删除按钮 + AlertDialog 确认对话框。

**Requirements:** R2 删除成员

**Dependencies:** U4（点击删除按钮触发）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-delete-dialog.test.tsx`

**Approach:** 添加 `const [deleteTarget, setDeleteTarget] = useState<TeamUser | null>(null)` 状态。渲染 `AlertDialog`，controlled by `open={!!deleteTarget}`。添加 delete mutation，`onSuccess` 时 toast.success + invalidateQueries + setDeleteTarget(null)；`onError` 时 toast.error。确认按钮在 `isPending` 时禁用并显示「删除中...」。

**Patterns to follow:** `curated-customers/page.tsx` 的 `DeleteGroupDialog` + `send-plans/page.tsx` 的 AlertDialog

**Execution note:** 先测试确认和取消行为，再测试 mutation 调用。

**Test scenarios:**
- 点击删除后弹出确认对话框，显示确认文案
- 确认删除后调用 delete API
- 删除成功后对话框关闭，显示 toast.success
- 删除失败后显示 toast.error
- 点击取消后对话框关闭，不调用 API
- 删除期间确认按钮禁用，文案显示「删除中...」

**Verification:** 删除成员后列表刷新，该成员消失。

### U7. 状态切换

**Goal:** 实现启用/禁用按钮，点击后切换成员状态。

**Requirements:** R3 启用/禁用切换

**Dependencies:** U4（按钮已渲染）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/test/settings/team/team-status-toggle.test.tsx`

**Approach:** 添加 toggleStatus mutation，调用 `tenantApi.team.update(userId, { status: newStatus })`。按钮 onClick 调用该 mutation。`onSuccess` 时 toast.success；`onError` 时 toast.error。按钮在 `isPending` 时禁用。

**Execution note:** 测试两个方向的切换（激活→禁用、禁用→激活）。

**Test scenarios:**
- 已激活成员点击「禁用」后调用 update API，status 参数为 `disabled`
- 已禁用成员点击「启用」后调用 update API，status 参数为 `active`
- 切换成功后显示 toast.success
- 切换失败后显示 toast.error
- 切换期间按钮禁用

**Verification:** 点击后成员状态在列表中实时更新。

---

## System-Wide Impact

| 维度 | 影响 |
|------|------|
| 前端代码 | `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx` — 主要改动文件 |
| 测试代码 | `frontend/apps/tenant/test/settings/team/` — 新增 7 个测试文件 |
| 后端代码 | 无改动 |
| 数据库 | 无改动 |
| API 接口 | 无改动（使用已有 PATCH/DELETE 接口） |
| 依赖 | 无新增 |
| 部署 | 前端重新构建即可 |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 4 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR | score: 7/10 → 9/10, 5 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **CODEX:** Codex outside voice 发现 15 个问题，1 个可操作问题已纳入（query key 统一），1 个 TODO 已记录（后端最后管理员保护）
- **CROSS-MODEL:** 2 项共识（useAuthStore hook 调用位置、时区测试依赖），1 项新发现已采纳（queryKeys.team 统一）
- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement
