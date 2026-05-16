# Codex Review · design.md · Round 2

## 0. 总体结论

**不建议直接签字。** 本轮只复核 Round 1 的 18 处 finding，不扩展完整性 / 准确性 / 冲突重审。结论是：18 处中有 12 处已按要求修好，6 处仍有文档内残留矛盾或局部未改干净。核心实现方向已经明显收敛：`tenant_companies.company_id`、`cleanup_queue.raw_row_pk text`、0009 保留 revision id 重写、0012 空 migration、`matched_keywords` 延后到 `v3-collection-pushback` 都已写入主段落；但签字前还必须清掉旧的 `0009a/0009b`、`0012 不跑`、`lease + 心跳`、`raw_row_id`、`OPENROUTER_API_KEY` 等残留表述，避免实施时按旧口径执行。

## 1. 18 处修复验证表

| Round 1 ID | 修复点 | 状态 | 文件:行号 证据 |
|---|---|---:|---|
| B-01 | `tenant_companies.shared_company_id` 改为 `company_id` | ✅ | `openspec/changes/v3-data-foundation/design.md:729-736` Step 3 用 `tenant_companies (tenant_id, company_id...)` 与 `ON CONFLICT (tenant_id, company_id)`；`design.md:990-1009` §7.3 明确“已确认无需运维核验”，字段名为 `company_id`，并列出 staging 验证项。 |
| B-02 | `cleanup_queue.raw_row_id bigint` 改为 `raw_row_pk text`，并用 `tid` 查腾道 raw | ✅ | `design.md:166-186` §2.2 表定义为 `raw_row_pk text` + `UNIQUE (raw_table, raw_row_pk)`；`design.md:656-662` `_load_raw_row` 对 `tendata_raw_companies` 使用 `WHERE tid = $1`，不再用 `WHERE id`。 |
| B-03 | Alembic 0009 保留 revision id 重写 partial，不新增 0009a | ⚠️ | 主策略已修：`design.md:419-443` 说明 Alembic 按 revision 图执行，推荐“保留 0009 revision id，重写其内容为 partial”；`design.md:545-558` 完整迁移链没有 `0009a`。但旧口径仍残留：`design.md:121-125` 仍写“写新迁移 0009b（或拆 0009 为 0009a/0009b）”，`design.md:1019` 与 `design.md:1204` 仍出现 `0009a`。 |
| B-04 | 0012 改为空 migration，不写“跳过” | ⚠️ | §3.5 已修：`design.md:474-495` 明确保留 `revision = "20260501_0012"`，`upgrade()/downgrade()` 均 `pass`，且写明“绝不跳过中间 revision”。但 `design.md:270` 仍写“alembic 0012 不跑”，与 §3.5 冲突。 |
| B-05 | fan-out 用 `collection_task_keywords`，本 change 不操作 `matched_keywords` | ✅ | `design.md:729-736` Step 3 从 `collection_task_keywords ctk` join `collection_keywords ck`，按 `ctk.task_id = :task_id` 做 task 内 fan-out；`design.md:741` 明确本 change 不引入 `matched_keywords`，跨租户历史 fan-out 由 `v3-collection-pushback` 实施。 |
| H-01 | 锁表描述 + `CREATE INDEX` 是否 `CONCURRENTLY` | ⚠️ | 主段落已修：`design.md:543` 说明 PG 11+ 不触发表 rewrite，但 `ALTER TABLE` 仍需 `ACCESS EXCLUSIVE` 锁，索引默认阻塞 DML，生产大表可在 Alembic 外用 `CONCURRENTLY`。但 `design.md:506` 注释写“使用 op.execute 单独事务跑 CONCURRENTLY”，实际 `design.md:513-523` SQL 没有 `CONCURRENTLY`；`design.md:1192` 风险缓解仍写“ALTER ADD COLUMN ... NULL 不锁表”，遗漏 DEFAULT 字段与 DDL 锁。 |
| H-02 | shared company 去重索引必须是 UNIQUE INDEX | ✅ | `design.md:513-518` 创建 `CREATE UNIQUE INDEX uq_shared_companies_normalized_country`；`design.md:1024-1044` 再次说明 UPSERT 去重必须使用 UNIQUE INDEX，普通表达式索引不能支撑 `ON CONFLICT`。 |
| H-03 | `matched_keywords` 不属于本 change，归 `v3-collection-pushback` | ✅ | `design.md:741` 明确“不引入 `matched_keywords` 字段”，跨租户历史 fan-out + matched_keywords 由 `v3-collection-pushback` 统一引入。`rg` 未发现 Step 3 继续写 `matched_keywords`。 |
| H-04 | `source_type` 命名映射：DB `tengdao` vs API `tendata` | ✅ | `design.md:693-704` 增加命名映射表，明确 DB `company_sources.source_type` 用 `tengdao`，raw 表/API 参数用 `tendata`，cleanup_service 写 `company_sources` 必须插入 `'tengdao'`。 |
| H-05 | `competitor_companies` 保留 0008 enrichment 字段 + staging 验证 | ✅ | `design.md:331-373` 明确实际生产结构 = schema.sql 基础 + 0008 enrichment 字段，并列出 `source_id / company_name_en / esdate / legalperson / reg_capital / ...`；`design.md:365` 要求 0009 partial 绝不能 drop/recreate；`design.md:568` 加入 staging 验证。 |
| H-06 | `admin_collection_service` 改造范围 + 工作量重估 | ✅ | `design.md:757-784` 新增 admin_collection_service 改造段，覆盖 dashboard、clean 列表、raw tab、health reconcile，并把 Slice 1.B 工作量从 2-3 天改为 3-4 天。 |
| M-01 | cleanup_queue 不加 lease，cleanup_service 不接入 heartbeat | ⚠️ | 修复段已存在：`design.md:912-917` 明确 cleanup_queue 不加 lease/heartbeat 字段，cleanup_service 不接入 `_heartbeat_loop`。但残留旧说法仍多：`design.md:115` 称 cleanup_service 已有“lease + 心跳”，`design.md:651` 注释“保留：lease + 重试 + 心跳”，`design.md:1088` 仍列 `test_lease_concurrent_workers`，`design.md:1094` 仍列 `test_heartbeat_extends_lease`。 |
| M-02 | `contact_count` 用 `shared_contacts` 统计 | ✅ | `design.md:786-803` 明确 `tenant_contacts` 无 `shared_company_id`，统计改基于 `shared_contacts WHERE company_id = shared_companies.id`，并说明这是共享层联系人总数。 |
| M-03 | `has_china_pcb_supplier` 固定 true | ⚠️ | §5.3 已修：`design.md:836-846` 明确 V3 固定 true，函数直接 `return True`。但 `design.md:747-754` 的字段填充示例仍按 `bool(raw_row.pcb_suppliers...)` 推断，和固定 true 冲突。 |
| M-04 | AI 调用用平台级 key，不用租户级 key | ✅ | `design.md:848-857` 明确 cleanup_service 写 shared 层不取租户级 OpenRouter key，使用平台级 key，并设平台总配额；`design.md:1070-1075` 安全段再次确认平台 key 来源。 |
| M-05 | 励销云 raw 不入 cleanup_queue | ⚠️ | 数据模型段已修：`design.md:194-198` 明确励销云不入队，cleanup_queue 仅承载腾道 raw。但旧逻辑仍残留：`design.md:676-683` cleanup_service 仍处理 `lixiaoyun_raw_companies` 并“标 done”，`design.md:1067-1068` 也写 raw_table=`lixiaoyun_*` 标 done。 |
| M-06 | `daily_limit 1000` 注明对 0009 的修订 | ✅ | `design.md:288-293` 明确 `daily_stage1_limit` 与 `daily_stage2_limit` 默认 1000，并注明原 0009 是 30/100，按业务真源 §5.2 修订。 |
| M-07 | `keyword_master` RLS 延后到 `v3-collection-pushback` | ✅ | `design.md:387-410` 明确本 change 仅建表占位，不开启 RLS；RLS + worker 数据库角色留到 `v3-collection-pushback` 决定。 |
| L-01 | `test_lixiaoyun_skip` 拼写 | ✅ | `design.md:1087` 测试名为 `test_lixiaoyun_skip`，已补齐 `test_` 前缀。 |
| L-02 | OpenRouter key 来源统一为 `PLATFORM_OPENROUTER_API_KEY` | ⚠️ | 主安全段与 K8s 示例已修：`design.md:1070-1075`、`design.md:1157-1160` 均使用 `PLATFORM_OPENROUTER_API_KEY`。但 `design.md:1139` 仍写共享 env 为 `OPENROUTER_API_KEY`，与统一命名冲突。 |

