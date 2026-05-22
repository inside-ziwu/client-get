# richtext-email-editor Specification

## Purpose
TBD - created by archiving change simplify-email-editor. Update Purpose after archive.
## Requirements
### Requirement: 编辑器 SHALL 提供单一富文本编辑模式
Admin 端和 Tenant 端邮件模板编辑器 MUST 使用 shared-ui 的 TipTap 富文本编辑器替代原有的多模式切换。编辑器 MUST 支持以下格式操作：加粗、斜体、换行、有序列表、无序列表。

#### Scenario: 新建模板时进入富文本编辑器
- **WHEN** 用户在 Admin 端或 Tenant 端点击新建模板
- **THEN** 打开编辑抽屉，编辑区域显示 TipTap 富文本编辑器，无模式切换标签

#### Scenario: 编辑器不显示原有模式切换
- **WHEN** 编辑抽屉打开
- **THEN** 不存在"可视化"、"HTML"、"纯文本"等 Tab 切换项

### Requirement: 编辑器 SHALL 输出 body_html 和 body_text
保存模板时，编辑器 MUST 将富文本内容转换为简单 HTML 存入 `body_html`，同时提取纯文本存入 `body_text`。`body_design` MUST 传 null。

#### Scenario: 保存富文本模板
- **WHEN** 用户在富文本编辑器中输入"你好 **张三**"并点击保存
- **THEN** `body_html` 包含 `<p>你好 <strong>张三</strong></p>`
- **AND** `body_text` 包含 `你好 张三`
- **AND** `body_design` 为 null

#### Scenario: 保存空内容模板
- **WHEN** 用户清空编辑器内容并点击保存
- **THEN** `body_html` 为空字符串或最小空段落
- **AND** `body_text` 为空字符串

### Requirement: 变量 SHALL 在光标位置插入
用户点击变量 Badge 时，MUST 将变量占位符插入到富文本编辑器当前光标位置。

#### Scenario: 光标在段落中间时插入变量
- **WHEN** 用户将光标定位在文本中间
- **AND** 点击变量 Badge
- **THEN** 变量占位符插入到光标位置

#### Scenario: 编辑器未聚焦时插入变量
- **WHEN** 编辑器未聚焦
- **AND** 用户点击变量 Badge
- **THEN** 变量插入到编辑器末尾

### Requirement: 历史模板 SHALL 降级为富文本编辑
打开编辑已有模板时，MUST 将 `body_html` 加载到 TipTap 编辑器中。纯文本模板（body_html 为空但 body_text 有内容）MUST 将 body_text 转换为 HTML（换行转 `<br>`）后加载。

#### Scenario: 打开含 body_design 的模板
- **WHEN** 用户编辑一个含 `body_design` 的模板
- **THEN** `body_html` 内容加载到富文本编辑器中
- **AND** 保存后 `body_design` 被清空为 null

#### Scenario: 打开纯文本模板（body_html 为空）
- **WHEN** 用户编辑一个 `body_html` 为空但 `body_text` 有内容的模板
- **THEN** `body_text` 中的 `\n` 转换为 `<br>` 后加载到编辑器

### Requirement: GrapesJS SHALL 被完全移除
shared-ui 中的 `grapes-email-editor.tsx` MUST 删除，`grapesjs` 和 `grapesjs-preset-newsletter` 依赖 MUST 移除。

#### Scenario: shared-ui 不再包含 GrapesJS
- **WHEN** 构建 shared-ui 包
- **THEN** 不包含 grapesjs 相关代码和依赖

#### Scenario: Admin 和 Tenant 均使用 TipTap
- **WHEN** Admin 端或 Tenant 端打开邮件模板编辑页面
- **THEN** 使用 shared-ui 的 TipTap 编辑器组件

