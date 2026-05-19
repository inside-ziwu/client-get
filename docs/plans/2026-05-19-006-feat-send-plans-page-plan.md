---
title: "feat: 发送计划页 — 向导式新建 + 详情页改造 + 执行控制"
type: feat
status: active
date: 2026-05-19
origin: openspec/changes/2026-05-19-send-plans-page/
---

# feat: 发送计划页 — 向导式新建 + 详情页改造 + 执行控制

## Overview

将发送计划的新建页从单步草稿表单重写为四步向导（基本信息 → 步骤配置 → 收件人 → 确认），调用 `complete-create` API 一次提交；详情页从简单摘要改造为纵向分区布局（概览 + 步骤 + 收件人 + 发送日志）+ 状态驱动的执行控制按钮。后端做 3 处 JOIN 微调 + 1 处过滤参数，不改 schema。

## Problem Frame

后端已完整就绪（计划 CRUD、complete-create、步骤配置、收件人锁定/预览、生命周期控制、Worker 发送、EngageLab 集成），但前端在 Next.js 迁移后只有骨架。用户无法通过 UI 完成一次完整的邮件发送计划流程——步骤配置、收件人选择、执行控制全部缺失。（see origin: `openspec/changes/2026-05-19-send-plans-page/proposal.md`）

## Requirements Trace

- R1. 新建页为四步向导，调用 `complete-create` 一次性创建计划+步骤+锁定收件人
- R2. 向导 Step 1：基本信息（名称、描述、发件人名称、发件邮箱、发送域名）
- R3. 向导 Step 2：步骤配置（模板选择、延迟天数、触发条件、AI 个性化、添加/删除步骤）
- R4. 向导 Step 3：收件人选择（群组模式、群组成员预览、锁定收件人默认 true）
- R5. 向导 Step 4：确认总览（只读展示全部配置，确认后提交）
- R6. 详情页纵向分区：概览 + 步骤摘要 + 收件人列表 + 发送日志
- R7. 详情页执行控制：根据 plan.status 显隐操作按钮（开始/暂停/恢复/取消）
- R8. 后端 `listSteps` JOIN 返回模板名称
- R9. 后端 `listRecipients` LEFT JOIN 返回 enrollment 状态
- R10. 后端 `GET /emails` 支持 `plan_id` 过滤

## Scope Boundaries

- 不改数据库 schema
- 不在详情页提供编辑步骤/追加收件人
- 不做邮件模板编辑（独立功能）
- 不做 A/B 测试或发送时间优化
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件（除本计划）
- 收件人来源第一期只实现 `group` 模式

## Context & Research

### Relevant Code and Patterns

**前端表单模式（已有）：**
- 新建页：`useState` 管理表单 → `useMutation` 提交 → `onSuccess` 中 `toast.success` + `queryClient.invalidateQueries` + `router.replace`
- 参考文件：`send-plans/new/page.tsx`（当前简单表单）、`templates/page.tsx`、`settings/team/page.tsx`

**前端详情页模式（已有）：**
- `DescriptionList` 组件（`shared-ui`）：网格 2 列布局，items 数组 `{label, value}`
- `DataTable` 组件：表格 + 分页
- `StatusTag` 组件：6 种状态彩色标签（draft/scheduled/running/paused/completed/cancelled）
- 参考文件：`send-plans/[id]/page.tsx`（当前详情页）

**前端空白点（需新建）：**
- 多步向导：项目中无先例，onboarding 页只有静态步骤展示，不是交互式向导
- 状态驱动按钮组：项目中无先例，最接近的是 company-detail 的 editing 状态切换

**后端待改方法（已定位）：**
- `list_plan_steps()`：`tenant_messaging_service.py:871-896`，当前只 SELECT `sequence_steps`
- `list_plan_recipients()`：`tenant_messaging_service.py:703-737`，当前只 JOIN 公司/联系人表
- `list_emails()`：`tenant_messaging_service.py:1007-1065`，当前无 `plan_id` 过滤
- `GET /emails` 路由：`messaging.py:386-398`，当前参数只有 `limit` + `cursor`

