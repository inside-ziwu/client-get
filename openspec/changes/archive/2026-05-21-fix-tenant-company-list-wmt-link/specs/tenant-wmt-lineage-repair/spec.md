## ADDED Requirements

### Requirement: 系统 SHALL 定时修复 WMT 血缘与租户可见关系
系统 SHALL 提供后台 repair，用于在外部流程重建或批量更新 WMT 表后，在最多几分钟内恢复 tenant 公司列表。

#### Scenario: repair 补齐当前 WMT 关键词血缘
- **WHEN** `waimaotong_clean_companies.keyword_master_ids` 为空或缺失，但可通过 clean 主路径或 raw fallback 推导出关键词
- **THEN** repair SHALL 将推导出的 keyword master ids 回写到当前 WMT clean 记录

#### Scenario: repair 重建当前 WMT tenant relation
- **WHEN** 当前 WMT 公司已具备关键词血缘，且租户存在匹配的 active `tenant_keyword`
- **THEN** repair SHALL 为该租户写入或恢复 visible `tenant_companies` 关系，且 `clean_company_id` SHALL 指向当前 WMT id

#### Scenario: repair 隐藏 stale visible relation
- **WHEN** visible `tenant_companies.clean_company_id` 已无法 JOIN 当前 `waimaotong_clean_companies.id`
- **THEN** repair SHALL 将该关系隐藏，避免 tenant 列表继续依赖过期 WMT id

### Requirement: 系统 MUST 防止多实例并发 repair
系统 MUST 在 repair 执行期间使用 PostgreSQL advisory lock，避免多个 backend 实例同时执行同一轮 WMT lineage repair。

#### Scenario: 已有实例持有 repair lock
- **WHEN** 一个 backend 实例已经持有 WMT lineage repair advisory lock
- **THEN** 其他实例 MUST 跳过本轮 repair，不得并发写入相同 lineage 和 tenant relation

### Requirement: WMT keyword_master_ids MUST 不为 NULL
`waimaotong_clean_companies.keyword_master_ids` MUST 使用空数组表示无血缘，而不是使用 NULL。

#### Scenario: migration 规范化 keyword_master_ids
- **WHEN** 数据库迁移运行到 WMT lineage repair 版本
- **THEN** 现有 NULL `keyword_master_ids` MUST 被更新为 `{}`
- **AND** 列 MUST 设置为 `NOT NULL DEFAULT '{}'`
