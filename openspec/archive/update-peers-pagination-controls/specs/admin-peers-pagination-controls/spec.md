## ADDED Requirements

### Requirement: 同行公司页支持配置每页数量

Admin 同行公司页 MUST 允许用户在分页组件中选择每页 `20 / 50 / 100` 条数据。

#### Scenario: 用户切换每页数量

- **WHEN** 用户在同行公司页分页组件中选择 `50` 或 `100`
- **THEN** 前端 MUST 使用所选值作为 `page_size` 请求同行公司数据
- **AND** 表格分页状态 MUST 显示当前每页数量

### Requirement: 同行公司页支持指定页码跳转

Admin 同行公司页 MUST 支持用户输入页码并跳转到指定页。

#### Scenario: 用户输入页码跳转

- **WHEN** 用户在分页组件中输入目标页码并确认
- **THEN** 前端 MUST 使用目标页码作为 `page` 请求同行公司数据
- **AND** 保持当前每页数量不变

### Requirement: 同行公司页每页数量有上限

Admin 同行公司页相关接口 MUST 限制每页最大 `100` 条。

#### Scenario: 请求超过最大每页数量

- **WHEN** 请求同行公司数据时 `page_size > 100`
- **THEN** 后端 MUST 拒绝该请求或将其限制在不超过 `100`
- **AND** 不得执行超过 `100` 条每页的数据查询
