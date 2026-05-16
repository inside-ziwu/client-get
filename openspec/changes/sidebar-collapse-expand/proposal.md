## Why

侧边栏始终占据 256px 宽度，在小屏桌面（1280–1440px）或内容密集页面中压缩了主内容区可用空间。用户无法根据当前任务需求调整布局，影响效率。

## What Changes

- 侧边栏底部新增收起/展开切换按钮
- 收起状态：侧边栏缩为 ~64px 仅显示图标
- 鼠标悬停收起态侧边栏时，浮层展开完整菜单（覆盖内容区，不推开布局）
- 用 localStorage 持久化展开/收起偏好，刷新后保持上次状态
- Admin 端和 Tenant 端同时实现，共享核心逻辑

## Non-Goals

- 不涉及移动端侧边栏行为（当前 `lg:hidden` 逻辑不变）
- 不修改菜单项数据结构或路由逻辑
- 不引入全局状态管理（Zustand），仅用组件内 state + localStorage

## Capabilities

### New Capabilities

- `sidebar-collapse`: 侧边栏收起/展开交互能力（图标态、悬停浮层展开、状态持久化）

### Modified Capabilities

无

## Impact

- 前端 `frontend/apps/admin/src/components/layout/sidebar.tsx` — 重写
- 前端 `frontend/apps/tenant/src/components/layout/sidebar.tsx` — 重写
- 前端 `frontend/apps/admin/src/components/layout/app-shell.tsx` — 调整 flex 布局适配动态宽度
- 前端 `frontend/apps/tenant/src/components/layout/app-shell.tsx` — 同上
- 无后端变更、无数据库变更、无 API 变更
