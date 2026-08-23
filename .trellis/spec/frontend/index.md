# 前端开发规范（frontend/）

> pnpm workspace：`apps/admin`（Next.js 15 + React 19，SSR 预取壳 + 客户端页）、`apps/tenant`（纯客户端渲染）、`packages/shared-*`。UI 设计契约（原仓库根 `DESIGN.md`）已整体迁入本目录。

## 规范索引

| 文件 | 内容 | 何时读 |
|---|---|---|
| [directory-structure.md](./directory-structure.md) | workspace 布局、页面模式、API 前缀与环境变量、命名 | 新增页面 / 包 |
| [design-system.md](./design-system.md) | 设计令牌（frontmatter）、原则、色彩 / 字体 / 布局 / 圆角、Do & Don't | 任何 UI 改动前 |
| [component-guidelines.md](./component-guidelines.md) | `@shared/ui` 原语、列表页五件套公开 API（已冻结）、列表交互口径 | 做列表页 / 改组件 |
| [state-management.md](./state-management.md) | React Query、`queryKeys`、Zustand 认证、权限、分页 hook | 取数 / 状态 |
| [type-safety.md](./type-safety.md) | 手写 `shared-types` 与后端同步、API 函数签名 | 改契约 |
| [quality-guidelines.md](./quality-guidelines.md) | 门禁、Vitest 模式、UI 规则摘要、部署联调坑、评审清单 | 提交前 |

## 开发前检查清单（Pre-Development Checklist）

- [ ] 读 design-system.md 与 component-guidelines.md：用 `@shared/ui` 原语与五件套，不在 app 内复制布局 / 分页 / 状态判断
- [ ] 服务端状态用 React Query + `queryKeys` 工厂；认证只从 `useAuthStore` 读；权限经 `usePermission`
- [ ] 涉及后端字段：同一 PR 同步 `shared-types` / `shared-api`（type-safety.md）
- [ ] admin 页面：SSR 预取 key 与客户端 `useQuery` key 完全一致
- [ ] 五态可区分：loading / refresh / empty / 筛选无结果 / error
- [ ] 过一遍 [../guides/index.md](../guides/index.md) 的思考触发器

## 质量检查（Quality Check）

- [ ] `cd frontend && pnpm type-check` 通过；tenant 改动跑 `pnpm --filter @apps/tenant test`；admin 改动跑 `pnpm build:admin`
- [ ] 列表页：refetch 不清空旧行、mutation pending 有反馈、危险操作有确认对话框
- [ ] 无散写像素列宽与颜色 class；图标按钮有 `aria-label`
- [ ] 收尾按 [../guides/delivery-checklist.md](../guides/delivery-checklist.md)
