---
title: "feat: 优选客户页 — 群组管理 + 群组公司列表 + 添加弹窗"
type: feat
status: active
date: 2026-05-19
origin: openspec/changes/2026-05-19-curated-customers-page/proposal.md
---

# feat: 优选客户页 — 群组管理 + 群组公司列表 + 添加弹窗

## Overview

将 `/curated-customers` 从 33 行占位实现升级为完整的群组管理页面：左侧群组 CRUD 面板 + 右侧群组内公司列表 + 「从公司列表添加」弹窗。后端仅需在现有 `GET /companies` 上加 `group_id` 可选参数；前端复用公司列表页的筛选/表格/详情模式，抽取 CompanyDetail 和 CompanyFilters 为共享组件。

## Problem Frame

优选客户页当前仅是占位页（33 行，调 prospects API，5 列表格），无法使用已就绪的 groups + group_members 后端能力。用户无法按群组管理公司、无法浏览群组内公司详情、无法从全量公司池中挑选添加到群组。（see origin: `openspec/changes/2026-05-19-curated-customers-page/proposal.md`）

## Requirements Trace

- R1. 后端 `GET /companies` 支持 `group_id` 可选过滤，复用全部现有查询逻辑
- R2. 左侧群组面板：列表 + 选中态 + 新建/编辑/删除群组 + 空状态引导
- R3. 右侧群组公司表格：表头字段与公司列表对齐，支持分页、查看详情 Drawer、移除
- R4. 「从公司列表添加」弹窗：完整筛选 + 多选 + 已在群组禁选 + 批量添加
- R5. CompanyDetail / CompanyFilters 抽取为共享组件，供两个页面复用
- R6. 群组删除二次确认，说明"仅删除群组，不影响公司数据"

## Scope Boundaries

- 不改变 groups / group_members 表结构
- 不新增 API 路由（仅扩展 `GET /companies` 参数）
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件
- 不涉及 auto_rules 功能

## Context & Research

### Relevant Code and Patterns

- **后端 SQL 模式**: `tenant_query_service.py` `companies_page()` 使用动态 `where_clauses` 列表 + `params` 字典构建查询，FROM 子句为 `wc JOIN tc ON tc.clean_company_id = wc.id AND tc.tenant_id = :tenant_id`。加 `group_id` 时追加条件 JOIN
- **后端路由模式**: `ops.py` GET /companies 已有 30+ Query 参数，`or None` 转换空列表，`effective_limit` / `offset` 处理分页
- **前端页面模式**: `companies/page.tsx` 完整实现了 FilterValues 类型 → buildParams → 双 useQuery（filters + list）→ 表格 → 分页 → Sheet Drawer 详情
- **前端组件**: CompanyDetail（266 行）接收 `{ company, onGroupAdd, onSaved }` Props，Sheet 右侧抽屉模式
- **共享 UI 库**: `@shared/ui` 导出 33 个组件，包含 Dialog/AlertDialog/Sheet/Card/MultiSelect/Badge/Table 等全部所需组件
- **页面基础组件**: `page-kit.tsx` 提供 PageHeader / SearchBar / DataTable
- **Groups API 客户端**: `shared-api/src/tenant/groups.ts` 已有完整 CRUD + batchAdd/batchRemove（T0 已修复字段名）

### Institutional Learnings

- 无直接相关的 `docs/solutions/` 条目

## Key Technical Decisions

- **D1: group_id 过滤实现**: 在 `companies_page()` 的 FROM 子句中追加条件 JOIN `group_members gm ON gm.tenant_company_id = tc.id AND gm.group_id = :group_id`，而非在 WHERE 中子查询。JOIN 方式利用 `group_members(group_id, tenant_company_id)` 上的 UNIQUE 索引（see origin: design.md D1）
- **D2: 移除操作直接用 tc_id**: 后端 `batch-remove` 读取 `tenant_company_ids`，右侧表格 companies API 已返回 `tc_id`，无需额外字段（see origin: design.md D6）
- **D3: 已在群组禁选 — 前端方案**: 弹窗打开时额外请求群组内公司的 tc_id 集合（群组成员通常 < 200），前端 Set 判断禁选。不改后端（see origin: design.md D5 方案 A）
- **D4: 多选状态规则**: 翻页保留选中（Set<string>），重新筛选清空选中，禁选项不可被选中（see origin: design.md D9）
- **D5: CompanyDetail 抽取**: 移到 `components/company-detail.tsx`，`onGroupAdd` 改 optional，原位置 re-export（see origin: design.md D7）
- **D6: CompanyFilters 抽取范围**: FilterValues 类型 + 筛选 UI + buildParams + filters API 调用，接收 `onApply(filters)` 回调（see origin: design.md D8）

