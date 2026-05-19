## ADDED Requirements

### Requirement: 详情 API SHALL 返回完整 wmt AI 评估和贸易字段
`GET /companies/{id}` 响应 MUST 包含以下字段（在现有基础上补充）：
- `score_details`: array | null（评分明细）
- `company_type_analysis`: string | null
- `email_priority`: string | null
- `sales_approach`: string | null
- `match_reasons`: array | null
- `potential_needs`: array | null
- `recommended_products`: array | null
- `risk_factors`: array | null
- `main_business`: array | null
- `trade_summary`: object | null
- `phone`: string | null
- `company_size`: string | null

#### Scenario: wmt 记录有 AI 评估数据
- **WHEN** 查询一条 wmt 记录有 score_details=[{"dimension":"行业匹配","score":20,"max_possible":25}]
- **THEN** 详情响应包含 `"score_details": [{"dimension":"行业匹配","score":20,"max_possible":25}]`

#### Scenario: wmt 记录无 AI 数据
- **WHEN** 查询一条 wmt 记录 score_details=NULL
- **THEN** 详情响应 `"score_details": null`

### Requirement: 详情 Drawer SHALL 以 660px 宽度展示完整信息
点击"详情"按钮 MUST 打开 660px 宽度的右侧 Drawer，包含以下分区：
1. **基本信息**（2 列 grid）：网站、国家、细分行业、成立年、关键词（左列）+ 评级、平台总分、评分调整、进口额、进口次数（右列）
2. **AI 评估**（当 grade 或 score 存在时展示）：评分明细进度条、细分行业、公司类型分析、邮箱优先级、产品标签、匹配原因、潜在需求等
3. **贸易数据**（当 has_trade_data 或 trade_summary 存在时展示）
4. **标签**
5. **备注**
6. **联系人表**（姓名、职位、部门、邮箱、邮箱状态、电话）

#### Scenario: 打开详情 Drawer
- **WHEN** 用户点击某公司行的"详情"按钮
- **THEN** 右侧滑出 660px 宽度的 Drawer，标题为公司名，内容按上述分区展示

#### Scenario: 字段为空的分区处理
- **WHEN** 某公司无 AI 评估数据（grade=null, score=null）
- **THEN** AI 评估分区不展示

### Requirement: 详情 Drawer SHALL 支持编辑模式
Drawer 默认只读态，点击"编辑"按钮进入编辑态：
- 标签：可增删（输入+回车添加，点击 × 删除）
- 备注：textarea 可编辑
- 评分调整：number input（-20 ~ +20）

编辑态按钮组变为"保存"+"取消"。

#### Scenario: 编辑并保存
- **WHEN** 用户点击"编辑"，修改备注为"Q4 跟进"，评分调整为 +5，点击"保存"
- **THEN** 调用 `PATCH /prospects/{id}`，body 包含 `{"note": "Q4 跟进", "score_adjustment": 5}`，成功后退出编辑态，数据刷新

#### Scenario: 取消编辑
- **WHEN** 用户点击"编辑"后点击"取消"
- **THEN** 退出编辑态，所有修改丢弃，恢复只读显示

#### Scenario: 评分调整边界值
- **WHEN** 用户输入评分调整 = 25（超出 +20）
- **THEN** input 限制在 -20 ~ +20 范围内，不允许超出

### Requirement: PATCH API SHALL 支持 score_adjustment 字段
`PATCH /prospects/{id}` MUST 接受 `score_adjustment` 字段（integer，-20 ~ +20），存储到 `tenant_companies.score_adjustment`。

#### Scenario: 更新评分调整
- **WHEN** 发送 `PATCH /prospects/{id}` body `{"score_adjustment": 10}`
- **THEN** `tenant_companies.score_adjustment` 更新为 10，响应包含更新后的完整公司数据

#### Scenario: 超范围的评分调整
- **WHEN** 发送 `PATCH /prospects/{id}` body `{"score_adjustment": 30}`
- **THEN** 返回 422，message 说明范围限制

### Requirement: 详情 SHALL 加载并展示联系人列表
Drawer 打开时 MUST 调用 `GET /companies/{id}/contacts` 加载联系人，展示为表格：姓名、职位、部门、邮箱、邮箱状态、电话。

#### Scenario: 公司有联系人
- **WHEN** contacts API 返回 3 条联系人记录
- **THEN** 联系人表显示 3 行，各字段正确渲染

#### Scenario: 公司无联系人
- **WHEN** contacts API 返回空数组
- **THEN** 联系人区域显示"暂无联系人数据"
