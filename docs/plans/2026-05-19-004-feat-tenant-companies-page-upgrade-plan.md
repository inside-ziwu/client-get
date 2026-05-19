---
title: "feat: Tenant 公司列表页全面升级（筛选/表格/详情/操作）"
type: feat
status: active
date: 2026-05-19
origin: openspec/changes/tenant-companies-page-upgrade/
depth: standard
---

# feat: Tenant 公司列表页全面升级（筛选/表格/详情/操作）

## Overview

将 tenant 端公司列表页从 MVP 状态（68 行，仅关键词搜索 + 国家筛选 + 基础表格）升级为完整功能页面：9 项筛选控件、多选批量操作、页码分页、660px 详情 Drawer（含 AI 评估/贸易数据/编辑模式）、加入群组 Modal、拉黑 Modal。后端 API 需补齐 wmt 字段、扁平化详情响应、扩展 filters 和 PATCH 端点。

## Problem Frame

迁移 `20260519_0045` 已将数据源切到 `waimaotong_clean_companies`，但 UI 和 API 响应格式未跟进。wmt 表中丰富的 AI 评估（score_details、company_type_analysis 等）和贸易数据（trade_summary、trade_amount_3y_usd 等）无法呈现给租户用户。前端缺少分页、多选、详情编辑、群组操作和拉黑功能。(see origin: openspec/changes/tenant-companies-page-upgrade/proposal.md)

## Requirements Trace

- R1. 列表 API 补齐 wmt 字段（sub_industry、phone、trade_amount_3y_usd、trade_count、description、data_source_tags、company_size）并返回 `tc_id`
- R2. 详情 API 扁平化响应，补齐 AI 评估字段和 score_adjustment
- R3. filters API 新增 sub_industries、product_tags、grades 选项
- R4. 路由新增 grade 筛选参数
- R5. PATCH API 支持 score_adjustment（-20~+20）
- R6. 前端共享类型对齐后端响应，操作 API 统一使用 tc_id
- R7. 筛选面板：9 项控件（搜索词、国家、细分行业、关键词、评级、进口额/次数/联系人/成立年范围）
- R8. 表格：多选 checkbox + 批量操作栏 + 页码分页
- R9. 详情 Drawer：660px，基本信息/AI 评估/贸易数据/标签/备注/联系人，含编辑模式
- R10. 群组 Modal：单条 + 批量加入，radio 选群组
- R11. 拉黑 Modal：确认弹窗 + 危险样式

## Scope Boundaries

- 不新增"精准客户/普通"状态概念
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件
- 不新增 API 路由（复用现有路由，仅扩展响应和参数）
- 不新增数据库迁移（`score_adjustment` 列已由 migration 20260507_0025 创建）

## Context & Research

### Relevant Code and Patterns

**Backend:**
- `backend/app/services/tenant_query_service.py` — `companies_page()` (22 cols, cursor 分页)、`v3_company_detail()` (20 cols, `tenant_state` 嵌套)
- `backend/app/services/tenant_ops_service.py` — `companies_filters()` (3 options)、`update_prospect()` (note/tags/business_status)
- `backend/app/api/tenant/ops.py` — 26 个 query params，无 grade
- `backend/app/services/admin_collection_service.py:2498-2534` — wmt 列表查询参考；`:2542-2544` — 详情用 `SELECT *` 获取全部 AI 字段
- `backend/alembic/versions/20260507_0025_tenant_companies_private_fields.py` — score_adjustment 已建（int, CHECK -20~+20, 含索引）