**前端 API 客户端（已定位）：**
- `sending-plans.ts`：缺 `completeCreate` 方法；`SendingPlanStep` 类型缺 `template_name`
- `SendingPlanRecipient` 类型已有 `enrollment_status?` 和 `current_step` 字段（但 `current_step` 应改为可选）
- `emails.ts`：`list()` 方法已存在，需加 `plan_id` 参数

## Key Technical Decisions

- **向导状态管理用 `useState`**：不引入额外状态库。单个 `formData` 对象 + `currentStep` 数字。每步组件接收 `formData` 和 `onChange` 回调。（see origin: design.md D9）
- **步骤指示器内联实现**：不抽取独立 Stepper 组件，直接在向导页面用 div + 样式实现编号+标题横排。（see origin: design.md D1）
- **lock_recipients 默认 true**：减少用户遗忘风险。（审查决策 D8）
- **详情页纵向分区不用 Tab**：向导完成创建后详情页以只读为主，纵向布局足够。（see origin: proposal.md D2）
- **发送日志首版实现基础列表**：调 `GET /emails?plan_id={id}` 展示邮件记录。（审查决策 D7）
- **执行控制按钮状态映射**：`ACTION_MAP` 常量定义各状态下可用按钮。取消操作弹 AlertDialog 二次确认。（see origin: design.md D7）

## Open Questions

### Resolved During Planning

- 发送域名 API：已确认 `GET /domains`（`ops.py:403`），前端 `domains.ts` 已就绪
- `SendingPlanRecipient` 类型：已有 `enrollment_status?` 和 `current_step`，后端 JOIN 后前端无需新增字段
- 发送日志 API：复用 `GET /emails` 加 `plan_id` 参数，不需要新建专用端点

### Deferred to Implementation

- 向导步骤校验的具体错误提示文案：实现时根据字段确定
- 收件人预览表格的列宽和排序：实现时调整
- 发送日志的分页大小：实现时决定（建议 20）

## Implementation Units

### Phase 0: 后端微调 + 前端 API 客户端

- [ ] **Unit 1: 后端 listSteps JOIN 模板名称**

**Goal:** `GET /sending-plans/{id}/steps` 返回 `template_name` 字段

**Requirements:** R8

**Dependencies:** 无

**Files:**
- Modify: `backend/app/services/tenant_messaging_service.py`（`list_plan_steps` 方法，~行 871-896）
- Test: `backend/tests/test_sending_plan_creation.py`

**Approach:**
- SQL 追加 `LEFT JOIN email_templates et ON et.id = ss.template_id`
- SELECT 追加 `et.name AS template_name`
- 返回字典追加 `template_name` 键

**Patterns to follow:**
- 同文件 `list_plan_recipients()` 已有多表 JOIN 的写法
- `list_emails()` 已有 `LEFT JOIN email_templates et ON et.id = e.template_id` 可参考

**Test scenarios:**
- Happy path: 创建计划含 2 个步骤（各指向不同模板），调 listSteps，验证每个步骤返回正确的 `template_name`
- Edge case: 步骤引用的模板被删除（`deleted_at` 非空），验证 LEFT JOIN 返回 `template_name: null` 而非报错

**Verification:**
- 集成测试通过
- 手动调 API 确认返回中包含 `template_name`

---

- [ ] **Unit 2: 后端 listRecipients JOIN enrollment 数据**

**Goal:** `GET /sending-plans/{id}/recipients` 返回 `enrollment_status` 和 `current_step`

**Requirements:** R9

**Dependencies:** 无

**Files:**
- Modify: `backend/app/services/tenant_messaging_service.py`（`list_plan_recipients` 方法，~行 703-737）
- Test: `backend/tests/test_sending_plan_creation.py`