## Open Questions

### Resolved During Planning

- **Q1: batchRemoveMembers 字段名不一致** → T0 已修复，`{ member_ids }` → `{ tenant_company_ids }`
- **Q2: group_id JOIN vs WHERE 子查询** → JOIN 方式，利用现有 UNIQUE 索引
- **Q3: 群组成员计数是否需要单独 API** → 不需要，groups.list 已返回 `member_count`

### Deferred to Implementation

- **Q4: CompanyFilters 的 filters API 调用是否应该也带 group_id** → 实现时确认，当前设计中筛选选项来自全量公司而非群组内公司
- **Q5: 添加弹窗中群组成员列表的分页策略** → 群组成员通常 < 200，一次性取全部 tc_id 做 Set 判断；若后期群组规模增大再优化

## Output Structure

```
frontend/apps/tenant/src/
├── components/
│   ├── company-detail.tsx          # 从 companies/ 移出（共享）
│   └── company-filters.tsx         # 从 companies/page.tsx 提取（新文件）
└── app/(dashboard)/
    ├── companies/
    │   ├── page.tsx                # 修改：使用抽取后的共享组件
    │   └── company-detail.tsx      # 修改：改为 re-export
    └── curated-customers/
        ├── page.tsx                # 重写：左右分栏 + 群组管理
        └── add-company-modal.tsx   # 新文件：从公司列表添加弹窗
```

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
┌─ curated-customers/page.tsx ─────────────────────────────────────────┐
│                                                                       │
│  ┌─ Left Panel (240px) ──┐  ┌─ Right Panel (flex-1) ───────────────┐ │
│  │                        │  │                                       │ │
│  │  「新建群组」按钮       │  │  群组名 + 编辑/删除按钮 + 「添加」   │ │
│  │  ─────────────────     │  │  ─────────────────────────────────    │ │
│  │  群组 A  [✏️🗑️]       │  │  CompanyFilters (共享)                │ │
│  │  群组 B  [✏️🗑️]  ←──selected──→  companies API(group_id=B)      │ │
│  │  群组 C  [✏️🗑️]       │  │  ┌──────────────────────────────┐    │ │
│  │                        │  │  │ 公司表格 (同 companies 表头)  │    │ │
│  │  ─────────────────     │  │  │ 操作: 查看详情 | 移除        │    │ │
│  │  (无群组时空状态引导)   │  │  └──────────────────────────────┘    │ │
│  │                        │  │  分页                                 │ │
│  └────────────────────────┘  └───────────────────────────────────────┘ │
│                                                                       │
│  Sheet: CompanyDetail (共享)                                          │
│  Dialog: 新建/编辑群组弹窗                                            │
│  AlertDialog: 删除群组确认                                            │
│  Dialog: AddCompanyModal (add-company-modal.tsx)                      │
└───────────────────────────────────────────────────────────────────────┘
```

## Implementation Units

- [ ] **Unit 1: 后端 — companies API 加 group_id 支持**

**Goal:** `GET /companies` 支持按群组过滤公司

**Requirements:** R1

**Dependencies:** None

**Files:**
- Modify: `backend/app/services/tenant_query_service.py` — `companies_page()` 加 `group_id` 参数
- Modify: `backend/app/api/tenant/ops.py` — GET /companies 路由加 `group_id` Query 参数
- Test: `backend/tests/test_companies_group_filter.py`

**Approach:**
- `companies_page()` 签名加 `group_id: str | None = None`
- 当 `group_id` 存在时，在 FROM 子句的 `wc JOIN tc` 后追加 `JOIN group_members gm ON gm.tenant_company_id = tc.id AND gm.group_id = :group_id`，同时在 COUNT 查询中也追加相同 JOIN
- 路由层加 `group_id: str | None = Query(None, description="群组ID过滤")`，透传给 service

**Patterns to follow:**
- `tenant_query_service.py:136-388` 的动态 WHERE + params 字典模式
- `ops.py:40-119` 的 Query 参数定义和透传模式

**Test scenarios:**
- Happy path: 创建群组 → 添加 2 家公司 → `GET /companies?group_id=xxx` 只返回这 2 家
- Happy path: 不传 group_id 时行为不变，返回全量公司
- Edge case: group_id 指向空群组 → 返回空列表和 total=0
- Edge case: group_id 与分页参数组合 → 分页正确
- Edge case: group_id 与筛选参数组合（如 keyword）→ 在群组内进一步过滤
- Integration: group_id 过滤 + tenant_id 隔离 → 租户 A 的 group_id 不返回租户 B 的公司

**Verification:**
- 后端测试通过
- 手动调用 API 验证 group_id 过滤结果正确

---

- [ ] **Unit 2: 前端共享组件抽取 — CompanyDetail + CompanyFilters + API 类型**

**Goal:** 将 CompanyDetail 和 CompanyFilters 从 companies 页面抽取为共享组件，更新 API 客户端类型

**Requirements:** R5

**Dependencies:** None

**Files:**
- Create: `frontend/apps/tenant/src/components/company-detail.tsx` — 从 companies/ 移入
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/company-detail.tsx` — 改为 re-export
- Create: `frontend/apps/tenant/src/components/company-filters.tsx` — 从 companies/page.tsx 提取
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` — 导入共享组件替换内联代码
- Modify: `frontend/packages/shared-api/src/tenant/companies.ts` — `CompanyListFilters` 加 `group_id?: string`

**Approach:**
- CompanyDetail: 移动到 `components/company-detail.tsx`，Props 中 `onGroupAdd` 改为 optional（`onGroupAdd?: ...`），原位置改为 `export { default } from '@/components/company-detail'`
- CompanyFilters: 从 `companies/page.tsx` 提取 FilterValues 类型、EMPTY_FILTERS 常量、buildParams 函数、筛选 UI 渲染部分，封装为接收 `{ onApply, filtersOptions }` 的组件。COUNTRY_ZH / countryZh / dash 等辅助函数也移入或保留在页面
- companies/page.tsx 中筛选区域改为使用 `<CompanyFilters>` 组件
- `CompanyListFilters` 类型加 `group_id?: string` 字段

**Patterns to follow:**
- `companies/company-detail.tsx` 现有 Props 结构和 Sheet 集成模式
- `companies/page.tsx:44-97` FilterValues / buildParams 的现有实现

**Test scenarios:**
- Happy path: companies 页面功能完全不变 — 筛选、表格、详情 Drawer 行为与抽取前一致
- Integration: re-export 路径正确，companies 页面的 import 无需改变
- Edge case: CompanyDetail 不传 onGroupAdd 时，「加入群组」按钮不渲染

**Verification:**
- companies 页面启动无报错
- 筛选/表格/详情功能与抽取前行为一致
- TypeScript 编译通过

---

- [ ] **Unit 3: 优选客户页主页面 — 左侧群组面板 + 右侧公司表格**

**Goal:** 重写 curated-customers/page.tsx，实现左右分栏布局，左侧群组 CRUD 管理，右侧群组内公司列表 + 详情 + 移除

**Requirements:** R2, R3, R6

**Dependencies:** Unit 1, Unit 2

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx` — 全面重写

