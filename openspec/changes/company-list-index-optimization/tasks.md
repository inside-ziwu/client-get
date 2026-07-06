## 1. Alembic 迁移文件

- [x] 1.1 编写迁移文件（autocommit 模式），按以下顺序执行：
  1. `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lxc_entname_eng_lower_full ON lixiaoyun_api_clean_companies (lower(trim(entname_eng)))`（完整函数索引，无 WHERE 条件）
  2. `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wmt_raw_sys_company_id ON waimaotong_raw_companies (sys_company_id)`
  3. `DROP INDEX IF EXISTS idx_lx_clean_entname_eng_lower`（删除旧 partial index）
  - 迁移文件使用 `op.get_context().autocommit_block()` 或 `connection.execution_options(isolation_level="AUTOCOMMIT")`

## 2. 开发库验证

- [x] 2.1 在开发库（Neon）执行 `alembic upgrade head`，确认迁移成功
- [x] 2.2 运行 `EXPLAIN (ANALYZE, BUFFERS)` 确认：
  - `lixiaoyun_api_clean_companies` 走 Index Scan（使用 `idx_lxc_entname_eng_lower_full`）
  - `waimaotong_raw_companies` 走 Index Scan（使用 `idx_wmt_raw_sys_company_id`）
- [x] 2.3 核心 JOIN EXPLAIN ANALYZE（2026-07-05 dev）：Execution Time 9.6ms（小数据集 planner 选 Seq Scan，仍 <1s）

## 3. 部署生产

- [x] 3.1 迁移 `20260611_0001` 已随 backend 镜像合并上线（commit `7527056`）
- [x] 3.2 生产 `alembic upgrade head` 已执行：`idx_lxc_entname_eng_lower_full`、`idx_wmt_raw_sys_company_id` 均已建，旧 partial `idx_lx_clean_entname_eng_lower` 已删（2026-07-05 只读核验）
- [x] 3.3 生产 EXPLAIN ANALYZE（2026-07-05，37146 条大租户）：`lixiaoyun` 走 Index Scan，Execution Time 6.5ms（优化前 3.6s）
