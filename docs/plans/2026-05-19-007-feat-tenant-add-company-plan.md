---
title: "feat: Tenant 公司列表页新增公司 Drawer"
type: feat
status: completed
date: 2026-05-19
origin: openspec/changes/2026-05-19-tenant-add-company/proposal.md
---

# feat: Tenant 公司列表页新增公司 Drawer

## Overview

Tenant 端公司列表页新增「新增公司」入口。点击后右侧滑出 Sheet 表单（基本信息 12 字段 + 联系人可选多行 + 备注），提交后调用 `POST /api/v1/companies` 创建公司并刷新列表。后端 INSERT 扩展 5 个已有字段的写入。

## Problem Frame

用户只能从系统已有的 `waimaotong_clean_companies` 中挑选公司加入群组，无法录入系统中不存在的目标客户。后端 `create_company` 的 INSERT 只写 7 个字段，忽略了 phone、employee_size、founded_year、full_address、description 5 个已有列。前端完全没有创建 UI。(see origin: `openspec/changes/2026-05-19-tenant-add-company/proposal.md`)

## Requirements Trace

- R1. 公司列表页 PageHeader 右侧显示「新增公司」按钮
- R2. 点击按钮后右侧 Sheet 展开，表单分三组（基本信息 / 联系人 / 备注）
- R3. 公司名称为唯一必填字段，其余均可选
- R4. 国家下拉复用 `filters()` 数据，员工规模下拉为固定选项
- R5. 联系人支持多行添加/删除，提交时过滤全空行
- R6. 产品标签支持多值输入
- R7. 后端 INSERT 扩展写入 phone、employee_size、founded_year、full_address、description
- R8. 提交成功后 toast + 关闭 Sheet + invalidate 列表查询
- R9. 提交失败显示后端返回的具体错误信息

## Scope Boundaries

- 不做公司编辑功能（本次只做新增）
- 不改数据库 schema / migration（5 个字段已存在于表中）
- 不改 admin 端代码
- 不做批量导入
- 不修改去重逻辑（advisory lock 策略不变）

## Context & Research

### Relevant Code and Patterns

- `backend/app/services/tenant_ops_service.py` — `create_company` 方法（116-237 行），INSERT 在 164-184 行
- `backend/app/services/tenant_ops_service.py` — `_ensure_contact_from_payload` 方法（990-1072 行），已支持 `contacts[]` 数组
- `backend/app/api/tenant/ops.py` — POST `/companies` 路由（131-143 行），`payload: dict` 无 Pydantic 约束
- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` — 列表页，已有 Sheet/QueryClient/invalidate 模式
- `frontend/apps/tenant/src/app/(dashboard)/companies/company-detail.tsx` — 详情 Sheet 组件，参考布局和 useMutation 模式
- `frontend/apps/tenant/src/components/company-filters.tsx` — `countryZh()` 翻译函数和 `COUNTRY_ZH` 映射
- `frontend/apps/tenant/src/components/pages/page-kit.tsx` — `PageHeader` 组件，已有 `action?: ReactNode` prop
- `frontend/packages/shared-api/src/tenant/companies.ts` — `create(data: Record<string, unknown>)` 已就绪
- `frontend/packages/shared-ui/src/components/` — Sheet、Input、Textarea、Select、Label、Button、MultiSelect 组件

### Institutional Learnings

- send-plans 的 step-basic-info.tsx 提供了表单验证模式参考：validate 函数返回 `Record<string, string>` 错误映射
- company-detail.tsx 的 useMutation + toast + invalidateQueries 是标准的提交模式
- 查询 key 分层 `['tenant', 'companies', ...]` 允许 `invalidateQueries({ queryKey: ['tenant', 'companies'] })` 批量失效

## Key Technical Decisions

- **Sheet 而非 Modal/独立页面**: 字段较多（12+），Modal 空间不够；独立页面跳转断开上下文。Sheet 在列表旁展开，填完即回。(see origin: design.md D1)
- **Sheet 宽度 w-[660px]**: 与已有的公司详情 Sheet 一致
- **founded_year 类型转换**: payload 中为字符串，INSERT 前需 `int()` 转换，无效值置 `None`
- **联系人 payload key**: 前端用 `title` 字段，后端 `_ensure_contact_from_payload` 已映射为 DB 的 `position` 列，无需额外处理
- **产品标签**: 使用 MultiSelect 组件的 `allowCreate` 模式，payload 传 `string[]`，后端 `CAST(:product_tags AS text[])` 已处理
- **表单状态管理**: 使用 useState 管理表单数据，不引入 react-hook-form（与现有代码风格一致）

## Open Questions

### Resolved During Planning

- **国家数据来源**: 复用 `tenantApi.companies.filters()` 返回的 `countries` 列表，配合 `countryZh()` 翻译
- **员工规模选项**: 固定列表 `1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5000+`，与 admin 端一致
- **联系人默认行数**: 默认显示一行空行，全空时提交自动过滤
- **列表查询/详情查询是否需改**: 不需要，`tenant_query_service.py` 的 SELECT 已包含 5 个新字段

### Deferred to Implementation

- **表单各字段的具体 placeholder 文案**: 实现时根据字段语义确定
- **founded_year 的合理范围校验（如 1800-当前年份）**: 视实际需求决定是否添加前端校验

## Output Structure

```
frontend/apps/tenant/src/app/(dashboard)/companies/
  page.tsx                  # 修改: 添加按钮 + 引入 Sheet
  company-detail.tsx        # 不改
  add-company-sheet.tsx     # 新增: 新增公司 Sheet 表单