**Frontend:**
- `frontend/packages/shared-api/src/tenant/companies.ts` — Company (32 字段含 4 个幽灵字段)、CompanyListFilters (cursor/limit 分页)
- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` — 68 行 MVP
- `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx` — 570 行参考（filters+appliedFilters 模式、page 分页、score_details 进度条）
- `frontend/apps/tenant/src/components/pages/page-kit.tsx` — DataTable 无 checkbox 支持
- `frontend/packages/shared-ui/` — shadcn/ui 组件库：Badge, Button, Input, Checkbox, Sheet, Dialog, AlertDialog, Table, Progress, MultiSelect, RatingTag 等

**Mock:**
- `docs/mock/tenant-companies.html` — Tailwind CSS，两行筛选（5 select + 4 range），9 列表格，660px Drawer

### Institutional Learnings

- `docs/solutions/best-practices/admin-waimaotong-fullstack-display-rewrite-2026-05-19.md` — wmt 列补齐用 `ADD COLUMN IF NOT EXISTS`；分页 ORDER BY 需唯一键；text[] 陷阱需采样验证
- `docs/solutions/database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md` — FK 迁移注意 CASCADE 类型漂移

## Key Technical Decisions

| 决策 | 理由 | 来源 |
|------|------|------|
| D1: 详情 API 扁平化 | 减少前端解构层级，与列表风格一致 | eng-review |
| D2: filters 拆为 4 条独立查询 | 避免单条复杂查询维护和性能风险 | eng-review |
| D3: 删除 Company 幽灵字段 | score_adjusted_at/by/reason、is_precise_customer 后端不返回 | eng-review |
| D4: CompanyListFilters 改 page-based | cursor→page/page_size，与 admin 对齐 | eng-review |
| D7: 列表返回双 ID（id + tc_id） | 列表返回 wc.id，操作 API 需 tc.id，否则全部操作 404 | eng-review 致命 |
| D9: 后端加 grade query param | 前端筛选有评级，路由无此参数会静默失效 | eng-review |

## Open Questions

### Resolved During Planning

- score_adjustment 迁移是否需要：**不需要**，migration 20260507_0025 已创建
- wmt 表 AI 评估字段哪些可用：admin 详情用 `SELECT *` 返回全部，含 score_details/company_type_analysis/email_priority/sales_approach/match_reasons/potential_needs/recommended_products/risk_factors/main_business/trade_summary
- DataTable 是否支持多选：**不支持**，需在 page.tsx 中用原生 `<table>` + Checkbox 组件自行实现（参考 admin client-page.tsx 模式）

### Deferred to Implementation

- wmt 表 `score_details` 的 JSON 结构：需查数据确认字段名（dimension/score/max_possible），影响前端进度条渲染
- `data_source_tags` text[] 实际值域：影响来源标签颜色映射
- Detail API `SELECT *` vs 显式列名：实施时根据 admin 参考模式决定

## High-Level Technical Design

> *以下说明仅为方向性指引，不是实施规范。实施时应以此为上下文，而非照搬。*

```
依赖关系图：

  IU-1 列表 API + tc_id ──┐
                           │
  IU-2 详情 API 扁平化 ────┤
                           ├──▶ IU-4 前端类型 ──┬──▶ IU-5 筛选+表格+分页
  IU-3 Filters + PATCH ───┘                    │
                                               ├──▶ IU-6 详情 Drawer
                                               │
                                               └──▶ IU-7 群组+拉黑 Modal
                                                         │
                                                         ▼
                                                    IU-8 集成验证
```

前端 page.tsx 结构（参考 admin client-page.tsx 模式）：

```
page.tsx (~400-500 行)
├── filters 状态 + appliedFilters 状态
├── useQuery: list(appliedFilters) + filters()
├── 筛选面板（行 1: 5 select，行 2: 4 range，行 3: 查询/重置）
├── 批量操作栏（选中时显示）
├── 原生 <table> + Checkbox 多选
├── 分页组件
├── <CompanyDetail> Drawer (sheet)
├── <GroupModal> Dialog
└── <BlacklistModal> AlertDialog

company-detail.tsx (~300 行)
├── 基本信息 grid
├── AI 评估区域（score_details 进度条）
├── 贸易数据区域
├── 标签（只读/编辑）
├── 备注（只读/编辑）
├── 评分调整（只读/编辑）
└── 联系人表

