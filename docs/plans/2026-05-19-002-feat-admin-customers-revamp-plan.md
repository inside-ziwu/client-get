---
title: "feat: 改造 admin 客户数据页面，数据源切换到 waimaotong_clean_companies"
type: feat
status: active
date: 2026-05-19
origin: openspec/changes/admin-customers-revamp/
---

# feat: 改造 admin 客户数据页面，数据源切换到 waimaotong_clean_companies

## Overview

将 admin 端 `/collection/customers` 页面从 `clean_companies` 表切换到 `waimaotong_clean_companies`（940 行，70+ 列含 AI 字段预留）+ `waimaotong_clean_contacts`（6335 行）。删除健康卡片，扩展筛选区至 7 维，表格扩展至 13 列，详情 Sheet 重写为 5 分组（基本信息 / AI 评估 / 贸易数据 / 联系人 / 数据来源）。

旧 API `GET /collection/clean-companies` 保留不动。

## Problem Frame

当前 `/collection/customers` 页面仅展示 `clean_companies` 的 7 列基础字段和 4 字段简陋详情。线上已存在更丰富的 `waimaotong_clean_companies` 表（含 AI 分析字段预留）和关联的 `waimaotong_clean_contacts`，但 admin 后端没有查询这两张表的 API。需要将页面数据源切换过去，并复刻外部仓库 sysdev-ft-marketing 的交互模式。(see origin: openspec/changes/admin-customers-revamp/proposal.md)

## Requirements Trace

- R1. 后端提供 3 个新 API 端点查询 waimaotong_clean_companies / waimaotong_clean_contacts
- R2. 列表 API 支持 q/country/industry/size/year_min/year_max/has_contacts/grade 8 维筛选 + 分页 + 排序
- R3. 详情 API 返回全量字段（含 JSONB AI 字段）
- R4. 联系人 API 通过 sys_company_id subquery 关联
- R5. 前端删除健康卡片，数据源切换到新 API
- R6. 前端筛选区 7 维（公司名/域名、国家、行业、员工规模、成立年份范围、有联系人）
- R7. 前端表格 13 列，AI 字段 null 显示 `-`，评级 Badge 颜色编码
- R8. 前端详情 Sheet 5 分组，AI 评估/贸易数据分组条件显示
- R9. 前端分页控件：总条数、上一页/下一页、页码、每页条数选择（20/50/100）
- R10. 旧 API 和 clean_companies 相关代码保留不动

## Scope Boundaries

- 不删除 clean_companies / clean_contacts 表及其 API
- 不新增 Alembic 迁移（表已存在于线上）
- 不运行 AI Flow（AI 字段当前全空，页面预留展示位）
- 不改动侧边栏路由结构
- 不修改 tenant 端的公司展示逻辑
- 不处理 admin-waimaotong-display change（外贸通原始数据页面，独立 change）

## Context & Research

### Relevant Code and Patterns

**后端模式参照：**
- `backend/app/services/admin_collection_service.py` — 2428 行的服务类，所有 admin collection 查询方法集中于此
  - `list_clean_companies()` (line 988)：当前 customers 页面数据源，WHERE 构建 + COUNT + SELECT 分页模式
  - `list_v3_raw_companies()` (line 1110)：waimaotong 分支 (line 1210-1246) 的 employee_size 文本提取和筛选逻辑
  - `list_v3_raw_company_contacts()` (line 941)：waimaotong 联系人查询模式
  - `get_lixiaoyun_clean_company_detail()` (line 2392)：详情查询 + AppError 404 模式
- `backend/app/api/admin/collection.py` — 路由层，`paginated_response` / `success_response` 包装，`PlatformAuthContext` 认证
- `backend/app/core/errors.py` — `AppError(code="NOT_FOUND", message="...", status_code=404)` 模式

**前端模式参照：**
- `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx` (476 行) — **最直接的参照**
  - `FilterValues` 对象 + `EMPTY_FILTERS` 模式管理筛选状态
  - `appliedFilters` / `filters` 双状态（编辑中 vs 已提交）
  - `useQuery` + TanStack Query 数据获取
  - `detailQuery` + `contactsQuery` 在 Sheet 打开时按需加载
  - `dash()` 工具函数处理 null 值
  - Sheet + 分组展示详情
  - 分页控件 + pageSize 选择
