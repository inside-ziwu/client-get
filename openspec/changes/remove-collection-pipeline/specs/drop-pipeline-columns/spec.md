## ADDED Requirements

### Requirement: 系统 SHALL 删除 waimaotong_raw_companies 的 20 个 CG 原生列

在管道代码删除且无任何代码引用后，通过 Alembic revision 物理删除以下 20 列：

`keyword_master_id`, `collection_type`, `source_id`, `country_iso3`, `address`, `emails`, `trade_amount_3y_usd`, `trade_count`, `has_trade_data`, `customs_data`, `search_payload`, `detail_payload`, `trade_payload`, `raw_payload`, `detail_fetched_at`, `trade_status`, `trade_fetched_at`, `contacts_status`, `contacts_fetched_at`, `enrichment_error`

删除后 waimaotong_raw_companies MUST 从 53 列减到 33 列。

#### Scenario: 列删除成功

- **GIVEN** 管道代码已删除，无任何代码引用上述 20 列
- **WHEN** 执行 Alembic upgrade
- **THEN** waimaotong_raw_companies 表恰好剩余 33 列

#### Scenario: 删除前代码中无残留引用

- **GIVEN** 管道代码已删除
- **WHEN** 在 `backend/app/` 中 grep 上述 20 个列名
- **THEN** 除 admin_collection_service.py 的 SQL 已修改外，无任何代码引用

### Requirement: 系统 SHALL 删除 waimaotong_raw_contacts 的 5 个兼容列

通过同一 Alembic revision 物理删除以下 5 列：

`sys_contact_id`, `contact_id`, `sys_company_id`, `api_company_id`, `company_id`

删除后 waimaotong_raw_contacts MUST 从 21 列减到 16 列。

#### Scenario: 列删除成功

- **GIVEN** 管道代码已删除，无任何代码引用上述 5 列
- **WHEN** 执行 Alembic upgrade
- **THEN** waimaotong_raw_contacts 表恰好剩余 16 列

#### Scenario: downgrade 可恢复表结构

- **GIVEN** upgrade 已执行
- **WHEN** 执行 Alembic downgrade
- **THEN** 25 列结构恢复（数据不可恢复）

### Requirement: 系统 SHALL 修改 admin_collection_service.py 中引用被删列的 SQL

`admin_collection_service.py` 保留（管理端数据查看），但其 SQL 中引用了部分即将删除的列（如 waimaotong 分支的 SELECT/WHERE），MUST 在列删除前同步修改。

#### Scenario: 管理端数据查看正常

- **GIVEN** admin_collection_service.py 中引用被删列的 SQL 已修改
- **WHEN** 访问管理端 raw 数据浏览端点
- **THEN** 接口正常返回，无 SQL 报错

#### Scenario: SQL 中无被删列引用

- **GIVEN** 修改完成
- **WHEN** 在 admin_collection_service.py 中 grep 被删的 25 个列名
- **THEN** 无任何引用
