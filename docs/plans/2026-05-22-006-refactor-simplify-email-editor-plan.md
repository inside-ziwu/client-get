---
title: 简化邮件模板编辑器（GrapesJS → TipTap）
type: refactor
status: active
date: 2026-05-22
origin: openspec/changes/simplify-email-editor/
execution_posture: tdd
---

# 简化邮件模板编辑器（GrapesJS → TipTap）

## Summary

将 Admin 和 Tenant 的邮件模板编辑器从 GrapesJS 多模式切换（可视化/HTML/纯文本）替换为 shared-ui 中的单一 TipTap 富文本编辑器。同时通过一次性数据迁移脚本将 12 条生产模板的 body_html 归一化为 TipTap 可直接加载的 HTML，完全移除 GrapesJS 依赖。采用 TDD 执行姿态，每个实施单元 2-5 分钟。

---

## Problem Frame

邮件模板编辑器有多种模式（Admin: 可视化/HTML；Tenant: 可视化/HTML/纯文本），增加用户认知负担和代码复杂度。实际使用中 B2B 外贸邮件以文字为主，不需要拖拽式可视化设计。线上 0 个模板使用过 GrapesJS 可视化模式（body_design 全为 NULL）。GrapesJS 包体积 ~200KB gzipped，远大于实际需求。

---

## Requirements

- R1. Admin 端和 Tenant 端统一使用 shared-ui 的 TipTap 富文本编辑器，移除多模式切换
- R2. 编辑器支持加粗、斜体、换行、有序/无序列表
- R3. 保存时输出 body_html + body_text，body_design 传 null
- R4. 变量点击在光标位置插入（未聚焦时插入末尾）
- R5. 历史模板通过数据迁移归一化，TipTap 可直接加载
- R6. 完全移除 GrapesJS 及相关依赖

---

## Scope Boundaries

- 不改动后端 API 和渲染逻辑
- 不做数据库 schema 迁移（body_design 字段保留，仅清洗数据）
- 不引入 Markdown 语法
- 不支持图片、表格等复杂格式
- 不改动邮件发送通道

---

## Context & Research

### Relevant Code and Patterns

- `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx` — 当前 GrapesJS 封装，forwardRef + useImperativeHandle 模式（将被替换）
- `frontend/packages/shared-ui/src/index.ts` — 所有组件通过 `export * from './components/xxx'` 导出
- `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`（569 行）— 三模式编辑器，GrapesJS visual + HTML textarea + text textarea
- `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`（353 行）— 两模式编辑器，GrapesJS visual + HTML textarea
- `frontend/apps/tenant/vitest.config.ts` — Vitest 4.1 + jsdom + @testing-library/react，别名 `@shared/ui` 指向源码
- `frontend/apps/tenant/test/login-page.test.tsx` — 测试模式参考：vi.mock + render + screen 断言
- `backend/scripts/backfill_tendata_raw_contacts.py` — Python 迁移脚本模式参考

### Institutional Learnings

无直接相关 learnings。邮件模板编辑器是新领域。

---

## Key Technical Decisions

- **D1 TipTap 选型**：headless ProseMirror 封装，~60KB gzipped，与 shadcn/Tailwind 无缝集成（see origin: design.md D1）
- **D2 组件位置**：shared-ui，Admin 和 Tenant 共享（see origin: design.md D2）
- **D3 半受控模式**：TipTap 内部非受控，通过 onUpdate 回调同步 HTML/text 到 React state；不将 state 回写为 content prop（避免光标跳动）；保存时从 state 读取，无需 imperative 调用（see origin: design.md D3）
- **D4 body_design = null**：迁移已清空所有 body_design，前端传 null 让 sanitize_html() 正常运行（see origin: design.md D7）
- **D5 数据迁移 4 分类**：proper_html 不动、raw_text 转段落（不二次 escape）、style_only/empty_html 从 body_text 生成（需 escape）（see origin: design.md D5）
- **D6 SSR 兼容**：useEditor 传 `immediatelyRender: false`（see origin: design.md D10）
- **D7 Tailwind reset**：编辑区域加 prose class 保证列表样式可见（see origin: design.md D9）
- **D8 变量格式**：统一 `{{name}}`（无空格），修复 Admin EMPTY_FORM 的 `{{ contact_name }}`（see origin: design.md D8）