backend/app/services/
  tenant_ops_service.py     # 修改: INSERT 扩展 5 字段

backend/tests/
  test_tenant_create_company.py  # 新增: pytest 测试
```

## Implementation Units

- [x] **Unit 1: 后端 INSERT 扩展 5 字段**

**Goal:** `create_company` 的 INSERT 语句从 7 字段扩展为 12 字段，支持写入 phone、employee_size、founded_year、full_address、description

**Requirements:** R7

**Dependencies:** 无

**Files:**
- Modify: `backend/app/services/tenant_ops_service.py`
- Test: `backend/tests/test_tenant_create_company.py`

**Approach:**
- 在 INSERT 语句的列列表和 VALUES 中追加 5 个字段
- 参数字典中新增 5 个 `payload.get()` 取值
- `founded_year` 需要 `int()` 转换，无效值（None、非数字字符串）置 `None`
- 其余 4 个字段直接透传，均为可选文本

**Patterns to follow:**
- 已有的 `payload.get("english_name")` 取值模式（`tenant_ops_service.py:176`）
- `_normalize_country_iso3` 的防御性类型处理模式

**Test scenarios:**
- Happy path: 传入全部 5 个新字段，验证 INSERT 后行包含正确值
- Happy path: 只传 name（最小 payload），验证 5 个新字段为 NULL
- Edge case: `founded_year` 为字符串 "2010"，验证转换为 int 2010
- Edge case: `founded_year` 为 None 或空字符串，验证存为 NULL
- Edge case: `founded_year` 为非数字字符串 "abc"，验证存为 NULL 不报错

**Verification:**
- `cd backend && python -m pytest tests/test_tenant_create_company.py -v` 全部通过

- [x] **Unit 2: 新增公司 Sheet 表单组件**

**Goal:** 创建 `add-company-sheet.tsx`，包含分三组的表单（基本信息 12 字段 + 联系人可选多行 + 备注），提交调用 create API

**Requirements:** R2, R3, R4, R5, R6, R8, R9

**Dependencies:** Unit 1（后端需支持新字段）

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/companies/add-company-sheet.tsx`

**Approach:**
- Props: `open: boolean`, `onOpenChange: (open: boolean) => void`, `onSuccess: () => void`
- 表单状态用 useState 管理，初始值全部为空
- 基本信息区域 12 个字段：公司名称（Input, 必填）、英文名称（Input）、国家（Select，数据来自 `filtersQuery`）、域名（Input）、网站（Input）、电话（Input）、行业（Input）、员工规模（Select，固定选项）、成立年份（Input type=number）、地址（Input）、公司简介（Textarea）、产品标签（MultiSelect allowCreate）
- 联系人区域：数组状态 `[{name, email, title}]`，默认一行空行，支持添加/删除，至少保留一行
- 备注区域：Textarea
- 提交：校验 name 非空 → 构建 payload → useMutation 调 `tenantApi.companies.create()` → 成功 toast + onSuccess + 重置表单 → 失败显示 `error.response?.data?.message`
- Sheet 关闭时重置表单状态

**Patterns to follow:**
- `company-detail.tsx` 的 useMutation + toast + invalidate 模式
- `send-plans/new/step-basic-info.tsx` 的 Label + Input + 错误提示布局
- `page.tsx` 的 `filtersQuery` 数据获取模式（国家列表）
- `company-filters.tsx` 的 `countryZh()` 翻译函数