**Approach:**
- 左侧面板固定宽度，群组列表用 `useQuery(['groups'])` + `tenantApi.groups.list()`
- `selectedGroupId` 状态管理当前选中群组，点击切换
- 新建群组: Dialog 弹窗输入 name + description → `groups.create()` → invalidate → 自动选中新群组
- 编辑群组: Dialog 弹窗编辑 name + description → `groups.update()` → invalidate
- 删除群组: AlertDialog 二次确认 → `groups.delete()` → invalidate → 选中第一个剩余群组
- 群组列表项 hover 时显示编辑/删除图标
- 右侧面板: `useQuery(['companies', { group_id, ...filters }])` 加载群组内公司
- 表头字段与公司列表对齐（13 列）
- 分页: 页码模式，复用 companies 页面的分页 UI 模式
- 查看详情: Sheet + CompanyDetail（onGroupAdd 不传）
- 移除: AlertDialog 确认 → `groups.batchRemoveMembers(groupId, [tcId])` → invalidate
- 右侧标题区: 群组名 + 编辑/删除按钮 + 「添加公司」按钮
- 无群组时右侧显示空状态引导
- 使用 CompanyFilters 共享组件

**Patterns to follow:**
- `companies/page.tsx` 的整体架构: 状态管理 + useQuery + 表格 + 分页 + Sheet Drawer
- `companies/page.tsx:374-397` 的 Sheet/CompanyDetail 集成模式
- `@shared/ui` 的 Dialog / AlertDialog / Sheet / Card 组件

