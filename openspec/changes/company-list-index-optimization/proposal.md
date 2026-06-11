## Why

公司列表查询（`/t/{slug}/api/v1/companies`）耗时 3.6s，根因是 `lixiaoyun_api_clean_companies` 表的 JOIN 条件 `lower(trim(lxc.entname_eng)) = lower(trim(wr_raw.source_competitor))` 无法命中任何索引，每次查询都触发全表扫描。

上次优化（ccb5ecf）尝试将该 JOIN 改写为 LATERAL 子查询，开发环境验证通过但生产上线后公司列表返回 0 条数据，已紧急回退（1749987）。本次采用纯索引方案——不修改任何 SQL 查询语句，只添加函数索引让现有查询自动走索引扫描。

## What Changes

- 在 `lixiaoyun_api_clean_companies` 表上创建 `lower(trim(entname_eng))` 函数索引，让现有 LEFT JOIN 条件能走索引
- 确认 `waimaotong_raw_companies.sys_company_id` 索引状态（上次迁移文件被回退删除，但生产库可能保留了索引），必要时补建
- 所有索引使用 `CREATE INDEX CONCURRENTLY` 避免锁表
- 先在开发库通过 `EXPLAIN ANALYZE` 验证索引命中，再部署生产

## Non-Goals

- 不修改 `tenant_query_service.py` 中的任何 SQL 查询语句
- 不修改前端代码
- 不引入新的查询模式（如 LATERAL JOIN、物化视图等）
- 不做 `waimaotong_raw_companies` 表上 `source_competitor` 列的函数索引（该列仅作为 JOIN 的右侧值，索引建在左侧 `entname_eng` 上即可）

## Capabilities

### New Capabilities

无新增能力。

### Modified Capabilities

- `tenant-companies-list`: 查询性能提升（非功能性变更），行为和返回结果不变

## Impact

| 影响范围 | 说明 |
|---------|------|
| 数据库 | 新增 1-2 个索引（Alembic 迁移），`CREATE INDEX CONCURRENTLY` 不阻塞读写 |
| 后端代码 | 无变更 |
| 前端代码 | 无变更 |
| 部署 | 后端镜像更新后 `alembic upgrade head` 自动执行迁移 |
| 风险 | 极低——纯索引添加，不改变查询逻辑和结果集 |
