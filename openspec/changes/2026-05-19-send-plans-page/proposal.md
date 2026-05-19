## Why

发送计划页的后端已完整就绪（计划 CRUD、步骤配置、收件人锁定/预览、生命周期控制、Worker 发送、EngageLab 集成），但前端在 Next.js 迁移后只有骨架：列表页能展示、新建页只创建草稿（名称+描述）、详情页只有只读摘要和收件人表格。

核心交互全部缺失：步骤配置、收件人选择、执行控制（开始/暂停/恢复/取消）。用户无法通过 UI 完成一次完整的邮件发送计划流程。

## What Changes

**后端 API — 微调（3 处 JOIN + 1 处过滤参数）**

核心 API 已就绪，详情页展示需要 3 处微调：
- `GET /sending-plans/{id}/steps`：JOIN `email_templates` 返回模板名称（当前只返回 `template_id`）
- `GET /sending-plans/{id}/recipients`：LEFT JOIN `sequence_enrollments` 返回 `enrollment_status` + `current_step`
- `GET /emails`：新增 `plan_id` 可选过滤参数，支持按计划查看发送日志
- 其余 API 无改动：`complete-create`、生命周期控制、收件人预览

**前端新建页（重写为向导式）**

将 `/send-plans/new` 从单步表单重写为多步向导，调用 `complete-create` API 一次提交：
- Step 1：基本信息（名称、描述、发件人、发送域名）
- Step 2：配置发送步骤（选模板、设延迟天数、触发条件）
- Step 3：选择收件人（收件人来源+预览候选人列表）
- Step 4：确认总览（只读展示全部配置，用户确认后提交）
- 提交：调用 `complete-create`，成功后跳转详情页

**前端详情页（改造为纵向分区+执行控制）**

将 `/send-plans/[id]` 从简单摘要改为纵向分区布局，只读展示+操作按钮：
- 概览区：计划基本信息 + 执行控制按钮（开始/暂停/恢复/取消，按状态显隐）
- 步骤摘要区：只读展示已配置的步骤列表（步骤号、模板名、延迟天数、触发条件）
- 收件人列表区：只读展示已锁定的收件人（公司、邮箱、enrollment 状态、当前步骤）
- 发送日志区：展示该计划已发送邮件的基础记录（收件人、主题、状态、发送时间）

**前端列表页 — 无改动**

现有列表页已满足需求。

## Decisions

### D1: 新建流程 — 向导式 + complete-create

新建页做成多步向导，一次配完所有信息后调用 `complete-create` API 提交。避免用户在多个页面/Tab 间跳转配置。

**否决方案**: 分步创建（先建草稿，再在详情页 Tab 里配步骤和收件人）→ 需要详情页承载复杂编辑 UI，增加页面复杂度。

### D2: 详情页布局 — 纵向分区，不用 Tab

详情页采用纵向分区（与公司详情页风格一致），只读展示+执行控制。因为编辑工作在新建向导中完成，详情页不需要复杂编辑交互，纵向布局足够。

**否决方案**: Tab 切换 → 适合详情页需要承载编辑功能的场景，但本方案详情页以只读为主，Tab 反而增加切换成本。

### D3: 详情页不提供编辑步骤/追加收件人

创建后的计划不支持在详情页编辑步骤或追加收件人。如需调整，用户应取消当前计划并新建。简化交互，降低状态复杂度。

### D4: 执行控制按钮按状态显隐

根据计划状态动态显示可用操作：
- `draft` → [开始]
- `scheduled` → [开始] [取消]
- `running` → [暂停] [取消]
- `paused` → [恢复] [取消]
- `completed` / `cancelled` → 无操作按钮

### D5: 向导中收件人来源

向导 Step 3 的收件人来源对应后端 `recipient_source` 字段，支持 `group`（按群组）、`manual`（手动）、`filter`（按筛选条件）。第一期优先实现 `group` 模式（选择已有客户群组），与优选客户页联动。

## Non-Goals

- 后端只做 3 处 JOIN 微调 + 1 处过滤参数，不改数据库 schema
- 不在详情页提供编辑步骤/追加收件人功能
- 不做邮件模板编辑（模板管理是独立功能）
- 不做 A/B 测试或发送时间优化
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件

## Capabilities

### New Capabilities

- `send-plan-wizard`: 新建向导（基本信息 → 步骤配置 → 收件人选择 → 一键创建）
- `send-plan-execution-control`: 详情页执行控制（开始/暂停/恢复/取消按钮，按状态显隐）

### Modified Capabilities

- `send-plan-detail`: 详情页从简单摘要改造为纵向分区（概览+步骤+收件人+日志）+ 执行控制
- `send-plan-new`（删除重建）: 现有新建页整体替换为向导式

## Impact

| 层 | 影响范围 | 说明 |
|----|---------|------|
| 后端 API | `tenant_messaging_service.py` | listSteps JOIN 模板名、listRecipients JOIN enrollment、list_emails 加 plan_id 过滤 |
| 前端页面 | `send-plans/new/page.tsx` | 从单步表单重写为多步向导 |
| 前端页面 | `send-plans/[id]/page.tsx` | 从简单摘要改造为纵向分区+执行控制 |
| 前端 API 客户端 | `shared-api/src/tenant/sending-plans.ts` | 新增 `completeCreate` 方法（对接 complete-create API） |
| 前端组件 | `send-plans/` 目录下新增组件 | 向导步骤组件、步骤配置器、收件人选择器、执行控制栏 |
| 依赖 | 邮件模板列表 API | 向导 Step 2 选模板需调用 `GET /email-templates` |
| 依赖 | 客户群组 API | 向导 Step 3 按群组选收件人需调用 `GET /groups` |
