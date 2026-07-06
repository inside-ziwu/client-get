# tenant-companies-list Specification

## Purpose
TBD - created by archiving change fix-tenant-company-list-wmt-link. Update Purpose after archive.
## Requirements
### Requirement: tenant 公司列表 SHALL 只展示匹配租户关键词的 wmt 公司
tenant 公司列表 SHALL 以 `waimaotong_clean_companies` 为唯一公司数据源，并且只展示已通过 wmt 血缘匹配当前租户 active 关键词的公司。查询 SHALL 通过 LEFT JOIN `waimaotong_raw_companies`（关联条件：`sys_company_id`）附加 `source_competitor` 字段。

查询涉及的 JOIN 列 SHALL 有对应索引覆盖：
- `waimaotong_raw_companies.sys_company_id` SHALL 有 B-Tree 索引（`idx_wmt_raw_sys_company_id`）
- `lixiaoyun_api_clean_companies` 上 SHALL 有 `lower(trim(entname_eng))` 完整函数索引（`idx_lxc_entname_eng_lower_full`），以支持 `source_competitor_cn` 的 LEFT JOIN 匹配

#### Scenario: 返回匹配关键词的 wmt 公司
- **WHEN** 租户访问 `/t/{slug}/api/v1/companies`
- **THEN** 响应中的每家公司 MUST 来自 `waimaotong_clean_companies`
- **AND** 每家公司 MUST 已存在对应租户的 visible `tenant_companies` 关系
- **AND** 每家公司 MUST 包含 `source_competitor` 字段（通过 LEFT JOIN `waimaotong_raw_companies` 获取）

#### Scenario: 不返回未归因 wmt 公司
- **WHEN** 某条 wmt clean 无法通过来源同行血缘获得关键词归因
- **THEN** tenant 公司列表 MUST NOT 返回该公司

#### Scenario: 不返回旧 clean 公司
- **WHEN** `tenant_companies.clean_company_id` 指向旧 `clean_companies.id` 且无法 JOIN 到 `waimaotong_clean_companies.id`
- **THEN** tenant 公司列表 MUST NOT 返回该旧关联对应的数据

#### Scenario: 生产数据规模下查询走索引扫描而非全表扫描
- **WHEN** 在生产数据规模下执行公司列表查询
- **THEN** `EXPLAIN ANALYZE` 输出中 `lixiaoyun_api_clean_companies` 的访问方式 MUST 为 Index Scan（使用 `idx_lxc_entname_eng_lower_full`），不得退化为导致慢查询的 Seq Scan 全表扫描
- **AND** 查询总耗时 MUST 低于 1 秒
- **NOTE** 小数据集（如开发库仅数十行）下 planner 可能合理选择 Seq Scan，此为正常优化行为，不违反本要求

#### Scenario: 索引创建不阻塞生产查询
- **WHEN** Alembic 迁移执行创建上述索引
- **THEN** 索引创建 MUST 使用 `CREATE INDEX CONCURRENTLY`
- **AND** 迁移过程 MUST NOT 对表加排他锁

