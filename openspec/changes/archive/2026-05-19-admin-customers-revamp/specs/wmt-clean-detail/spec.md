## ADDED Requirements

### Requirement: 系统 SHALL 提供外贸通清洗公司详情 API

系统 SHALL 提供 `GET /admin/api/v1/collection/wmt-clean-companies/{id}` 端点，返回 `waimaotong_clean_companies` 单条记录的完整字段。

响应格式：`ApiResponse<WmtCleanCompanyDetail>`，包含所有基础字段 + AI 分析字段（score_details, match_reasons, potential_needs, recommended_products, risk_factors, main_business, trade_summary 等 JSONB 字段）。

#### Scenario: 正常获取详情

- **WHEN** 请求 `GET /collection/wmt-clean-companies/123`，记录存在
- **THEN** 返回该记录的完整字段，JSONB 字段解析为 JSON 对象/数组

#### Scenario: 记录不存在

- **WHEN** 请求 `GET /collection/wmt-clean-companies/99999`，记录不存在
- **THEN** 返回 404 错误，message 为 "公司不存在"

### Requirement: 系统 SHALL 提供外贸通清洗公司联系人 API

系统 SHALL 提供 `GET /admin/api/v1/collection/wmt-clean-companies/{id}/contacts` 端点，通过 `sys_company_id` 关联查询 `waimaotong_clean_contacts`。

响应字段：id, name, position, department, email, email_status, phone, mobile, linkedin, whatsapp, source, confidence, created_at。

#### Scenario: 正常获取联系人

- **WHEN** 请求 `GET /collection/wmt-clean-companies/1/contacts`，该公司有联系人
- **THEN** 返回按 `created_at ASC` 排序的联系人列表

#### Scenario: 无联系人

- **WHEN** 请求 `GET /collection/wmt-clean-companies/6/contacts`，该公司无联系人
- **THEN** 返回空数组 `[]`

#### Scenario: 公司不存在

- **WHEN** 请求 `GET /collection/wmt-clean-companies/99999/contacts`，公司记录不存在
- **THEN** 返回空数组 `[]`（subquery 无匹配，与无联系人行为一致）

### Requirement: 前端 SHALL 展示多分组详情 Sheet

前端 SHALL 在用户点击公司名时，从右侧滑出 Sheet 面板展示公司详情，分为以下分组：

**分组 1：基本信息**（始终显示）
company_name, english_name, country, domain, website, industry, phone, employee_size, company_size, founded_year, full_address, description

**分组 2：AI 评估**（仅当 grade 或 score 有值时显示）
grade（Badge）, score, score_details（多维度展示）, sub_industry, company_type_analysis, product_tags（Badge 列表）, match_reasons（列表）, potential_needs（列表）, recommended_products（列表）, risk_factors（列表）, main_business（列表）, email_priority

**分组 3：贸易数据**（仅当 has_trade_data 为 true 或 trade_summary 有值时显示）
has_trade_data, trade_amount_3y_usd, trade_count, trade_summary（结构化展示）

**分组 4：联系人**（始终显示）
通过独立 API 获取，展示为表格：name, position, department, email, email_status, phone, linkedin, source

**分组 5：数据来源与元数据**（始终显示）
data_source_tags, source_id, sys_company_id, detail_status, contacts_status, trade_status, created_at, updated_at

#### Scenario: 打开含基础数据的公司详情

- **WHEN** 用户点击一个只有基础字段（AI 字段全空）的公司名
- **THEN** Sheet 打开，显示分组 1（基本信息）、分组 4（联系人）、分组 5（数据来源）；分组 2（AI 评估）和分组 3（贸易数据）不显示

#### Scenario: 打开含完整数据的公司详情

- **WHEN** 用户点击一个 AI 字段和贸易数据均有值的公司名
- **THEN** Sheet 打开，显示全部 5 个分组

#### Scenario: score_details 多维度展示

- **WHEN** 公司的 `score_details` 为 `[{dimension: "relevance", score: 35, max_possible: 40, explanation: "..."}, ...]`
- **THEN** 详情中展示每个维度的进度条（score/max_possible）和说明文本

#### Scenario: 联系人加载

- **WHEN** Sheet 打开
- **THEN** 自动调用联系人 API 获取数据，加载中显示 loading 状态，加载完成后展示联系人表格

#### Scenario: 关闭 Sheet

- **WHEN** 用户关闭详情 Sheet
- **THEN** Sheet 关闭，清空选中公司状态
