# Admin 客户数据页界面优化

**日期**: 2026-06-09
**范围**: 轻量级 UI 调整
**状态**: 待实施

## 目标

优化 admin 端客户数据页（`waimaotong_clean_companies`）的可用性：更准确的页面标题、新增采集类型维度的筛选与展示、精简无用列、改善列宽分配。

## 需求

### 1. 页面标题与描述修改

- 标题：「外贸通客户数据」→「客户数据」
- 描述：「waimaotong_clean_companies 清洗后的公司数据及联系人。」→「清洗后的公司数据及联系人。」

### 2. 新增筛选条件：采集类型

- 筛选名称：采集类型
- 判断逻辑：`data_source_tags` 包含 `"外贸通关键词采集"` → 关键词采集；不包含 → 精准反推
- 选项：「不限」（默认）、「关键词采集」、「精准反推」
- 后端需新增查询参数支持按 `data_source_tags` 过滤

### 3. 表格列调整

- 移除「电话」列
- 新增「采集类型」列，显示「关键词采集」或「精准反推」

### 4. 列宽优化

- 当前 13 列过多导致内容截断，移除电话列后重新分配宽度
- 公司名、域名、行业等高信息密度列适当加宽
- 评级、评分、成立年份等短内容列收窄

## 技术要点

- 前端页面：`frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`
- 后端 API：`GET /api/v1/collection/wmt-clean-companies`（`backend/app/api/admin/collection.py`）
- 后端服务：`backend/app/services/admin_collection_service.py` — `list_wmt_clean_companies()`
- 数据字段：`data_source_tags text[]` 已存在于 `waimaotong_clean_companies` 表