---

## Open Questions

### Resolved During Planning

- **TipTap 在 jsdom 中是否可测试**：ProseMirror 依赖 contenteditable，jsdom 部分支持。组件渲染测试可行，交互测试需浏览器验证。计划在 tenant/test/ 写基础渲染测试，编辑器交互通过 dev server 手动 QA。

### Deferred to Implementation

- **onUpdate debounce 频率**：长内容场景可能需要 debounce，具体阈值需运行时验证
- **key prop 更新策略**：editingId 变化 vs 递增计数器，取决于实际组件生命周期行为

---

## Implementation Units

### U1. 迁移脚本辅助函数 + 测试

**Goal:** 实现 body_html 分类和转换的纯函数，通过 pytest TDD 驱动

**Requirements:** R5

**Dependencies:** None

**Files:**
- Create: `backend/scripts/migrate_email_templates_html.py`
- Create: `backend/tests/test_migrate_email_templates.py`

**Approach:**
- 提取 4 个纯函数：`classify_html(body_html)`、`raw_text_to_html(text)`、`plain_text_to_html(text)`、`text_from_html(html)`
- classify_html 返回枚举：proper_html / raw_text / style_only / empty_html
- raw_text_to_html 不做 escape（已被 bleach 转义），仅做换行→段落/br 转换
- plain_text_to_html 先 html.escape() 再转换（用于 style_only / empty_html 分类，从 body_text 生成）
- text_from_html 用正则或 html 库提取纯文本（补填空 body_text）

**Execution note:** TDD — 先写 pytest 测试覆盖所有分类和转换场景，再实现函数。

**Patterns to follow:**
- `backend/tests/test_engagelab_adapter.py` — pytest 测试结构参考

**Test scenarios:**
- Happy path: classify_html 对含 `<p>` 标签的 HTML 返回 proper_html
- Happy path: classify_html 对纯文本（无 HTML 标签）返回 raw_text
- Happy path: classify_html 对仅含 `<style>` 的 HTML 返回 style_only
- Happy path: classify_html 对空字符串返回 empty_html
- Happy path: raw_text_to_html 将 `\n\n` 转为段落分隔，`\n` 转为 `<br>`
- Edge case: raw_text_to_html 保留已有的 `&amp;` 不做二次 escape
- Happy path: plain_text_to_html 将 `<script>` 转为 `&lt;script&gt;`
- Happy path: text_from_html 从 `<p>你好 <strong>张三</strong></p>` 提取 `你好 张三`
- Edge case: text_from_html 对空 HTML 返回空字符串

**Verification:**
- `pytest backend/tests/test_migrate_email_templates.py` 全部通过

---

### U2. 迁移脚本主逻辑

**Goal:** 实现连接数据库、遍历两张表、分类处理、--dry-run 的完整迁移脚本

**Requirements:** R5

**Dependencies:** U1

**Files:**
- Modify: `backend/scripts/migrate_email_templates_html.py`

**Approach:**
- argparse 接收 `--db-url` 和 `--dry-run` 参数
- 使用 psycopg 连接数据库（项目已有 psycopg 依赖）
- 遍历 `email_templates` 和 `platform_email_templates` 两张表
- 对每条记录：classify → 按分类转换 body_html → 补填空 body_text → body_design 设 NULL
- dry-run 模式打印变更计划不写库，正式模式用事务批量更新
- 输出统计：各分类数量、body_text 补填数量、body_design 清空数量