**Test scenarios:**
- Happy path: 只填公司名称 → 提交成功 → Sheet 关闭 + toast
- Happy path: 填写全部字段 + 多个联系人 → 提交成功 → payload 包含所有字段
- Edge case: 公司名称为空 → 提交按钮时显示校验错误，不发请求
- Edge case: 联系人全部为空行 → payload 中 contacts 为空数组或不传
- Error path: API 返回错误 → toast 显示后端错误信息
- Integration: 提交成功后 onSuccess 回调触发（用于列表 invalidate）

**Verification:**
- 浏览器打开 /companies → 点"新增公司" → Sheet 展开 → 表单可填写 → 提交成功/失败行为正确

- [x] **Unit 3: 列表页按钮接入**

**Goal:** 公司列表页 PageHeader 添加「新增公司」按钮，控制 Sheet 开关状态，提交成功后刷新列表

**Requirements:** R1, R8

**Dependencies:** Unit 2（Sheet 组件需已创建）

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**Approach:**
- 新增 `useState<boolean>` 控制 Sheet 的 open 状态
- PageHeader 添加 `action` prop，放置 Button（文案「新增公司」，带 Plus icon）
- 引入 `AddCompanySheet` 组件，传入 open、onOpenChange、onSuccess（调用 `invalidateList`）
- `invalidateList` 已存在（行 99），直接复用

**Patterns to follow:**
- `send-plans/page.tsx` 的 PageHeader action 用法：`action={<Button>新建计划</Button>}`
- 已有的 `invalidateList` 函数复用

**Test scenarios:**
- Happy path: 页面加载后 PageHeader 右侧显示「新增公司」按钮
- Happy path: 点击按钮 → Sheet 展开 → 关闭 Sheet → 按钮仍在
- Integration: Sheet 提交成功 → 列表自动刷新（新公司出现在列表中）

**Verification:**
- 浏览器打开 /companies → 按钮可见 → 点击打开 Sheet → 新建公司 → 列表刷新且新公司出现

- [x] **Unit 4: 端到端验证**

**Goal:** 完整流程验证，确认前后端联通、数据正确写入和展示

**Requirements:** R1-R9 全部

**Dependencies:** Unit 1, 2, 3

**Files:** 无新增/修改

**Approach:**
- 场景 A: 最小化创建 — 只填公司名称 → 提交 → 列表出现新公司
- 场景 B: 全量创建 — 填写全部 12 个基本信息字段 + 2 个联系人 + 备注 → 提交 → 点击详情确认所有字段正确
- 场景 C: 校验测试 — 不填公司名称直接提交 → 显示校验错误
- 场景 D: 重复创建 — 创建同名同国家公司 → 验证后端去重逻辑（advisory lock）行为符合预期

**Test expectation: none** -- 端到端验证通过浏览器手动测试完成，不产生自动化测试代码

**Verification:**
- 浏览器 preview 截图确认各场景通过

## System-Wide Impact

- **Interaction graph:** `page.tsx` → `AddCompanySheet` → `tenantApi.companies.create()` → `tenant_ops_service.create_company()` → INSERT `waimaotong_clean_companies` + `tenant_companies` + `_ensure_contact_from_payload()`
- **Error propagation:** API 错误通过 AxiosError 传播到前端 → mutation onError → toast 显示 `error.response.data.message`
- **State lifecycle risks:** Sheet 关闭时需重置表单状态，避免残留数据影响下次打开
- **API surface parity:** `create` API 的 payload 为 `Record<string, unknown>`，新字段直接透传，无需修改 API 客户端类型
- **Unchanged invariants:** advisory lock 去重逻辑不变；`_ensure_contact_from_payload` 的联系人去重逻辑不变；列表/详情查询 SQL 不变

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| founded_year 类型转换失败导致 INSERT 报错 | 防御性转换：try/except 包裹，无效值置 None |
| Sheet 表单字段过多导致滚动体验差 | 分三组视觉分隔，SheetContent 设置 overflow-y-auto |
| 国家 filters 接口未返回数据时下拉为空 | Select 组件无选项时显示占位文本，不影响提交 |

## Sources & References

- **Origin document:** [proposal.md](openspec/changes/2026-05-19-tenant-add-company/proposal.md)
- **Design document:** [design.md](openspec/changes/2026-05-19-tenant-add-company/design.md)
- **Tasks document:** [tasks.md](openspec/changes/2026-05-19-tenant-add-company/tasks.md)
- Related code: `backend/app/services/tenant_ops_service.py`, `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`
