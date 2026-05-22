## ADDED Requirements

### Requirement: 模板变量 SHALL 由后端统一定义并通过 API 暴露

后端 MUST 定义 `TEMPLATE_VARIABLES` 作为变量的单一数据源。前端 MUST 通过 API 获取变量列表，MUST NOT 硬编码变量定义。

#### Scenario: 变量列表 API

- **WHEN** 前端请求 `GET /t/{slug}/api/v1/email-templates/variables`
- **THEN** 返回包含 4 个变量的列表：`company_name`、`contact_name`、`contact_email`、`sender_name`
- **THEN** 每个变量包含 `name` 和 `label` 字段

#### Scenario: 前端展示变量列表

- **WHEN** 用户打开模板编辑器
- **THEN** 变量列表从 API 获取，包含后端定义的所有变量
- **THEN** 不包含 `product_name`

#### Scenario: contact_email 变量正确渲染

- **WHEN** 模板中包含 `{{contact_email}}` 且邮件被发送
- **THEN** `{{contact_email}}` 被替换为收件人的实际邮箱地址

### Requirement: 预览和发送 SHALL 使用相同的变量映射

`sample_emails`（预览路径）和 `claim_due_emails`（发送路径）MUST 使用相同的 4 个变量进行渲染。

#### Scenario: 预览与发送一致

- **WHEN** 模板包含 `{{sender_name}}` 和 `{{contact_email}}`
- **AND** 用户预览邮件
- **THEN** 两个变量都被正确替换

#### Scenario: 发送与预览一致

- **WHEN** 同一模板通过 `claim_due_emails` 发送
- **THEN** 变量替换结果与预览完全一致

### Requirement: 变量 Badge 点击 SHALL 插入到编辑器光标位置

用户点击变量 Badge 时，系统 MUST 将变量占位符插入到当前活跃编辑器的光标位置，而非仅复制到剪贴板。

#### Scenario: 在 HTML / 纯文本 textarea 中插入变量

- **WHEN** 用户在 HTML 或纯文本 textarea 中有光标定位
- **AND** 用户点击变量 Badge（如 `{{company_name}}`）
- **THEN** `{{company_name}}` 被插入到光标位置
- **THEN** 光标移动到插入文本之后

#### Scenario: 在 GrapesJS 可视化编辑器中插入变量

- **WHEN** 用户在 GrapesJS 编辑器中正在编辑某个文本组件（RTE 激活）
- **AND** 用户点击变量 Badge
- **THEN** 变量占位符被插入到 RTE 光标位置

#### Scenario: GrapesJS 未选中文本组件时的 fallback

- **WHEN** 用户在 GrapesJS 编辑器中未激活任何文本组件的 RTE
- **AND** 用户点击变量 Badge
- **THEN** 系统回退为复制变量到剪贴板
- **THEN** 显示 toast 提示用户先在编辑器中选中文本区域

### Requirement: 纯文本模板 SHALL 正确显示邮件内容

当模板仅有 `body_text` 而 `body_html` 为空时，系统 MUST 确保收件人能看到邮件内容。

#### Scenario: body_html 为空但 body_text 有内容

- **WHEN** 原始模板的 `body_html` 为空或仅含空白（在变量替换之前检查）
- **AND** `body_text` 有实际内容
- **THEN** 系统对 `body_text` 做 HTML escape 后转换为简单 HTML（换行转 `<br>`）作为 `body_html`
- **THEN** 然后正常进行变量替换和发送

#### Scenario: body_text 含特殊字符时的安全转换

- **WHEN** 原始模板 `body_html` 为空
- **AND** `body_text` 包含 HTML 特殊字符（如 `<`、`>`、`&`）
- **THEN** 特殊字符被正确转义（如 `<` → `&lt;`）
- **THEN** 生成的 HTML 结构完整，不会被特殊字符破坏

#### Scenario: body_html 和 body_text 均有内容

- **WHEN** 邮件发送时 `body_html` 有实际内容
- **THEN** 系统使用原始 `body_html`，不做 fallback 转换

### Requirement: 变量 SHALL 在邮件主题中同样生效

模板变量的渲染 MUST 同时覆盖 `subject`、`body_html`、`body_text` 三个字段，使用相同的变量映射。

#### Scenario: 主题中使用变量

- **WHEN** 模板主题包含 `{{company_name}}`
- **AND** 邮件被发送
- **THEN** 主题中的 `{{company_name}}` 被替换为实际公司名称
