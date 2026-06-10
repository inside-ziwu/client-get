## ADDED Requirements

### Requirement: 关键词采集数据按行业分发到租户
系统 SHALL 在 wmt_lineage_repair 自愈循环中，将 `data_source_tags` 包含「外贸通关键词采集」的公司分发给行业匹配的全部 active 租户。

#### Scenario: PCB 行业租户收到全量关键词采集数据
- **WHEN** 自愈循环执行一轮，存在 `status='active'` 且 `lower(trim(industry))` 命中行业别名（pcb/电路板）的租户
- **THEN** 该租户的 tenant_companies 包含全部关键词采集公司，data_status 按现有三分支规则分级（missing_contacts / insufficient_data / ready）

#### Scenario: 行业不匹配的租户不受影响
- **WHEN** 租户 industry 归一化后不在行业别名表内，或租户 status != 'active'
- **THEN** 该租户的 tenant_companies 不新增关键词采集公司

#### Scenario: 行业写法归一化
- **WHEN** 租户 industry 值为「PCB」「pcb」「 PCB 」「电路板」等大小写/空格变体
- **THEN** 归一化（lower + trim）后均命中别名，正常分发

#### Scenario: 幂等重复执行
- **WHEN** 自愈循环连续执行多轮
- **THEN** tenant_companies 不产生重复行；仅当 data_status 计算结果变化时更新该行

#### Scenario: 增量数据自动分发
- **WHEN** 外部采集程序写入新的关键词采集公司
- **THEN** 下一轮自愈循环自动将其分发给行业匹配的租户，无需人工触发

#### Scenario: 新建 PCB 租户自动接收
- **WHEN** 新租户创建且 industry 命中行业别名
- **THEN** 下一轮自愈循环自动推送全量关键词采集数据（规则即语义，工程审查 7A）

### Requirement: data_source_tags GIN 索引
系统 SHALL 通过 alembic 迁移为 `waimaotong_clean_companies.data_source_tags` 创建 GIN 索引（jsonb_path_ops），支撑循环内 jsonb 包含查询及 admin/tenant 筛选。

#### Scenario: 迁移幂等
- **WHEN** 迁移重复执行（CREATE INDEX IF NOT EXISTS）
- **THEN** 不报错、不产生重复索引
