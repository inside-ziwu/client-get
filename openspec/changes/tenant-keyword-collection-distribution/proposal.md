## Why

waimaotong_clean_companies 中「关键词采集」数据（data_source_tags 含「外贸通关键词采集」，生产 4035+ 条且持续增长）在现有机制下永远不会进入 tenant 端：增量分发完全依赖关键词血缘（keyword_master_ids），而这批数据仅 30 条有血缘，且 lineage repair 的血缘回填只覆盖精准反推链路。同时 tenant 端无法区分公司的采集类型（admin 端已上线该能力）。

## What Changes

- `wmt_lineage_repair` 自愈循环新增「行业 fan-out」：data_source_tags 含「外贸通关键词采集」的整批数据视为 PCB 行业，推送给 `lower(trim(industry))` 匹配行业别名（pcb/电路板）且 status='active' 的全部租户；增量数据随循环自动分发
- 新增共享模块 `collection_source`：采集标签常量、jsonb SQL 片段、keyword/reverse 判定函数；admin service / tenant service / 行业 fan-out 三处引用同一真源
- tenant 公司列表与详情返回 `collection_type` 计算字段；列表新增「采集类型」筛选与列；详情页展示采集类型
- 顺手修复 `tenant_query_service.py` 4 处存量 jsonb 潜伏 bug（source_type/sources 三处 + product_tags 一处：生产库两列均为 jsonb，现有 `&&` text[] 操作符被调用即 500）
- alembic 迁移：`waimaotong_clean_companies.data_source_tags` 加 GIN 索引（jsonb_path_ops）

## Non-Goals

- 不透出来源关键词（matched_keywords 维持空数组）
- 不做关键词血缘回填（1360 条英文词不进 keyword_master）
- 不加行业分发开关（规则即语义：未来新 PCB 租户自动接收，工程审查 7A）
- 不做行业回收逻辑（单向分发，与现有关键词 fan-out 一致，工程审查 2A）
- 不搭 DB 集成测试基设（进 TODOS，工程审查 4A/D12）
- 不做行业规则数据化（第二采集行业出现时触发，TODOS D13）

## Capabilities

### New Capabilities

- `tenant-industry-fanout`: 关键词采集数据按行业规则自动分发到 tenant_companies
- `tenant-collection-type-display`: tenant 端按采集类型（关键词采集/精准反推）筛选和展示公司

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 worker | `wmt_lineage_repair.py` — 新增行业 fan-out SQL + 行业别名常量，更新模块 docstring |
| 后端共享模块 | 新增 `app/services/collection_source.py`；`admin_collection_service.py` 改为引用 |
| 后端服务 | `tenant_query_service.py` — collection_type 筛选/返回字段 + 4 处 jsonb bug 修复 |
| 后端 API | `GET /companies`（tenant ops）新增 `collection_type` 参数 |
| 数据库 | alembic 迁移：data_source_tags GIN 索引 |
| 前端类型 | `shared-api/src/tenant/companies.ts` — 参数与响应类型 |
| 前端页面 | `company-filters.tsx`（筛选三件套）、`companies/page.tsx`（加列）、`company-detail.tsx`（详情展示） |

## 决策依据

需求与工程审查全记录见 `docs/brainstorms/2026-06-09-tenant-keyword-collection-distribution-requirements.md`（D1-D7 需求决策 + 1A/2A/3A/4A/7A/8A/9A/10A/11B 审查决策）。
