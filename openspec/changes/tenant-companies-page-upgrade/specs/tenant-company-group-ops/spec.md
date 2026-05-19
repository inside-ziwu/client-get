## ADDED Requirements

### Requirement: 单条加入群组 SHALL 弹出群组选择 Modal
点击行操作栏"加入群组"按钮 MUST 弹出 Modal，展示当前租户的群组列表（从 `GET /groups` 加载），每个群组显示名称和成员数。用户选择一个群组后点击"确认加入"。

#### Scenario: 选择群组并确认
- **WHEN** 用户点击某公司的"加入群组"，选择"PCB 核心采购商"群组，点击"确认加入"
- **THEN** 调用 `POST /groups/{groupId}/members/batch-add`，body `{"tenant_company_ids": ["{companyId}"]}`，成功后关闭 Modal 并刷新列表

#### Scenario: 没有可用群组
- **WHEN** `GET /groups` 返回空列表
- **THEN** Modal 内显示"暂无群组，请先创建群组"

#### Scenario: 取消操作
- **WHEN** 用户点击"取消"
- **THEN** Modal 关闭，不发送请求

### Requirement: 详情 Drawer 内 SHALL 支持加入群组
详情 Drawer 的按钮区 MUST 包含"加入群组"按钮，点击后弹出同样的群组选择 Modal。

#### Scenario: 从详情 Drawer 加入群组
- **WHEN** 用户在详情 Drawer 点击"加入群组"
- **THEN** 弹出群组选择 Modal，提交成功后关闭 Modal，Drawer 保持打开

### Requirement: 批量加入群组 SHALL 对选中的多家公司生效
选中多行后，批量操作栏的"加入群组"按钮 MUST 弹出群组选择 Modal，标题显示"将选中的 N 家公司批量加入群组"。

#### Scenario: 批量加入群组
- **WHEN** 用户选中 5 家公司，点击批量"加入群组"，选择群组后确认
- **THEN** 调用 `POST /groups/{groupId}/members/batch-add`，body `{"tenant_company_ids": ["id1","id2","id3","id4","id5"]}`，成功后关闭 Modal，清除选中状态，刷新列表

#### Scenario: 批量操作部分失败
- **WHEN** 批量加入请求返回错误
- **THEN** 显示错误提示（toast），不清除选中状态
