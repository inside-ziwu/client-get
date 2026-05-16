## 1. 证据与范围

- [x] 1.1 只读查询线上 `tendata_raw_contacts` 与 `tendata_raw_companies.raw_payload.contacts` 分布
- [x] 1.2 确认线上主路径为 `tendata_raw_contacts`，不是 `raw_payload.contacts`
- [x] 1.3 将线上统计和修复范围写入本 change

## 2. 测试先行

- [x] 2.1 为 cleanup 增加 RED 测试：`tendata_raw_contacts` 中有 email 时应写入 `clean_contacts`
- [x] 2.2 为 tenant 联系人 API 增加断言：由 `tendata_raw_contacts` 回填的联系人可展示姓名、职位、邮箱、电话
- [x] 2.3 为历史 backfill 增加 RED 测试：通过 `clean_company_sources` 回填历史 raw contacts
- [x] 2.4 为 backfill 幂等增加测试：重复运行不产生重复 `clean_contacts`
- [x] 2.5 为无 email raw contact 增加测试：不得写入 `clean_contacts`
- [x] 2.6 为同一 clean company 下重复 email 增加 RED 测试：backfill 必须先去重再 upsert，不触发 PostgreSQL 同语句重复 conflict

## 3. 实现

- [x] 3.1 调整 `CleanupService` 顺序：先写 `clean_company_sources`，再通过 source mapping materialize `tendata_raw_contacts`
- [x] 3.2 扩展 `CleanupService`，处理 tendata raw company 时读取 `tendata_raw_contacts`
- [x] 3.3 抽取共享 upsert 逻辑，避免 `raw_payload.contacts` 与 `tendata_raw_contacts` 两条路径语义分叉
- [x] 3.4 新增一次性 backfill 脚本或服务入口，支持 dry-run 和正式执行
- [x] 3.5 backfill 使用 set-based SQL 或批处理，按 `clean_company_id + lower(email)` 去重后再 upsert
- [x] 3.6 确保生产执行前不会自动触发写库；必须由用户明确运行

## 4. 验证

- [x] 4.1 运行后端目标测试，覆盖 cleanup、backfill、tenant 联系人 API
- [x] 4.2 运行 `openspec validate backfill-tendata-raw-contacts-to-clean --strict`
- [x] 4.3 本地 dry-run 输出可回填公司数、去重前候选联系人行数、去重后 upsert 联系人行数
- [x] 4.4 如用户明确触发生产 backfill，执行前后只读统计并记录结果（已于 2026-05-11 用户触发后执行生产 backfill：前置 dry-run `clean_company_rows=1886`、`candidate_contact_rows=112058`、`deduped_contact_rows=108291`、`clean_contacts=102461`、`missing_candidate_contacts=6632`、`duplicate_email_groups=0`；执行返回 `inserted_or_updated_rows=108291`；后置验收 `clean_contacts=109093`、`missing_candidate_contacts=0`、`duplicate_email_groups=0`、`visible_gap_after=222`）
- [x] 4.5 更新任务勾选状态，未执行生产 backfill 时明确记录未执行原因
