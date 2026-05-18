## ADDED Requirements

### Requirement: 系统 SHALL 通过 Alembic 迁移物理删除两张表共 21 个未使用列

系统 MUST 创建一个 Alembic revision，在 upgrade 中执行 `ALTER TABLE DROP COLUMN`：
- `waimaotong_raw_companies` 删除 13 列：`country_name`, `country_code`, `logo`, `origin`, `social_medias`, `tags`, `revenue`, `founded_date`, `legal_name`, `company_type`, `sic_codes`, `naics_codes`, `website_url`
- `waimaotong_raw_contacts` 删除 8 列：`job_title`, `country`, `region`, `score`, `emails`, `linkedin_url`, `twitter_url`, `facebook_url`

#### Scenario: 正常执行 upgrade 删除列

- **GIVEN** 线上两张表存在这 21 列
- **WHEN** 执行 `alembic upgrade head`
- **THEN** `waimaotong_raw_companies` 从 66 列减少到 53 列
- **THEN** `waimaotong_raw_contacts` 从 29 列减少到 21 列
- **THEN** 两张表上其余列的数据和约束不受影响

#### Scenario: 重复执行 upgrade（幂等性）

- **GIVEN** 迁移已执行过，21 列已不存在
- **WHEN** 再次执行 `alembic upgrade head`
- **THEN** Alembic 识别当前版本已是最新，不做任何操作

### Requirement: downgrade MUST 恢复 21 列的结构定义

downgrade 函数 MUST 加回 21 列，使用与删除前一致的列名、类型和默认值。数据不可恢复。

#### Scenario: 正常执行 downgrade 恢复列结构

- **GIVEN** upgrade 已执行，21 列已删除
- **WHEN** 执行 `alembic downgrade -1`
- **THEN** 两张表的列以正确的类型重新添加
- **THEN** 新加回的列值全部为 NULL（原数据不恢复）

#### Scenario: downgrade 后表结构与删除前一致

- **GIVEN** 执行了 downgrade
- **WHEN** 检查表结构（`\d waimaotong_raw_companies` 和 `\d waimaotong_raw_contacts`）
- **THEN** 21 列的列名和类型与删除前完全一致

### Requirement: 实施前 MUST 确认线上数据状况

在执行迁移前，MUST 先查询线上两张表这 21 列的非空数据行数，确认是否有需要保留的数据。

#### Scenario: 列中无非空数据

- **GIVEN** 查询结果显示 21 列全部为 NULL
- **WHEN** 决定是否执行迁移
- **THEN** 可直接执行，无数据丢失风险

#### Scenario: 列中存在非空数据

- **GIVEN** 查询结果显示某些列有非空值
- **WHEN** 决定是否执行迁移
- **THEN** MUST 先评估数据价值，必要时导出备份后再执行