**Patterns to follow:**
- `backend/scripts/backfill_tendata_raw_contacts.py` — DB 连接和 argparse 模式

**Test scenarios:**
- Test expectation: none — 主逻辑依赖数据库连接，通过 --dry-run + 本地库手动验证

**Verification:**
- `python backend/scripts/migrate_email_templates_html.py --db-url "postgresql://postgres:postgres@localhost:5432/clientget" --dry-run` 输出合理的变更计划

---

### U3. 安装 TipTap 依赖 + 移除 GrapesJS 依赖

**Goal:** 更新 shared-ui 的 package.json，安装 TipTap 并移除 GrapesJS

**Requirements:** R1, R6

**Dependencies:** None

**Files:**
- Modify: `frontend/packages/shared-ui/package.json`

**Approach:**
- `pnpm add @tiptap/react @tiptap/pm @tiptap/starter-kit @tiptap/extension-placeholder --filter shared-ui`
- `pnpm remove grapesjs grapesjs-preset-newsletter --filter shared-ui`
- 运行 `pnpm install` 验证依赖树无冲突

**Test scenarios:**
- Test expectation: none — 依赖变更，通过 pnpm install 成功验证

**Verification:**
- `pnpm install` 成功无报错
- shared-ui package.json 不再包含 grapesjs

---

### U4. 删除 GrapesJS 组件 + 更新导出

**Goal:** 移除 GrapesJS 封装组件和相关类型声明，清理 shared-ui 导出

**Requirements:** R6

**Dependencies:** U3

**Files:**
- Delete: `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`
- Delete: `frontend/apps/admin/src/grapesjs-preset-newsletter.d.ts`
- Modify: `frontend/packages/shared-ui/src/index.ts`

**Approach:**
- 删除 grapes-email-editor.tsx
- 删除 admin 的 grapesjs-preset-newsletter.d.ts 类型声明
- 从 index.ts 移除 `export * from './components/grapes-email-editor'`
- 暂不添加新导出（U7 添加）

**Test scenarios:**
- Test expectation: none — 文件删除，通过 grep 确认无残留引用

**Verification:**
- `grep -r "grapes-email-editor" frontend/packages/shared-ui/src/` 无匹配
- `ls frontend/apps/admin/src/grapesjs-preset-newsletter.d.ts` 不存在

---

### U5. EmailRichEditor 骨架 + onUpdate 回调

**Goal:** 创建 TipTap 富文本编辑器基础组件，实现半受控模式的 onUpdate 数据同步

**Requirements:** R1, R2, R3

**Dependencies:** U3

**Files:**
- Create: `frontend/packages/shared-ui/src/components/email-rich-editor.tsx`
- Create: `frontend/apps/tenant/test/email-rich-editor.test.tsx`

**Approach:**
- `'use client'` 指令
- Props 接口：`{ initialContent?: string; placeholder?: string; onUpdate?: (html: string, text: string) => void }`
- useEditor 配置：StarterKit（含 Bold/Italic/BulletList/OrderedList/ListItem）+ Placeholder 扩展
- `immediatelyRender: false`（D6 SSR 兼容）
- onUpdate 回调在编辑器内容变化时触发，传递 editor.getHTML() 和 editor.getText()
- 编辑区域 `className="prose"` 处理 Tailwind reset（D7）

**Execution note:** TDD — 先写渲染测试（组件挂载不崩溃），再实现组件。

**Patterns to follow:**
- `frontend/apps/tenant/test/login-page.test.tsx` — vitest + testing-library 测试模式

**Test scenarios:**
- Happy path: 组件渲染不崩溃（render 无异常）
- Happy path: 传入 initialContent 后编辑区域包含对应内容（若 jsdom 支持）
- Edge case: initialContent 为空时渲染 placeholder 文本

**Verification:**
- `cd frontend/apps/tenant && pnpm vitest run test/email-rich-editor.test.tsx` 通过

---

