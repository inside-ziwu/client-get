## Why

Tenant 公司列表页目前只有基础的关键词搜索 + 国家多选，表格列少、无分页、详情仅展示 6 个字段且不可编辑，缺少群组操作和拉黑功能。迁移 `20260519_0045` 已将数据源切到 `waimaotong_clean_companies`，但 UI 和 API 响应格式未跟进，导致 wmt 表丰富的 AI 评估、贸易数据等字段无法呈现给租户用户。

参照 `docs/mock/tenant-companies.html` 的目标设计，需要全面升级公司列表页，使其具备完整的筛选、展示、编辑和操作能力。

## What Changes

**后端 API**
- 扩展 `GET /companies/filters` 返回 `sub_industries`、`product_tags`、`grades` 的 options 列表
- 对齐 `GET /companies` 列表响应字段，补充 `phone`、`sub_industry`、`trade_amount_3y_usd`、`trade_count`、`description`、`data_source_tags` 等 wmt 字段
- 对齐 `GET /companies/{id}` 详情响应字段，补充 AI 评估字段（`score_details`、`company_type_analysis`、`email_priority`、`sales_approach`、`match_reasons`、`potential_needs`、`recommended_products`、`risk_factors`、`main_business`）和贸易数据（`trade_summary`）
- 扩展 `PATCH /prospects/{id}` 支持 `score_adjustment` 字段（-20 ~ +20）

**前端 Tenant 公司列表页**
- 筛选面板：搜索框 + 国家 + 细分行业 + 关键词 + 评级 + 进口额范围 + 进口次数范围 + 联系人范围 + 成立年范围
- 表格列：☐ 多选 | 公司名+域名 | 国家 | 细分行业 | 关键词 | 评级 | 总分 | 操作
- 页码分页（参考 admin 的分页模式）
- 批量选择 + 批量加入群组
- 660px 详情 Drawer：基本信息（2列）、AI 评估、贸易数据、标签（可编辑）、备注（可编辑）、评分调整、联系人表
- 加入群组 Modal（单条 + 批量）
- 拉黑确认 Modal

**前端共享类型**
- 更新 `Company` 接口和 `CompanyListFilters` 类型，对齐后端字段

## Non-Goals

- 不新增"精准客户/普通"状态概念（后期单独做）
- 不改变筛选参数列表（后端 query params 保持不变）
- 不做移动端适配
- 不触碰 admin 端代码
- 不修改 `docs/` 下的任何文件

## Capabilities

### New Capabilities

- `tenant-company-filters`: 筛选面板 UI（2 行 9 个筛选控件 + 查询/重置按钮）及 filters API 的 options 扩展
- `tenant-company-list`: 表格列对齐 mock、批量选择、页码分页
- `tenant-company-detail`: 660px 详情 Drawer（基本信息 + AI 评估 + 贸易数据 + 可编辑标签/备注/评分调整 + 联系人表）
- `tenant-company-group-ops`: 加入群组 Modal（单条 + 批量），调用现有 groups API
- `tenant-company-blacklist`: 拉黑确认 Modal，调用现有 blacklist API

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 层 | 影响范围 | 说明 |
|----|---------|------|
| 后端 API | `backend/app/api/tenant/ops.py` | 无需改路由，响应格式由 service 层控制 |
| 后端 Service | `backend/app/services/tenant_query_service.py` | `companies_page`、`v3_company_detail` 的 SELECT 和返回字典需扩展字段 |
| 后端 Service | `backend/app/services/tenant_ops_service.py` | `companies_filters` 扩展 options；`update_prospect` 支持 score_adjustment |
| 数据库 | `tenant_companies` 表 | 需新增 `score_adjustment` 列（smallint, 默认 0）；需要 Alembic 迁移 |
| 前端类型 | `frontend/packages/shared-api/src/tenant/companies.ts` | `Company` 和 `CompanyListFilters` 接口扩展 |
| 前端类型 | `frontend/packages/shared-types/src/models.ts` | 可能需要新增 wmt 字段类型 |
| 前端页面 | `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` | 全面重写（~70 行 → ~500+ 行） |
| 前端组件 | `frontend/apps/tenant/src/components/` | 可能抽取 CompanyDetailDrawer、GroupModal、BlacklistModal 等组件 |
| 依赖顺序 | 后端先行 → 前端跟进 | 数据库迁移 → 后端 service → 前端类型 → 前端 UI |
