## ADDED Requirements

### Requirement: 系统 SHALL 从 wmt 血缘生成租户可见公司
系统 SHALL 只把匹配当前租户 active 关键词的 `waimaotong_clean_companies` 写入 `tenant_companies`，且 `tenant_companies.clean_company_id` MUST 指向当前存在的 `waimaotong_clean_companies.id`。

#### Scenario: clean 主路径生成租户公司
- **WHEN** `waimaotong_clean_companies.sys_company_id` 能关联到 `waimaotong_raw_companies.sys_company_id`，且 `raw.source_competitor` 能精确匹配 `lixiaoyun_api_clean_companies.entname_eng`
- **THEN** 系统 MUST 使用 `lixiaoyun_api_clean_companies.keyword_master_ids` 匹配 active `tenant_keyword` 并写入对应租户的 `tenant_companies`

#### Scenario: raw fallback 生成租户公司
- **WHEN** `raw.source_competitor` 未匹配 lixiaoyun clean，但能精确匹配 `lixiaoyun_api_companies.entname_eng`
- **THEN** 系统 MUST 使用 `lixiaoyun_api_companies.keyword_master_id` 匹配 active `tenant_keyword` 并写入对应租户的 `tenant_companies`

#### Scenario: 无血缘公司不进入租户列表
- **WHEN** wmt clean 无法通过 clean 主路径或 raw fallback 获得关键词血缘
- **THEN** 系统 MUST NOT 写入 `tenant_companies`

### Requirement: 系统 MUST 保持 wmt fan-out 幂等
系统 MUST 保证基于 WMT 血缘的 tenant relation fan-out 可重复运行，且不会为同一租户和同一当前 WMT 公司重复创建关系。

#### Scenario: 重复 fan-out 不重复插入
- **WHEN** repair 或 fan-out 对同一批 active keyword 与 WMT 公司重复执行
- **THEN** `tenant_companies` MUST 最多保留一条 `(tenant_id, clean_company_id)` 关系

#### Scenario: fan-out 写入后可 JOIN wmt
- **WHEN** fan-out 为租户生成公司可见关系
- **THEN** 新增或恢复的 `tenant_companies.clean_company_id` MUST 能 JOIN 到当前 `waimaotong_clean_companies.id`