**Test scenarios:**
- Happy path: 页面加载 → 群组列表正确显示 → 点击群组 → 右侧加载该群组公司
- Happy path: 新建群组 → 列表刷新 → 自动选中新群组
- Happy path: 编辑群组名 → 列表和标题区同步更新
- Happy path: 删除群组 → 确认弹窗 → 列表刷新 → 选中下一个群组
- Happy path: 点击公司行"查看详情" → Sheet Drawer 打开 → 展示完整信息
- Happy path: 点击"移除" → 确认弹窗 → 移除成功 → 列表刷新
- Edge case: 无群组时 → 显示空状态引导文案 + 创建按钮
- Edge case: 群组内无公司时 → 右侧显示空状态 + "添加公司"入口
- Edge case: 删除最后一个群组 → 回到空状态引导

**Verification:**
- 页面渲染无报错
- 群组 CRUD 全流程可用
- 公司列表展示、分页、详情 Drawer 正常
- 移除操作正确刷新数据

---

- [ ] **Unit 4: 从公司列表添加弹窗**

**Goal:** 实现「从公司列表添加」弹窗，支持筛选、多选、已在群组禁选、批量添加

**Requirements:** R4

**Dependencies:** Unit 2, Unit 3

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`
- Modify: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx` — 集成弹窗

**Approach:**
- Dialog 弹窗，Props: `{ groupId, open, onClose }`
- 内部使用 CompanyFilters 共享组件做筛选
- 公司列表: `useQuery` 调 `companies.list({ ...filters })`（不带 group_id，查全部）
- 已在群组标记: 额外 `useQuery` 获取群组内公司 tc_id 集合，用 `Set<string>` 存储
- 匹配的行 checkbox 禁选 + 灰色样式 + "已添加"文字标记
- 多选状态: `selectedTcIds: Set<string>`，翻页保留，重新筛选清空
- 底部操作栏: 已选 N 家 + 「添加到群组」按钮
- 添加: `groups.batchAddMembers(groupId, [...selectedTcIds])` → invalidate → onClose

**Patterns to follow:**
- `companies/page.tsx` 的 Checkbox 多选 + selectedIds 管理模式
- `companies/page.tsx` 的表格列定义和分页实现
- CompanyFilters 共享组件的 onApply 回调模式

**Test scenarios:**
- Happy path: 打开弹窗 → 显示全量公司列表 → 勾选 → 点击添加 → 成功 → 弹窗关闭 → 右侧列表刷新
- Happy path: 使用筛选条件缩小范围 → 勾选 → 添加
- Happy path: 翻页后勾选 → 回到第 1 页 → 之前的勾选仍在
- Edge case: 已在群组的公司行灰色 + checkbox 禁用 + "已添加"标记
- Edge case: 重新点击「查询」→ 已选项清空
- Edge case: 全选当前页时跳过已在群组的公司
- Error path: batchAddMembers 失败 → toast 错误提示 → 弹窗不关闭

