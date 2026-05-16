# Codex Review · design.md · Round 3（清场验证）

## 0. 总体结论

本轮只验证 Round 2 §1.3 清场清单，不重审 Round 1/2 已 ✅ finding。结论：16 项中 14 项已清干净，2 项仍有残留，暂不建议签字。未清项分别是：迁移示例 `CONCURRENTLY` 注释与实际 SQL 仍不一致；励销云 “标 done 跳过” 旧表述仍残留一处。其余指定关键词已按预期清掉或仅保留教育性否定引用。

## 1. 16 项清场验证表

| Round 2 §1.3 ID | 状态 | 证据(行号) |
|---|---:|---|
| 1. 删除 `0009b / 0009a/0009b` 方案描述 | ✅ | `design.md:421` / `:436` / `:445` 仅在 §3.2 解释“拆分会断链 / 不再考虑”；`design.md:121-124` 已改为“保留原 0009 revision id，重写 partial”。 |
| 2. “数据迁移 0009a” → “0009 partial 重写” | ✅ | `design.md:1024` 性能预算已写“数据迁移 0009 partial 重写”。`rg "0009a|0009b"` 未在性能预算命中。 |
| 3. “§3 alembic 0009a/0014” → “§3 alembic 0009 partial + 0012 空 + 0014” | ✅ | `design.md:1209` PM checklist 已写“0009 partial 重写 + 0012 空 migration + 0014 新建”。 |
| 4. “alembic 0012 不跑” → “0012 空 migration pass” | ✅ | `design.md:270` 写“alembic 0012 改空 migration（保留 revision id 但 upgrade/downgrade 都 pass）”；`rg "0012 不跑"` 无命中。 |
| 5. 迁移示例 CONCURRENTLY 说明一致 | ⚠️ | `design.md:508` 注释仍写“单独事务跑 CONCURRENTLY”，但 `design.md:516-524` 的 SQL 未使用 `CONCURRENTLY`；`design.md:545` 又说默认停服窗口内跑，索引可不 CONCURRENTLY。注释与 SQL 仍冲突。 |
| 6. 风险表 R3 不再用 “NULL 不锁表” 概括 | ✅ | `design.md:1197` 已改为 PG 11+ 不触发表 rewrite、但仍需 `ACCESS EXCLUSIVE` 锁，并说明索引阻塞写入；`rg "NULL 不锁表"` 无命中。 |
| 7. 删 cleanup_service “心跳” 描述（§4.1 注释、§115 总览） | ✅ | `design.md:115` 仅写队列消费 + 重试 + UPSERT + lixiaoyun 跳过规则；`design.md:653` 写“不接 heartbeat”。未再出现“lease + 重试 + 心跳”。 |
| 8. health_check 改 queue_depth/failed_rate/last_processed_at | ✅ | `design.md:920-927` health_check 返回 `queue_depth`、`failed_rate_5m`、`last_processed_at`，且说明 cleanup_service 不依赖 heartbeat age。 |
| 9. 测试列表 test_lease/test_heartbeat 移走 | ✅ | `rg "test_lease_concurrent_workers|test_heartbeat_extends"` 无命中；`design.md:1098-1100` 将 heartbeat / lease 测试移到长任务 worker change。 |
| 10. has_china_pcb_supplier 主函数 + 字段填充示例都固定 True | ✅ | `design.md:754` 字段填充示例固定 `True`；`design.md:842-844` `_infer_has_china_pcb_supplier()` 直接 `return True`。 |
| 11. lixiaoyun mark done 分支改防御性兜底（标 failed 报警） | ✅ | `design.md:678-683` 若 lixiaoyun 误入 cleanup_queue，则 `_mark_failed(... LIXIAOYUN_NOT_QUEUEABLE ...)`，不再 mark done。 |
| 12. lixiaoyun raw_table 标 done 表述修订 | ⚠️ | 主安全段已修：`design.md:1072` 写检测到 `raw_table='lixiaoyun_*'` 入队则标 failed 报警。但 `design.md:369` 仍写“标 done 跳过励销云”旧表述。 |
| 13. 日志示例 raw_row_id → raw_row_pk | ✅ | `design.md:953` 结构化日志使用 `raw_row_pk`；`rg "raw_row_id"` 仅在 `design.md:186` 的 B-02 教育性修订说明命中。 |
| 14. 共享 env OPENROUTER_API_KEY → PLATFORM_OPENROUTER_API_KEY | ✅ | `design.md:1078`、`:1144`、`:1162` 均为 `PLATFORM_OPENROUTER_API_KEY`；`rg "OPENROUTER_API_KEY"` 无裸 `OPENROUTER_API_KEY` 命中。 |
| 15. R2 风险改 staging schema introspection | ✅ | `design.md:1196` R2 缓解已写 `staging schema introspection`，并要求 `\d tenant_companies` 比对 schema.sql。`rg "待运维确认"` 无命中。 |
| 16. checklist 50-100 行改重估范围 | ✅ | `design.md:1210` checklist 已写 cleanup_service + admin_collection_service + migration + tests，共 ~580-750 行 / 3-4 天；`design.md:774` 的 50-100 行仅作为“原估算（已废弃）”。 |

### 1.1 逐项清场说明

