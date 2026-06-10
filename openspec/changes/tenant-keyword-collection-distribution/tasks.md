## 1. 共享模块（T1）

- [x] 1.1 新建 `backend/app/services/collection_source.py`：`KEYWORD_COLLECTION_TAG` 常量、`KEYWORD_TAG_JSONB` SQL 片段、`compute_collection_type()` 函数
- [x] 1.2 `admin_collection_service.py` 删除本地 `_keyword_tag_jsonb` 与行内判定，改引用共享模块（行为不变）

## 2. 行业 fan-out（T2 + T3）

- [x] 2.1 `wmt_lineage_repair.py` 新增 `_PCB_INDUSTRY_ALIASES` 常量（全小写，附「新增行业别名需登记 / 第二行业出现时数据化」注释）与 `_SQL_FAN_OUT_INDUSTRY`（design.md §2 SQL：jsonb 包含 + lower(trim) 归一化 + active 过滤 + data_status CASE + ON CONFLICT 幂等，无 visibility_status）
- [x] 2.2 `run_wmt_lineage_repair_on_connection` 在 delete_stale 之前执行行业 fan-out，stats 新增 `industry_fan_out` 计数，模块 docstring 更新为四步流程
- [x] 2.3 新建 alembic 迁移：`data_source_tags` GIN 索引（jsonb_path_ops，IF NOT EXISTS）

## 3. tenant 后端（T4 + T5）

- [x] 3.1 修复 `tenant_query_service.py` 4 处 jsonb 误用（:248 source_type、:251/:636 sources、:231 product_tags，见 design.md §3.1），全文件 grep ` && ` 确认无第五处
- [x] 3.2 `companies_page` 新增 `collection_type` 参数与 WHERE 分支（keyword/reverse/None），行输出新增 `collection_type` 字段
- [x] 3.3 `v3_company_detail` 返回 dict 新增 `collection_type`
- [x] 3.4 `app/api/tenant/ops.py` GET /companies 新增 `collection_type: str | None = None` 透传

## 4. tenant 前端（T6）

- [x] 4.1 `shared-api/src/tenant/companies.ts`：行/详情类型新增 `collection_type: 'keyword' | 'reverse'`，列表参数新增 `collection_type?: string`
- [x] 4.2 `company-filters.tsx`：FilterValues/EMPTY_FILTERS/buildParams 新增 collection_type，筛选选项硬编码（不限/关键词采集/精准反推）
- [x] 4.3 `companies/page.tsx`：新增「采集类型」列，列头数组与空态 colSpan 同步
- [x] 4.4 `company-detail.tsx`：详情展示采集类型

## 5. 测试（T7）

- [x] 5.1 新建 `backend/tests/test_collection_source.py`：判定函数 5 口径用例 + SQL 片段常量断言；admin `test_wmt_clean_filter.py` 中计算类测试迁移至此（过滤 SQL 断言保留原文件并改断言引用共享常量）
- [x] 5.2 新建 `backend/tests/test_lineage_repair_industry_fanout.py`：SQL 断言（jsonb 包含/lower(trim/= ANY/active/CASE 三分支/ON CONFLICT/无 visibility_status）+ 执行顺序 + 别名全小写
- [x] 5.3 新建 `backend/tests/test_tenant_companies_filter.py`：collection_type 三分支 WHERE 断言 + 行输出字段 + **[CRITICAL 回归]** source_type/sources/product_tags 修复后断言（不含 `&& ARRAY`、不含 `&& :`）
- [x] 5.4 ops.py collection_type 参数透传断言；运行 `pytest backend/tests/`（154 passed；唯一失败 `test_dashboard_email_stats.py::test_percentage_calculation` 经 git stash 验证为 main 存量问题，与本 change 无关，归属 email-status-reconciliation 范畴）

## 6. 验证（T8，人工）

- [x] 6.1 dev 库执行一轮 lineage repair：插入 2 条测试关键词采集公司（含双标签/无联系人用例），industry_fan_out=4（2 公司×2 PCB 租户），data_status 分级正确（ready/missing_contacts），第二轮 industry_fan_out=0 幂等通过；测试数据已清理
- [x] 6.2 dev server 手动 QA 通过（列表采集类型列/筛选三态/叠加筛选/详情展示，用户 2026-06-10 确认）；注：行业 fan-out 已因遗留 reload 进程提前在生产执行（3 租户×4045 条，数据=预期终态，D15 决策保留）