**Verification:**
- 弹窗打开/关闭正常
- 筛选功能与公司列表页一致
- 禁选标记正确显示
- 批量添加后数据正确刷新

---

- [ ] **Unit 5: 后端集成测试**

**Goal:** 为 `companies_page(group_id=...)` 路径编写 pytest 集成测试

**Requirements:** R1

**Dependencies:** Unit 1

**Files:**
- Create: `backend/tests/test_companies_group_filter.py`

**Approach:**
- 使用现有测试模式: `create_app()` + `lifespan_context` + `AsyncClient`
- 认证链: admin 登录 → 创建租户 → 租户用户登录
- 测试流程: 创建群组 → 添加公司到群组 → GET /companies?group_id=xxx 验证过滤结果
- 验证 group_id + 筛选参数组合
- 验证空群组返回空列表

**Patterns to follow:**
- `backend/tests/test_tenant_settings_api.py` 的测试初始化和认证模式
- `backend/tests/` 中其他 API 测试的断言风格

**Test scenarios:**
- Happy path: group_id 过滤返回正确的公司子集
- Happy path: 不传 group_id 返回全量（回归）
- Edge case: 空群组 → items=[], total=0
- Edge case: group_id + keyword 组合过滤
- Integration: 不同租户的 group_id 隔离验证

**Verification:**
- `pytest backend/tests/test_companies_group_filter.py` 全部通过

---

- [ ] **Unit 6: 端到端验证**

**Goal:** 手动验证完整流程

**Requirements:** R1-R6

**Dependencies:** Unit 1-5

**Files:** None（手动测试）

**Test expectation: none — 手动验证，无自动化测试代码**

**Approach:**
- 完整流程: 新建群组 → 添加公司（通过弹窗）→ 查看详情 Drawer → 移除公司 → 编辑群组 → 删除群组
- 验证空状态引导
- 验证分页行为
- 验证筛选行为
- 检查 TypeScript 编译无错误
- 检查控制台无运行时错误

**Verification:**
- 上述全流程无报错
- TypeScript 编译通过
- 浏览器控制台无错误

## System-Wide Impact

- **Interaction graph:** `groups.batchRemoveMembers` 触发后端 `business_status` 状态回退（'in_group' → 'new'，如果不在任何其他群组）；`groups.batchAddMembers` 触发 `business_status` 更新为 'in_group'。invalidateQueries 覆盖 `['companies']` 和 `['groups']` 两个 query key
- **Error propagation:** 后端 group_id JOIN 不匹配时返回空结果而非报错；前端 mutation 失败通过 toast 提示
- **State lifecycle risks:** 多选状态（selectedTcIds）在重新筛选时清空，避免不一致；翻页保留选中通过 Set 独立管理，不依赖渲染状态
- **API surface parity:** GET /companies 新增 group_id 参数为可选，不影响现有调用方
- **Integration coverage:** 后端集成测试覆盖 group_id 过滤 + 租户隔离
- **Unchanged invariants:** groups CRUD API 不变；group_members 表结构不变；公司列表页（/companies）行为不变

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| CompanyFilters 抽取后 companies 页面回归 | Unit 2 完成后立即验证 companies 页面功能不变 |
| 群组成员量大时禁选判断性能 | 群组成员通常 < 200，一次性取 tc_id 做 Set 判断；后期可改后端标记 |
| 动态 SQL JOIN 条件影响查询性能 | group_members 表有 UNIQUE(group_id, tenant_company_id) 索引 |
| companies_page 的 COUNT 查询需要同步加 JOIN | Unit 1 中明确包含 COUNT 查询的 JOIN 同步 |

## Sources & References

- **Origin document:** [proposal.md](openspec/changes/2026-05-19-curated-customers-page/proposal.md)
- **Design document:** [design.md](openspec/changes/2026-05-19-curated-customers-page/design.md)
- **Tasks document:** [tasks.md](openspec/changes/2026-05-19-curated-customers-page/tasks.md)
- Related code: `backend/app/services/tenant_query_service.py` companies_page()
- Related code: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`
- Related code: `frontend/packages/shared-api/src/tenant/groups.ts`
- Mock design: `docs/mock/tenant-curated-customers.html`
