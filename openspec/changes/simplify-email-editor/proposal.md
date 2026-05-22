## Why

邮件模板编辑器当前有多种模式（Admin: 可视化/HTML；Tenant: 可视化/HTML/纯文本），增加了用户认知负担和代码复杂度。实际使用中，B2B 外贸邮件以文字内容为主，不需要拖拽式可视化设计，也不应要求用户手写 HTML。Admin 和 Tenant 统一简化为单一富文本编辑器（支持加粗、换行、列表等基础格式），既降低使用门槛，又大幅减少前端代码和依赖。

## What Changes

- **BREAKING** 移除 Admin 端和 Tenant 端邮件模板编辑器的多模式切换，统一替换为单一 TipTap 富文本编辑器
- **BREAKING** 完全移除 GrapesJS 依赖（shared-ui 中的 `grapes-email-editor.tsx` 删除）
- TipTap 编辑器组件放在 shared-ui（`packages/shared-ui`），Admin 和 Tenant 共享
- 富文本编辑器输出简单 HTML 存入 `body_html`，自动提取纯文本存入 `body_text`
- `body_design` 字段不再写入（保存时传 null/空对象）
- 一次性数据迁移：将所有历史模板的 body_html 归一化为 TipTap 可加载的 HTML（裸文本加 `<p>` 标签、空 body_html 从 body_text 生成、清空 body_design）
- 变量插入改为在富文本编辑器光标位置直接插入

## Capabilities

### New Capabilities

- `richtext-email-editor`: 基于 TipTap 的富文本邮件编辑器（shared-ui 共享组件），支持加粗、斜体、换行、有序/无序列表、变量插入。Admin 和 Tenant 共用。

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 影响范围 | 详情 |
|---------|------|
| 前端 shared-ui | 删除 `grapes-email-editor.tsx`；新增 TipTap 富文本编辑器组件；移除 grapesjs 依赖 |
| 前端 Tenant | `templates/page.tsx` 重写编辑器区域；移除 editorMode 状态和三模式切换 |
| 前端 Admin | `email-templates/client-page.tsx` 重写编辑器区域；移除 visual/html 模式切换 |
| 前端依赖 | shared-ui 新增 `@tiptap/react`、`@tiptap/starter-kit` 等；移除 `grapesjs`、`grapesjs-preset-newsletter` |
| 后端 API | 无变更 |
| 数据库 | 无 schema 变更；一次性数据迁移归一化 body_html、清空 body_design |
| 历史数据 | 迁移脚本处理 4 种场景：正常 HTML 不动、裸文本加标签、style-only/空 HTML 从 body_text 生成 |

## Non-Goals

- 不改动后端保存/渲染/发送逻辑
- 不做数据库 schema 迁移（`body_design` 字段保留，仅清洗数据）
- 不引入 Markdown 语法——用户直接操作富文本工具栏
- 不支持图片、表格等复杂格式
