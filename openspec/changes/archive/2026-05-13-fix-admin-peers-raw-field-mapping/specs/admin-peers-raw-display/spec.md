## ADDED Requirements

### Requirement: Admin同行公司页必须展示V3 raw字段
Admin「同行公司」页面 SHALL query the existing V3 raw Lixiaoyun companies API and render company fields from top-level response fields rather than relying on `raw_payload`.

#### Scenario: 列表展示真实字段
- **WHEN** `/collection/peers` receives a Lixiaoyun raw company row with `name`, `english_name`, `employee_scale`, `reg_capital`, `esdate`, `reg_address`, `domain`, `contacts_count`, `keyword_normalized`, and `created_at`
- **THEN** the table SHALL display those values in the corresponding columns

#### Scenario: 字段为空时显示占位符
- **WHEN** a Lixiaoyun raw company row has null or empty optional fields
- **THEN** the table and details SHALL display `-` only for those missing fields while keeping available fields visible

#### Scenario: 页面不得回退到旧raw接口
- **WHEN** the Admin Next.js code is inspected or tested
- **THEN** `/collection/peers` SHALL use the V3 raw company API client method for Lixiaoyun and SHALL NOT call the legacy `listRawCompanies('lixiaoyun')` path

#### Scenario: API从payload兜底英文名和联系人数量
- **WHEN** a Lixiaoyun raw company row has empty top-level `english_name` and no split contact rows, but its `raw_payload` contains `name_en` or `company_name_en` and `contacts_count` or `lx_contacts`
- **THEN** the V3 raw company API SHALL return the fallback English name and non-zero `contacts_count` in top-level response fields
