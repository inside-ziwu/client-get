## Why

邮件模板编辑器存在三个影响用户体验和功能正确性的问题：
1. 前端展示了 5 个模板变量，但后端实际只渲染 3 个，导致用户使用 `product_name` / `contact_email` 后发出的邮件包含未替换的原始占位符
2. 变量只能"点击复制"再手动粘贴，交互效率低
3. 纯文本模式编辑的内容存入 `body_text`，但 `body_html` 为空时邮件客户端优先渲染空 HTML，导致收件人看到空邮件

这些问题在日常使用中已被验证复现，需要立即修复。

## What Changes

- **移除不可用变量**：从前端变量列表移除 `product_name`（无数据源）；将 `contact_email` 补入后端渲染映射（数据已存在于查询结果中）
- **统一预览/发送映射**：`sample_emails`（预览路径）和 `claim_due_emails`（发送路径）使用相同的 4 变量映射，修复预览中 `sender_name` 缺失的隐藏 bug
- **变量插入交互**：变量 Badge 从"复制到剪贴板"改为"插入到当前编辑器光标位置"，支持 HTML textarea、纯文本 textarea 和 GrapesJS 可视化编辑器三种模式
- **纯文本 fallback**：后端发送逻辑增加兜底——当原始模板 `body_html` 为空时，先对 `body_text` 做 HTML escape，再转为简单 HTML 作为 `body_html`
- **变量合同 API**：后端定义 `TEMPLATE_VARIABLES` 常量并通过 API 暴露，前端从 API 获取变量列表，消除前后端硬编码不一致的根因

## Non-Goals

- 不重构模板编辑器的整体架构或切换编辑器组件
- 不新增变量类型（如自定义变量）
- 不修改邮件发送通道（EngageLab）的集成逻辑
- 不变更数据库 schema

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

（无现有 spec 需修改——当前 openspec/specs/ 中不包含邮件模板相关 spec）

## Impact

| 区域 | 影响 |
|------|------|
| 前端 `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx` | 变量列表修改、插入逻辑重写 |
| 后端 `backend/app/services/tenant_messaging_service.py` | `claim_due_emails` 渲染映射补充 `contact_email`；增加 `body_text → body_html` fallback |
| API `backend/app/api/tenant/messaging.py` | 新增变量列表 endpoint |
| 前端 API 层 `frontend/packages/shared-api/src/tenant/email-templates.ts` | 新增 `getVariables()` 方法 |
| 共享 UI `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx` | GrapesEmailEditorHandle 新增 `insertVariable()` 方法 |
| 数据库 | 无变更 |
| 依赖顺序 | 后端先改（渲染映射 + fallback）→ 前端再改（变量列表 + 插入交互） |
