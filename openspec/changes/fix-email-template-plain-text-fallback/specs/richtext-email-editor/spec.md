## MODIFIED Requirements

### Requirement: 编辑器 SHALL 输出 body_html 和 body_text
保存模板时，Admin 端和 Tenant 端的富文本编辑器 MUST 将富文本内容转换为简单 HTML 存入 `body_html`，同时提取纯文本存入 `body_text`。`body_design` MUST 传 null。

#### Scenario: 保存富文本模板
- **WHEN** 用户在 Admin 端或 Tenant 端富文本编辑器中输入"你好 **张三**"并点击保存
- **THEN** create/update payload 的 `body_html` 包含 `<p>你好 <strong>张三</strong></p>`
- **AND** create/update payload 的 `body_text` 包含 `你好 张三`
- **AND** create/update payload 的 `body_design` 为 null

#### Scenario: 保存空内容模板
- **WHEN** 用户在 Admin 端或 Tenant 端清空编辑器内容并点击保存
- **THEN** create/update payload 的 `body_html` 为空字符串或最小空段落
- **AND** create/update payload 的 `body_text` 为空字符串
- **AND** create/update payload 的 `body_design` 为 null

#### Scenario: Admin 端保存平台模板时提交 body_text
- **WHEN** 平台管理员在 Admin 端创建或更新平台邮件模板
- **THEN** 请求 payload MUST 包含富文本编辑器当前输出的 `body_text`
- **AND** 后端 MUST 将该字段作为平台模板的纯文本内容保存