**Approach:**
- SQL 追加 `LEFT JOIN sequence_enrollments se ON se.plan_id = pr.plan_id AND se.tenant_contact_id = pr.tenant_contact_id`
- SELECT 追加 `se.status AS enrollment_status, se.current_step AS current_step`
- 返回字典追加对应键

**Patterns to follow:**
- 同方法已有的 JOIN 链（`tenant_companies` → `waimaotong_clean_companies` → `tenant_contacts`）

**Test scenarios:**
- Happy path: 创建计划 → 锁定收件人 → 创建 enrollment → 调 listRecipients，验证返回 enrollment_status="active" 和 current_step=1
- Edge case: 收件人已锁定但尚未 enroll，验证 enrollment_status=null, current_step=null

**Verification:**
- 集成测试通过

---

- [ ] **Unit 3: 后端 GET /emails 加 plan_id 过滤**

**Goal:** `GET /emails` 支持按 `plan_id` 过滤，供详情页发送日志区使用

**Requirements:** R10

**Dependencies:** 无

**Files:**
- Modify: `backend/app/services/tenant_messaging_service.py`（`list_emails` 方法，~行 1007-1065）
- Modify: `backend/app/api/tenant/messaging.py`（`GET /emails` 路由，~行 386-398）
- Test: `backend/tests/test_sending_plan_creation.py`

**Approach:**
- 路由加 `plan_id: str | None = Query(None)` 参数，透传给 service
- service 方法加 `plan_id: str | None = None` 参数
- 当 `plan_id` 传入时追加 `AND e.plan_id = CAST(:plan_id AS uuid)` 到 WHERE 子句
- COUNT 查询同步追加

**Patterns to follow:**
- 同文件 `list_emails` 的 `cursor_clause` 条件拼接方式

**Test scenarios:**
- Happy path: 创建 2 个计划各发 1 封邮件，调 `GET /emails?plan_id={plan1.id}`，验证只返回计划 1 的邮件
- Happy path: 不传 plan_id，验证返回全部邮件（向后兼容）

**Verification:**
- 集成测试通过

---

- [ ] **Unit 4: 前端 API 客户端更新**

**Goal:** 新增 `completeCreate` 方法，更新类型定义，`emails.list` 加 `plan_id` 参数

**Requirements:** R1, R8, R9, R10

**Dependencies:** Unit 1-3（后端就绪后类型才完整，但前端可先写）

**Files:**
- Modify: `frontend/packages/shared-api/src/tenant/sending-plans.ts`
- Modify: `frontend/packages/shared-api/src/tenant/emails.ts`

**Approach:**
- `sending-plans.ts`：添加 `completeCreate(data)` 方法，POST `/api/v1/sending-plans/complete-create`
- `sending-plans.ts`：`SendingPlanStep` 类型追加 `template_name?: string`
- `sending-plans.ts`：`SendingPlanRecipient` 类型中 `current_step` 改为可选
- `emails.ts`：`list` 方法参数追加 `plan_id?: string`

**Patterns to follow:**
- 同文件已有的 `create`、`update` 等方法签名风格

**Test scenarios:**
- Test expectation: none — 纯类型定义和 API 客户端方法，无行为逻辑

**Verification:**
- TypeScript 编译通过
- 后续向导和详情页正确调用

### Phase 1: 新建向导 — 页面骨架 + 基本信息

- [ ] **Unit 5: 向导主页面骨架**

**Goal:** 搭建四步向导的容器：步骤指示器 + 步骤切换 + formData 状态管理 + 导航按钮

**Requirements:** R1