### U6. EmailRichEditor 工具栏

**Goal:** 添加加粗、斜体、有序列表、无序列表工具栏按钮

**Requirements:** R2

**Dependencies:** U5

**Files:**
- Modify: `frontend/packages/shared-ui/src/components/email-rich-editor.tsx`

**Approach:**
- 编辑器上方渲染工具栏 div，4 个 shadcn Button（variant="ghost" size="sm"）
- 每个按钮调用对应 TipTap command：toggleBold / toggleItalic / toggleOrderedList / toggleBulletList
- 按钮 active 状态通过 editor.isActive() 反映当前光标格式
- 按钮图标可用文字标签（B / I / OL / UL）或 lucide-react 图标

**Patterns to follow:**
- shared-ui 其他组件的 shadcn Button 使用方式

**Test scenarios:**
- Happy path: 工具栏渲染 4 个按钮（通过 test role="button" 查询）

**Verification:**
- dev server 中编辑器上方显示工具栏，点击按钮可切换格式

---

### U7. EmailRichEditor insertVariable + 更新导出

**Goal:** 通过 forwardRef + useImperativeHandle 暴露 insertVariable 方法，更新 shared-ui 导出

**Requirements:** R4

**Dependencies:** U5, U6

**Files:**
- Modify: `frontend/packages/shared-ui/src/components/email-rich-editor.tsx`
- Modify: `frontend/packages/shared-ui/src/index.ts`

**Approach:**
- 定义 `EmailRichEditorHandle` 接口：`{ insertVariable(text: string): void }`
- forwardRef 包裹组件，useImperativeHandle 暴露 insertVariable
- insertVariable 实现：检查 editor.isFocused，未聚焦时先 editor.commands.focus('end')，然后 editor.commands.insertContent(text)
- index.ts 添加 `export * from './components/email-rich-editor'`

**Patterns to follow:**
- `grapes-email-editor.tsx` 的 forwardRef + useImperativeHandle 模式（已删除但可参考 git history）

**Test scenarios:**
- Happy path: ref 上存在 insertVariable 方法（typeof ref.current.insertVariable === 'function'）

**Verification:**
- index.ts 导出 EmailRichEditor 和 EmailRichEditorHandle
- TypeScript 编译无错误

---

### U8. Tenant 类型 + state 清理

**Goal:** 清除 Tenant templates/page.tsx 中所有 GrapesJS 相关的类型、state 和辅助函数

**Requirements:** R1, R6

**Dependencies:** U7

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**Approach:**
- TemplateForm 类型：移除 `body_design: unknown` 字段
- EMPTY_FORM：移除 `body_design: null`
- 移除 imports：GrapesEmailEditor, GrapesEmailEditorHandle, Tabs, TabsContent, TabsList, TabsTrigger, Textarea（编辑器用的）
- 添加 imports：EmailRichEditor, EmailRichEditorHandle
- 移除 state：`editorMode`、`htmlTextareaRef`、`textTextareaRef`
- 移除函数：`insertAtCursor`、`handleEditorModeChange`
- editorRef 类型从 `GrapesEmailEditorHandle` 改为 `EmailRichEditorHandle`
- 添加 state：`editorKey`（用于 key prop 强制重建）和 `bodyHtml`/`bodyText`（onUpdate 同步目标）

**Test scenarios:**
- Test expectation: none — 类型/state 清理是纯重构，通过 TypeScript 编译验证

**Verification:**
- TypeScript 无 body_design 相关类型错误
- 无 GrapesJS 相关 import

---

### U9. Tenant 编辑器区域替换

**Goal:** 将 Tabs + GrapesJS/Textarea 三模式编辑器替换为单一 TipTap 编辑器

**Requirements:** R1, R3