- `frontend/packages/shared-api/src/admin/collection.ts` — 类型定义 + API 方法
  - `WaimaotongRawCompanyRow` / `WaimaotongRawContactRow` 类型模式
  - `collectionApi()` 方法注册模式
- `frontend/packages/shared-api/src/index.ts` — 类型导出（需新增 3 个类型）

### Key Data Facts

- `waimaotong_clean_companies`: 940 行，基础字段填充率 > 90%，AI 字段全 NULL
- `waimaotong_clean_contacts`: 6335 行，通过 `sys_company_id` (UUID) 关联
- `employee_size` 字段为文本（如 "50-199"），筛选需用 `NULLIF(substring(employee_size from '([0-9]+)'), '')::int`
- `founded_year` 为整数，可直接 `>=` / `<=` 比较

## Key Technical Decisions

- **独立方法，不复用 provider 分发**：`waimaotong_clean_companies`（70 列）和 `waimaotong_raw_companies`（33 列）字段集差异极大，独立方法更清晰 (see origin: openspec/changes/admin-customers-revamp/design.md D1)
- **联系人 subquery 关联**：`waimaotong_clean_contacts` 通过 `sys_company_id` 关联，不通过 `id`，与线上数据一致 (see origin: design.md D2)
- **改造现有页面，不新建路由**：`/collection/customers` 语义匹配，避免新增菜单项 (see origin: design.md D3)
- **AI 字段条件显示**：详情 Sheet 中 AI 分组仅在有数据时显示，表格中 null 显示 `-` (see origin: design.md D4)
- **contacts 端点公司不存在时返回空数组**：subquery 一次查询，与现有 list_v3_raw_company_contacts 模式一致（评审决议）

## Open Questions

### Resolved During Planning

- **contacts 404 行为**：采用 subquery 返回空数组，不区分公司不存在和无联系人（评审已确认）
- **employee_size 筛选**：复用现有 `NULLIF(substring(...))` 表达式（line 1218）
- **404 异常模式**：使用 `AppError(code="NOT_FOUND", ...)` （line 2422-2425）

### Deferred to Implementation

- **score_details 进度条组件**：具体 UI 实现取决于数据结构，目前 AI 字段全空，先预留位置
- **trade_summary 结构化展示**：JSONB 结构未知，先以 JSON 预览形式展示

## Implementation Units

- [ ] **Unit 1: 后端 Service 层 — 3 个查询方法**

  **Goal:** 在 admin_collection_service.py 新增 `list_wmt_clean_companies`、`get_wmt_clean_company`、`list_wmt_clean_company_contacts` 三个方法

  **Requirements:** R1, R2, R3, R4

  **Dependencies:** 无

  **Files:**
  - Modify: `backend/app/services/admin_collection_service.py`

  **Approach:**
  - `list_wmt_clean_companies`: WHERE 构建模式参照 `list_clean_companies()` (line 988)。employee_size 文本提取参照 line 1218 的 `NULLIF(substring(...))` 表达式。SELECT 一次性返回 ~30 字段（基础+AI），AI 字段 NULL 原样返回。has_contacts 筛选用 `contacts_count > 0`。返回 `(list[dict], int)` 元组
  - `get_wmt_clean_company`: SELECT * 查询，不存在时 `raise AppError(code="NOT_FOUND", message="公司不存在", status_code=404)`。JSONB 字段由 SQLAlchemy 自动反序列化
  - `list_wmt_clean_company_contacts`: subquery 获取 sys_company_id，查询 waimaotong_clean_contacts 的 13 个字段，按 created_at ASC 排序。返回 list[dict]
  - 所有方法使用 `_datetime_iso()` 格式化时间字段，字符串化 id

  **Patterns to follow:**
  - `list_clean_companies()` (line 988-1108) — WHERE 构建 + COUNT + SELECT 分页
  - `get_lixiaoyun_clean_company_detail()` (line 2392-2428) — 详情 + 404
  - `list_v3_raw_company_contacts()` (line 941-986) — 联系人查询 + 字段格式化
  - `_wmt_emp_expr` (line 1218) — employee_size 文本提取

  **Test scenarios:**
  - Happy path: 无筛选分页查询返回 20 条，按 created_at DESC 排序
  - Happy path: q 参数同时搜索 company_name 和 domain（ILIKE）
  - Happy path: country 精确匹配筛选
  - Happy path: size=medium 过滤 employee_size 文本中数字在 50-199 范围
  - Happy path: year_min + year_max 组合筛选 founded_year
  - Happy path: has_contacts=true 筛选 contacts_count > 0
  - Happy path: 详情 API 返回全量字段，JSONB 字段解析为对象
  - Happy path: 联系人 API 通过 sys_company_id subquery 返回关联联系人
  - Edge case: AI 字段全 NULL 时列表正常返回，字段值为 null
  - Edge case: 联系人 API 公司不存在时返回空列表
  - Error path: 详情 API 公司不存在时返回 404

  **Verification:**
  - 后端启动无报错
  - `/docs` 页面可见 3 个新端点
  - curl 调用列表端点返回分页数据
  - curl 调用详情端点返回完整字段
  - curl 调用联系人端点返回联系人列表

