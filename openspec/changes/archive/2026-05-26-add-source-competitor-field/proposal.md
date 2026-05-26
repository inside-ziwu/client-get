## Why

tenant 端公司列表和详情页缺少"来源同行"信息，用户无法得知每家公司是通过哪个同行厂商反推获得的。该字段数据已存在于 `waimaotong_raw_companies.source_competitor`，覆盖率 99.96%，只需透传到前端即可。

## What Changes

- 后端列表/详情查询 SQL 增加 LEFT JOIN `waimaotong_raw_companies`，取 `source_competitor` 字段
- 后端 API 响应增加 `source_competitor` 字段
- 前端 Company 类型增加 `source_competitor` 可选字段
- 前端公司列表页新增"来源同行"列
- 前端公司详情页新增"来源同行"展示

## Non-Goals

- 不做数据冗余（不在 `waimaotong_clean_companies` 表新增字段）
- 不做数据库迁移
- 不支持按来源同行筛选/搜索（后续需求）
- 不处理 `peer_companies` 表与前端的直接关联

## Capabilities

### New Capabilities

- `source-competitor-display`: 在 tenant 端公司列表和详情页展示来源同行字段

### Modified Capabilities

- `tenant-companies-list`: 列表查询 SQL 和响应结构增加 `source_competitor` 字段

## Impact

| 模块 | 影响范围 | 说明 |
|------|---------|------|
| 后端 | `backend/app/services/tenant_query_service.py` | 列表和详情查询 SQL 加 JOIN、响应加字段 |
| 前端共享包 | `frontend/packages/shared-api/src/tenant/companies.ts` | Company 类型加字段 |
| 前端 tenant | `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` | 列表加列 |
| 前端 tenant | 公司详情页组件 | 详情加字段展示 |

依赖顺序：后端先行 → 前端跟进（前后端可并行开发，前端 `source_competitor` 为可选字段）