### 1.1 逐项核验展开

#### B-01

- 主 SQL 已经使用 `company_id`。
- §7.3 已经从“待运维确认”改成“事实已查 schema.sql”。
- staging 验证项已列出 `company_id`、FK、UNIQUE、join 可读。
- 仅在风险表 R2 仍有“待运维确认”旧口径，归入 §2 新问题，不影响 B-01 主修复判定。

#### B-02

- §2.2 已经把队列外键从 bigint 改成 text。
- `_load_raw_row` 对腾道 raw 已经按 `tid` 查询。
- 主链路“腾道 raw → cleanup_queue → cleanup_service”可以按文档语义执行。
- 日志示例还残留 `raw_row_id`，归入 §2 新问题，不影响 B-02 主修复判定。

#### B-03

- §3.1 / §3.2 已经解释 Alembic revision 图，不再把文件名顺序当执行顺序。
- §3.2 推荐策略是保留原 `20260430_0009` revision id。
- §3.7 的迁移链写的是 `0009 phase1_collection_schema_partial`，没有写 `0009a`。
- 但 §1.3、性能预算、PM checklist 仍残留 `0009a/0009b`。
- 因此 B-03 不能判 ✅，只能判 ⚠️。

#### B-04

- §3.5 已经给出空 migration 代码。
- `upgrade()` 和 `downgrade()` 都是 `pass`。
- §3.5 明确 Alembic 线性链不能跳过中间 revision。
- 但 §2.3 末尾仍写“alembic 0012 不跑”。
- 因此前后口径仍冲突，判 ⚠️。

