## 1. 后端：建立变量合同 + 修复渲染映射 + 纯文本 fallback

- [ ] 1.1 在 `TenantMessagingService` 中定义 `TEMPLATE_VARIABLES` 常量
  - 包含 4 个变量：`company_name`（公司名称）、`contact_name`（联系人姓名）、`contact_email`（联系人邮箱）、`sender_name`（发件人姓名）
  - 文件：`backend/app/services/tenant_messaging_service.py`
- [ ] 1.2 统一 `claim_due_emails`（发送路径）和 `sample_emails`（预览路径）的变量映射
  - `claim_due_emails`（约 1428 行）：在 `_render_text()` 的 mapping 中加入 `contact_email`（取自 `to_email` 字段），共 4 个变量，`body_html`、`body_text`、`subject` 三处同步
  - `sample_emails`（约 1098 行）：构建显式 mapping dict 传给 `_render_text`，包含 `sender_name`（从 plan 配置获取），不再传整个 recipient dict
  - 文件：`backend/app/services/tenant_messaging_service.py`
- [ ] 1.3 在 `claim_due_emails` 的 `_render_text()` 调用**之前**，增加 fallback 逻辑
  - 检查原始 `row["body_html"]`（模板原文），若为空或仅含空白
  - 对 `row["body_text"]` 做 `html.escape()` 转义特殊字符
  - 将换行转 `<br>`，包裹 `<p>` 标签
  - 赋值为 `body_html`，然后正常走渲染流程
  - 文件：`backend/app/services/tenant_messaging_service.py`

## 2. 后端：新增变量列表 API

- [ ] 2.1 新增 endpoint `GET /t/{slug}/api/v1/email-templates/variables`，返回 `TEMPLATE_VARIABLES` 列表
  - 文件：`backend/app/api/tenant/messaging.py`

## 3. 后端：单元测试

- [ ] 3.1 测试变量映射正确性：模板中包含 4 个变量占位符时全部被正确替换
- [ ] 3.2 测试 fallback 逻辑：原始 body_html 为空时，body_text 被转为 HTML（含 html.escape 验证）；body_html 非空时不触发 fallback
  - 文件：`backend/tests/test_email_template_rendering.py`（新建）

## 4. 前端：消费变量 API + 移除硬编码

- [ ] 4.1 在 shared-api 中新增 `getVariables()` 方法
  - 文件：`frontend/packages/shared-api/src/tenant/email-templates.ts`
- [ ] 4.2 删除 `page.tsx` 中硬编码的 `VARIABLES` 数组（第 49-55 行），改为从 API 获取（React Query 缓存）
  - 文件：`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

## 5. 前端：变量插入交互改造

- [ ] 5.1 在 `GrapesEmailEditorHandle` 接口新增 `insertVariable(text: string): boolean` 方法
  - 实现：获取 selected component → 检查 RTE 是否激活 → 插入文本 → 成功返回 true，未激活返回 false
  - 文件：`frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`
- [ ] 5.2 为 HTML textarea 和纯文本 textarea 实现"插入到光标位置"功能
  - 获取 `selectionStart`/`selectionEnd`，在光标处插入变量文本，更新 React state 并恢复光标位置
  - 文件：`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`
- [ ] 5.3 修改变量 Badge 的 `onClick`，根据当前 `editorMode` 分发到对应的插入逻辑
  - 可视化模式：调用 `editorRef.current?.insertVariable()`，返回 false 时 fallback 为复制 + toast
  - HTML/纯文本模式：调用 textarea 插入函数
  - 文件：`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`
- [ ] 5.4 更新变量区域的 Label 文案，从"变量（点击复制）"改为"变量（点击插入）"

## 6. 验证

- [ ] 6.1 后端：运行 pytest 确认新增测试通过
- [ ] 6.2 前端：启动 dev server，验证变量列表从 API 获取且正确显示 4 个变量
- [ ] 6.3 前端：HTML 模式下点击变量 Badge → 变量插入到 textarea 光标位置；纯文本模式同理
- [ ] 6.4 前端：可视化模式下，编辑文本组件时点击变量 → 插入到 RTE 光标位置；未选中组件时 → toast 提示 + 复制到剪贴板
- [ ] 6.5 端到端：创建纯文本模板 → 预览 → 确认内容不为空
