## ADDED Requirements

### Requirement: 拉黑操作 SHALL 弹出确认 Modal
点击行操作栏"拉黑"按钮 MUST 弹出确认 Modal，内容说明"将「{公司名}」加入黑名单后，不会再向其发送邮件，且不会出现在发送计划目标中。"

#### Scenario: 确认拉黑
- **WHEN** 用户点击某公司的"拉黑"，Modal 弹出后点击"确认拉黑"
- **THEN** 调用 `POST /companies/{id}/blacklist`，body `{"reason": "manual blacklist"}`，成功后关闭 Modal，刷新列表（该公司从列表中消失）

#### Scenario: 取消拉黑
- **WHEN** 用户点击"取消"
- **THEN** Modal 关闭，不发送请求

### Requirement: 拉黑按钮 SHALL 使用危险样式
拉黑按钮 MUST 使用红色/危险样式（variant="destructive" 或红色边框），与普通操作按钮视觉区分。

#### Scenario: 按钮样式
- **WHEN** 表格渲染操作列
- **THEN** "详情"和"加入群组"为默认样式，"拉黑"为红色危险样式