**Dependencies:** U8

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**Approach:**
- 删除整个 Tabs 区域（line 462-487 区域）
- 替换为 `<EmailRichEditor ref={editorRef} key={editorKey} initialContent={form.body_html} onUpdate={(html, text) => { setBodyHtml(html); setBodyText(text); }} />`
- key prop 使用 editorKey state，切换模板时更新以强制重建

**Test scenarios:**
- Integration: 编辑器渲染无模式切换 Tab
- Happy path: 传入 body_html 后编辑器显示内容

**Verification:**
- dev server Tenant 端打开模板编辑抽屉，看到 TipTap 编辑器，无 Tab 切换

---

### U10. Tenant 保存逻辑 + 变量插入 + 其他简化

**Goal:** 重写 saveTemplate、handleVariableClick、openEdit/openCreate/submitAiGenerate

**Requirements:** R3, R4

**Dependencies:** U9

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**Approach:**
- **saveTemplate 重写**：body_html 和 body_text 直接从 bodyHtml/bodyText state 读取（onUpdate 已同步），body_design 不再传递（或传 null），移除所有 editorMode 分支
- **handleVariableClick 简化**：统一调用 `editorRef.current?.insertVariable(\`{{${name}}}\`)`，移除 editorMode 分支和 clipboard fallback
- **openEdit 简化**：加载模板后设置 form（不含 body_design），递增 editorKey 触发编辑器重建，不再设置 editorMode
- **openCreate 简化**：重置 form 为 EMPTY_FORM，递增 editorKey
- **submitAiGenerate 简化**：AI 生成后设置 form，递增 editorKey 重载编辑器内容，不再设置 editorMode
- 清理所有未使用的 import（Tabs 相关、Textarea 可能仍用于其他地方——检查后决定）

**Test scenarios:**
- Happy path: 保存时 payload 包含 body_html 且不含 body_design
- Happy path: 变量 Badge 点击后变量插入到编辑器
- Integration: AI 生成后编辑器内容更新

**Verification:**
- dev server 保存模板成功，network tab 中 payload 无 body_design
- 点击变量 Badge 在编辑器中插入变量文本

---

### U11. Admin 类型 + state 清理 + EMPTY_FORM 修复

**Goal:** 清除 Admin client-page.tsx 中 GrapesJS 相关代码，修复变量格式

**Requirements:** R1, R6, R3

**Dependencies:** U7

**Files:**
- Modify: `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`

**Approach:**
- TemplateForm 类型：移除 `body_design?: unknown` 字段
- EMPTY_FORM：移除 `body_design: undefined`，修复 `{{ contact_name }}` → `{{contact_name}}`（D8）
- 移除 imports：GrapesEmailEditor, GrapesEmailEditorHandle, Tabs 相关, Code2, FileText 图标
- 添加 imports：EmailRichEditor, EmailRichEditorHandle
- 移除 state：`mode`
- editorRef 类型改为 EmailRichEditorHandle
- templateToForm：移除 body_design 赋值
- 添加 state：`bodyHtml`/`bodyText`（onUpdate 同步目标）

**Test scenarios:**
- Test expectation: none — 类型/state 清理，通过 TypeScript 编译验证

**Verification:**
- TypeScript 编译无错误
- EMPTY_FORM 中变量格式为 `{{contact_name}}`

---

### U12. Admin 编辑器替换 + 保存逻辑

**Goal:** 替换 Admin 的 Tabs+GrapesJS 编辑器为 TipTap，重写保存逻辑

**Requirements:** R1, R3

**Dependencies:** U11

**Files:**
- Modify: `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`

**Approach:**
- 删除 Tabs 区域（line 302-328），替换为 EmailRichEditor
- Wire onUpdate 同步到 bodyHtml/bodyText state
- **save 函数重写**：body_html 从 bodyHtml state 读取，移除 mode 分支，不传 body_design（或传 null）
- **openEdit**：加载模板后不再设置 mode（无需区分 visual/html）
- **SheetDescription** 文案更新：移除"可视化模式会保存 GrapesJS body_design"的描述
- 清理未使用的 import