- [ ] **Unit 2: 后端 API 路由 — 3 个端点**

  **Goal:** 在 collection.py 新增 `GET /collection/wmt-clean-companies`、`GET /collection/wmt-clean-companies/{company_id}`、`GET /collection/wmt-clean-companies/{company_id}/contacts` 三个路由

  **Requirements:** R1, R2, R3, R4

  **Dependencies:** Unit 1

  **Files:**
  - Modify: `backend/app/api/admin/collection.py`

  **Approach:**
  - 列表路由：接收 page/page_size/q/country/industry/size/year_min/year_max/has_contacts/grade 参数，调用 service.list_wmt_clean_companies，返回 paginated_response
  - 详情路由：接收 company_id (int)，调用 service.get_wmt_clean_company，返回 success_response
  - 联系人路由：接收 company_id (int)，调用 service.list_wmt_clean_company_contacts，返回 paginated_response(rows, total=len(rows))
  - 所有路由使用 `PlatformAuthContext = Depends(get_current_platform_user)` 认证

  **Patterns to follow:**
  - `list_collection_clean()` (line 141-170) — 列表路由模式
  - `get_v3_raw_company_debug()` (line 248-259) — 详情路由模式
  - `list_v3_raw_company_contacts()` (line 262-273) — 联系人路由模式

  **Test scenarios:**
  - Happy path: 列表端点正确传递所有筛选参数到 service 层
  - Happy path: 详情端点返回 `{success: true, data: {...}}`
  - Happy path: 联系人端点返回 `{data: [...], pagination: {total: N}}`
  - Edge case: page_size 超过 100 时被截断

  **Verification:**
  - FastAPI `/docs` 页面展示 3 个新端点及其参数说明
  - 请求/响应格式与现有端点一致

