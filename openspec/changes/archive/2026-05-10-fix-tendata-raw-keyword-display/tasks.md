## 1. 后端 Contract 测试

- [x] 1.1 在后端 API contract 测试中 seed `keyword_master(keyword='线路板')` 与一条关联该 `keyword_master_id` 的 `tendata_raw_companies`。
- [x] 1.2 调用 `/api/v1/raw/tendata/companies`，断言响应行保留 `keyword_master_id`。
- [x] 1.3 断言同一响应行返回 `keyword = '线路板'`。
- [x] 1.4 覆盖 `keyword_master_id IS NULL` 的 tendata raw 行仍可返回，且响应包含 `keyword: null`。

## 2. 后端 API 实现

- [x] 2.1 修改 `backend/app/services/admin_collection_service.py` 中 `list_v3_raw_companies` 的 tendata 分支，查询 `LEFT JOIN keyword_master km ON km.id = c.keyword_master_id`。
- [x] 2.2 在 tendata 分支 SELECT 中返回 `km.keyword AS keyword`。
- [x] 2.3 保持现有 `keyword_master_id` 字段返回，不改过滤参数和分页行为。
- [x] 2.4 确认本 change 不新增 Alembic migration，不修改 `tendata_raw_companies` schema。

## 3. 前端展示调整

- [x] 3.1 在 `frontend/packages/shared-api/src/admin/collection.ts` 和 `frontend/apps/admin/src/pages/CollectionArchive/index.tsx` 的 `RawCompanyRow` 类型中补充 `keyword?: string | null`，并停止使用腾道页本地 `keyword_normalized` 展示字段。
- [x] 3.2 修改 `frontend/apps/admin/src/pages/CollectionArchive/index.tsx` 中腾道数据页关键词列，展示 `row.keyword`；不得 fallback 到 `row.keyword_normalized`。
- [x] 3.3 保持 `keyword: null` 时显示 `—`。
- [x] 3.4 用 `rg` 核对 V3 raw tendata 列表是否还有页面继续依赖 `row.keyword_normalized` 展示关键词。

## 4. 验证

- [x] 4.1 运行新增或修改的后端目标测试，确认 `/api/v1/raw/tendata/companies` 返回 `keyword`。
- [x] 4.2 运行匹配的前端类型检查或 admin 构建，确认 `RawCompanyRow.keyword` 类型被接受。
- [x] 4.3 手工或浏览器验证 admin `/collection/tendata` 关键词列显示 `keyword_master.keyword`，无关键词时显示 `—`。
- [x] 4.4 更新本 `tasks.md` 勾选已完成项，并记录无法验证项的原因。
