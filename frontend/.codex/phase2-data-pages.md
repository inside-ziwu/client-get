# Phase 2: 数据密集页面

> 前置：Phase 1 已完成（布局 + 登录 + Dashboard 可用）
> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`

## 目标

实现 Companies、CuratedCustomers、SendPlans（列表 + 新建 + 详情）五个数据密集页面。

## 前置：cmdk MultiSelect 组件

在 `packages/shared-ui/src/components/multi-select.tsx` 自建 MultiSelect 组件：
- 基于 cmdk + Popover
- 支持多选 checkbox 模式
- 支持自由文本输入创建新选项
- 已选项以 Badge 展示，可单独删除
- 支持异步选项加载

在 `packages/shared-ui/src/index.ts` 导出。

antd `Select mode="tags"` 的替代品，Companies 页面 5 个筛选字段要用。

## 页面实现

### 1. Companies 页

`src/app/(dashboard)/companies/page.tsx`

参照现有 `apps/tenant/src/pages/Companies/index.tsx`（约 698 行）。这是最复杂的页面。

核心功能：
- **10 项筛选**（顶部筛选栏）：
  - 多选 OR：国家、行业细分、产品标签、数据来源 → 用 MultiSelect
  - 档位筛：成立时间、注册资金、公司规模、进出口额、进出口次数、联系人数量 → 用 Select
  - 筛选变化时重置分页
- **表格**：HTML table + 手动状态管理（不用 TanStack Table）
  - 游标分页（"加载更多"按钮，不是传统分页）
  - 列：公司名、国家、行业、评分、状态、联系人数、操作
- **Drawer 详情**（用 Sheet 组件）：
  - 公司基本信息
  - 联系人列表
  - 私有操作：备注编辑、标签管理、群组管理
- **批量操作**：顶部 batch bar，批量加入群组

关键 API：
- `tenantApi.companies.list(params)` — 带筛选 + 游标分页
- `tenantApi.companies.getDetail(id)` — 单个公司详情
- `tenantApi.companies.updateNote(id, note)` — 更新备注
- `tenantApi.companies.updateTags(id, tags)` — 更新标签

用到的 @shared/ui 组件：Button, Input, Select, Sheet, Table, Badge, Card, MultiSelect

### 2. CuratedCustomers 页

`src/app/(dashboard)/curated-customers/page.tsx`

参照现有 `apps/tenant/src/pages/CuratedCustomers/index.tsx`（约 300 行）。

与 Companies 共用筛选组件。区别：
- 数据来源不同（`tenantApi.curatedCustomers.list()`）
- 无 Drawer 详情
- 无私有操作

建议：将 10 项筛选抽为 `src/components/company-filters.tsx` 共用组件。

### 3. SendPlans 列表

`src/app/(dashboard)/send-plans/page.tsx`

参照现有 `apps/tenant/src/pages/SendPlans/index.tsx`。

核心功能：
- 状态切换 tab（全部 / 草稿 / 进行中 / 已完成）→ 用 Tabs 组件
- 表格：计划名、状态、发送进度、创建时间、操作
- 操作：编辑 / 删除 / 开始发送

### 4. SendPlans 新建

`src/app/(dashboard)/send-plans/new/page.tsx`

参照现有 `apps/tenant/src/pages/SendPlans/New.tsx`。

核心功能：
- 多步表单（Step 1: 选择目标客户 → Step 2: 选择模板 → Step 3: 配置发送参数 → Step 4: 预览确认）
- 每步用 Card 包装
- 最终提交创建发送计划

### 5. SendPlans 详情

`src/app/(dashboard)/send-plans/[id]/page.tsx`

参照现有 `apps/tenant/src/pages/SendPlans/Detail.tsx`。

核心功能：
- 计划详情展示（自建 dl/dt/dd 布局）
- 发送进度（自建 Progress 组件或 Radix Progress）
- 监控数据：发送状态统计

## 约束

- 所有页面 `'use client'`
- 表格手动实现（HTML table + map），不用 TanStack Table
- 表单用 useState，不引入 react-hook-form
- 游标分页保持原有逻辑
- 筛选组件在 Companies 和 CuratedCustomers 间共用
