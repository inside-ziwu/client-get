## Why

Admin 同行公司页当前固定每页 20 条，运营查看大量励销云同行公司时只能逐页点击，效率低。需要让分页组件支持配置每页数量，并支持输入页码直接跳转。

## What Changes

- 同行公司页分页从固定 `PAGE_SIZE=20` 改为可配置页大小。
- 每页数量仅允许 `20 / 50 / 100`，最大每页 `100`。
- 分页组件支持指定页码跳转。
- 前端查询参数、React Query key 与分页状态同步 `page` 和 `pageSize`。
- 后端 Admin V3 raw company 接口限制 `page_size <= 100`，防止手动请求绕过前端上限。

## Non-Goals

- 不修改 tenant 公司列表分页。
- 不修改 Tendata / 外贸通归档页分页交互。
- 不调整同行公司筛选条件、表格列、详情 Drawer 或数据排序。
- 不修改数据库 schema、采集 worker、清洗 worker 或线上数据。

## Capabilities

### New Capabilities

- `admin-peers-pagination-controls`: Admin 同行公司页必须支持可配置每页数量和指定页码跳转。

### Modified Capabilities

无。

## Impact

- **前端**：`frontend/apps/admin/src/pages/PeersData/index.tsx`；新增 admin 页面源码约束测试。
- **后端**：`backend/app/api/admin/collection.py` 的 `list_v3_raw_companies` 参数校验；新增/更新后端验证。
- **API**：继续使用既有 `page` / `page_size` 参数，新增 `page_size <= 100` 约束。
- **数据库 / Worker / 部署**：无 schema、worker 或外部服务改动。
