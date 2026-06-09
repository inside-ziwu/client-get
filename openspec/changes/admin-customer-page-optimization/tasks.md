## 1. 后端 API

- [x] 1.1 在 `list_wmt_clean_companies()` 中新增 `collection_type` 参数，添加 `data_source_tags` 过滤条件（keyword: `ANY()` / reverse: `IS NULL OR NOT ANY()`）
- [x] 1.2 在 `list_wmt_clean_companies()` 的行处理循环中计算并返回 `collection_type` 字段（keyword/reverse）
- [x] 1.3 在路由 `list_wmt_clean_companies` 中新增 `collection_type: str | None = None` 查询参数并传入 service

## 2. 前端类型

- [x] 2.1 在 `WmtCleanCompanyRow` 类型中新增 `collection_type: string` 字段
- [x] 2.2 在 `listWmtCleanCompanies` 的参数类型中新增 `collection_type?: string`

## 3. 前端页面

- [x] 3.1 修改页面标题为「客户数据」，描述为「清洗后的公司数据及联系人。」
- [x] 3.2 在 `FilterValues` 中新增 `collection_type` 字段，新增 Select 筛选下拉（不限/关键词采集/精准反推）
- [x] 3.3 将 `collection_type` 筛选条件传入 API 调用
- [x] 3.4 移除「电话」列，新增「采集类型」列（显示 row.collection_type === 'keyword' ? '关键词采集' : '精准反推'）
- [x] 3.5 优化表格列宽分配（公司名、域名、行业加宽，评级/评分/成立年份收窄）

## 4. 测试

- [x] 4.1 新建 `backend/tests/test_wmt_clean_filter.py`，测试 collection_type=keyword 和 collection_type=reverse 的过滤结果（含 NULL data_source_tags 行）
