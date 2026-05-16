## 1. Admin 端侧边栏改造

- [x] 1.1 改造 `frontend/apps/admin/src/components/layout/sidebar.tsx`：添加 collapsed state + localStorage 读写 + 收起态 UI（仅图标 w-16）+ 底部切换按钮
- [x] 1.2 添加悬停浮层逻辑：收起态下 mouseEnter 展开完整菜单浮层（absolute 定位），mouseLeave 关闭
- [x] 1.3 调整 `frontend/apps/admin/src/components/layout/app-shell.tsx`：确保 flex 布局适配动态 sidebar 宽度

## 2. Tenant 端侧边栏改造

- [x] 2.1 改造 `frontend/apps/tenant/src/components/layout/sidebar.tsx`：同 Admin 端逻辑
- [x] 2.2 添加悬停浮层逻辑：同 Admin 端
- [x] 2.3 调整 `frontend/apps/tenant/src/components/layout/app-shell.tsx`：同 Admin 端

## 3. 验证

- [x] 3.1 启动 Admin 开发服务器，验证收起/展开、悬停浮层、刷新持久化
- [x] 3.2 启动 Tenant 开发服务器，验证同上功能