group-modal.tsx (~80 行)
blacklist-modal.tsx (~50 行)
```

## Implementation Units

### - [ ] IU-1: 后端 — 列表 API 字段补充 + 双 ID + grade 筛选

**Goal:** 列表 API 返回 `tc_id` 和缺失的 wmt 字段，支持 grade 筛选参数

**Requirements:** R1, R4

**Dependencies:** None

**Files:**
- Modify: `backend/app/services/tenant_query_service.py`
- Modify: `backend/app/api/tenant/ops.py`

**Approach:**
- `companies_page()` SELECT 新增 `tc.id AS tc_id`（D7），新增 `wc.phone`、`wc.trade_amount_3y_usd`、`wc.trade_count`、`wc.description`、`wc.data_source_tags`、`wc.company_size`
- 返回字典新增对应 key，`tc_id` 转 str
- `ops.py` 路由新增 `grade: Optional[str] = Query(None)` 参数
- `companies_page()` WHERE 加入 `wc.grade = :grade`（当 grade 非空时）

**Patterns to follow:**
- 同方法内已有的列映射模式（如 `wc.company_name AS name`）
- 路由层现有 query param 模式（如 `country_iso3`）

**Test scenarios:**
- Happy path: 列表响应包含 `tc_id` 字段且值为 tenant_companies.id
- Happy path: 列表响应包含 phone、trade_amount_3y_usd 等新字段
- Happy path: `grade=A` 筛选只返回 A 级公司
- Edge case: grade 参数为空时不过滤
- Edge case: 新字段为 NULL 时返回 null（不崩溃）

**Verification:**
- `curl` 列表 API，响应含 `tc_id` 且与 `id` 不同
- `curl` 带 `grade=A` 参数，结果全部为 A 级

---

### - [ ] IU-2: 后端 — 详情 API 扁平化 + AI 评估字段

**Goal:** 详情响应扁平化（移除 tenant_state 嵌套），补齐 AI 评估和贸易字段

**Requirements:** R2

**Dependencies:** None

**Files:**
- Modify: `backend/app/services/tenant_query_service.py`

**Approach:**
- `v3_company_detail()` 返回字典中，将 `tenant_state` 内的 `note`、`tags`、`score`、`business_status`、`data_status`、`model_score` 提升到根级别（D1）
- SELECT 补充 AI 字段：`wc.score_details`、`wc.company_type_analysis`、`wc.email_priority`、`wc.sales_approach`、`wc.match_reasons`、`wc.potential_needs`、`wc.recommended_products`、`wc.risk_factors`、`wc.main_business`、`wc.trade_summary`、`wc.phone`、`wc.company_size`
- 新增 `tc.score_adjustment` 到 SELECT 和返回字典
- JSON 类型字段（score_details 等）直接透传，无需 Python 层解析

**Patterns to follow:**
- Admin `get_wmt_clean_company()` 用 `SELECT *` 获取全部字段（admin_collection_service.py:2544）
- 列表 API 的 dict 构建模式

**Test scenarios:**
- Happy path: 详情响应中 note/tags/score 在根级别，无 tenant_state 嵌套
- Happy path: 响应包含 score_details（JSON 数组）、company_type_analysis（字符串）等 AI 字段
- Happy path: 响应包含 score_adjustment（整数）
- Edge case: AI 字段全部为 NULL 时返回 null
- Edge case: score_details 为空数组时返回 []
- Integration: 前端 Drawer 消费扁平化响应无需额外解构

**Verification:**
- `curl` 详情 API，响应无 `tenant_state` key
- `curl` 详情 API，响应包含 `score_details`、`score_adjustment` 等字段

---

### - [ ] IU-3: 后端 — Filters 扩展 + PATCH score_adjustment

**Goal:** filters 返回 5 类选项；PATCH 支持 score_adjustment 更新

**Requirements:** R3, R5

**Dependencies:** None

**Files:**
- Modify: `backend/app/services/tenant_ops_service.py`

**Approach:**

**Filters (D2):**
- 拆为 4 条独立查询（原 1 条 + 新增 3 条）：
  1. 原查询保留 countries、business_statuses、data_statuses
  2. `SELECT DISTINCT wc.sub_industry FROM waimaotong_clean_companies wc JOIN tenant_companies tc ... WHERE sub_industry IS NOT NULL`
  3. `SELECT DISTINCT unnest(wc.product_tags) FROM ... WHERE product_tags IS NOT NULL`
  4. `SELECT DISTINCT wc.grade FROM ... WHERE grade IS NOT NULL`
- 返回字典新增 `sub_industries`、`product_tags`、`grades` key

**PATCH:**
- `update_prospect()` 新增 `score_adjustment` 字段处理
- 校验范围 -20 ~ +20，超范围返回 422（HTTPException）
- UPDATE SQL 加入 `score_adjustment = COALESCE(:score_adjustment, score_adjustment)`

**Patterns to follow:**
- 原 `companies_filters()` 的 array_agg(DISTINCT) 模式
- `update_prospect()` 现有的 COALESCE 更新模式

**Test scenarios:**
- Happy path: filters 响应包含 sub_industries、product_tags、grades 数组
- Happy path: PATCH score_adjustment=10 成功更新
- Edge case: filters 各选项去重且排除 NULL
- Edge case: 无数据时 filters 返回空数组
- Error path: PATCH score_adjustment=25 返回 422
- Error path: PATCH score_adjustment=-25 返回 422
- Happy path: PATCH score_adjustment=-20 和 +20 边界值成功

**Verification:**
- `curl` filters API 包含 5 类选项
- `curl` PATCH 含 score_adjustment，数据库值正确更新
- `curl` PATCH 超范围值，返回 422

---

### - [ ] IU-4: 前端 — 共享类型更新

**Goal:** Company 和 CompanyListFilters 类型与后端响应对齐

**Requirements:** R6

**Dependencies:** IU-1, IU-2, IU-3

**Files:**
- Modify: `frontend/packages/shared-api/src/tenant/companies.ts`

**Approach:**

**Company 接口 (D3):**
- 删除幽灵字段：`score_adjusted_at`、`score_adjusted_by`、`score_adjust_reason`、`is_precise_customer`
- 新增字段：`tc_id`（string）、`sub_industry`、`phone`、`trade_amount_3y_usd`（number|null）、`trade_count`（number|null）、`description`、`data_source_tags`（string[]）、`company_size`
- 详情扩展字段（可选，用于详情 API 响应）：`score_details`、`company_type_analysis`、`email_priority`、`sales_approach`、`match_reasons`、`potential_needs`、`recommended_products`、`risk_factors`、`main_business`、`trade_summary`、`score_adjustment`
- 修正字段名：`country` → `country_iso3`、`total_score` → `score`、`notes` → `note`、`industry` → `industry_desc`

**CompanyListFilters (D4):**
- 删除 `cursor`、`limit`
- 新增 `page`、`page_size`、`grade`
- 确认 `trade_amount_min/max`、`trade_count_min/max`、`contact_count_min/max`、`founded_year_from/to` 存在

**companiesApi:**
- 确认 `detail(id)`、`contacts(id)`、`blacklist(id, reason)` 方法签名无需改动（ID 语义由前端传入决定）

**Patterns to follow:**
- 现有 Company 接口的可选字段标注模式（`field?: type`）
- admin 端类型定义风格

**Test scenarios:**
- Happy path: `pnpm build` 编译通过，无类型错误
- Integration: 前端代码中使用 `company.tc_id` 调用操作 API

**Verification:**
- `pnpm build` 全量构建无报错

---

### - [ ] IU-5: 前端 — 筛选面板 + 表格 + 多选 + 分页

**Goal:** 完整的筛选面板、带 checkbox 的数据表格、页码分页、批量操作栏

**Requirements:** R7, R8

**Dependencies:** IU-4

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**Approach:**

**筛选面板:**
- 采用 admin client-page.tsx 的 `filters` + `appliedFilters` 双状态模式
- 行 1：搜索框 + 国家 MultiSelect + 细分行业 Select + 关键词 MultiSelect + 评级 Select
- 行 2：进口额范围（两个 Input[type=number]）+ 进口次数范围 + 联系人范围 + 成立年范围
- 行 3：查询按钮（提交 filters → appliedFilters，重置 page=1）+ 重置按钮（清空所有筛选）
- 下拉选项从 `GET /companies/filters` 动态加载（useQuery）

**表格:**
- 不复用 page-kit DataTable（不支持 checkbox），用原生 `<table>` + shadcn Table 组件
- 列：Checkbox | 公司名+域名 | 国家 | 细分行业 | 关键词 tags | 评级 RatingTag | 总分 | 操作（详情/加入群组/拉黑）
- 多选逻辑：selectedIds 状态，行选/全选/半选（Checkbox indeterminate）
- 拉黑按钮用 destructive variant（红色样式）

**批量操作栏:**
- 选中时浮出：`已选 N 家公司` + 加入群组按钮 + 取消选择

**分页:**
- page + page_size 参数（与 appliedFilters 合并传给列表 API）
- 显示：总条数 + 每页条数 Select（20/50/100）+ 上一页/下一页 + 页码展示
- 翻页时保持筛选条件，切筛选时重置到第 1 页

**Patterns to follow:**
- `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx` — filters 模式、分页模式、表格布局
- `docs/mock/tenant-companies.html` — UI 布局和控件排列

**Test scenarios:**
- Happy path: 筛选面板展示 9 项控件，下拉选项从 API 加载
- Happy path: 点击查询，列表刷新且回到第 1 页
- Happy path: 点击重置，所有筛选清空
- Happy path: 勾选行 → 批量操作栏出现 → 显示正确数量
- Happy path: 全选 → 半选 → 取消选择交互正常
- Happy path: 翻页后筛选条件保持
- Edge case: 无数据时显示空状态
- Edge case: 筛选参数正确传递到 API（检查 network 请求）

**Verification:**
- 浏览器中筛选面板展示完整
- 多选 checkbox 行为正确（行选、全选、半选）
- 分页翻页正常，筛选条件不丢失

---

### - [ ] IU-6: 前端 — 详情 Drawer

**Goal:** 660px 详情 Drawer，含基本信息/AI 评估/贸易数据/编辑模式/联系人表

**Requirements:** R9

**Dependencies:** IU-4

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/companies/company-detail.tsx`
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**Approach:**

