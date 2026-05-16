## Context

线上 `clientget` schema 显示，`tendata_raw_companies` 通过 `keyword_master_id` 外键关联 `keyword_master(id)`，并不存在 `keyword_normalized` 字段。当前 admin 腾道数据页调用 V3 raw 公司列表接口 `/api/v1/raw/tendata/companies`，前端关键词列读取 `row.keyword_normalized`；后端 tendata 分支只返回 `keyword_master_id`，没有 join `keyword_master` 返回可展示关键词，因此页面显示 `—`。

该 change 的约束是以线上 schema 为准，只修复 admin raw 列表展示字段断链，不改变 raw 表结构、不迁移数据、不触发采集或清洗。

## Goals / Non-Goals

**Goals:**

- V3 admin 腾道 raw 公司列表接口基于 `tendata_raw_companies.keyword_master_id -> keyword_master.id` 返回可展示关键词。
- Admin 腾道数据页关键词列展示 `keyword_master.keyword` 对应值。
- 保留现有 `keyword_master_id` 响应字段，便于排查与筛选。
- 用后端 API contract 测试覆盖有 `keyword_master_id` 的腾道 raw 行应返回可展示关键词。

**Non-Goals:**

- 不修改 `tendata_raw_companies`、`keyword_master` 或其他数据库 schema。
- 不新增 `tendata_raw_companies.keyword_normalized`。
- 不迁移或修补线上数据。
- 不处理 raw → clean 清洗、`clean_company_keywords`、`tenant_companies` 物化。
- 不调整采集任务、调度任务或 worker 行为。

## Decisions

### D1. 展示关键词从 `keyword_master` 读取

后端 V3 raw 公司列表的 tendata 分支应在查询中 `LEFT JOIN keyword_master km ON km.id = c.keyword_master_id`，并返回 `km.keyword AS keyword`。这样实现直接对应线上外键关系，避免把 raw 表不存在的 `keyword_normalized` 当作展示来源。

备选方案：只在前端根据 `keyword_master_id` 再发请求查关键词。该方案会增加列表页请求次数或引入批量接口，不符合当前问题的最小修复范围。

### D2. 保持 `keyword_master_id` 原样返回

接口继续返回 `keyword_master_id`。它是线上 raw 行的真实关联字段，也是后端过滤参数和排查数据归因时需要的字段。

备选方案：只返回 `keyword`，隐藏 `keyword_master_id`。该方案会降低排查能力，不采用。

### D3. 前端关键词列展示 `keyword`

Admin 腾道数据页关键词列应读取 API 返回的 `keyword` 字段。`keyword_normalized` 不再作为腾道 raw 页展示字段来源。

备选方案：后端补 `keyword_normalized` 以适配现有前端读取。该方案能快速消除 `—`，但会继续让页面依赖与 raw schema 不一致的字段名，不采用为目标方案。

## Risks / Trade-offs

- [接口字段兼容风险] 其他页面或调用方可能仍读取 `keyword_normalized` → 本 change 仅调整已定位的 admin 腾道数据页；实施时用 `rg` 核对 V3 raw tendata 响应调用点。
- [空关联显示] 如果未来存在 `keyword_master_id IS NULL` 或 FK 被置空的 raw 行，`keyword` 会为空 → 页面继续显示 `—`，同时保留 `keyword_master_id` 为空的排查信号。
- [测试数据与线上差异] 本地测试库可能没有线上数据 → contract 测试应自行 seed `keyword_master` 与 `tendata_raw_companies`，不依赖线上数据。

## Migration Plan

无需数据库迁移。

部署顺序：

1. 后端先返回 `keyword` 字段并保留现有字段。
2. 前端关键词列改读 `keyword`。
3. 运行后端 API contract 测试与前端类型检查。

回滚策略：回滚后端和前端代码即可；无 schema 与数据变更需要回滚。

## Open Questions

无。
