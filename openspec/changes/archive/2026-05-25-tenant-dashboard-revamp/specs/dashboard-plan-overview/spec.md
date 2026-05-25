## ADDED Requirements

### Requirement: 系统 SHALL 提供计划维度概览统计 API

系统 SHALL 提供 `GET /api/v1/dashboard/plan-overview` 端点，接受可选的 `plan_id` 查询参数，返回计划维度的统计指标。

**请求参数**：
- `plan_id`（可选）：指定计划 ID，不传则返回租户级汇总

**响应字段**：
- `keyword_count`: 关键词数
- `companies_collected`: 已采集公司数
- `companies_scored`: 已评分公司数（score IS NOT NULL）
- `contacts_total`: 联系人总数
- `emails_drafted`: 草稿数
- `emails_sent`: 已发送数
- `plans`: 计划列表（用于前端计划选择器，包含 id 和 name）

#### Scenario: 查询租户级汇总
- **GIVEN** 租户已登录且有多个发送计划
- **WHEN** 请求 `GET /api/v1/dashboard/plan-overview` 不带 plan_id
- **THEN** 返回该租户所有计划的汇总统计

#### Scenario: 查询指定计划统计
- **GIVEN** 租户已登录且存在 plan_id = "xxx"
- **WHEN** 请求 `GET /api/v1/dashboard/plan-overview?plan_id=xxx`
- **THEN** 返回该计划维度的统计指标

#### Scenario: 指定计划不存在或不属于当前租户
- **GIVEN** plan_id 不存在或属于其他租户
- **WHEN** 请求 plan-overview
- **THEN** 返回 404 错误

#### Scenario: 租户无任何计划
- **GIVEN** 租户没有发送计划
- **WHEN** 请求 plan-overview
- **THEN** 所有计数字段返回 0，plans 返回空数组

### Requirement: 前端 SHALL 展示计划概览模块

前端首页 SHALL 展示计划概览模块，包含：
1. 计划选择下拉框（默认"全部计划"，可选择单个计划）
2. 统计指标卡片：关键词数、已采集公司、已评分、联系人总数、草稿数、已发送

#### Scenario: 切换计划选择器
- **WHEN** 用户在下拉框中选择某个计划
- **THEN** 概览统计指标按该计划维度刷新

#### Scenario: 选择"全部计划"
- **WHEN** 用户选择"全部计划"
- **THEN** 展示租户级汇总数据
