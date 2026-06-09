## Why

admin 端「外贸通客户数据」页面存在多个可用性问题：标题暴露内部技术表名（waimaotong_clean_companies）、缺少按采集类型筛选的能力、电话列信息密度低且占据宽度、列宽分配不合理导致高价值字段被截断。

## What Changes

- 页面标题从「外贸通客户数据」改为「客户数据」，描述去掉技术表名前缀
- 后端新增 `collection_type` 查询参数，基于 `data_source_tags` 字段过滤（关键词采集 / 精准反推）
- 后端在列表响应中返回 `collection_type` 计算字段（业务规则单一真源，D5）
- 前端新增「采集类型」Select 筛选下拉
- 前端移除「电话」列，新增「采集类型」列
- 优化表格列宽分配
- 新增后端测试覆盖 collection_type 筛选的 NULL 安全

## Non-Goals

- 不重构 data_source_tags 的标签体系
- 不改动详情 Sheet 的展示内容
- 不补全已有 6 个筛选条件的测试
- 不搭建前端测试基础设施
- 不为 data_source_tags 新增数据库索引（admin 查询量低）

## Capabilities

### New Capabilities

- `admin-customer-filter-collection-type`: 按采集类型（关键词采集/精准反推）筛选和展示客户数据

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 API | `GET /api/v1/collection/wmt-clean-companies` 新增 `collection_type` 参数，响应新增 `collection_type` 字段 |
| 后端服务 | `admin_collection_service.py` — `list_wmt_clean_companies()` 新增过滤逻辑 |
| 前端页面 | `client-page.tsx` — 标题、筛选、列定义、列宽 |
| 前端类型 | `shared-api/src/admin/collection.ts` — API 参数和响应类型 |
| 后端测试 | 新增 `test_wmt_clean_filter.py` |
| 数据库 | 无变更，`data_source_tags text[]` 已存在 |

依赖顺序：后端 API（T1+T2） → 前端类型（T3） → 前端页面（T4），测试（T5）可并行。

关联决策：D2（NULL 安全）、D5（后端返回计算字段）、D6（混合标签处理）。
