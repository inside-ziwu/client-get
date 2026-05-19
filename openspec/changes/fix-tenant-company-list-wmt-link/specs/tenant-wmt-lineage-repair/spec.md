## ADDED Requirements

### Requirement: 系统 SHALL 补全当前 wmt 数据血缘
系统 SHALL 对当前线上因采集字段缺失造成的 wmt 血缘缺口做一次性补全，补全后才能生成 tenant 可见关系。

#### Scenario: APCB raw fallback 补全
- **WHEN** `source_competitor = 'APCB ELECTRONICS (KUNSHAN) CO., LTD.'` 无法匹配 lixiaoyun clean 但能匹配 lixiaoyun raw
- **THEN** 系统 SHALL 使用 lixiaoyun raw 的 `keyword_master_id` 补齐该批 wmt 数据的关键词血缘

#### Scenario: Kinwong 未确认不自动补全
- **WHEN** `source_competitor = 'SHENZHEN KINWONG ELECTRONIC CO LTD'` 无法精确匹配 lixiaoyun clean 或 raw
- **THEN** 系统 MUST 将该批数据列为待确认补全项，且 MUST NOT 使用模糊匹配自动写入关键词血缘

### Requirement: 系统 SHALL 修复旧 tenant_companies 悬空关联
系统 SHALL 清理或隐藏 `tenant_companies.clean_company_id` 指向旧 `clean_companies.id` 的悬空关系，并按 wmt 血缘重建指向 `waimaotong_clean_companies.id` 的关系。

#### Scenario: 修复后列表 JOIN 非空
- **WHEN** 数据补全和关系修复完成
- **THEN** active 租户的 `tenant_companies` MUST 能通过 `clean_company_id = waimaotong_clean_companies.id` JOIN 出 tenant 公司列表数据

#### Scenario: 修复不破坏租户隔离
- **WHEN** 同一 wmt company 匹配多个关键词或多个租户
- **THEN** 系统 MUST 按 active `tenant_keyword` 分租户写入，并保持 `(tenant_id, clean_company_id)` 幂等

### Requirement: 系统 MUST 保留生产修复前快照
系统 MUST 在生产补数或修复 tenant relation 前保留受影响数据快照，以便回滚。

#### Scenario: 修复前生成快照
- **WHEN** 生产修复脚本以写入模式执行
- **THEN** 系统 MUST 先保存将被隐藏、更新或新增影响的 `tenant_companies` 标识和原始字段

#### Scenario: 未授权不执行写入
- **WHEN** 用户未显式授权生产补数或修复
- **THEN** 系统 MUST 只允许 dry-run，不得修改线上数据库