#### B-05

- Step 3 已经改为 `collection_task_keywords`。
- SQL 已经按 `task_id` 做本 task 内 fan-out。
- 文档明确跨租户历史 fan-out 延后给 `v3-collection-pushback`。
- `matched_keywords` 已从本 change 的 Step 3 删除。
- 本项可判 ✅。

#### H-01

- 正文已经承认 `ALTER TABLE` 仍拿 `ACCESS EXCLUSIVE` 锁。
- 正文已经承认 `CREATE INDEX` 默认阻塞 DML。
- 正文已经说明大表可在 Alembic 外用 `CREATE INDEX CONCURRENTLY`。
- 但迁移示例注释说“跑 CONCURRENTLY”，实际 SQL 没有 `CONCURRENTLY`。
- 风险表仍用“NULL 不锁表”简化表述。
- 本项还需清理，判 ⚠️。

#### H-02

- 0014 示例已经创建 UNIQUE INDEX。
- §8.1 也重复说明 UPSERT 必须依赖 UNIQUE INDEX。
- 这正是 Round 1 要求。
- 本项判 ✅。

#### H-03

- 文档明确本 change 不加 `matched_keywords`。
- 归属已经落到 `v3-collection-pushback`。
- Step 3 SQL 未再引用该字段。
- 本项判 ✅。

#### H-04

- 映射表覆盖 DB source_type、raw 表名、API 参数、业务文案四层。
- DB 写入值明确为 `tengdao`。
- API/UI 参数明确可继续用 `tendata`。
- 本项判 ✅。

