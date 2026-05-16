## Why

tenant 公司列表页当前联系人信息展示不正确，影响租户判断客户是否可触达以及后续外联操作。本 change 只收口联系人数量和联系人明细展示问题。

## What Changes

- 修正 tenant 公司列表的联系人展示，确保列表数量、详情联系人明细、空态与后端字段契约一致。
- 修正腾道采集结果中的联系人明细落库链路，确保 provider 已返回的 `contacts` 不只写成 `contacts_count`，还会进入 raw payload 并清洗到 `clean_contacts`。
- 对齐 tenant 公司 API 返回结构、前端类型与渲染逻辑，避免前端读取旧字段或错误 fallback。
- 增加覆盖联系人数量和联系人明细字段的后端/前端验证，防止 admin 有联系人数据但 tenant 不正确展示的回归。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `tenant-company-v3-contract`: 补充 tenant 公司列表和详情必须展示当前联系人数量与联系人明细字段的要求，并禁止回退到旧字段或错误别名。

## Impact

- **前端**：`frontend/apps/tenant/src/pages/Companies/index.tsx` 及相关 tenant API 类型/渲染逻辑。
- **后端**：`backend/app/services/tenant_query_service.py`、`backend/app/api/tenant/ops.py`、`backend/app/services/collection_service.py`、`backend/app/services/cleanup_service.py` 及对应测试。
- **规格**：新增 `openspec/changes/fix-tenant-company-list-display/specs/tenant-company-v3-contract/spec.md` delta。
- **不涉及**：数据库 schema、admin 采集页面能力、联系人分类规则、评分模板。
