## Why

admin 客户数据页、tenant 公司列表与 tenant 优选客户都在查看同一批 V3 clean company 数据，但当前筛选条件、参数命名与语义不一致，导致运营侧能筛出的客户集合无法在租户侧用同样条件复现。现在需要把三处筛选契约收口到同一套字段与语义，避免后续排查数据差异时把 UI 参数漂移误判为数据问题。

## What Changes

- 对齐 admin 客户数据页、tenant 公司列表、tenant 优选客户的筛选维度、控件命名、API 参数与后端查询语义。
- tenant 公司列表和 tenant 优选客户应补齐 admin 客户数据页已有但 tenant 缺失的筛选维度；admin 客户数据页也应调整为 tenant 当前 V3 筛选契约中更明确的多选 OR / 档位语义。
- 以 admin 客户数据页现有基础筛选为基准，补齐 tenant 两处页面缺失项，并将三处都收口到同一份 shared clean-company filter contract；tenant-only 私有筛选保留但不纳入基础筛选一致性范围。
- 抽取或沉淀共享筛选参数映射，避免三处页面继续各自维护一套互不兼容的字段名。
- 增加后端和前端验证，覆盖相同筛选条件在 admin clean companies 与 tenant companies 中的语义一致性。
- 不改变清洗、采集、评分、租户私有状态或数据归属逻辑。

## Capabilities

### New Capabilities
- `cross-surface-company-filter-alignment`: 约束 admin 客户数据页、tenant 公司列表、tenant 优选客户使用一致的 V3 公司筛选维度、参数和语义。

### Modified Capabilities
- `tenant-company-v3-contract`: 补充 tenant 公司列表与 tenant 优选客户筛选必须与 admin 客户数据页保持一致的要求，并明确 tenant 仍只能返回当前租户可见公司。

## Impact

- **前端**：`frontend/apps/tenant/src/pages/Companies/index.tsx`、`frontend/apps/tenant/src/pages/CuratedCustomers/index.tsx`、`frontend/apps/admin/src/pages/CollectionArchive/index.tsx`、`frontend/packages/shared-api/src/tenant/companies.ts`、`frontend/packages/shared-api/src/admin/collection.ts`；可能新增共享筛选常量或 mapper。
- **后端**：`backend/app/api/tenant/ops.py`、`backend/app/services/tenant_query_service.py`、`backend/app/api/admin/collection.py`、`backend/app/services/admin_collection_service.py`。
- **测试**：补充 tenant/admin 筛选参数映射、后端查询语义与前端构参测试；必要时增加手工验收记录。
- **不涉及**：数据库 schema、清洗队列、采集 worker、评分 worker、线上数据同步、镜像构建与上线。