#### H-05

- competitor 表段落已经写明“schema.sql 基础 + 0008 enrichment”。
- 0008 字段清单已经列出。
- staging 验证也加入 0008 字段仍存在。
- 本项判 ✅。

#### H-06

- admin_collection_service 四处改造范围已列出。
- clean/raw 页面、health reconcile、waimaotong tab 都覆盖。
- 工作量已经从 2-3 天重估到 3-4 天。
- 但 checklist 仍写“50-100 行”，归入 §2 新问题。
- 主修复判 ✅。

#### M-01

- 修复段明确 cleanup_queue 不加 lease/heartbeat 字段。
- 修复段明确 cleanup_service 不接 `_heartbeat_loop`。
- 但文档其他位置仍保留 lease/heartbeat 叙述和测试。
- 这是执行层会误解的残留。
- 本项判 ⚠️。

#### M-02

- SQL 已经改成 `shared_contacts WHERE company_id = shared_companies.id`。
- 文档明确 contact_count 是共享层联系人数量。
- 未再使用不存在的 `tenant_contacts.shared_company_id`。
- 本项判 ✅。

#### M-03

- §5.3 的最终函数已固定 `return True`。
- 说明文字也承认原 `any(...) or True` 是错误写法。
- 但 §4.3 的字段填充示例还按 raw payload 判断 true/false。
- 同一字段两个口径会造成实现分歧。
- 本项判 ⚠️。

#### M-04

- cleanup_service 不取租户级 key 的原则已写清。
- 平台级 key 和平台配额已写清。
- 租户级 key 只给 tenant 端业务使用。
- 本项判 ✅。

#### M-05

- 数据模型段已经写励销云不入 cleanup_queue。
- 这符合 Round 1 修复要求。
- 但 cleanup_service 伪代码仍包含 lixiaoyun 入队后 mark done 分支。
- 安全段也仍写 lixiaoyun raw_table 标 done。
- 该项尚未全篇统一，判 ⚠️。

#### M-06

- 两个 daily limit 都已写 1000。
- 注释明确原 0009 是 30 / 100。
- 注释明确本次按业务真源修订。
- 本项判 ✅。

#### M-07

- keyword_master / tenant_keyword 仅建表占位。
- RLS policy 已注释掉。
- worker 数据库角色问题明确后续 change 再定。
- 本项判 ✅。

#### L-01 / L-02

- L-01 拼写已修，测试名为 `test_lixiaoyun_skip`。
- L-02 主段落与 K8s 示例已统一到 `PLATFORM_OPENROUTER_API_KEY`。
- L-02 仍有旧 env 名残留，因此判 ⚠️。

### 1.2 状态汇总

- ✅ 已修好：B-01、B-02、B-05、H-02、H-03、H-04、H-05、H-06、M-02、M-04、M-06、M-07、L-01。
- ⚠️ 需补清残留：B-03、B-04、H-01、M-01、M-03、M-05、L-02。
- 🔴 未发现完全未修的 Round 1 finding。
- 本报告把“主修复已完成但旧段落未清”的项统一判 ⚠️。
- 这些 ⚠️ 大多不需要重新设计，只需要全篇统一口径。
- 但签字前必须修，因为它们会影响实施者按哪一段执行。

### 1.3 签字前必修清单

