## ADDED Requirements

### Requirement: 系统 SHALL 从 wmt 血缘生成租户可见公司
系统 SHALL 只把匹配当前租户 active 关键词的 `waimaotong_clean_companies` 写入 `tenant_companies`，且 `tenant_companies.clean_company_id` MUST 指向 `waimaotong_clean_companies.id`。

#### Scenario: clean 主路径生成租户公司
- **WHEN** `waimaotong_clean_companies.sys_company_id` 能关联到 `waimaotong_raw_companies.sys_company_id`，且 `raw.source_competitor` 能精确匹配 `lixiaoyun_api_clean_companies.entname_eng`
- **THEN** 系统 MUST 使用 `lixiaoyun_api_clean_companies.keyword_master_ids` 匹配 active `tenant_keyword` 并写入对应租户的 `tenant_companies`

#### Scenario: raw fallback 生成租户公司
- **WHEN** `raw.source_competitor` 未匹配 lixiaoyun clean，但能精确匹配 `lixiaoyun_api_companies.entname_eng`
- **THEN** 系统 MUST 使用 `lixiaoyun_api_companies.keyword_master_id` 匹配 active `tenant_keyword` 并写入对应租户的 `tenant_companies`

#### Scenario: 无血缘公司不进入租户列表
- **WHEN** wmt clean 无法通过 clean 主路径或 raw fallback 获得关键词血缘
- **THEN** 系统 MUST NOT 写入 `tenant_companies`，并 MUST 输出 unresolved lineage 诊断记录

### Requirement: 系统 MUST 禁止旧 clean id 写入 tenant_companies
系统 MUST 防止任何 fan-out 路径继续把旧 `clean_companies.id` 写入 `tenant_companies.clean_company_id`。

#### Scenario: fan-out 写入后可 JOIN wmt
- **WHEN** fan-out 为租户生成公司可见关系
- **THEN** 新增或更新的 `tenant_companies.clean_company_id` MUST 能 JOIN 到 `waimaotong_clean_companies.id`

#### Scenario: 旧 clean only id 被拒绝
- **WHEN** 待写入的公司 id 只能 JOIN 到 `clean_companies.id` 而不能 JOIN 到 `waimaotong_clean_companies.id`
- **THEN** 系统 MUST NOT 将该 id 写入 `tenant_companies.clean_company_id`

### Requirement: 系统 SHALL 提供 dry-run 诊断
系统 SHALL 在实际写入前提供 dry-run 诊断，用于展示每个租户将新增、保留、隐藏或无法归因的 wmt 公司数量。

#### Scenario: dry-run 输出租户影响
- **WHEN** 运维执行 wmt lineage fan-out dry-run
- **THEN** 输出 MUST 包含每个 tenant slug 的预计 visible wmt 公司数量、新增数量、旧悬空数量和 unresolved source competitor 清单

#### Scenario: dry-run 不修改数据
- **WHEN** dry-run 执行完成
- **THEN** `tenant_companies`、`waimaotong_clean_companies`、`waimaotong_raw_companies` MUST 没有任何写入变化
