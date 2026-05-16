# Tasks · v3-data-foundation

> 范围：仅数据基础层 schema + collection run/task + API contract。实现型 worker / cleanup / Sealos / AI enrichment 不在本 change。
> 审查状态（2026-05-08）：Spec Review Passed / Ready for Implementation。该状态仅表示规格审查通过，不表示 migration / API / 前端实现已完成。

## 0. 前置确认

- [x] T-DF-00 用户确认本 change 范围：12 张 schema 表 + API contract + collection_runs 迁入内容
- [x] T-DF-01 用户确认 `collection_runs.triggered_tenant_id` 字段语义，并已写入 design/spec；admin 点击采集时写入该关键词当前 active 订阅中最早订阅的租户；尚未执行 migration

## 1. Schema

- [x] T-DF-10 建 `keyword_master`
- [x] T-DF-11 建 `tenant_keyword`
- [x] T-DF-12 建 `lixiaoyun_raw_companies`
- [x] T-DF-13 建 `lixiaoyun_raw_contacts`
- [x] T-DF-14 建 `tendata_raw_companies`
- [x] T-DF-15 建 `tendata_raw_contacts`
- [x] T-DF-16 建 `clean_companies`
- [x] T-DF-17 建 `clean_contacts`
- [x] T-DF-18 建 `clean_company_sources`
- [x] T-DF-19 建 `clean_company_keywords`
- [x] T-DF-20 建 `tenant_companies`
- [x] T-DF-21 建 `tenant_contacts`
- [x] T-DF-22 建 `collection_runs`
- [x] T-DF-23 调整 `collection_tasks`：增加 `run_id`、`scheduled_biz_date`、`batch_no`、`page_size`、`cursor_snapshot`

## 2. 迁移规则

- [x] T-DF-30 数据迁移：`collection_keywords` → 归一化 → `keyword_master` + `tenant_keyword`
- [x] T-DF-31 废弃 `collection_keywords / collection_task_keywords` 真源职责，保留为迁移输入/兼容桥
- [x] T-DF-32 定义现有 raw / clean 数据到新表关系的迁移映射与边界；具体 ETL 在实现 change 中展开

## 3. 索引

- [x] T-DF-40 建客户列表 10 项筛选索引
- [x] T-DF-41 建关键词/run/task 关联索引
- [x] T-DF-42 建 raw 来源去重索引
- [x] T-DF-43 建 clean source / keyword 关联索引

## 4. API Contract

- [x] T-DF-50 输出 admin API contract：平台关键词、collection runs、raw 数据、clean 客户
- [x] T-DF-51 输出 tenant API contract：租户关键词、客户列表、客户详情、联系人列表
- [x] T-DF-52 明确 API 字段来源：clean 主表 / source 关联 / keyword 关联 / tenant 视图
- [x] T-DF-53 明确 API 筛选参数与 10 项索引字段一一对应

## 5. 验证

- [x] T-DF-90 OpenSpec strict validate 通过
- [x] T-DF-91 grep 确认本 change 不再承载 cleanup_service / worker base / Sealos / AI 回填 / competitor 重构范围
- [x] T-DF-92 用户签字确认 data foundation 可作为后续实现基准
