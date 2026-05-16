## Context

当前 Admin 和 Tenant 两端侧边栏均为固定 `w-64`（256px），在 `lg` 断点以上显示。两端 Sidebar 组件结构高度一致：Logo 区 + ScrollArea 内的分组导航链接。AppShell 用 flex 布局将 Sidebar 与主内容区并排。

## Goals / Non-Goals

**Goals:**

- 用户可通过底部按钮切换侧边栏展开/收起
- 收起态仅显示图标（~64px 宽），悬停时浮层展开完整菜单
- 偏好通过 localStorage 持久化
- 两端共享逻辑，最小化重复代码

**Non-Goals:**

- 不改动移动端（`<lg`）的行为
- 不引入 Zustand 或 Context — 组件内 useState 足矣
- 不做动画过渡（保持简单，后续可选加入）

## Decisions

### 1. 状态管理：组件内 state + localStorage

**选择**: Sidebar 组件内 `useState` + `useEffect` 读写 localStorage key `sidebar-collapsed`。

**备选**: 提升到 AppShell 通过 props 传递 / 用 Zustand store。

**理由**: 侧边栏状态不影响其他组件渲染逻辑；AppShell 只需根据 sidebar 实际 DOM 宽度自适应（flex 天然做到）。无需额外状态共享。

### 2. 收起态宽度与悬停展开

**选择**: 收起时 `w-16`（64px）仅渲染图标。整个 aside 区域监听 `onMouseEnter`/`onMouseLeave`，悬停时在收起态旁以 `absolute` 定位展开完整菜单浮层。

**备选**: CSS `group-hover` 纯样式方案。

**理由**: JS 事件方案可精确控制展开时机和状态，且后续可方便加 delay 或动画。absolute 浮层不推开主内容区，避免 layout shift。

### 3. 布局适配

**选择**: AppShell 中 Sidebar 的容器无需额外逻辑 — `shrink-0` + sidebar 自身切换 `w-64`/`w-16`，flex 布局自动让主内容区填满剩余空间。

### 4. 两端代码复用

**选择**: 在各自的 `sidebar.tsx` 中分别实现（菜单项数据不同，import 路径不同）。核心交互逻辑相同，但不抽取到 packages — 代码量小（~30 行状态逻辑），抽取的成本大于收益。

## Risks / Trade-offs

- **[无动画]** → 收起/展开无过渡，视觉上较突兀。可后续用 `transition-all duration-200` 补充，不影响功能。
- **[悬停浮层遮挡]** → 浮层用 `z-40` 确保覆盖主内容区但不覆盖 header（header `z-20` → 改为 `z-50`）。
- **[SSR hydration mismatch]** → localStorage 读取在 useEffect 中执行（客户端），首次渲染默认展开态，hydration 后可能闪一下。可接受，因为这是纯前端 UI 偏好，无 SEO 影响。
