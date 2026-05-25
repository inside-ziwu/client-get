## ADDED Requirements

### Requirement: 系统 SHALL 提供按日期范围查询邮件发送统计的 API

系统 SHALL 提供 `GET /api/v1/dashboard/email-stats` 端点，接受 `start_date` 和 `end_date` 查询参数（YYYY-MM-DD 格式），返回该日期范围内的发送统计汇总和每日明细数据。

**请求参数**：
- `start_date`（可选）：起始日期，默认 30 天前
- `end_date`（可选）：结束日期，默认今天

**响应字段 — summary**：
- `targets`: 目标数（日期范围内所有邮件记录数）
- `sent`: 已发送数（排除 draft/pending/queued 状态）
- `delivered`: 已送达数（delivered/opened/clicked/replied 状态）
- `delivered_percent`: 送达率（delivered / sent * 100，保留两位小数）
- `invalid_email`: 无效邮箱数
- `soft_bounce`: 软退信数
- `billing`: 计费数（等同 sent）
- `total_opens`: 打开总次数（所有邮件 open_count 之和）
- `total_open_percent`: 打开次数率（total_opens / sent * 100）
- `opens`: 独立打开数（first_opened_at 非空的邮件数）
- `open_percent`: 独立打开率（opens / sent * 100）
- `report_spam`: 举报垃圾邮件数
- `unsubscribe`: 退订数

**响应字段 — daily**：
- `date`: 日期（YYYY-MM-DD）
- `sent`: 当日发送数
- `delivered`: 当日送达数
- `opens`: 当日独立打开数

#### Scenario: 默认查询近30天统计
- **GIVEN** 租户已登录
- **WHEN** 请求 `GET /api/v1/dashboard/email-stats` 不带日期参数
- **THEN** 返回近 30 天的 summary 和 daily 数据，summary 中各比率字段正确计算

#### Scenario: 自定义日期范围查询
- **GIVEN** 租户已登录
- **WHEN** 请求 `GET /api/v1/dashboard/email-stats?start_date=2026-05-01&end_date=2026-05-15`
- **THEN** 返回 2026-05-01 至 2026-05-15 范围内的统计数据

#### Scenario: 无邮件数据时返回零值
- **GIVEN** 租户在指定日期范围内没有任何邮件记录
- **WHEN** 请求 email-stats
- **THEN** summary 所有计数字段返回 0，所有比率字段返回 0，daily 返回空数组

#### Scenario: 日期格式错误
- **GIVEN** 请求参数日期格式不合法
- **WHEN** 请求 `GET /api/v1/dashboard/email-stats?start_date=invalid`
- **THEN** 返回 400 错误，提示日期格式应为 YYYY-MM-DD

### Requirement: 系统 SHALL 保证邮件统计数据的租户隔离

系统 MUST 确保 email-stats API 仅返回当前认证租户的邮件统计数据，不得泄露其他租户数据。

#### Scenario: 租户只能看到自己的统计
- **GIVEN** 租户 A 有 100 封邮件，租户 B 有 200 封邮件
- **WHEN** 租户 A 请求 email-stats
- **THEN** 返回的 targets 为 100，不包含租户 B 的数据

#### Scenario: 未认证请求被拒绝
- **GIVEN** 请求未携带有效 JWT
- **WHEN** 请求 email-stats
- **THEN** 返回 401 未授权错误

### Requirement: 前端 SHALL 展示发送统计和追踪统计卡片

前端首页 SHALL 展示两组统计卡片，各包含 6 个指标：

**发送统计**（第一组）：
1. 目标数（targets）— 蓝色
2. 已发送（sent）— 蓝色
3. 已送达（delivered）+ 送达率百分比 — 绿色
4. 无效邮箱（invalid_email）— 橙色
5. 软退信（soft_bounce）— 紫色
6. 计费数（billing）— 蓝色

**追踪统计**（第二组）：
1. 打开次数（total_opens）+ 打开次数率百分比 — 蓝色
2. 打开次数率（total_open_percent）— 绿色
3. 独立打开数（opens）— 蓝色
4. 独立打开率（open_percent）— 绿色
5. 举报垃圾邮件（report_spam）— 红色
6. 退订（unsubscribe）— 红色

#### Scenario: 统计卡片正确展示数据
- **GIVEN** API 返回 summary 数据
- **WHEN** 页面渲染完成
- **THEN** 12 个统计卡片分两组展示，数值和百分比正确对应

#### Scenario: 加载中状态
- **GIVEN** API 请求进行中
- **WHEN** 页面渲染
- **THEN** 统计卡片显示加载占位符（skeleton 或 "-"）

### Requirement: 前端 SHALL 展示日期范围选择器

前端首页顶部 SHALL 展示日期范围选择器，包含快捷预设按钮和自定义日期范围输入。

快捷预设：
- 今天：当天
- 昨天：前一天
- 近7天：前 6 天到今天
- 近30天：前 29 天到今天（默认选中）

#### Scenario: 默认选中近30天
- **GIVEN** 用户进入首页
- **WHEN** 页面加载完成
- **THEN** "近30天" 按钮高亮，展示近 30 天的统计数据

#### Scenario: 切换快捷预设
- **WHEN** 用户点击 "近7天" 按钮
- **THEN** 按钮高亮切换，日期范围更新，统计数据和趋势图重新请求

#### Scenario: 自定义日期范围
- **WHEN** 用户手动选择起止日期
- **THEN** 快捷预设按钮取消高亮，按自定义日期范围请求数据

### Requirement: 前端 SHALL 展示发送趋势图

前端首页 SHALL 展示堆叠柱状图，横轴为日期，纵轴为数量，包含三个 category：
- 已发送（蓝色 #1677ff）
- 已送达（绿色 #52c41a）
- 打开（橙色 #fa8c16）

图表使用 recharts 的 `BarChart` 组件，`stacked` 模式。

#### Scenario: 趋势图正确展示每日数据
- **GIVEN** API 返回 daily 数组包含 7 天数据
- **WHEN** 页面渲染
- **THEN** 趋势图展示 7 根堆叠柱，每根包含三种颜色

#### Scenario: 无数据时展示空状态
- **GIVEN** API 返回 daily 为空数组
- **WHEN** 页面渲染
- **THEN** 趋势图区域显示空状态提示
