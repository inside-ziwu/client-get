## ADDED Requirements

### Requirement: tenant 公司列表 SHALL 只展示匹配租户关键词的 wmt 公司
tenant 公司列表 SHALL 以 `waimaotong_clean_companies` 为唯一公司数据源，并且只展示已通过 wmt 血缘匹配当前租户 active 关键词的公司。

#### Scenario: 返回匹配关键词的 wmt 公司
- **WHEN** 租户访问 `/t/{slug}/api/v1/companies`
- **THEN** 响应中的每家公司 MUST 来自 `waimaotong_clean_companies`
- **AND** 每家公司 MUST 已存在对应租户的 visible `tenant_companies` 关系

#### Scenario: 不返回未归因 wmt 公司
- **WHEN** 某条 wmt clean 无法通过来源同行血缘获得关键词归因
- **THEN** tenant 公司列表 MUST NOT 返回该公司

#### Scenario: 不返回旧 clean 公司
- **WHEN** `tenant_companies.clean_company_id` 指向旧 `clean_companies.id` 且无法 JOIN 到 `waimaotong_clean_companies.id`
- **THEN** tenant 公司列表 MUST NOT 返回该旧关联对应的数据
