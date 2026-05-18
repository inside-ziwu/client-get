## ADDED Requirements

### Requirement: 系统 SHALL 提供外贸通清洗公司列表 API

系统 SHALL 提供 `GET /admin/api/v1/collection/wmt-clean-companies` 端点，从 `waimaotong_clean_companies` 表返回分页列表数据。

响应格式：`PaginatedResponse<WmtCleanCompanyRow>`，包含基础字段和 AI 分析字段（AI 字段可为 null）。

请求参数：
- `page` (int, 默认 1)：页码
- `page_size` (int, 默认 20, 最大 100)：每页条数
- `q` (str?)：公司名/域名模糊搜索
- `country` (str?)：国家精确匹配
- `industry` (str?)：行业模糊搜索
- `size` (str?)：员工规模档位（tiny/small/medium/large）
- `year_min` (int?)：成立年份最小值
- `year_max` (int?)：成立年份最大值
- `has_contacts` (bool?)：是否有联系人
- `grade` (str?)：评级筛选（A/B/C/X）

响应字段：id, source_id, name, company_name, english_name, country, country_iso3, domain, industry, sub_industry, phone, employee_size, company_size, founded_year, website, full_address, description, grade, score, email_priority, company_type_analysis, product_tags, data_source_tags, has_trade_data, trade_amount_3y_usd, trade_count, contacts_count, detail_status, contacts_status, trade_status, sys_company_id, created_at, updated_at。

#### Scenario: 无筛选条件查询首页

- **WHEN** 请求 `GET /collection/wmt-clean-companies?page=1&page_size=20` 无其他筛选参数
- **THEN** 返回按 `created_at DESC` 排序的前 20 条记录，包含 `pagination.total` 总数

#### Scenario: 公司名模糊搜索

- **WHEN** 请求 `GET /collection/wmt-clean-companies?q=circuit`
- **THEN** 返回 `company_name ILIKE '%circuit%' OR domain ILIKE '%circuit%'` 的记录

#### Scenario: 国家精确筛选

- **WHEN** 请求 `GET /collection/wmt-clean-companies?country=China`
- **THEN** 返回 `country = 'China'` 的记录

#### Scenario: 员工规模档位筛选

- **WHEN** 请求 `GET /collection/wmt-clean-companies?size=medium`
- **THEN** 返回 `employee_size` 字段中数字落在 50-199 区间的记录（从文本中提取数字）

#### Scenario: 成立年份范围筛选

- **WHEN** 请求 `GET /collection/wmt-clean-companies?year_min=2010&year_max=2020`
- **THEN** 返回 `founded_year` 在 2010-2020 之间的记录

#### Scenario: 有联系人筛选

- **WHEN** 请求 `GET /collection/wmt-clean-companies?has_contacts=true`
- **THEN** 返回 `contacts_count > 0` 的记录

#### Scenario: AI 字段为空时的响应

- **WHEN** 记录的 AI 字段（grade, score, sub_industry 等）均为 NULL
- **THEN** 响应中这些字段值为 `null`，不省略字段

### Requirement: 前端 SHALL 展示多维筛选区

前端 `/collection/customers` 页面 SHALL 展示筛选区，包含以下筛选项：公司名/域名搜索框、国家输入、行业输入、员工规模下拉（tiny/small/medium/large）、成立年份范围（min/max 两个输入）、有联系人开关。

筛选区 SHALL 包含「查询」和「重置」按钮。点击重置 SHALL 清空所有筛选条件并回到第一页。

#### Scenario: 用户输入筛选条件并查询

- **WHEN** 用户在搜索框输入 "circuit"，选择国家 "China"，点击「查询」
- **THEN** 页面发送请求 `GET /collection/wmt-clean-companies?q=circuit&country=China&page=1`，表格展示筛选结果

#### Scenario: 用户点击重置

- **WHEN** 用户已设置多个筛选条件，点击「重置」
- **THEN** 所有筛选项恢复为空/默认值，页码重置为 1，表格展示全量数据首页

### Requirement: 前端 SHALL 展示公司列表表格

前端 SHALL 展示水平可滚动的表格，包含 13 列：公司名（可点击）、国家、域名、行业、员工规模、成立年份、电话、评级（Badge）、评分、细分行业、联系人数、详情状态（Badge）、入库时间。

评级列 SHALL 使用颜色编码 Badge：A=green、B=blue、C=orange、X=red。值为 null 时显示 `-`。

#### Scenario: 正常数据展示

- **WHEN** API 返回包含基础字段的记录
- **THEN** 表格展示所有 13 列，AI 字段为 null 的列显示 `-`

#### Scenario: 点击公司名

- **WHEN** 用户点击某行的公司名
- **THEN** 打开该公司的详情 Sheet

#### Scenario: 空数据

- **WHEN** API 返回 0 条记录
- **THEN** 表格展示空状态提示文字

### Requirement: 前端 SHALL 支持分页

前端 SHALL 展示分页控件，包含总条数、上一页/下一页按钮、当前页/总页数、每页条数选择（20/50/100）。

#### Scenario: 切换页码

- **WHEN** 用户点击「下一页」
- **THEN** 页面请求下一页数据，表格更新

#### Scenario: 切换每页条数

- **WHEN** 用户将每页条数从 20 改为 50
- **THEN** 页码重置为 1，以新 page_size 重新请求数据

#### Scenario: 第一页禁用上一页

- **WHEN** 当前为第 1 页
- **THEN** 「上一页」按钮为禁用状态