**Test scenarios:**
- Happy path: 保存时 payload 不含 body_design
- Happy path: 编辑器渲染无模式切换 Tab

**Verification:**
- dev server Admin 端编辑模板，编辑器无 Tab 切换
- 保存模板成功，network tab 中 payload 无 body_design

---

### U13. 构建验证 + 最终清理

**Goal:** 确保两端构建成功，清理所有残留引用

**Requirements:** R6

**Dependencies:** U10, U12

**Files:**
- Verify: `frontend/apps/tenant/`
- Verify: `frontend/apps/admin/`
- Verify: `frontend/packages/shared-ui/`

**Approach:**
- `grep -r "grapesjs\|GrapesJS\|grapes-email-editor\|GrapesEmailEditor" frontend/ --include="*.ts" --include="*.tsx" | grep -v node_modules` 确认无残留
- `grep -r "editorMode\|editor_mode" frontend/ --include="*.ts" --include="*.tsx" | grep -v node_modules` 确认无残留
- 运行 TypeScript 编译检查
- Tenant 和 Admin dev server 启动无错误

**Test scenarios:**
- Happy path: grep 无 GrapesJS 残留引用
- Happy path: TypeScript 编译通过
- Integration: 两端 dev server 启动成功

**Verification:**
- `pnpm -r build` 或 `tsc --noEmit` 无错误
- 两端 dev server 正常运行
- 模板创建、编辑、保存、预览全流程正常

---

## System-Wide Impact

- **Interaction graph:** EmailRichEditor 通过 onUpdate 回调同步到父组件 state → 保存时从 state 读取发送 API。变量 Badge onClick → editorRef.insertVariable()。后端 API 和渲染逻辑不变。
- **Error propagation:** TipTap 编辑器加载失败只影响编辑区域，不阻塞页面其他功能。保存逻辑的错误处理沿用现有 try-catch + toast 模式。
- **State lifecycle risks:** key prop 强制重建编辑器时，未保存的编辑内容会丢失。这是现有行为（切换模板时即重置表单），不引入新风险。
- **API surface parity:** Tenant 和 Admin 都使用相同的 EmailRichEditor 组件和 onUpdate 模式，保持一致。
- **Unchanged invariants:** 后端 create/update/preview/send API 完全不变。sanitize_html() 在 body_design=null 时正常运行（D4）。邮件渲染逻辑 _render_text 不受影响。

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| TipTap 在 jsdom 中测试受限 | 基础渲染测试可行，编辑器交互通过 dev server 手动 QA |
| 历史模板 body_html 含非 TipTap 标签 | 生产数据已验证：0 个复杂模板，迁移脚本覆盖全部 4 种分类 |
| key prop 重建导致编辑内容丢失 | 仅在切换模板/AI 生成时触发，用户预期此时内容会更新 |
| getText() 列表无前缀 | 可接受：邮件纯文本不强求列表格式 |

---

## Documentation / Operational Notes

- 部署顺序：先执行数据迁移脚本（U2 --dry-run 确认后正式运行），再部署前端镜像
- 迁移脚本需要生产库连接权限，由用户手动触发
- 构建和推送镜像由用户显式触发（AGENTS.md §7）

---

## Sources & References

- **Origin document:** [openspec/changes/simplify-email-editor/](openspec/changes/simplify-email-editor/)
- **Design decisions:** [design.md](openspec/changes/simplify-email-editor/design.md)（D1-D10）
- **Task breakdown:** [tasks.md](openspec/changes/simplify-email-editor/tasks.md)
- **Spec:** [specs/richtext-email-editor/spec.md](openspec/changes/simplify-email-editor/specs/richtext-email-editor/spec.md)
- **Engineering review:** /plan-eng-review 通过（4 个问题已修复：.d.ts 删除、D8 数字修正、body_design=null、移除 getHtml/getText）
