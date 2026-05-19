## ADDED Requirements

### Requirement: 列表 API SHALL 返回完整 wmt 字段
`GET /companies` 响应的每条记录 MUST 包含以下字段（在现有基础上补充）：
- `sub_industry`: string | null（细分行业）
- `phone`: string | null（电话）
- `trade_amount_3y_usd`: number | null（近 3 年进口额 USD）
- `trade_count`: number | null（进口次数）
- `description`: string | null（公司描述）
- `data_source_tags`: string[]（数据来源标签）

现有字段保持不变。

#### Scenario: wmt 记录有完整数据
- **WHEN** 查询一条 wmt 记录 sub_industry="PCB 制造"、phone="+1-555-0100"、trade_amount_3y_usd=2340000
- **THEN** 列表响应该条记录包含 `"sub_industry": "PCB 制造"`, `"phone": "+1-555-0100"`, `"trade_amount_3y_usd": 2340000.0`

#### Scenario: wmt 记录字段为 NULL
- **WHEN** 查询一条 wmt 记录 sub_industry=NULL、phone=NULL
- **THEN** 列表响应该条记录 `"sub_industry": null`, `"phone": null`

### Requirement: 表格 SHALL 展示 mock 定义的列
表格 MUST 包含以下列（从左到右）：
1. 多选框（checkbox）
2. 公司名称（company_name + domain 双行展示）
3. 国家（country_iso3 badge）
4. 细分行业（sub_industry）
5. 关键词（product_tags，tag 样式）
6. 评级（grade，彩色 tag）
7. 总分（score）
8. 操作（详情、加入群组、拉黑按钮）

不展示"状态"列（后期新增）。

#### Scenario: 正常展示一行数据
- **WHEN** 列表返回一条公司记录，name="Advanced Circuits Inc."、domain="advancedcircuits.com"、country_iso3="US"、sub_industry="PCB 制造"、product_tags=["industrial pcb"]、grade="A"、score=82
- **THEN** 表格该行展示：公司名+域名双行、US badge、"PCB 制造"、"industrial pcb" tag、A 绿色 tag、82、三个操作按钮

#### Scenario: 字段缺失
- **WHEN** 某公司 sub_industry=null、product_tags=[]、grade=null、score=null
- **THEN** 对应列展示 "-"

### Requirement: 表格 SHALL 支持多选
每行 MUST 有 checkbox，表头 MUST 有全选 checkbox。选中行时：
- 行背景高亮
- 表格上方显示批量操作栏："已选 N 家" + "加入群组"按钮 + "取消选择"按钮

#### Scenario: 选中部分行
- **WHEN** 用户勾选 3 行
- **THEN** 批量操作栏显示"已选 3 家"，全选框变为半选状态

#### Scenario: 全选
- **WHEN** 用户勾选全选框
- **THEN** 当前页所有行被选中，批量操作栏显示"已选 N 家"（N = 当前页条数）

#### Scenario: 取消选择
- **WHEN** 用户点击"取消选择"
- **THEN** 所有选中状态清除，批量操作栏隐藏

### Requirement: 列表 SHALL 支持页码分页
列表 MUST 使用页码分页（`page` + `page_size` 参数），底部显示：
- 左侧：总条数 + 每页条数选择（20/50/100）
- 右侧：上一页/下一页按钮 + 页码跳转输入

#### Scenario: 翻页
- **WHEN** 用户点击"下一页"，当前第 1 页
- **THEN** 前端调用 `GET /companies?page=2&page_size=20`，表格刷新，多选状态清除

#### Scenario: 切换每页条数
- **WHEN** 用户将每页条数从 20 切换到 50
- **THEN** 回到第 1 页，使用 `page_size=50` 重新请求

#### Scenario: 最后一页
- **WHEN** 当前已在最后一页
- **THEN** "下一页"按钮禁用