**Dependencies:** 无

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx`（整体重写）

**Approach:**
- `currentStep` state（0-3）控制当前步骤
- `formData` state 存储全部表单数据（类型 `WizardFormData`）
- 步骤指示器：4 个编号+标题的 div 横排，当前步骤高亮（active 样式），已完成步骤用不同样式
- 底部按钮栏：上一步 / 下一步（step 0-2）/ 创建计划（step 3）
- 下一步前调当前步骤的校验函数（每步返回 boolean）
- 步骤组件按 `currentStep` 条件渲染（暂用占位 div）

**Patterns to follow:**
- 现有 `send-plans/new/page.tsx` 的页面结构（PageHeader + Card 包裹）
- onboarding 页的步骤展示布局（编号 + 标题）

**Test scenarios:**
- Test expectation: none — UI 骨架，无独立行为逻辑

**Verification:**
- 页面渲染四步指示器，点击下一步/上一步正确切换

---

- [ ] **Unit 6: Step 1 基本信息表单**

**Goal:** 实现向导第一步：名称、描述、发件人名称、发件邮箱、发送域名

**Requirements:** R2

**Dependencies:** Unit 4（`domains.list` 已就绪）、Unit 5

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-basic-info.tsx`

**Approach:**
- 接收 props：`formData.plan` + `onChange` 回调
- 域名下拉：`useQuery(['tenant', 'domains'])` 加载域名列表，过滤 `verification_status === 'verified'`
- 字段：名称（Input 必填）、描述（Textarea 可选）、发件人名称（Input 必填）、发件邮箱（Input 必填）、发送域名（Select 必填）
- 导出校验函数：检查所有必填字段非空

**Patterns to follow:**
- `settings/team/page.tsx` 的表单字段布局（Label + Input 垂直排列）
- `domains.ts` 的 `list()` 调用方式

**Test scenarios:**
- Happy path: 填写所有必填字段 → 校验通过，允许下一步
- Error path: 留空必填字段 → 校验失败，显示错误提示
- Edge case: 无已验证域名 → Select 显示空列表或提示文案

**Verification:**
- 表单渲染所有字段，域名下拉加载成功，校验逻辑正确

### Phase 2: 新建向导 — 步骤配置 + 收件人

- [ ] **Unit 7: Step 2 步骤配置**

**Goal:** 实现向导第二步：发送步骤卡片列表，支持模板选择、延迟天数、触发条件、AI 个性化、添加/删除

**Requirements:** R3

**Dependencies:** Unit 5

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-configure-steps.tsx`

**Approach:**
- 接收 props：`formData.steps` + `onChange` 回调
- 模板列表：`useQuery(['tenant', 'emailTemplates'])` 加载
- 每个步骤渲染为 Card：模板 Select + 延迟天数 Input + 触发条件 Select + AI 个性化 Checkbox + AI 指令 Textarea
- 第一步锁定：`condition_type="always"`、`delay_days=0`，相关字段 disabled
- 后续步骤：`condition_type` 可选 `no_reply`（默认）/`opened`/`clicked`，`delay_days` 默认 3
- 添加步骤：末尾追加，`step_number` 自动递增
- 删除步骤：删除后重新编号，至少保留 1 个步骤
- 导出校验函数：每个步骤必须选择模板

**Patterns to follow:**
- `email-templates.ts` 的 `list()` 调用
- 现有表单中 Select 组件的使用方式

**Test scenarios:**
- Happy path: 添加 2 个步骤，各选模板 → 校验通过
- Happy path: 删除第 2 步 → 剩余步骤重新编号
- Error path: 某步骤未选模板 → 校验失败
- Edge case: 只有 1 个步骤时删除按钮不显示
- Edge case: 第一步的 condition_type 和 delay_days 字段不可编辑

**Verification:**
- 步骤卡片正确渲染和交互，添加/删除/重编号正常

---

- [ ] **Unit 8: Step 3 收件人选择**

**Goal:** 实现向导第三步：群组选择 + 群组成员预览 + 锁定收件人

**Requirements:** R4

**Dependencies:** Unit 5

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-recipients.tsx`

**Approach:**
- 接收 props：`formData.plan.recipient_config` + `formData.lock_recipients` + `onChange` 回调
- 群组下拉：`useQuery(['tenant', 'groups'])` 加载群组列表
- 选中群组后更新 `recipient_config: { group_id: selectedGroupId }`
- 群组成员预览：`useQuery(['tenant', 'groups', groupId, 'members'])` 加载成员列表，展示为 DataTable（公司、联系人、邮箱）
- 锁定收件人 Checkbox，默认勾选
- 统计摘要：合计 N 人
- 导出校验函数：必须选择群组