1. `0009a/0009b` 仍有 3 处命中，但均在解释 Alembic revision 链为什么不能拆。
2. 这 3 处不是执行方案，不会要求实施者新增 0009a 或 0009b。
3. 性能预算中的旧“0009a”已经消失，改成了 `0009 partial 重写`。
4. PM checklist 中旧“0009a/0014”已经消失，且补齐了 0012 空 migration。
5. `0012 不跑` 已清零，当前文档使用“空 migration pass”口径。
6. 这点很关键：文档现在没有暗示跳过 Alembic 中间 revision。
7. `CONCURRENTLY` 是本轮最大的未清点。
8. 当前默认策略和 SQL 都像“停服窗口普通索引”，但注释仍像“并发索引”。
9. R3 锁表风险已经比 Round 2 准确，不再用“NULL 不锁表”粗略概括。
10. 风险表现在区分了 table rewrite、`ACCESS EXCLUSIVE` 锁、索引阻塞 DML。
11. cleanup_service 的 §115 总览已经删掉“心跳”。
12. §4.1 也明确“不接 heartbeat”，保留的是队列消费和重试。
13. health_check 已从 heartbeat age 转向队列指标。
14. 当前指标足以表达 cleanup_service 的短任务健康状态。
15. `test_lease_concurrent_workers` 和 `test_heartbeat_extends_lease` 已完全移走。
16. 文档把 heartbeat / lease 测试放到了未来长任务 worker change。
17. `has_china_pcb_supplier` 的函数和字段填充示例已经一致。
18. 两处都固定为 `True`，没有再从 `pcb_suppliers` 做真假推断。
19. 励销云处理分支本身已修成 failed + 报警。
20. 但 competitor 表说明段仍有“标 done 跳过”旧说法，构成残留。
21. 日志示例已使用 `raw_row_pk`。
22. `raw_row_id` 仅作为历史错误字段被教育性引用。
23. OpenRouter 环境变量已统一到 `PLATFORM_OPENROUTER_API_KEY`。
24. 未发现裸 `OPENROUTER_API_KEY` 作为实际 env key 的残留。
25. R2 风险已经从“待运维确认”改成 staging schema introspection。
26. 这是更可执行的验证口径。
27. checklist 已使用 ~580-750 行 / 3-4 天的重估范围。
28. “50-100 行”只作为已废弃估算保留在说明里，不在签字 checklist 中。
29. 本轮没有发现 Round 2 清单以外的大面积新冲突。
30. 但两处残留都和实施动作相关，因此不能签字。

## 2. 新引入问题（如有）

### 2.1 H-01 仍未清：CONCURRENTLY 注释与 SQL 冲突

- `design.md:508` 注释称“使用 op.execute 单独事务跑 CONCURRENTLY”。
- `design.md:516-524` 实际 SQL 是普通 `CREATE INDEX`，没有 `CONCURRENTLY`。
- `design.md:545` 又明确“默认在停服窗口内跑，索引可不 CONCURRENTLY”。
- 这三处不能同时成立。
- 清场建议：把 `design.md:508` 改成“本示例默认停服窗口普通 CREATE INDEX；生产大表可在 Alembic 外用 CONCURRENTLY”。
- 如要保留 `CONCURRENTLY` 示例，应另写 autocommit 场景，不放在当前默认 migration 代码块里。

### 2.2 M-05 仍有旧表述：励销云 “标 done 跳过”

- `design.md:678-683` 已把执行分支修成防御性兜底：误入队则标 failed 并报警。
- `design.md:1072` 也已统一到“标 failed 报警”。
- 但 `design.md:369` 仍写“本 change 仅在 §4 cleanup_service 中‘标 done 跳过励销云’逻辑里注释清楚理由”。
- 这会让读者误以为 §4 的目标仍是 mark done。
- 清场建议：把 `design.md:369` 改成“本 change 仅在 §4 cleanup_service 中保留防御性兜底：误入队则标 failed 报警”。

### 2.3 指定硬关键词结果

- `rg "0009a|0009b"`：3 处，均为 §3.2 教育性“断链 / 不再考虑”语义。
- `rg "raw_row_id"`：1 处，位于 §2.2 B-02 修订说明，属于教育性引用。
- `rg "OPENROUTER_API_KEY"`：4 处，均带 `PLATFORM_` 前缀。
- `rg "待运维确认"`：无命中。
- `rg "lease + 重试 + 心跳"`：无命中。
- `rg "0012 不跑"`：无命中。
- `rg "NULL 不锁表"`：无命中。
- `rg "test_lease_concurrent_workers|test_heartbeat_extends"`：无命中。

## 3. 无技术背景版摘要

- 大部分旧说法已经清掉：0009/0012 的迁移策略、raw_row_pk、平台级 OpenRouter key、cleanup_service 不接心跳、health 指标、测试名等都已统一。
- 还剩 2 个会误导实施的小残留：一个是索引迁移到底要不要 `CONCURRENTLY` 的注释矛盾；一个是励销云误入队时到底标 failed 还是旧的 mark done 表述。
- 建议修完这 2 行级问题后再签字；本轮不建议直接签字。

## 4. 原始需求对照

- 只验证 18 项清场清单：已执行；本报告按用户列出的 16 条逐项验证。
- 不修改被审文件：已遵守；`openspec/changes/v3-data-foundation/design.md` 未编辑。
- 报告 100-150 行：已按行数要求控制。
- 输出到指定路径：已写入 `_control/reviews/codex-code-review-v3-data-foundation-design-round3.md`。