1. 删除或改写 `design.md:121-125` 的 `0009b / 0009a/0009b` 方案。
2. 把 `design.md:1019` 的“数据迁移 0009a”改为“0009 partial 重写”。
3. 把 `design.md:1204` 的“0009a/0014”改为“0009 partial/0014”。
4. 把 `design.md:270` 的“alembic 0012 不跑”改为“0012 空 migration pass”。
5. 统一 H-01：迁移示例若不写 `CONCURRENTLY`，就不要在注释里说“跑 CONCURRENTLY”。
6. 改写 `design.md:1192`，不要再用“NULL 不锁表”概括带 DEFAULT 的 DDL。
7. 删除 `design.md:115` 的 cleanup_service “心跳”描述。
8. 删除或改写 `design.md:651` 的“保留：lease + 重试 + 心跳”注释。
9. 将 `design.md:919-925` 的 health_check 从 heartbeat age 改成队列/失败率/最近处理时间。
10. 把 `design.md:1088` 与 `design.md:1094` 中 cleanup_service 相关 lease/heartbeat 测试移到未来 worker base change。
11. 把 `design.md:753` 的 `has_china_pcb_supplier` 填充改为固定 `True`。
12. 删除或重写 `design.md:676-683` 的 lixiaoyun 入队后 mark done 分支。
13. 删除或重写 `design.md:1067-1068` 的 lixiaoyun raw_table mark done 表述。
14. 把 `design.md:948` 的 `raw_row_id` 改成 `raw_row_pk`。
15. 把 `design.md:1139` 的 `OPENROUTER_API_KEY` 改成 `PLATFORM_OPENROUTER_API_KEY`。
16. 把 `design.md:1191` 的 “§7.3 待运维确认”改成 staging schema introspection 风险。
17. 把 `design.md:1205` 的 “50-100 行”改成已重估的完整改造范围。
18. 修完后再跑一次 `rg \"0009a|0009b|0012 不跑|raw_row_id|OPENROUTER_API_KEY|lease \\+ 重试 \\+ 心跳|待运维确认\" design.md` 做清场。

## 2. 新引入问题（如有）

### 2.1 旧迁移命名残留会误导执行顺序

- `design.md:419-443` 与 `design.md:545-558` 已把正式策略改成“保留 0009 revision id，重写 partial”。
- 但 `design.md:121-125` 仍要求写新 `0009b` 或拆 `0009a/0009b`。
- `design.md:1019` 性能预算仍写“数据迁移 0009a”。
- `design.md:1204` PM checklist 仍写“§3 alembic 0009a/0014 迁移策略合理”。
- 这会让实施者误以为仍要新建 0009a/0009b。
- 建议：全篇统一为“0009 原 revision id partial 重写”，删除 `0009a/0009b` 残留；若保留备选策略，只能放在 §3.4 replacement revision，并标明“不推荐且需改 down_revision”。

### 2.2 0012 空 migration 与“不跑”口径冲突

- `design.md:474-495` 明确 0012 作为空 migration 仍会执行。
- `design.md:270` 仍写“alembic 0012 不跑”。
- 这不是措辞小问题：Alembic 链路里“执行空节点”和“不跑”是两种不同操作。
- 建议：把 `design.md:270` 改为“0012 保留 revision id，但 upgrade/downgrade 改为空 pass”。

### 2.3 cleanup_service lease/heartbeat 口径未统一

- `design.md:912-917` 的修复结论是对的：cleanup_queue 不加 lease/heartbeat，cleanup_service 不接 heartbeat。
- 但前文、代码注释、测试清单仍保留 lease/heartbeat。
- `design.md:919-925` 的 `health_check` 仍依赖 `_last_heartbeat_age_s`，这也和“不接 heartbeat”不一致。
- 建议：cleanup_service 的健康检查改为 `queue_depth / failed_rate / last_processed_at`，不要以 heartbeat age 判定健康；heartbeat 测试放到未来接入长任务 worker 的 change。

### 2.4 `has_china_pcb_supplier` 主函数和字段填充示例冲突

- `design.md:841-843` 固定 `return True`。
- `design.md:753` 又按 raw 里的 `pcb_suppliers` 布尔判断。
- 这会导致实现者不知道以哪个为准。
- 建议：`_parse_d038_d039_fields()` 内也直接写 `'has_china_pcb_supplier': True`，并把 raw 推断移出 V3。

### 2.5 励销云“不入队”与 cleanup_service “标 done”并存