**Drawer 容器:**
- 使用 shadcn Sheet 组件，设 `style={{ width: 660 }}`（或 className）
- 标题为公司名，按钮区：加入群组 + 编辑/保存/取消 + 关闭

**基本信息区域（2 列 grid）:**
- 左列：网站、国家、细分行业、成立年、关键词 tags
- 右列：评级 RatingTag、总分（wmt_score）、评分调整（只读数值/编辑 number input）、进口额（格式化 USD）、进口次数

**AI 评估区域（当 grade 或 score 存在时展示）:**
- score_details 进度条：每个维度一行（dimension 名 + score/max_possible 进度条）
- 参考 admin client-page.tsx 的 `h-2 rounded-full bg-muted` + `bg-primary` 进度条模式
- 其他字段：company_type_analysis、email_priority、sales_approach、product_tags、match_reasons、potential_needs、recommended_products、risk_factors

**贸易数据区域（当 has_trade_data 或 trade_summary 存在时展示）:**
- trade_amount_3y_usd、trade_count、trade_summary

**编辑模式 (D6 读写切换):**
- 默认只读，点击"编辑"进入编辑态
- 可编辑字段：标签（输入+回车添加，× 删除）、备注（textarea）、评分调整（number input, min=-20 max=+20）
- 保存调 `PATCH /prospects/{tc_id}`（使用 tc_id），成功后退出编辑态并 invalidate query
- 取消丢弃修改，恢复只读

