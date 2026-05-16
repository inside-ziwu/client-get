## Why

Tenant 线上没有真实运营数据，继续兼容旧 tenant company 字段会让查询、前端类型和验收口径继续漂移。已完成的 V3 字段收口需要独立 OpenSpec change 补登记，便于审查、归档和从 `v3-tenant-companies` 大 change 中追踪。

## What Changes

- **BREAKING**: tenant company 对外契约不再返回、展示或筛选 `grade` / `total_score` / `notes` / `is_precise_customer` / `score_adjustment*`。
- **BREAKING**: 后端不再引用 `tenant_companies.deleted_at` / `tc.deleted_at` 作为 tenant company 可见性语义，统一使用 `visibility_status`。
- `/prospects` 只返回 V3 字段：`id` / `name` / `country_iso3` / `score` / `model_score` / `business_status` / `data_status` / `created_at`。
- `/companies` 删除 `grade` query 参数，评分筛选只保留分数区间。
- 删除 `/emails/stats/by-grade` 后端路由、service 方法、前端请求和图表。
- `TenantMessagingService._recipients_from_filter()` 删除 `grade` 过滤，国家过滤改用 `country_iso3`。
- `ScoringService._load_company_context()` 只读取当前 `clean_companies` 字段，并删除 `tc.is_precise_customer` 与 `precise_customer` 评分条件分支。
- tenant Companies / CuratedCustomers / EmailMonitor 页面删除旧字段展示和调分入口。
- shared-api / shared-types 中 tenant company 契约统一到 `score` / `model_score` / `note` / `tags`。

## Capabilities

### New Capabilities
- `tenant-company-v3-contract`: tenant company API、前端页面和共享类型只使用 V3 字段契约。

### Modified Capabilities
- `tenant-company-status-semantics`: tenant company 可见性与状态查询不再依赖旧软删除字段或旧评级字段。

## Impact

- 后端：tenant ops、tenant query、tenant messaging、scoring service。
- 前端：tenant Companies、CuratedCustomers、EmailMonitor。
- 共享包：`packages/shared-api/src/tenant/*`、`packages/shared-types/src/*`。
- 测试：tenant business status semantics、V3 data foundation API contract。