**Patterns to follow:**
- `groups.ts` 的 `list()` 和 `listMembers()` 调用
- `curated-customers/page.tsx` 中群组列表的加载模式

**Test scenarios:**
- Happy path: 选择群组 → 预览表格显示成员列表 → 校验通过
- Error path: 未选择群组 → 校验失败
- Edge case: 选中的群组无成员 → 预览表格为空，显示提示
- Happy path: 切换群组 → 预览表格刷新

**Verification:**
- 群组选择和成员预览正常工作

### Phase 3: 新建向导 — 确认 + 提交

- [ ] **Unit 9: Step 4 确认总览**

**Goal:** 实现向导第四步：只读展示前三步配置摘要

**Requirements:** R5

**Dependencies:** Unit 5

**Files:**
- Create: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-confirmation.tsx`

**Approach:**
- 接收 props：完整 `formData`（只读）
- 三个分区：基本信息（DescriptionList）、步骤配置（只读 Table）、收件人摘要（群组名 + 锁定状态 + 预估人数）
- 模板名称从前端已加载的模板列表中查找（传入 `templates` 列表 prop 或从 queryClient cache 取）
- 群组名称同理从群组列表 cache 取
- 无校验（纯展示）

**Patterns to follow:**
- `DescriptionList` 组件的 items 格式
- 详情页 `send-plans/[id]/page.tsx` 的信息展示布局

**Test scenarios:**
- Happy path: 展示基本信息、步骤列表、收件人摘要，所有数据与前三步输入一致
- Edge case: 步骤中 AI 个性化关闭时不显示 AI 指令列

**Verification:**
- 确认页完整展示所有配置信息

---

- [ ] **Unit 10: 向导提交逻辑**

**Goal:** 确认步骤点击"创建计划"后构建 payload 调 `completeCreate`，成功跳转详情页

**Requirements:** R1

**Dependencies:** Unit 4（`completeCreate` 方法）、Unit 5、Unit 9

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx`

**Approach:**
- `useMutation` 调 `tenantApi.sendingPlans.completeCreate(payload)`
- 构建 payload：从 `formData` 映射到 API 期望的结构
- `onSuccess`：`toast.success('发送计划创建成功')` → `router.push(/send-plans/${plan.id})`
- `onError`：`toast.error(error.message)`，留在当前页
- 提交按钮：`disabled={mutation.isPending}`，文案改为"创建中..."

**Patterns to follow:**
- 现有 `send-plans/new/page.tsx` 的 mutation 模式
- `settings/team/page.tsx` 的 onSuccess 跳转模式

**Test scenarios:**
- Happy path: 点击创建 → API 成功 → toast + 跳转详情页
- Error path: API 返回 422（校验错误）→ toast.error 显示后端错误信息
- Edge case: 提交过程中按钮 disabled 防重复点击

**Verification:**
- 完整创建流程：填写 → 确认 → 提交 → 跳转

### Phase 4: 详情页改造

- [ ] **Unit 11: 详情页概览区改造**

**Goal:** 扩展概览区展示完整计划信息

**Requirements:** R6

**Dependencies:** 无

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- 扩展 DescriptionList items：发件人名称、发件邮箱、发送域名、收件人数、已发送数、创建时间、描述
- StatusTag 保持现有实现

**Patterns to follow:**
- 当前详情页的 DescriptionList 用法（grid-cols-2 布局）

**Test scenarios:**
- Happy path: 详情页加载后 DescriptionList 展示所有字段，数据与 API 返回一致

**Verification:**
- 概览区展示完整信息

---

- [ ] **Unit 12: 步骤摘要区**

**Goal:** 详情页新增只读步骤列表区

**Requirements:** R6, R8

