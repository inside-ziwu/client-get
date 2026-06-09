## Context

admin 端客户数据页展示 `waimaotong_clean_companies` 表的清洗后公司数据。当前页面标题暴露内部表名，缺少按采集类型筛选的能力，电话列占位但信息价值低。

现有代码结构：
- 后端 `list_wmt_clean_companies()` 使用 `where_parts` + `params` 模式构建动态过滤
- `data_source_tags text[]` 字段已存在于表和 API 响应中
- `tenant_query_service.py:248` 已有 `data_source_tags && ARRAY[...]::text[]` 的过滤先例

## Goals / Non-Goals

**Goals:**
- 让 admin 用户能按采集类型筛选和识别数据来源
- 简化页面标题，去掉内部技术命名
- 优化表格列宽，减少内容截断

**Non-Goals:**
- 不重构 data_source_tags 标签体系
- 不改详情 Sheet
- 不补全其他筛选条件的测试

## Decisions

### D1: 采集类型判断规则
- 选择：`data_source_tags` 包含 `"外贸通关键词采集"` → 关键词采集，否则 → 精准反推
- 替代方案：基于 `source_type` 或其他字段判断 — 不可行，`data_source_tags` 是唯一标识采集来源的字段
- NULL 和空数组均视为精准反推（工程审查 D2）

### D2: 后端返回 collection_type 计算字段
- 选择：后端在 `list_wmt_clean_companies()` 返回中计算并附加 `collection_type` 字段
- 替代方案：前端从 `data_source_tags` 推导 — 违反 DRY，筛选和展示的判断逻辑写两份
- 来源：工程审查 D5，Codex outside voice

### D3: collection_type 筛选的 SQL 实现
- 关键词采集：`'外贸通关键词采集' = ANY(data_source_tags)`
- 精准反推：`(data_source_tags IS NULL OR NOT '外贸通关键词采集' = ANY(data_source_tags))`
- 复用 `where_parts` + `params` 模式，collection_type 值为固定枚举不需要参数化

## Risks / Trade-offs

- [风险] 中文标签 `"外贸通关键词采集"` 硬编码在 SQL 中 → 提取为常量，未来如需改名只改一处
- [风险] 混合标签（同时包含多个来源）→ 工程审查 D6 确认：包含即为关键词采集