**联系人表:**
- useQuery 调用 `GET /companies/{id}/contacts`
- 列：姓名、职位、部门、邮箱、邮箱状态、电话
- 无联系人时显示"暂无联系人数据"

**Patterns to follow:**
- Admin client-page.tsx 的 Sheet 详情结构和 score_details 渲染
- 现有 RatingTag 组件

**Test scenarios:**
- Happy path: 点击详情按钮 → 660px Drawer 打开，各区域正确渲染
- Happy path: 编辑 → 修改备注和评分调整 → 保存 → API 调用成功 → 退出编辑态
- Happy path: 联系人表正确加载和渲染
- Edge case: AI 字段全部 NULL → AI 评估区域不展示
- Edge case: 无联系人 → 显示空状态提示
- Edge case: score_adjustment input 限制 -20~+20 范围
- Edge case: 取消编辑 → 修改丢弃，恢复原值
- Integration: 保存使用 `tc_id` 调用 PATCH，非 `id`

**Verification:**
- 浏览器中 Drawer 打开/关闭正常
- 各区域正确渲染（包括进度条）
- 编辑保存后数据刷新

---

### - [ ] IU-7: 前端 — 群组 Modal + 拉黑 Modal

**Goal:** 群组选择 Modal（单条+批量）和拉黑确认 Modal

**Requirements:** R10, R11

