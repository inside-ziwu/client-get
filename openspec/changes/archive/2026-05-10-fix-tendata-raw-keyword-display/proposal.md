## Why

Admin 腾道数据页的关键词列当前显示为 `—`，但线上 `tendata_raw_companies` 已通过 `keyword_master_id` 外键关联到 `keyword_master`。该问题会让运营误判腾道 raw 数据缺少关键词归因，影响线上数据排查与采集结果验收。

## What Changes

- 修正 V3 admin raw 公司列表中腾道数据的关键词展示来源：基于 `tendata_raw_companies.keyword_master_id -> keyword_master.id` 读取关键词信息。
- 调整 admin 腾道数据页关键词列，展示 API 返回的 `keyword_master.keyword` 对应值。
- 保持线上 raw 表 schema 不变；不新增 `tendata_raw_companies.keyword_normalized`，不迁移线上数据。
- 补充 API contract 测试，覆盖腾道 raw 有 `keyword_master_id` 时列表响应可返回可展示关键词。

## Capabilities

### New Capabilities

- `admin-raw-company-keyword-display`: 约束 admin raw 公司列表按线上 `keyword_master_id` 外键展示关键词，避免把 raw 表不存在的归一字段当作展示来源。

### Modified Capabilities

- 无。

## Impact

- 后端：`backend/app/services/admin_collection_service.py` 中 V3 raw 公司列表的 tendata 分支查询与响应字段。
- 前端：`frontend/apps/admin/src/pages/CollectionArchive/index.tsx` 腾道数据页关键词列；`frontend/packages/shared-api/src/admin/collection.ts` raw 行类型。
- 测试：后端 admin raw 公司列表 API contract 测试。
- 不涉及：数据库 schema 变更、线上数据迁移、腾道采集任务触发、raw → clean 清洗、租户公司物化。
