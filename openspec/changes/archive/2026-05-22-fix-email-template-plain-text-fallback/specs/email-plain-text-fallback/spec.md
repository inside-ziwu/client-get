## ADDED Requirements

### Requirement: 邮件发送链路 SHALL 为缺失的纯文本内容生成兜底
当邮件模板的 `body_text` 为空、空白或 NULL 时，发送入队逻辑 MUST 从同一封邮件渲染后的 `body_html` 提取可读纯文本，并将结果写入 queued email 的 `body_text`，随后传给邮件 provider 的 `text` 字段。

#### Scenario: HTML 模板缺失 body_text 时生成纯文本
- **GIVEN** 一个发送计划步骤引用的模板有 `body_html`，但 `body_text` 为 NULL、空字符串或仅空白
- **WHEN** sending worker 领取到期邮件并创建 queued email
- **THEN** queued email 的 `body_text` 包含从渲染后 `body_html` 提取的纯文本
- **AND** EngageLab payload 的 `text` 字段使用该纯文本

#### Scenario: 已有 body_text 时优先使用模板纯文本
- **GIVEN** 一个发送计划步骤引用的模板同时有 `body_html` 和非空 `body_text`
- **WHEN** sending worker 领取到期邮件并创建 queued email
- **THEN** queued email 的 `body_text` 使用渲染后的模板 `body_text`
- **AND** 系统 MUST NOT 用 `body_html` 提取结果覆盖该纯文本

#### Scenario: HTML 块级结构转换为可读换行
- **GIVEN** `body_html` 包含多个段落、`<br>` 或列表项
- **WHEN** 系统从 HTML 提取 fallback 纯文本
- **THEN** 纯文本保留可读换行
- **AND** 不包含 HTML 标签

#### Scenario: HTML 为空时保持空纯文本
- **GIVEN** 模板的 `body_text` 为空且 `body_html` 也为空
- **WHEN** sending worker 创建 queued email
- **THEN** queued email 的 `body_text` 为空字符串
- **AND** 发送流程不因 fallback 缺少来源而报错
