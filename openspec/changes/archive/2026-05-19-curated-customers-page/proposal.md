## Why

优选客户页（`/curated-customers`）当前是占位实现——仅 33 行，调 `prospects` API 显示 5 列，无群组管理功能。而后端 `groups` + `group_members` 表和完整的群组 CRUD API 已经就绪，前端公司列表页也已有调用群组 API 的 GroupModal。

需要将优选客户页升级为「左侧群组管理 + 右侧群组公司列表」的双栏布局，参照 `docs/mock/tenant-curated-customers.html` 的目标设计。

## What Changes

**后端 API（改动极小）**
- `GET /companies` 新增可选参数 `group_id`：当传入时，通过 JOIN `group_members` 过滤只返回该群组内的公司。复用现有的字段映射、分页、排序、筛选逻辑
- 无需新增路由或数据库表——groups CRUD 和 batch-add/batch-remove 全部已有

**前端优选客户页（重写）**
- 左侧面板：群组列表 + 新建/编辑/删除群组
- 右侧面板：选中群组的公司列表（表头字段=公司列表表头字段），操作支持查看详情 + 移除群组
- 「从公司列表添加」弹窗：完整筛选 + 多选 + 已在群组中的公司禁选

**前端组件抽取**
- `CompanyDetail` 从 `companies/company-detail.tsx` 抽取到共享目录，供两个页面复用
- `CompanyFilters` 从 `companies/page.tsx` 提取筛选逻辑，供主页面弹窗复用

## Decisions

### D1: 群组公司列表数据来源 — 复用 companies API + group_id 过滤

在 `GET /companies` 加 `group_id` 可选参数，复用 `companies_page()` 的完整查询逻辑（25+ 字段、33 个筛选参数、分页、排序）。

**否决方案**: 扩展 `list_group_members` SQL 返回更多字段 → 需要手动维护字段同步，且缺少分页/筛选支持。

### D2: 查看详情交互 — 原地打开详情 Drawer

在优选客户页右侧直接打开 CompanyDetail Drawer，与公司列表页体验一致。需要将 `company-detail.tsx` 抽取为共享组件。

**否决方案**: 跳转到 `/companies` 页 → 割裂用户流程；简单弹窗提示 → 功能太弱。

### D3: 群组编辑/删除位置 — 左侧 hover + 右侧标题区

左侧群组列表项 hover 时显示编辑/删除图标，右侧面板标题区域也有编辑/删除按钮。双入口，操作灵活。

### D4: 已在群组中的公司处理 — 弹窗中禁选

「从公司列表添加」弹窗中，已在当前群组的公司行显示为禁选状态（灰色 + 已添加标记）。后端 `ON CONFLICT DO NOTHING` 保底，前端 UX 优先拦截。

### D5: 移除语义 — 仅从群组移除

「移除」操作仅将公司从当前群组移除（调 `batch-remove`），公司仍在公司列表中。

### D6: 群组删除确认

删除群组时弹出二次确认弹窗，说明"仅删除群组，不影响公司数据"。

### D7: 空状态引导

无群组时右侧显示空状态引导："创建你的第一个客户群组"。

## Non-Goals

- 不改变现有 groups 数据库表结构
- 不新增 API 路由（仅扩展 `GET /companies` 参数）
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件
- 不涉及自动规则（`auto_rules` 字段留空，后期单独做）

## Capabilities

### New Capabilities

- `curated-group-panel`: 左侧群组管理面板（列表 + 新建/编辑/删除，含空状态引导）
- `curated-company-list`: 右侧群组公司列表（复用公司列表列、分页，操作含查看详情和移除）
- `curated-add-from-companies`: 「从公司列表添加」弹窗（筛选 + 多选 + 已在群组禁选 + 批量添加）

### Modified Capabilities

- `tenant-company-detail`（上一个 change 新建）: CompanyDetail 组件需从 companies 目录抽取到共享位置，`onGroupAdd` 改为 optional

## Impact

| 层 | 影响范围 | 说明 |
|----|---------|------|
| 后端 Service | `backend/app/services/tenant_query_service.py` | `companies_page` 加 `group_id` 参数，多一个 JOIN 条件 |
| 后端 API | `backend/app/api/tenant/ops.py` | `GET /companies` 路由加 `group_id` Query param |
| 前端 API 客户端 | `frontend/packages/shared-api/src/tenant/companies.ts` | list 参数类型加 `group_id` 字段 |
| 前端共享组件 | `frontend/apps/tenant/src/components/company-detail.tsx`（新位置） | 从 companies 目录移出 |
| 前端共享组件 | `frontend/apps/tenant/src/components/company-filters.tsx`（新文件） | 从 companies/page.tsx 提取 |
| 前端页面 | `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx` | 全面重写（33 行 → ~400+ 行） |
| 前端组件 | `curated-customers/add-company-modal.tsx`（新文件） | 从公司列表添加弹窗 |
| 依赖顺序 | 后端先行 → 前端跟进 | 后端加 group_id 参数 → 前端组件抽取 → 页面重写 |
