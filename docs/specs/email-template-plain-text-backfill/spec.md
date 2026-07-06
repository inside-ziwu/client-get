# email-template-plain-text-backfill Specification

## Purpose
提供受控数据修复能力，用于回填平台与租户邮件模板中缺失的 `body_text`，避免存量模板继续产生缺失纯文本的邮件。

## Requirements
### Requirement: 存量邮件模板 SHALL 支持受控回填 body_text
系统 MUST 提供一次性数据修复脚本或命令，用于扫描 `platform_email_templates` 与 `email_templates` 中 `body_text` 为 NULL、空字符串或仅空白且 `body_html` 非空的记录，并从 `body_html` 生成可读纯文本回填到 `body_text`。

#### Scenario: dry-run 统计待回填模板
- **GIVEN** 数据库中存在缺失 `body_text` 但 `body_html` 可提取文本的平台模板或租户模板
- **WHEN** 操作者以 dry-run 模式运行回填脚本
- **THEN** 脚本 MUST 输出每张表的待回填数量
- **AND** 脚本 MUST NOT 更新任何数据库记录

#### Scenario: 执行回填更新缺失 body_text 的模板
- **GIVEN** 数据库中存在缺失 `body_text` 但 `body_html` 可提取文本的平台模板或租户模板
- **WHEN** 操作者以执行模式运行回填脚本
- **THEN** 脚本 MUST 只更新这些记录的 `body_text`
- **AND** 生成的 `body_text` MUST 不包含 HTML 标签
- **AND** 脚本 MUST 输出每张表的实际更新数量

#### Scenario: 已有 body_text 的模板不会被覆盖
- **GIVEN** 数据库中存在已填写非空 `body_text` 的平台模板或租户模板
- **WHEN** 操作者运行回填脚本
- **THEN** 脚本 MUST NOT 修改这些记录

#### Scenario: 无可提取文本的 HTML 不写入无意义内容
- **GIVEN** 数据库中存在 `body_text` 缺失且 `body_html` 为空或只包含无法提取文本的 HTML
- **WHEN** 操作者运行回填脚本
- **THEN** 脚本 MUST 跳过这些记录
- **AND** 脚本 MUST 在输出统计中体现跳过数量
