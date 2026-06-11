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
- [ ] 2.3 通过本地 API 调用 `/t/{slug}/api/v1/companies` 验证返回数据正确且响应时间 < 1s

## 3. 部署生产

- [ ] 3.1 推送代码到 GitHub，触发 backend `workflow_dispatch` 构建镜像
- [ ] 3.2 在 Sealos 控制台更新后端服务镜像 tag（启动时 `alembic upgrade head` 自动执行迁移）
- [ ] 3.3 验证生产公司列表查询正常返回数据且响应时间符合预期