**Dependencies:** IU-4

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/companies/group-modal.tsx`
- Create: `frontend/apps/tenant/src/app/(dashboard)/companies/blacklist-modal.tsx`
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**Approach:**

**GroupModal:**
- 使用 shadcn Dialog 组件
- useQuery 加载 `GET /groups` 群组列表
- radio 单选，每项显示群组名 + 成员数
- 标题区分：单条 "将 {公司名} 加入群组" / 批量 "将选中的 N 家公司批量加入群组"
- 确认调用 `POST /groups/{groupId}/members/batch-add`，body: `{ tenant_company_ids: [tc_id, ...] }`
- 成功后关闭 Modal、invalidate 列表 query、清除选中状态
- 空群组时显示"暂无群组，请先创建群组"

**BlacklistModal:**
- 使用 shadcn AlertDialog 组件（适合确认操作）
- 提示文案："将「{公司名}」加入黑名单后，不会再向其发送邮件，且不会出现在发送计划目标中。"
- 确认调用 `POST /companies/{tc_id}/blacklist`，body: `{ reason: "manual blacklist" }`
- 成功后关闭、invalidate 列表（公司从列表消失）
- 确认按钮用 destructive variant

**Patterns to follow:**
- `frontend/packages/shared-api/src/tenant/companies.ts` — `companiesApi.blacklist(id, reason)` 已有方法
- `groupsApi.batchAddMembers()` 已有方法
- shadcn AlertDialog 的 confirm/cancel 模式

**Test scenarios:**
- Happy path: 单条加入群组 → 选群组 → 确认 → 成功关闭
- Happy path: 批量加入群组 → 选群组 → 确认 → 成功 → 清除选中
- Happy path: 拉黑确认 → 公司从列表消失
- Edge case: 无群组时显示提示
- Edge case: 取消操作 → Modal 关闭，无请求
- Edge case: 从详情 Drawer 加入群组 → Modal 打开，成功后 Drawer 保持
- Error path: 批量加入失败 → toast 错误提示，不清除选中

**Verification:**
- 浏览器中单条/批量加入群组正常
- 拉黑确认后公司从列表消失
- 错误场景显示 toast

---

### - [ ] IU-8: 集成验证

**Goal:** 全链路功能验收和边界验收

**Requirements:** R1-R11

**Dependencies:** IU-1 ~ IU-7

**Files:**
- None (no code changes)

**Approach:**
- `pnpm build` 全量构建无报错
- 端到端流程验收：筛选 → 列表 → 多选 → 加入群组 → 详情查看 → 编辑保存 → 拉黑 → 分页翻页
- 空数据边界验收：无公司、无联系人、无群组、字段全 NULL 时 UI 不崩溃
- 关键路径：筛选 → 翻页 → 保持筛选条件
- 关键路径：详情查看 → 编辑保存 → 数据刷新
- 关键路径：多选 → 批量加入群组 → 清除选中 → 列表刷新

**Test scenarios:**
- Test expectation: none — 手动端到端验证

**Verification:**
- TypeScript 编译通过
- 所有关键路径在浏览器中正常工作
- 边界场景不崩溃

## System-Wide Impact

- **Interaction graph:** page.tsx → companiesApi (list/filters/detail/contacts/blacklist) → backend services → wmt tables + tenant_companies。GroupModal → groupsApi.batchAddMembers → backend group service
- **Error propagation:** API 错误通过 React Query onError → toast 提示用户；PATCH 422 在前端应展示校验错误
- **State lifecycle risks:** 多选状态在翻页时应清空（避免跨页选中的混淆）；编辑态在 Drawer 关闭时应丢弃未保存修改
- **API surface parity:** 详情扁平化仅影响 tenant 前端（admin 端独立 API），无跨端影响
- **Integration coverage:** tc_id 必须在所有操作调用中统一使用（blacklist、group batch-add、PATCH prospect），代码审查重点
- **Unchanged invariants:** admin 端 API 和页面不受影响；`GET /companies` 路由现有参数保持兼容；cursor 分页仍可用（page-based 是新增路径）

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| tc_id 混用导致操作 404 | 前端所有操作 API 调用统一使用 `company.tc_id`，代码审查重点关注 |
| 扁平化详情响应影响其他消费方 | 确认仅 tenant 前端消费此 API，无其他调用方 |
| filters DISTINCT 查询在大租户下变慢 | 租户级数据量有限（< 10k），可接受；若未来瓶颈可加缓存 |
| score_details JSON 结构不确定 | 实施时采样查数据确认字段名，影响进度条渲染 |
| DataTable 不支持 checkbox | 不复用 page-kit DataTable，用原生 table + Checkbox 组件 |

## Sources & References

- **Origin document:** [openspec/changes/tenant-companies-page-upgrade/](openspec/changes/tenant-companies-page-upgrade/)
  - [proposal.md](openspec/changes/tenant-companies-page-upgrade/proposal.md) — 变更范围和能力定义
  - [design.md](openspec/changes/tenant-companies-page-upgrade/design.md) — 7 个设计决策 (D1-D7)
  - [tasks.md](openspec/changes/tenant-companies-page-upgrade/tasks.md) — 12 组任务 + GSTACK REVIEW REPORT (D1-D9)
  - [specs/](openspec/changes/tenant-companies-page-upgrade/specs/) — 详情/群组/拉黑 spec
- **Engineering Review:** plan-eng-review (2026-05-19)，9 项决策全部确认，含 Outside Voice 交叉验证
- **Mock design:** `docs/mock/tenant-companies.html`
- **Admin reference:** `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`
- **Institutional learnings:** `docs/solutions/best-practices/admin-waimaotong-fullstack-display-rewrite-2026-05-19.md`
