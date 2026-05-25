## ADDED Requirements

### Requirement: 系统 SHALL 提供每日发送配额查询 API

系统 SHALL 提供 `GET /api/v1/dashboard/daily-quota` 端点，返回当前租户的每日发送配额信息。

**响应字段**：
- `limit`: 每日发送上限（租户所有域名 daily_limit 之和）
- `used`: 今日已发送数（emails 表今日 sent 记录数）
- `remaining`: 剩余可发送数（limit - used，不小于 0）

#### Scenario: 正常查询每日配额
- **GIVEN** 租户有域名暖域配置，daily_limit 总和为 500，今日已发送 120 封
- **WHEN** 请求 `GET /api/v1/dashboard/daily-quota`
- **THEN** 返回 `{limit: 500, used: 120, remaining: 380}`

#### Scenario: 租户无域名配置
- **GIVEN** 租户没有域名暖域配置
- **WHEN** 请求 daily-quota
- **THEN** 返回 `{limit: 0, used: 0, remaining: 0}`

#### Scenario: 已用量超过限额
- **GIVEN** 今日已发送数超过 daily_limit
- **WHEN** 请求 daily-quota
- **THEN** remaining 返回 0（不返回负数）

### Requirement: 系统 SHALL 提供 LLM 余额查询 API

系统 SHALL 提供 `GET /api/v1/dashboard/llm-balance` 端点，返回当前租户配置的 OpenRouter API 余额信息。

**响应字段**：
- `is_configured`: 是否已配置 OpenRouter API Key
- `balance_remaining`: 剩余额度（美元）
- `usage`: 已使用额度
- `limit`: 总额度
- `balance_status`: 余额状态（sufficient / low / empty / unknown）

#### Scenario: 已配置 OpenRouter 且有余额
- **GIVEN** 租户已配置 OpenRouter API Key，余额充足
- **WHEN** 请求 `GET /api/v1/dashboard/llm-balance`
- **THEN** 返回 `{is_configured: true, balance_remaining: 15.5, balance_status: "sufficient", ...}`

#### Scenario: 未配置 OpenRouter
- **GIVEN** 租户未配置 OpenRouter API Key
- **WHEN** 请求 llm-balance
- **THEN** 返回 `{is_configured: false, balance_remaining: null, balance_status: "unknown"}`

#### Scenario: OpenRouter API 调用失败
- **GIVEN** OpenRouter API 不可达或超时
- **WHEN** 请求 llm-balance
- **THEN** 返回缓存的余额数据（如有），或 `{is_configured: true, balance_status: "unknown"}`

### Requirement: 前端 SHALL 展示 LLM 余额和每日配额并排卡片

前端首页底部 SHALL 展示两个并排卡片：

**每日发送配额卡片**：
- 展示进度条（used / limit）
- 显示剩余可发送数
- 进度条颜色：< 80% 绿色，80-95% 橙色，> 95% 红色

**LLM 余额卡片**：
- 展示余额金额和状态
- 未配置时提示"未配置 OpenRouter"
- 余额不足时以红色警示

#### Scenario: 配额正常时展示绿色进度
- **GIVEN** 配额使用率 < 80%
- **WHEN** 页面渲染
- **THEN** 进度条为绿色，显示剩余量

#### Scenario: 配额接近上限时警示
- **GIVEN** 配额使用率 > 95%
- **WHEN** 页面渲染
- **THEN** 进度条为红色，显示剩余量