**Dependencies:** Unit 1（后端返回 template_name）

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- `useQuery(['tenant', 'sendingPlans', planId, 'steps'])` 调 `listSteps`
- 渲染为简单 Table（非 DataTable，数据量小无需分页）：步骤号、模板名称、延迟天数（第一步显示"立即"）、触发条件（中文映射）、AI 个性化（是/否）
- 用 Card 包裹，标题"发送步骤"

**Patterns to follow:**
- design.md D6 的步骤表格布局

**Test scenarios:**
- Happy path: 加载 3 步骤计划，表格展示 3 行，模板名称正确
- Edge case: 计划只有 1 个步骤，表格展示 1 行

**Verification:**
- 步骤列表正确展示

---

- [ ] **Unit 13: 收件人列表区**

**Goal:** 详情页新增带分页的收件人 DataTable

**Requirements:** R6, R9

**Dependencies:** Unit 2（后端返回 enrollment 数据）

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- `useQuery(['tenant', 'sendingPlans', planId, 'recipients'])` 调 `listRecipients`
- DataTable 列：公司、邮箱、enrollment 状态（StatusTag 或文字映射）、当前步骤
- 含分页（与现有详情页的收件人表格类似，但列更丰富）
- 用 Card 包裹，标题"收件人"

**Patterns to follow:**
- 当前详情页已有的 DataTable 收件人表格

**Test scenarios:**
- Happy path: 显示收件人列表，enrollment_status 和 current_step 正确展示
- Edge case: 收件人已锁定但未 enroll → 状态和步骤列显示"-"

**Verification:**
- 收件人表格展示正确，分页正常

---

- [ ] **Unit 14: 发送日志区**

**Goal:** 详情页新增该计划的邮件发送记录列表

**Requirements:** R6, R10

**Dependencies:** Unit 3（后端 plan_id 过滤）、Unit 4（前端 emails.list 加 plan_id）

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- `useQuery(['tenant', 'emails', { plan_id: planId }])` 调 `emails.list({ plan_id: planId })`
- DataTable 列：收件人（to_email）、主题、状态、发送时间
- 含分页
- 用 Card 包裹，标题"发送日志"
- 计划为 draft 状态时此区域显示空状态提示

**Patterns to follow:**
- 监控页面（如有）的邮件列表展示方式

**Test scenarios:**
- Happy path: running 状态计划显示已发送邮件列表
- Edge case: draft 状态计划无邮件 → 空状态提示
- Happy path: 分页正确翻页

**Verification:**
- 发送日志区展示该计划的邮件记录

### Phase 5: 执行控制

- [ ] **Unit 15: 执行控制按钮栏**

**Goal:** 根据计划状态显示对应操作按钮，调用生命周期 API

**Requirements:** R7

**Dependencies:** Unit 11

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- `ACTION_MAP` 常量定义状态到按钮的映射（see origin: design.md D7）
- 渲染在 PageHeader 右侧或概览区上方
- 每个按钮对应一个 `useMutation`：调 `sendingPlans.start/pause/resume/cancel`
- 操作成功后 `invalidateQueries(['tenant', 'sendingPlans', planId])`，刷新详情页所有数据
- 操作中按钮 disabled

**Patterns to follow:**
- company-detail 中操作按钮的 mutation + invalidate 模式

**Test scenarios:**
- Happy path: draft 状态 → 显示[开始发送]按钮 → 点击 → API 成功 → 状态变为 running → 按钮变为[暂停][取消]
- Happy path: running → [暂停] → paused → [恢复][取消]
- Happy path: completed/cancelled → 不显示操作按钮
- Error path: start 失败（如域名未验证）→ toast.error 显示后端错误

**Verification:**
- 各状态下按钮显隐正确，操作后状态刷新

---

- [ ] **Unit 16: 取消确认弹窗**

**Goal:** 取消操作前弹出 AlertDialog 二次确认

**Requirements:** R7