- `design.md:194-198` 已改成励销云不入 cleanup_queue。
- `design.md:676-683`、`design.md:1067-1068` 仍保留如果看到 `lixiaoyun_raw_companies` 就标 done 的逻辑。
- 如果励销云不入队，这段逻辑不是主路径，保留会让测试和指标设计继续围绕 “skip queue item” 展开。
- 建议：改成防御性兜底注释：“正常不会入队；如历史脏数据出现则 mark failed/skipped 并报警”，或完全删除该分支。

### 2.6 `raw_row_id` 日志字段残留

- `design.md:166-186` 已把队列主键改为 `raw_row_pk`。
- `design.md:948` 结构化日志仍写 `"raw_row_id": 67890`。
- 建议：同步改为 `"raw_row_pk": "xxx"`，并允许 text。

### 2.7 OpenRouter 环境变量还有旧名

- `design.md:1073` 和 `design.md:1157` 已统一为 `PLATFORM_OPENROUTER_API_KEY`。
- `design.md:1139` 仍写共享 env 包含 `OPENROUTER_API_KEY`。
- 建议：全篇只保留 `PLATFORM_OPENROUTER_API_KEY`；租户级 OpenRouter 配置仅由 tenant API 读取。

### 2.8 R2 风险条目仍把已确认事实写成“待运维确认”

- `design.md:990-1009` 已确认 `tenant_companies.company_id` 是事实。
- `design.md:1191` 风险 R2 仍写“tenant_companies FK 字段名与方案 B 假设不符”“§7.3 待运维确认”。
- 建议：R2 改为“生产 schema 与 repo schema 不一致风险”，缓解为“staging introspection 验证”，不要再说 §7.3 待确认。

### 2.9 PM checklist 仍保留旧工作量

- `design.md:757-784` 已把实际改造范围重估到约 580-750 行。
- `design.md:1205` checklist 仍写“cleanup_service 改造范围明确（50-100 行）”。
- 建议：改成“cleanup_service + admin_collection_service + migrations + tests 改造范围明确”。

## 3. 给用户的无技术背景版摘要

1. **还不能签字。** 大方向已经修对，但文档里还有旧说法残留，尤其是迁移编号、0012、worker 心跳、励销云入队这些地方，容易让工程执行跑偏。
2. **12 处已修好，6 处还要补。** 真正需要补的不是重新设计，而是把同一份文档里的前后口径统一。
3. **最关键的阻塞是迁移口径。** 正文说“重写原 0009”，但其他地方还写 `0009a/0009b`；正文说“0012 空 pass”，但前面还写“不跑 0012”。
4. **cleanup_queue 方向已对。** 腾道 text 主键问题已用 `raw_row_pk text` 解决；但日志和部分示例还残留 `raw_row_id`。
5. **签字前还有 6 处必修。** 清掉这些残留后，可以进入签字复核；当前版本不建议签。

## 4. 原始需求 → 已实现/未实现 对照清单

| 原始需求 | 状态 | 说明 |
|---|---:|---|
| 只验证 Round 1 的 18 处 finding | 已实现 | 本报告只围绕用户列出的 B/H/M/L 项复核；未重新展开完整设计审查。 |
| 不重审完整性 / 准确性 / 冲突 3 类范围扩展 | 已实现 | “新引入问题”仅记录修复本身造成或残留的文档内矛盾，不新增业务设计审查范围。 |
| 输出 18 处修复验证表 | 已实现 | 见 §1，逐项给出状态和文件行号证据。 |
| 输出新引入问题 | 已实现 | 见 §2，共 9 项，均是 Round 1 修复后的残留/矛盾。 |
| 输出无技术背景版摘要 | 已实现 | 见 §3，明确“还不能签字”和“还有 6 处必修”。 |
| 写报告到 `_control/reviews/codex-code-review-v3-data-foundation-design-round2.md` | 已实现 | 本文件即目标报告。 |
| 不修改被审文件 `openspec/changes/v3-data-foundation/design.md` | 已实现 | 仅新增本 review 报告，未修改 design.md。 |
