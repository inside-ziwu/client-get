# source-competitor-display Specification

## Purpose
TBD - created by archiving change add-source-competitor-field. Update Purpose after archive.
## Requirements
### Requirement: 公司列表 SHALL 展示来源同行列
公司列表表格 SHALL 包含"来源同行"列，展示该公司对应的 `source_competitor` 值。

#### Scenario: 正常展示来源同行
- **WHEN** 用户访问 tenant 公司列表页
- **THEN** 表格 MUST 包含"来源同行"列
- **AND** 每行展示该公司关联的 `waimaotong_raw_companies.source_competitor` 值

#### Scenario: 来源同行为空
- **WHEN** 某公司无法匹配到 raw 记录（`source_competitor` 为 null）
- **THEN** 该列 MUST 展示为空（不显示占位文本）

### Requirement: 公司详情 SHALL 展示来源同行字段
公司详情页 SHALL 展示"来源同行"字段。

#### Scenario: 详情页正常展示
- **WHEN** 用户打开某公司详情页
- **THEN** 详情页 MUST 展示"来源同行"字段及其值

#### Scenario: 详情页来源同行为空
- **WHEN** 该公司的 `source_competitor` 为 null
- **THEN** 详情页 MUST 不展示该字段或展示为空

### Requirement: API SHALL 返回 source_competitor 字段
公司列表和详情 API 响应 SHALL 包含 `source_competitor` 字段。

#### Scenario: 列表 API 返回 source_competitor
- **WHEN** 请求 `GET /t/{slug}/api/v1/companies`
- **THEN** 响应中每个公司对象 MUST 包含 `source_competitor` 字段（string | null）

#### Scenario: 详情 API 返回 source_competitor
- **WHEN** 请求 `GET /t/{slug}/api/v1/companies/{id}`
- **THEN** 响应公司对象 MUST 包含 `source_competitor` 字段（string | null）