**Dependencies:** Unit 15

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`

**Approach:**
- 点击取消按钮不直接调 API，先弹出 AlertDialog
- 确认文案："确定取消此发送计划？已发送的邮件不受影响。"
- 确认后调 `cancel` mutation，取消关闭弹窗

**Patterns to follow:**
- `curated-customers/page.tsx` 中删除群组的 AlertDialog 确认模式
- `shared-ui` 的 AlertDialog 组件

**Test scenarios:**
- Happy path: 点取消 → 弹窗出现 → 确认 → 调 API → 状态变 cancelled
- Happy path: 点取消 → 弹窗出现 → 取消（不确认）→ 弹窗关闭，无 API 调用

**Verification:**
- 二次确认流程正确

### Phase 6: 端到端验证

- [ ] **Unit 17: 端到端手动验证**

**Goal:** 完整流程验证：创建 → 查看 → 执行控制

**Requirements:** R1-R10

**Dependencies:** Unit 1-16

**Files:**
- 无新文件

**Approach:**
- 黄金路径：向导创建计划（4 步全填 → 提交）→ 详情页查看（概览+步骤+收件人+日志）→ 开始 → 暂停 → 恢复 → 取消
- 边缘情况：空群组、单步骤、无已验证域名

**Test scenarios:**
- Integration: 完整创建流程 — 填基本信息 → 配 2 个步骤 → 选群组 → 确认 → 提交成功 → 跳转详情页
- Integration: 详情页数据正确 — 概览信息、步骤列表、收件人列表与创建时输入一致
- Integration: 执行控制完整流程 — 开始 → 暂停 → 恢复 → 取消，每步状态和按钮正确变化
- Error path: 后端校验失败 — 如域名未验证，toast 显示后端错误

**Verification:**
- 所有路径无异常

## System-Wide Impact

- **Interaction graph:** 向导提交调 `complete-create`，后端在一个事务内创建 plan + steps + 锁定 recipients + 可选创建 enrollments。执行控制按钮调 lifecycle API（start/pause/resume/cancel），后端涉及域名校验、enrollment 创建、Worker 调度
- **Error propagation:** 前端统一用 `toast.error` 展示后端错误信息。后端 `complete-create` 的校验错误（`_normalize_complete_plan_payload`）返回 422 + 具体字段错误
- **State lifecycle risks:** `lock_recipients` 默认 true 避免空收件人问题；向导提交前有确认步骤减少误操作；取消有二次确认
- **API surface parity:** 后端 3 处 JOIN 只影响已有端点的返回字段（向后兼容扩展），`GET /emails` 新增可选参数（向后兼容）
- **Unchanged invariants:** 列表页 `send-plans/page.tsx` 不变；后端所有现有 API 的请求参数和必填字段不变；数据库 schema 不变

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| 向导是项目中首个多步表单，无先例可复用 | 保持简单实现（useState + 条件渲染），不引入状态库或独立组件 |
| 后端 JOIN 可能影响现有查询性能 | 使用 LEFT JOIN 确保向后兼容；涉及表数据量小（步骤 < 10，收件人 < 500） |
| complete-create 事务内操作多，前端需处理多种后端错误 | 后端已有完善的校验逻辑（`_normalize_complete_plan_payload`），前端统一 toast.error |
| 收件人预览用 groups.listMembers 而非真实 preview API（计划未创建时无法调用） | design.md 已标注此限制，首版可接受 |

## Sources & References

- **Origin document:** [proposal.md](openspec/changes/2026-05-19-send-plans-page/proposal.md), [design.md](openspec/changes/2026-05-19-send-plans-page/design.md), [tasks.md](openspec/changes/2026-05-19-send-plans-page/tasks.md)
- 后端 complete-create: `backend/app/services/tenant_messaging_service.py:355`（`create_complete_sending_plan`）
- 后端校验: `backend/app/services/tenant_messaging_service.py:1659`（`_normalize_complete_plan_payload`）
- 后端生命周期: `backend/app/api/tenant/messaging.py:154-210`
- 前端 API 客户端: `frontend/packages/shared-api/src/tenant/sending-plans.ts`
- 前端详情页: `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`
- 前端新建页: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx`