- [ ] **Unit 3: 前端 shared-api — 类型 + API 方法**

  **Goal:** 新增 WmtCleanCompanyRow、WmtCleanCompanyDetail、WmtCleanContactRow 类型和 3 个 API 调用方法

  **Requirements:** R1, R5

  **Dependencies:** Unit 2

  **Files:**
  - Modify: `frontend/packages/shared-api/src/admin/collection.ts`
  - Modify: `frontend/packages/shared-api/src/index.ts`

  **Approach:**
  - `WmtCleanCompanyRow`：列表字段类型，AI 字段均为 `| null`，参照 design.md SELECT 字段列表的 ~30 字段
  - `WmtCleanCompanyDetail`：extends WmtCleanCompanyRow，增加 JSONB 字段（score_details, match_reasons, potential_needs, recommended_products, risk_factors, main_business, trade_summary, sales_approach 等），类型为 `unknown[] | null` 或 `Record<string, unknown> | null`
  - `WmtCleanContactRow`：13 字段（id, name, position, department, email, email_status, phone, mobile, linkedin, whatsapp, source, confidence, created_at）
  - 在 `collectionApi()` 中新增 `listWmtCleanCompanies`、`getWmtCleanCompany`、`listWmtCleanCompanyContacts`
  - 在 `index.ts` 的 collection 类型导出中新增 3 个类型

  **Patterns to follow:**
  - `WaimaotongRawCompanyRow` (line 124-144) — 类型定义模式
  - `listWaimaotongRawCompanies()` (line 352-368) — API 方法模式
  - `index.ts` 中的 `from './admin/collection'` 导出模式

  **Test scenarios:**
  - Test expectation: none — 纯类型定义和 API 封装，无运行时行为

  **Verification:**
  - `pnpm build --filter shared-api` 编译无错误
  - TypeScript 类型正确导出，admin app 可引用

- [ ] **Unit 4: 前端页面改造 — 筛选区 + 表格 + 分页**

  **Goal:** 重写 client-page.tsx：删除健康卡片和旧类型，新增 7 维筛选区、13 列表格、带 pageSize 选择的分页控件

  **Requirements:** R5, R6, R7, R9, R10

  **Dependencies:** Unit 3

  **Files:**
  - Modify: `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`

  **Approach:**
  - **删除**：healthQuery + 4 个统计 Card、内联 CleanCompanyRow 类型、RangeField 组件
  - **筛选状态管理**：参照 waimaotong/client-page.tsx 的 `FilterValues` + `EMPTY_FILTERS` + `filters/appliedFilters` 双状态模式
  - **筛选区 UI**：公司名/域名输入框、国家输入框、行业输入框、员工规模 Select（tiny/small/medium/large）、成立年份 min/max 两个输入框、有联系人 Checkbox、查询/重置按钮。布局使用 grid
  - **表格**：13 列按 design.md 表格列设计，公司名可点击打开详情，评级 Badge 颜色编码（A=green B=blue C=orange X=red），null 显示 `-`。水平滚动，min-width 适配
  - **分页**：总条数 + 上一页/下一页 + 页码 + pageSize Select（20/50/100），切换 pageSize 重置页码
  - **数据源**：`adminApi.collection.listWmtCleanCompanies()` 替换 `listCleanCompanies()`
  - **页面标题**：从"客户采集归档"改为"外贸通客户数据"

  **Patterns to follow:**
  - `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx` — **主要参照**（筛选区、表格、分页的完整模式）
  - `dash()` 工具函数处理 null 值
  - `PAGE_SIZE_OPTIONS` 常量

  **Test scenarios:**
  - Happy path: 页面加载，列表显示 20 条数据
  - Happy path: 输入搜索条件点击查询，表格更新
  - Happy path: 点击重置，所有筛选条件清空，回到第 1 页
  - Happy path: 切换 pageSize 从 20 到 50，页码重置为 1
  - Happy path: 点击下一页/上一页，数据更新
  - Happy path: 评级列 A 显示绿色 Badge，B 蓝色，C 橙色，X 红色
  - Edge case: AI 字段全 null 时表格对应列显示 `-`
  - Edge case: 0 条数据时显示空状态提示
  - Edge case: 第 1 页时上一页按钮禁用，最后一页时下一页按钮禁用

  **Verification:**
  - `pnpm build --filter admin` 编译无错误
  - dev server 访问 `/collection/customers`，列表正常加载
  - 筛选、分页、pageSize 切换均工作正常

