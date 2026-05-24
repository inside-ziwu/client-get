## Context

团队管理页面（`frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`）目前仅有创建和列表功能。后端 CRUD 四个接口已完备（`backend/app/api/tenant/team.py`），前端 API 客户端已封装 update/delete（`frontend/packages/shared-api/src/tenant/team.ts`）。本次仅改前端 UI 层。

当前用户 ID 通过 `useAuthStore().payload.sub` 获取，用于自保护判断。

设计参考：`docs/mock/tenant-settings-team.html`

## Goals / Non-Goals

**Goals:**
- 补齐编辑、删除、状态切换的前端交互
- 角色和状态显示中文
- 最近登录显示完整时间
- 创建表单支持角色选择

**Non-Goals:**
- 不改后端接口
- 不改表格布局和列结构
- 不加头像、角色说明卡片
- 不做批量操作

## Decisions

### D1 编辑交互：Dialog 弹窗

使用 shadcn/ui 的 `Dialog` 组件实现编辑弹窗，与 mock 设计一致。弹窗内包含姓名输入框和角色下拉选择。

替代方案：行内编辑 — 交互更轻但实现复杂度高且与整体 UI 风格不一致，不采用。

### D2 删除交互：AlertDialog 确认

使用 `AlertDialog` 做删除确认，避免误操作。

### D3 自保护逻辑：前端对比 user.id 与 payload.sub

通过 `useAuthStore().payload.sub` 获取当前用户 ID，与列表中每行的 `user.id` 对比。当前用户的操作列不显示编辑角色/删除/禁用按钮，改为显示「当前账号」标识。

### D4 角色/状态映射：前端常量 Map

在页面文件内定义 `ROLE_LABELS` 和 `STATUS_LABELS` 常量 Map，纯展示映射无需抽到共享包。

### D5 时间格式化：new Date() 转换后格式化

用 `new Date(isoString)` 解析后，通过 `getFullYear()/getMonth()/getDate()/getHours()/getMinutes()` 格式化为 `YYYY-MM-DD HH:mm` 本地时间。无论后端返回 UTC 还是带时区偏移的 ISO，都能正确显示用户本地时间。

### D6 操作列按钮视觉层次：三级样式

与 mock 一致：
- 编辑 — 链接样式（`btn-link` / `variant="link"`），最轻量
- 禁用/启用 — 普通按钮（`variant="outline"` + `size="sm"`）
- 删除 — 红色危险按钮（`variant="destructive"` + `size="sm"`）

当前登录账号的行显示「当前账号」文本，不显示操作按钮。

### D7 错误反馈方式

- 编辑弹窗：保存失败时在弹窗内展示错误信息（不关闭弹窗），用户可修改后重试
- 删除、状态切换：失败时用 `toast.error` 提示
- 所有操作成功：用 `toast.success` 提示

### D8 Loading 状态

所有提交按钮在请求期间禁用并显示 loading 状态（利用 React Query mutation.isPending）。防止重复提交。

## 交互状态覆盖

| 功能 | Loading | 空状态 | 错误 | 成功 | 部分/边界 |
|------|---------|--------|------|------|-----------|
| 成员列表 | 首次加载时表格区域显示 DataTable 默认骨架（已有的 `emptyText` 占位）；后续刷新静默（React Query background refetch） | 表格显示「暂无数据」（DataTable 已内置，居中、`text-muted-foreground`） | 列表请求失败时在表格区域显示「加载失败，请刷新」文案 + 重试按钮（`variant="outline" size="sm"`） | 无额外反馈，数据直接渲染 | 成员名超长时 `truncate`（CSS `text-overflow: ellipsis`），表格列最小宽度保证操作列不换行 |
| 创建表单 | 提交按钮显示「创建中...」+ `disabled` | 不适用 | `toast.error('创建失败')` | `toast.success('成员已创建')` + 表单清空 + 列表刷新 | 邮箱已存在 → 后端返回 409，前端 `toast.error('该邮箱已存在')` |
| 编辑弹窗 | 保存按钮显示「保存中...」+ `disabled` | 不适用 | 弹窗内展示红色错误文案（`text-sm text-destructive`），弹窗不关闭 | `toast.success('成员已更新')` + 弹窗关闭 + 列表刷新 | 姓名为空时保存按钮 `disabled`（`!editName.trim()`） |
| 删除确认 | 确认按钮显示「删除中...」+ `disabled` | 不适用 | `toast.error('删除失败')` | `toast.success('成员已删除')` + 弹窗关闭 + 列表刷新 | 不适用 |
| 状态切换 | 按钮 `disabled`（`isPending`），不改文案 | 不适用 | `toast.error('状态更新失败')` | `toast.success('状态已更新')` + 列表刷新 | 不适用 |

## 响应式行为

页面使用 `tenant-page` 布局，已有响应式断点：

- **桌面端（md+）**：创建表单 `grid-cols-[1fr_1.5fr_1fr_auto]` 四列水平排列，表格完整展示所有列
- **移动端（<md）**：创建表单纵向堆叠（grid 默认 1 列）；表格卡片内水平滚动（Card + `overflow-x-auto`）保证操作列可访问
- 弹窗在移动端宽度自适应（DialogContent 已有 `max-w-lg w-full` + 两侧留白）

操作列不做响应式折叠（下拉菜单等），原因：操作项只有三个按钮，移动端水平滚动已足够。

## 边界场景

| 场景 | 处理方式 |
|------|----------|
| 成员姓名超长（>20字符） | 表格姓名列添加 `max-w-[160px] truncate`，hover 时 title 属性显示全名 |
| 角色列多角色 | 以中文顿号「、」拼接（如「管理员、运营」），已在 render 中实现 |
| 列表为空（0 个成员） | DataTable 内置空状态：「暂无数据」居中文案 |
| 网络断开时操作 | 依赖 React Query 的 mutation error 回调 → toast.error，无离线队列 |
| 并发操作（多管理员同时编辑） | 不做乐观更新；每次操作后 `invalidateQueries` 拉最新数据；后端以最后写入为准 |

## Risks / Trade-offs

- **[权衡] 单文件 vs 拆组件** — 目前页面逻辑集中在一个文件，增加编辑/删除弹窗后文件会变长。→ 接受：功能边界清晰，暂不拆分，后续若继续膨胀再拆。
- **[权衡] 移动端操作列** — 未做下拉菜单折叠，靠水平滚动。操作项少（3个），复杂度不值得。后续若增加更多操作再改为 DropdownMenu。
- **[接受] 无乐观更新** — 所有变更走 server round-trip 后刷新。团队管理是低频操作，延迟可接受。
