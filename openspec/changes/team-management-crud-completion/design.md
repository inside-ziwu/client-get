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

## Risks / Trade-offs

- **[权衡] 单文件 vs 拆组件** — 目前页面逻辑集中在一个文件，增加编辑/删除弹窗后文件会变长。→ 接受：功能边界清晰，暂不拆分，后续若继续膨胀再拆。