- [ ] **Unit 5: 前端页面改造 — 详情 Sheet**

  **Goal:** 实现多分组详情 Sheet：基本信息（始终显示）、AI 评估（条件显示）、贸易数据（条件显示）、联系人表格（独立 API）、数据来源（始终显示）

  **Requirements:** R8

  **Dependencies:** Unit 4

  **Files:**
  - Modify: `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`

  **Approach:**
  - **触发**：点击表格中公司名 → setSelected(row) → Sheet 打开
  - **详情数据**：Sheet 打开时 useQuery 调用 `getWmtCleanCompany(id)` 获取全量字段
  - **联系人数据**：Sheet 打开时独立 useQuery 调用 `listWmtCleanCompanyContacts(id)` 获取联系人
  - **分组 1 基本信息**（始终显示）：company_name, english_name, country, domain, website, industry, phone, employee_size, company_size, founded_year, full_address, description — 使用 grid 两列布局，null 显示 `-`
  - **分组 2 AI 评估**（仅当 grade 或 score 有值时显示）：grade Badge、score、score_details 多维度展示（进度条）、sub_industry、company_type_analysis、product_tags Badge 列表、match_reasons/potential_needs/recommended_products/risk_factors/main_business 列表、email_priority
  - **分组 3 贸易数据**（仅当 has_trade_data 为 true 或 trade_summary 有值时显示）：has_trade_data、trade_amount_3y_usd、trade_count、trade_summary（JSON 预览）
  - **分组 4 联系人**（始终显示）：表格展示 name/position/department/email/email_status/phone/linkedin/source，加载中显示 loading
  - **分组 5 数据来源**（始终显示）：data_source_tags、source_id、sys_company_id、detail_status/contacts_status/trade_status Badge、created_at/updated_at
  - **关闭**：清空 selected 状态

  **Patterns to follow:**
  - `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx` (line 102-120) — detailQuery + contactsQuery 按需加载模式
  - Sheet 组件已在当前页面使用

  **Test scenarios:**
  - Happy path: 点击公司名，Sheet 打开，显示基本信息
  - Happy path: 有 AI 数据的公司，显示全部 5 个分组
  - Happy path: 联系人加载后展示表格
  - Happy path: 关闭 Sheet，清空选中状态
  - Edge case: AI 字段全空时只显示分组 1/4/5，不显示分组 2/3
  - Edge case: 联系人为空时显示空状态
  - Edge case: score_details 为数组时展示多维度进度条

  **Verification:**
  - 点击任意公司名，Sheet 正确打开并加载详情
  - AI 字段全空的公司只看到基本信息、联系人、数据来源三个分组
  - 联系人表格正确展示

## System-Wide Impact

- **Interaction graph:** 新 API 端点 → admin_collection_service → waimaotong_clean_companies / waimaotong_clean_contacts 表。不涉及 Worker、回调或中间件
- **Error propagation:** Service 层 AppError → FastAPI 全局异常处理 → JSON 错误响应（现有机制）
- **State lifecycle risks:** 无。纯读取查询，不修改数据
- **API surface parity:** 旧 `GET /collection/clean-companies` 保留不动，前端不再调用但不删除
- **Unchanged invariants:** clean_companies 表及其 API、tenant 端公司展示、其他 collection 子页面均不受影响

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| waimaotong_clean_companies 不在 Alembic 管理中 | 本 change 不改表结构；后续单独补迁移文件 |
| AI 字段当前全空，页面信息稀疏 | 条件显示分组 + 基础字段填充率 > 90% |
| 联系人通过 sys_company_id 关联，无 FK 约束 | subquery 确保 company 存在；公司不存在时返回空列表 |
| client-page.tsx 全量重写，diff 较大 | 现有页面只有 200 行，参照模板（waimaotong/client-page.tsx 476 行）已验证可行 |

## Sources & References

- **Origin document:** [openspec/changes/admin-customers-revamp/](openspec/changes/admin-customers-revamp/)
- **Design:** [openspec/changes/admin-customers-revamp/design.md](openspec/changes/admin-customers-revamp/design.md)
- **Specs:** [wmt-clean-list/spec.md](openspec/changes/admin-customers-revamp/specs/wmt-clean-list/spec.md), [wmt-clean-detail/spec.md](openspec/changes/admin-customers-revamp/specs/wmt-clean-detail/spec.md)
- **Tasks:** [tasks.md](openspec/changes/admin-customers-revamp/tasks.md)
- **主要参照代码:** `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx`
- **外部参照仓库:** https://github.com/aoqi-ai/sysdev-ft-marketing
