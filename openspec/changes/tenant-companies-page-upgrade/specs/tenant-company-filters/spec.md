## ADDED Requirements

### Requirement: Filters API SHALL return sub_industries options
`GET /companies/filters` 响应 MUST 包含 `sub_industries` 字段，值为当前租户可见公司的 `waimaotong_clean_companies.sub_industry` 去重列表。

#### Scenario: 租户有多个细分行业的公司
- **WHEN** 租户的可见公司关联的 wmt 记录包含 sub_industry 值 "PCB 制造"、"电子分销"、"半导体设备"
- **THEN** filters 响应中 `sub_industries` 包含 `["PCB 制造", "电子分销", "半导体设备"]`（顺序不限）

#### Scenario: 所有公司 sub_industry 为 NULL
- **WHEN** 租户的所有可见公司关联的 wmt 记录 sub_industry 均为 NULL
- **THEN** filters 响应中 `sub_industries` 为空数组 `[]`

### Requirement: Filters API SHALL return product_tags options
`GET /companies/filters` 响应 MUST 包含 `product_tags` 字段，值为当前租户可见公司的 `waimaotong_clean_companies.product_tags` 去重展平列表。

#### Scenario: 租户公司有 product_tags
- **WHEN** 租户的可见公司关联的 wmt 记录 product_tags 包含 `["multilayer pcb", "industrial pcb"]` 和 `["multilayer pcb", "medical pcb"]`
- **THEN** filters 响应中 `product_tags` 包含 `["multilayer pcb", "industrial pcb", "medical pcb"]`（去重，顺序不限）

#### Scenario: 所有公司 product_tags 为空
- **WHEN** 租户的所有可见公司关联的 wmt 记录 product_tags 均为 NULL 或空数组
- **THEN** filters 响应中 `product_tags` 为空数组 `[]`

### Requirement: Filters API SHALL return grades options
`GET /companies/filters` 响应 MUST 包含 `grades` 字段，值为当前租户可见公司的 `waimaotong_clean_companies.grade` 去重列表。

#### Scenario: 租户公司有多个评级
- **WHEN** 租户的可见公司关联的 wmt 记录包含 grade 值 "A"、"B"、"C"
- **THEN** filters 响应中 `grades` 包含 `["A", "B", "C"]`（顺序不限）

#### Scenario: 所有公司无评级
- **WHEN** 租户的所有可见公司关联的 wmt 记录 grade 均为 NULL
- **THEN** filters 响应中 `grades` 为空数组 `[]`

### Requirement: 筛选面板 SHALL 展示 2 行 9 个筛选控件
前端筛选面板 MUST 包含以下控件，布局分 2 行：
- 行 1：搜索框（公司名/域名）、国家下拉、细分行业下拉、关键词下拉、评级下拉
- 行 2：进口额范围（min-max）、进口次数范围（min-max）、联系人数量范围（min-max）、成立年范围（起-止）

下方 MUST 有"查询"和"重置"按钮。

#### Scenario: 用户使用多个筛选条件查询
- **WHEN** 用户选择国家="US"，评级="A"，进口额最小=100000，点击"查询"
- **THEN** 前端调用 `GET /companies` 携带 `countries[]=US&grade=A&trade_amount_min=100000`，表格刷新并回到第 1 页

#### Scenario: 用户点击重置
- **WHEN** 用户已设置多个筛选条件后点击"重置"
- **THEN** 所有筛选控件恢复初始状态，表格重新加载不带筛选条件的数据

### Requirement: 下拉选项 SHALL 从 filters API 加载
细分行业、关键词、评级的下拉选项 MUST 从 `GET /companies/filters` 返回的 `sub_industries`、`product_tags`、`grades` 动态加载。国家选项从现有 `countries` 字段加载。

#### Scenario: filters API 返回空选项
- **WHEN** filters API 返回 `sub_industries: []`
- **THEN** 细分行业下拉仅显示"全部细分行业"占位选项
