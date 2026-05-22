## 0. 数据迁移（部署前执行）

- [ ] 0.1 创建迁移脚本 `backend/scripts/migrate_email_templates_html.py`：
  - 连接生产库，遍历 `email_templates` 和 `platform_email_templates`
  - 分类处理 body_html：proper_html 不动；raw_text 做 `\n\n` → 段落 + `\n` → `<br>` + `<p>` 包裹；style_only/empty_html 从 body_text 生成（先 escape）
  - body_text 为空但 body_html 有内容的，从 HTML 提取纯文本补填
  - `body_design` 统一设为 NULL
  - 支持 `--dry-run` 模式（只输出变更，不写库）
- [ ] 0.2 本地测试：用测试数据库验证 4 种分类的迁移结果
- [ ] 0.3 生产执行：先 `--dry-run` 确认，再正式执行，记录变更行数

## 1. 依赖变更

- [ ] 1.1 在 `frontend/packages/shared-ui/` 安装 TipTap 依赖：`@tiptap/react`、`@tiptap/pm`、`@tiptap/starter-kit`、`@tiptap/extension-placeholder`
- [ ] 1.2 从 `frontend/packages/shared-ui/` 移除 `grapesjs`、`grapesjs-preset-newsletter` 依赖
- [ ] 1.3 验证 `pnpm install` 成功，两端 dev server 正常启动

## 2. shared-ui 编辑器组件

- [ ] 2.1 删除 `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`
- [ ] 2.2 创建 `frontend/packages/shared-ui/src/components/email-rich-editor.tsx`：封装 TipTap 编辑器，通过 `onUpdate` 回调同步 HTML/text 到父组件（D3: 半受控模式），通过 `forwardRef` + `useImperativeHandle` 仅暴露 `insertVariable(text)` 方法
  - `useEditor` 传 `immediatelyRender: false`（D10: 避免 Next.js SSR hydration mismatch）
  - `insertVariable` 未聚焦时先 `editor.commands.focus('end')` 再插入
- [ ] 2.3 编辑器工具栏：加粗、斜体、有序列表、无序列表按钮（使用 shadcn Button 样式）
- [ ] 2.4 编辑器内部非受控，通过 `onUpdate` 回调同步 HTML/text 到父组件；不将 state 回写为 `content` prop（D3: 避免光标跳动）
- [ ] 2.5 编辑区域添加 `prose` class 或手写 list 样式（D9: Tailwind preflight reset 问题）
- [ ] 2.6 更新 `frontend/packages/shared-ui/src/index.ts`：移除 grapes-email-editor 导出，新增 email-rich-editor 导出

## 3. Tenant 端模板编辑页面重写

- [ ] 3.1 移除 `templates/page.tsx` 中的 GrapesJS 导入，替换为 EmailRichEditor
- [ ] 3.2 移除 `editorMode` 状态和三模式切换 Tabs（visual/html/text）
- [ ] 3.3 移除 `htmlTextareaRef`、`textTextareaRef` 及 `insertAtCursor` 函数
- [ ] 3.4 替换编辑区域为 TipTap 编辑器组件，传入 `form.body_html` 作为初始内容（迁移后 body_html 已归一化）；切换模板时通过 `key` prop 强制重建编辑器
- [ ] 3.5 重写 `saveTemplate`：`body_html` 和 `body_text` 从受控 state 读取，`body_design = null`
- [ ] 3.6 简化 `handleVariableClick`：统一调用 `editor.insertVariable(placeholder)`
- [ ] 3.7 简化 `openEdit`/`openCreate`/`submitAiGenerate`：移除 editorMode 相关逻辑；AI 生成后更新 `key` 以重载编辑器内容
- [ ] 3.8 更新 `TemplateForm` 类型：移除 `body_design` 字段
- [ ] 3.9 清理未使用的 import

## 4. Admin 端模板编辑页面重写

- [ ] 4.1 移除 `client-page.tsx` 中的 GrapesJS 导入，替换为 EmailRichEditor
- [ ] 4.2 移除 `mode` 状态和 visual/html 模式切换 Tabs
- [ ] 4.3 替换编辑区域为 TipTap 编辑器组件
- [ ] 4.4 重写保存逻辑：`body_html` 从受控 state 读取，`body_design = null`（D7: 迁移已清空历史 design，null 让 sanitize_html 正常运行）
- [ ] 4.5 修复 `EMPTY_FORM` 默认模板：`{{ contact_name }}` → `{{contact_name}}`（D8: 统一无空格格式）
- [ ] 4.6 更新 `TemplateForm` 类型：移除 `body_design` 字段
- [ ] 4.7 清理未使用的 import；删除 `frontend/apps/admin/src/grapesjs-preset-newsletter.d.ts` 类型声明文件

## 5. 验证

- [ ] 5.1 Tenant 端：新建模板 → 富文本编辑器正常显示，工具栏可用
- [ ] 5.2 Tenant 端：输入加粗文本 → 保存 → 重新打开 → 格式保留
- [ ] 5.3 Tenant 端：点击变量 Badge → 变量在光标位置插入
- [ ] 5.4 Tenant 端：AI 生成模板 → 生成结果加载到富文本编辑器
- [ ] 5.5 Admin 端：新建/编辑平台模板 → 富文本编辑器正常工作
- [ ] 5.6 打开已有历史模板 → 内容正常显示（迁移后的 HTML）
- [ ] 5.7 Admin 端：保存已有模板 → body_design 被清空
- [ ] 5.8 构建 Tenant + Admin 前端镜像并推送 ACR
- [ ] 5.9 线上验证模板创建、编辑、预览、发送流程正常
