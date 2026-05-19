## Tasks

### Phase 0: 前置准备

- [ ] **T0** `shared-api/src/tenant/sending-plans.ts` — 新增 `completeCreate` 方法，对接 `POST /sending-plans/complete-create`
- [x] **T1** ~~确认发送域名 API~~ — 已确认：`GET /domains`（`ops.py:403`），前端客户端 `domains.ts` 已就绪，无需新增

### Phase 0b: 后端微调

- [ ] **T1b** `tenant_messaging_service.py` `list_plan_steps()` — JOIN `email_templates` 返回 `template_name` 字段
- [ ] **T1c** `tenant_messaging_service.py` `list_plan_recipients()` — LEFT JOIN `sequence_enrollments` 返回 `enrollment_status` + `current_step`
- [ ] **T1d** `tenant_messaging_service.py` `list_emails()` + `messaging.py` `GET /emails` — 新增 `plan_id` 可选过滤参数
- [ ] **T1e** 后端测试 — 为 T1b/T1c/T1d 补充 pytest 集成测试

### Phase 1: 新建向导 — 页面骨架

- [ ] **T2** `send-plans/new/page.tsx` — 向导主页面：步骤指示器（四步横排）+ 步骤切换逻辑 + formData 状态管理 + 上一步/下一步/创建按钮
- [ ] **T3** `send-plans/new/step-basic-info.tsx` — Step 1 基本信息表单：名称、描述、发件人名称、发件邮箱、发送域名（Select，加载已验证域名列表）

### Phase 2: 新建向导 — 步骤配置 + 收件人

- [ ] **T4** `send-plans/new/step-configure-steps.tsx` — Step 2 步骤配置：步骤卡片列表 + 模板选择（加载邮件模板列表）+ 延迟天数 + 触发条件 + AI 个性化开关 + 添加/删除步骤 + 自动编号
- [ ] **T5** `send-plans/new/step-recipients.tsx` — Step 3 收件人选择：来源选择（group）+ 群组下拉（加载群组列表）+ 群组成员预览表格 + 锁定收件人勾选框（默认 true）+ 统计摘要

### Phase 3: 新建向导 — 确认 + 提交

- [ ] **T5b** `send-plans/new/step-confirmation.tsx` — Step 4 确认总览：只读展示基本信息 + 步骤配置表格 + 收件人摘要，模板名称从前端已加载列表取
- [ ] **T6** 向导提交逻辑 — 在确认步骤点击"创建计划"调 `completeCreate`，构建完整 payload，成功 toast + 跳转详情页，失败 toast.error

### Phase 4: 详情页改造

- [ ] **T7** `send-plans/[id]/page.tsx` — 概览区改造：DescriptionList 展示完整信息（发件人/邮箱/域名/收件人数/已发送/创建时间/描述）
- [ ] **T8** 步骤摘要区 — 只读 Table 展示步骤列表（步骤号、模板名称、延迟天数、触发条件、AI 个性化），数据源 `listSteps`（已含 template_name）
- [ ] **T9** 收件人列表区 — 只读 DataTable 展示已锁定收件人（公司、邮箱、enrollment 状态、当前步骤），数据源 `listRecipients`（已含 enrollment 数据），含分页
- [ ] **T9b** 发送日志区 — DataTable 展示该计划已发邮件（收件人、主题、状态、发送时间），数据源 `emails.list({ plan_id })`，含分页

### Phase 5: 执行控制

- [ ] **T10** 执行控制按钮栏 — 根据 plan.status 显隐操作按钮（开始/暂停/恢复/取消），调对应 API，操作成功后 invalidate 刷新
- [ ] **T11** 取消确认弹窗 — AlertDialog 二次确认："确定取消此发送计划？已发送的邮件不受影响。"

### Phase 6: 验证

- [ ] **T12** 端到端测试 — 向导创建计划（填基本信息 → 配步骤 → 选收件人 → 确认 → 提交）→ 详情页查看（概览+步骤+收件人+日志）→ 执行控制（开始/暂停/恢复/取消）
