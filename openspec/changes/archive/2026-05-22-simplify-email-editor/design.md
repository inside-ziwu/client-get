## Context

Admin 端有两种模式（visual/html），Tenant 端有三种模式（visual/html/text），两端都依赖 shared-ui 的 GrapesEmailEditor 组件。本次统一简化：两端都替换为 shared-ui 中的 TipTap 富文本编辑器，GrapesJS 完全移除。

当前代码状态：
- `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`：三模式切换、GrapesJS 引用
- `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`：两模式切换、GrapesJS 引用
- `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`：GrapesJS 封装组件
- `frontend/packages/shared-ui/package.json`：grapesjs + grapesjs-preset-newsletter 依赖

## Goals / Non-Goals

**Goals:**
- Admin 和 Tenant 统一使用 TipTap 富文本编辑器
- 编辑器组件放在 shared-ui，两端共享
- 完全移除 GrapesJS 依赖
- 支持基础格式：加粗、斜体、换行、有序/无序列表
- 输出简单 HTML 存 `body_html`，自动提取纯文本存 `body_text`
- 变量插入直接在富文本光标位置完成

**Non-Goals:**
- 不改动后端 API 和渲染逻辑
- 不做数据库 schema 迁移（字段保留，仅做数据清洗）
- 不引入 Markdown 语法
- 不支持图片、表格等复杂格式

## Decisions

### D1: 富文本编辑器选型 — TipTap

**选择 TipTap**，不选 Quill、Slate 或 Lexical。

理由：
- 基于 ProseMirror，架构稳定、扩展性好
- headless 设计，与 shadcn/ui + Tailwind 无缝集成
- 包体积合理（~60KB gzipped vs GrapesJS ~200KB+）

备选方案：Quill（定制 UI 困难）、Slate（太底层）、Lexical（生态不够成熟）

### D2: 组件放置位置 — shared-ui

TipTap 编辑器组件放在 `frontend/packages/shared-ui/src/components/`，替换 `grapes-email-editor.tsx`。

理由：Admin 和 Tenant 都需要邮件编辑器，shared-ui 是唯一正确位置。

### D3: 内容同步策略 — 半受控模式

TipTap 编辑器内部非受控（不将 React state 回写为 `content` prop），但通过 `onUpdate` 回调将 HTML/text 实时同步到 React state。保存时从 state 读取，无需 imperative 调用。

注意：
- 不可将 state 回写为 TipTap `content` prop，否则光标跳动
- 加载新模板内容（openEdit、AI 生成）时，需通过 `key` prop 强制重建编辑器，或调用 `editor.commands.setContent()`
- `onUpdate` 可加 debounce 优化长内容场景

### D4: HTML 输出策略

TipTap `editor.getHTML()` 输出简单 HTML（`<p>`、`<strong>`、`<em>`、`<br>`、`<ul>`/`<ol>`/`<li>`）。

- 保存时：`body_html = editor.getHTML()`，`body_text = editor.getText()`，`body_design = null`
- 后端 `sanitize_html()` 的 ALLOWED_TAGS 已包含所有这些标签
- 后端 `_body_html_fallback` 保留作为安全兜底

### D5: 历史模板数据迁移

线上数据现状（2026-05-22 生产库）：
- 2 个租户，10 个租户模板，2 个平台模板
- **0 个含 body_design** — 无人使用过 GrapesJS 可视化模式
- 4 种 body_html 状态需要分类处理

**一次性数据迁移**（部署前执行），将所有模板 body_html 归一化为 TipTap 可直接加载的 HTML：

| 分类 | 判断条件 | 数量 | 迁移动作 |
|------|---------|------|---------|
| proper_html | body_html 含 `<p>`/`<br>` 等标签 | 4 个 | 不动 |
| raw_text | body_html 有内容但无 HTML 标签 | 4 个 | `\n\n` → `</p><p>`，`\n` → `<br>`，包裹 `<p>`（已被 bleach 转义，不需再 escape） |
| style_only | body_html 仅含 `<style>` | 1 个 | 用 body_text 生成 HTML（需 escape） |
| empty_html | body_html 为空 | 3 个 | 用 body_text 生成 HTML（需 escape） |

迁移同时：
- 所有模板 `body_design` 设为 `NULL`
- `body_text` 为空但 body_html 有内容的模板，从 HTML 提取纯文本补填 body_text

迁移后前端加载逻辑简化为：直接用 body_html 初始化 TipTap，无需运行时分支判断。

### D6: GrapesJS 完全移除

- 删除 `grapes-email-editor.tsx`
- 从 shared-ui 的 `package.json` 移除 grapesjs + grapesjs-preset-newsletter
- 从 shared-ui 的 `index.ts` 移除导出

### D7: Admin 端 body_design — 传 null，依赖迁移清理

数据迁移（D5）在部署前执行，已将所有模板的 `body_design` 清为 NULL。迁移后 Admin 前端保存时传 `body_design = null`（与 Tenant 端一致），不触发 body_design 更新——因为已经是 NULL，无需再清。

好处：`_sanitize_template_content` 中 `body_design is None` 条件为 True，`sanitize_html()` 正常运行，符合安全最佳实践。若传 `{}`，sanitize 会被绕过（虽然 TipTap 输出安全标签无实际风险，但违反最小权限原则）。

### D8: 变量格式 — 统一 `{{name}}`（无空格）

线上约 4 个含变量模板全部使用 `{{name}}`（无空格），后端 `_render_text` 也用 `{{key}}` 替换。Admin 前端 `EMPTY_FORM` 默认值 `{{ contact_name }}` 是唯一的空格格式，需改为 `{{contact_name}}`。

### D9: TipTap Tailwind 样式 — prose class

Tailwind preflight 会 reset ul/ol 的默认样式。TipTap 编辑区域需添加 `prose` class（或手写 list 样式）以保证列表项可见。

### D10: TipTap SSR — immediatelyRender: false

Next.js App Router 下，TipTap `useEditor` 需传 `immediatelyRender: false` 以避免 SSR hydration mismatch。组件已有 `'use client'`，但此参数仍必需。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 历史复杂模板打开后布局丢失 | 线上无复杂布局模板；迁移脚本已将所有数据归一化 |
| 平台模板复制后编辑会丢失复杂布局 | 同上，后续平台模板也应用简单格式创建 |
| TipTap 新增依赖体积 | ~60KB gzipped，比移除的 GrapesJS (~200KB) 小，净减少 |
| getText() 列表无前缀 | 可接受：邮件纯文本不强求列表格式；如需可加 textSerializers |

## Open Questions

（无）
