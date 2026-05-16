# Codex Review · v3-data-foundation/design.md

## 0. 总体结论（1 段）

**不建议签字。** `openspec/changes/v3-data-foundation/design.md` 的大方向（方案 B：保留 `shared_companies + company_sources`，不跑 0009 破坏性 upgrade）与用户拍板一致，也基本对齐 `_control/v3/07-v3-scope-final.md` 和 `_control/v3/00-v3-business-goals.md` §5.2 的 raw → clean → tenant 视图分发目标；但实施前仍有 5 个阻塞：`tenant_companies` 字段名/FK 与设计 SQL 不一致、cleanup_queue 无法承载 `tendata_raw_companies.tid` 的 text PK、0009a 拆分策略破坏 Alembic revision 链、cleanup_service 的 fan-out SQL 没有对齐现有 schema/任务关系、以及 `ADD COLUMN DEFAULT` 的锁表风险表述过度简化。建议先修 design.md，再进入 Slice 0 / 1.A / 1.B 实施。

---

## 1. Blocker

| ID | finding | 证据(行号) | 建议 |
|---|---|---|---|
| B-01 | `tenant_companies` FK 字段名被设计成“待运维确认”，但当前仓库 schema 已明确是 `company_id uuid REFERENCES shared_companies(id)`，不是 `shared_company_id`，更不是 `clean_company_id`。design.md §4.2 / §7.3 仍按 `shared_company_id` 写 UPSERT，会直接跑失败。 | `design.md` 行 523-529 写 `tenant_companies (tenant_id, shared_company_id, matched_keywords, ...)`；行 532 才提示当前可能是 `clean_company_id`；行 736-742 又把核心 FK 切换留给运维确认。实际 schema：`backend/03_database/schema.sql` 行 390-408 定义 `tenant_companies.company_id uuid NOT NULL REFERENCES shared_companies(id)` 与 `UNIQUE (tenant_id, company_id)`。现有服务也大量 `JOIN shared_companies sc ON sc.id = tc.company_id`，如 `tenant_query_service.py` 搜索结果显示多处。 | 0014 必须明确选择现状字段名：**继续使用 `company_id`**，不要新增 `shared_company_id`，除非另开全仓重命名迁移。同步修正 design.md §4.2、§7.3、§8.1、§9、测试用例和所有示例 SQL：`ON CONFLICT (tenant_id, company_id)`。 |
| B-02 | cleanup_queue 的 `raw_row_id bigint` 与 `tendata_raw_companies.tid text PRIMARY KEY` 硬冲突，design.md 仍要求腾道 raw 入队并由 cleanup_service 消费，现有代码还明确“tendata 不能 enqueue”。这是 raw → clean 主链路阻断。 | `design.md` 行 167-181 定义 `cleanup_queue.raw_row_id bigint`；行 198-221 定义 `tendata_raw_companies.tid text PRIMARY KEY`；行 67、92、193-194 要求腾道入 cleanup_queue。现有 `collection_service.py` 行 102-108 注释 `tid text PK` 不能进入 `cleanup_queue.raw_row_id bigint`；行 224-229 对 tendata 只 upsert raw，不 enqueue。现有 `cleanup_service.py` 行 160-166 还用 `WHERE id = :id` 读取 `tendata_raw_companies`，但设计表无 `id` 字段。 | 在 0009a 中改队列表达：要么 `raw_row_pk text NOT NULL` 替代 bigint，要么增加 `raw_tid text` / `raw_uuid uuid` 等类型化字段；同时改 cleanup_service `_load_raw_row` 用 `tid` 查询。没有这个修正，V3 干净库唯一来源（腾道）不会进入 cleanup_service。 |
| B-03 | 0009a “从 0009 拆分”没有处理 Alembic revision 链。现有 0010 的 `down_revision` 指向 `20260430_0009`，如果新增 `0009a` 而跳过/移除原 0009，`alembic upgrade head` 不能自然跑到 0010/0011/0013/0014。 | `design.md` 行 393-404 写生产 0006 → 0007 → 0008 → `0009a` → 0010 → 0011 → 跳过 0012 → 0013 → 0014；行 406-418 说 0009a 替代 0009 部分。实际 `20260501_0010_add_default_partitions.py` 在 rg 输出中显示 `down_revision = "20260430_0009"`；原 0009 文件行 10-11 是 `revision = "20260430_0009"` / `down_revision = "20260429_0008"`。 | 必须在 design.md 中写清 Alembic 方案：推荐**保留 revision id `20260430_0009`，重写其 upgrade 内容为 partial**，并注明这是尚未生产升级时允许的迁移修订；如果不能改已提交 migration，则新建 replacement revision 后还要同步修改 0010 down_revision，不可只写“0009a”。 |
| B-04 | “跳过 0012”会让 0013 无法按线性链路执行，因为 0013 的 `down_revision` 指向 0012。design.md 说 `alembic upgrade head` 但又说 0012 不跑，两者矛盾。 | `design.md` 行 401 写 `0012 (跳过)`；行 724-731 又写 `alembic upgrade head`。rg 输出显示 `20260501_0013_drop_ai_fallback.py` 的 `down_revision = "20260501_0012"`，`20260501_0012_waimaotong_raw_contacts.py` 的 `down_revision = "20260501_0011"`。 | 不能“跳过”线性 migration。要么让 0012 改为空 migration 并继续保留 revision 链，要么修改 0013 down_revision 指向 0011，并说明为何安全；设计文档必须给唯一策略。 |
| B-05 | cleanup_service 改造 SQL 未覆盖现有 schema 的关键字段，且 fan-out 查询“所有命中租户”的语义不足。当前 §4.2 只从 `collection_keywords WHERE id = :keyword_id` 选一个租户，既不使用 `collection_task_keywords`，也没有实现 KeywordMaster 的跨租户复用。 | `design.md` 行 523-529 的 Step 3 使用 `FROM collection_keywords WHERE id = :keyword_id`；但现有 cleanup_service 行 237-247 是通过 `collection_task_keywords` 找 task 关联租户和关键词。最高真源要求跨租户复用：`_control/v3/00-v3-business-goals.md` 行 80-82，A 采过后 B 配同关键词应立即看到历史数据；`_control/v3/07-v3-scope-final.md` 行 97-103 把跨租户 fan-out 和 raw→clean→tenant 分发列为实施位置。 | §4.2 必须拆成两层：本 change 负责 task 内租户 fan-out；v3-collection-pushback 负责 KeywordMaster 历史 fan-out，或本 change 同步建可调用接口。SQL 至少应基于 `collection_task_keywords` + `collection_keywords.keyword_normalized`，并明确何时追加 B 租户历史可见。 |

---

## 2. High Risk

| ID | finding | 证据(行号) | 建议 |
|---|---|---|---|
| H-01 | 5 字段 ADD COLUMN 的锁表风险描述不准确。PostgreSQL 11+ 对“常量 DEFAULT”避免表重写，但 `ALTER TABLE ... ADD COLUMN` 仍会拿 `ACCESS EXCLUSIVE` 锁；同时 `CREATE INDEX` 默认会阻塞写入，design.md 只写“NULL 不锁表”会误导生产窗口评估。 | `design.md` 行 139-147：`contact_count int DEFAULT 0`、`has_china_pcb_supplier boolean DEFAULT true`；行 149-154 创建普通索引；行 913 写“ALTER ADD COLUMN ... NULL 不锁表（PostgreSQL 11+）”。但其中两个字段不是 NULL-only。 | 修改为：字段新增在 PG 11+ 不触发表重写（常量默认），但仍需要短暂 DDL 锁；生产索引用 `CREATE INDEX CONCURRENTLY` 或停服窗口内实测。若使用 Alembic transaction，`CONCURRENTLY` 需单独 autocommit。 |
| H-02 | `idx_shared_companies_normalized_country` 被当成 UPSERT 去重依据，但设计只创建普通 index，不是 UNIQUE index；PostgreSQL `ON CONFLICT` 不能引用普通表达式索引。 | `design.md` 行 513 写“UPSERT shared_companies（按 (normalize_name, country) 去重）”；行 759-763 仅写 `CREATE INDEX idx_shared_companies_normalized_country ON shared_companies (normalize_company_name(name), country)`。现有 schema 行 270-292 的 `shared_companies` 没有 `(normalize_company_name(name), country)` 唯一约束。 | 需要 `CREATE UNIQUE INDEX uq_shared_companies_normalized_country ON shared_companies (normalize_company_name(name), country) WHERE country IS NOT NULL`，或改用先 SELECT 再 INSERT 并处理并发冲突。否则 UPSERT 语义不成立。 |
| H-03 | `matched_keywords` 在 design.md 里被当作 `ARRAY` 字段使用，但现有 `tenant_companies` 没有该列；历史决策 D-012 提过 jsonb 数组，当前 scope 又把 D-009 fan-out 放到 v3-collection-pushback。字段类型和迁移归属不清，会导致 cleanup_service SQL 和前端筛选断裂。 | `design.md` 行 523-529 使用 `matched_keywords = ARRAY[...]`；现有 schema 行 390-408 无 `matched_keywords`，只有 `keyword_id`。Open questions 中 D-012 曾决策 `tenant_companies.matched_keywords jsonb 数组字段`，但本轮最高真源 `_control/v3/07-v3-scope-final.md` 行 81 把 UC-11 fan-out 归到 v3-collection-pushback。 | design.md 必须决定：本 change 是否给 `tenant_companies` 加 `matched_keywords jsonb/text[]`。若加，写入 0014 字段和 GIN 索引；若不加，cleanup_service 只能写 `keyword_id/collection_task_id`，跨租户复用另 change 实现。 |
| H-04 | `company_sources.source_type` 设计值写成 `'tengdao'`，但现有 schema check constraint 是 `'tengdao'` 还是历史代码里同时出现 `tendata`/`tengdao` 混用，需统一，否则 `INSERT company_sources` 可能违反约束或 UI 过滤不一致。 | `schema.sql` 行 297-306 允许 `('waimao_tong','tengdao','lixiaoyun')`；`design.md` 行 517-519 用 `'tengdao'`；但 raw 表命名是 `tendata_raw_*`，admin UI 方法名是 `list_raw_companies(table="tendata")`，`admin_collection_service.py` 行 402-416 使用 `"tendata"` 表参数。 | 数据库 source_type 保持 `tengdao`，API/UI 参数可用 `tendata`，但 design.md 需要加一张命名映射表，避免开发时把 source_type 写成 `tendata`。 |
| H-05 | 设计说本 change “不改 competitor_companies schema”，但 §2.5b 粘贴的是 schema.sql 基础表，未体现 0008 增补字段；同时 collection_service 当前 INSERT 使用 0008 字段。若 0009 partial/drop 处理不当，会回退到缺字段结构。 | `design.md` 行 327-347 说 competitor 表已存在且不改；粘贴字段只有 `company_name/domain/reason/source_type/raw_data` 等。实际 0008 行 12-23 给 `competitor_companies` 加 `source_id/company_name_en/esdate/legalperson/reg_capital/.../updated_at`；`collection_service.py` 行 673-695 INSERT/UPDATE 正在用这些字段。 | §2.5b 应注明“实际生产结构 = schema.sql + 0008 enrichment”，并在 0009 partial 明确绝不 drop/recreate competitor_companies。staging 校验加一项：0008 字段仍存在。 |
| H-06 | admin clean/raw 页面查询仍引用 `clean_companies` 和 `waimaotong_raw_*`，design.md 只说 cleanup_service 改 50-100 行，低估了后台 API 同步改造范围。 | `admin_collection_service.py` 行 355-369 dashboard 查 `clean_companies`；行 471-527 `list_clean_companies` 查 `clean_companies`；行 563-606 health reconcile 仍查 `waimaotong_raw_companies` / `clean_companies` / `tc.clean_company_id`。`design.md` 行 115 估算仅改 cleanup_service 50-100 行。 | tasks/design 应增加 admin_collection_service API 改造：clean 列表改查 `shared_companies + company_sources`；raw 表移除/隐藏 waimaotong；health reconcile 支持 tendata text PK。否则 admin-clean-companies / admin-tendata-raw 原型无法工作。 |

---

## 3. Medium / Low

| ID | finding | 证据(行号) | 建议 |
|---|---|---|---|
| M-01 | `cleanup_queue` 缺少 lease/heartbeat 字段，但 design.md §6 又把 cleanup_service 作为 WorkerBase 首个使用者，`_heartbeat_loop` 无字段可续约。 | `design.md` 行 169-181 的 cleanup_queue 无 `lease_id/lease_owner/lease_expires_at/heartbeat_at`；行 659-663 定义 heartbeat/reset。现有 cleanup_service 行 68-77 只是把 pending 改 processing，无 lease 超时恢复。 | 要么本 change 不做 heartbeat，只保留 retry；要么 0009a 给 cleanup_queue 加 lease 字段并改 claim/reset 语义。 |
| M-02 | `contact_count` 维护 SQL 按 `tenant_contacts.shared_company_id` 统计，但现有 `tenant_contacts` 没有该字段，只有 `tenant_company_id` 和 `contact_id`。 | `design.md` 行 553-560：`FROM tenant_contacts WHERE shared_company_id = shared_companies.id`。实际 schema 行 504-518：`tenant_contacts.tenant_company_id`、`contact_id`，无 `shared_company_id`。 | 改为从 `shared_contacts` 统计 `company_id = shared_companies.id`，或 join `tenant_contacts -> tenant_companies -> company_id`，并明确是共享联系人数量还是租户可见联系人数量。 |
| M-03 | `has_china_pcb_supplier` 推断函数永远返回 true：`any(...) or True` 恒 true，和字段语义“是否有中国 PCB 供应商”不一致。 | `design.md` 行 599-605：`return any(_is_china_company(s) for s in pcb_suppliers) or True`，空列表也 `return True`。 | 如果用户决策是反推默认 true，应写清“V3 固定 true，不做推断”；如果要推断，则移除 `or True` 并保留 NULL/false 的语义。 |
| M-04 | AI 回填按租户取 OpenRouter key 与 shared 层多租户共享数据存在归属矛盾：同一 shared company fan-out 多租户时，用哪个租户的 key 调 AI 不明确。 | `design.md` 行 607-610 说每租户每天 100 次 AI 推断；行 796-799 说 cleanup_service 调 AI 时按租户取 key。shared_companies 是共享层，行 36-40、73-78 说明多租户共享。 | 把 AI 回填移出 shared cleanup 同步路径，改为平台 key / 平台任务，或在 tenant 私有评分 worker 中做租户级推断；不要在共享数据写入时依赖随机租户 key。 |
| M-05 | `raw_table` 命名允许 `lixiaoyun_raw_companies` 入队但 cleanup_service “标 done 跳过”，会污染队列吞吐和健康指标，且 V3 业务路径已说明励销云不入 clean。 | `design.md` 行 192-195 要励销云 enqueue 后跳过；行 483-490 标 done。业务真源 `_control/v3/00-v3-business-goals.md` 行 89-90 明确励销云不进干净库。 | 如果只为审计，励销云 raw 不必入 cleanup_queue；保留 raw 表即可。若坚持入队，需要 health 指标区分 skipped/done，避免误报清洗吞吐。 |
| M-06 | `collection_keywords` 改造的默认值与现有 0009 不一致，design.md 未解释为何每日限制从 30/100 改 1000/1000。 | `design.md` 行 284、289 写 `daily_stage1_limit int DEFAULT 1000` / `daily_stage2_limit int DEFAULT 1000`；原 0009 行 157、162 是 30 / 100；业务真源 `_control/v3/00-v3-business-goals.md` 行 86-87 是 1000 条/数据源/天。 | 以 business-goals 为准可以接受，但 design.md 应注明这是对 0009 的有意修订，而非“沿用 0009”。 |
| M-07 | `keyword_master + tenant_keyword` 说“仅迁移层占位”，但 RLS policy 使用 `current_tenant_id()`，没有说明服务端 worker/admin 是否需要 bypass 或 service role。 | `design.md` 行 363-385 创建表和 RLS；scope 行 81 把 UC-11 fan-out 归后续。 | 占位迁移可建表，但 RLS/写入策略应延后或补充 worker 使用数据库角色说明，避免后续 fan-out worker 被 RLS 拦截。 |
| L-01 | 测试列表里有拼写/格式错误，可能影响任务拆分质量。 | `design.md` 行 810 写 `├_lixiaoyun_skip`，少 `test_` 前缀和树形符号。 | 改成 `test_lixiaoyun_skip`。 |
| L-02 | 部署示例同时说 OpenRouter key 从 admin 表密文取，又在 k8s yaml 里放 `OPENROUTER_API_KEY` secret，职责冲突。 | `design.md` 行 796-799 说从 `openrouter_providers` 表按租户取 key；行 877-881 又配置 `OPENROUTER_API_KEY` 环境变量。 | 二选一：V3 若使用 admin 配置，则 worker 只需要 DB key 解密能力；环境变量只保留加密密钥/默认兜底，不要命名成 OpenRouter API key。 |

---

## 4. 已验证正确（可选）

- 方案 B 的核心方向成立：`shared_companies`、`company_sources`、`tenant_companies` 已在当前 schema 中存在，且 `tenant_companies.company_id` 已指向 `shared_companies(id)`；见 `schema.sql` 行 270-308、390-408。
- design.md 对 4 类公司数据的业务隔离方向基本正确：励销云是同行/stage 2 输入，腾道 raw 是原始数据，shared 是清洗后干净库，tenant 是 RLS 视图；见 `design.md` 行 18-45、86-92。
- design.md 与业务真源 §5.2 大方向一致：`_control/v3/00-v3-business-goals.md` 行 86-91 明确“励销云 + 腾道”“raw → clean → tenant 分发”“励销云不进干净库”“干净库唯一来源 = 腾道”。
- 不跑原 0009 破坏性 upgrade 的判断正确：原 0009 行 19-22 会 `DROP TABLE tenant_companies/competitor_companies/company_sources/shared_companies CASCADE`，确实违反用户方案 B。
- 保留 `company_sources` 多源映射是合理的：当前 schema 行 297-308 已有 `UNIQUE (source_type, source_id)` 和 `idx_company_sources_company`，比 JSON 数组更适合 admin 按来源筛选。
- cleanup_service 现有工程骨架存在：`cleanup_service.py` 行 64-82 已有 `FOR UPDATE SKIP LOCKED` claim，行 100-113 有 attempts/failed 处理，行 270-285 有 failed 重置。
- 励销云不入 clean 的代码方向已有雏形：`cleanup_service.py` 行 89-90 对 `lixiaoyun_raw_companies` 直接 pass 后标 done，符合业务隔离方向。
- 0008 已经补足 competitor enrichment 字段，collection_service 当前 stage 1 写 competitor 的路径有代码依据；见 `20260429_0008_competitor_enrichment.py` 行 12-29 与 `collection_service.py` 行 666-720。

---

## 5. 无技术背景版摘要（3-5 条）

1. **现在不能签字实施。** 设计方向对，但里面几处字段名和数据库真实结构对不上，按原文写代码会直接迁移失败或运行失败。
2. **最大问题是“客户视图表”的字段名。** 真实库叫 `company_id`，设计文档写成 `shared_company_id`，还把它留给“运维确认”；这不是运维问题，是设计必须先定死的问题。
3. **腾道数据目前进不了清洗队列。** 队列表要求数字 ID，但腾道 raw 表主键是文本 `tid`；如果不改，V3 声称的“腾道 → 清洗 → 客户库”主链路断掉。
4. **迁移链不能跳着跑。** 文档说跳过 0012、拆 0009a，但 Alembic 是一条链，必须明确改 revision 链，否则 `upgrade head` 不会按设计执行。
5. **加字段不是“完全不锁表”。** PostgreSQL 11+ 可避免默认值重写整表，但 DDL 和建索引仍有锁；生产要用 staging 实测和停服/并发索引策略。

---

## 6. 原始需求 → 已实现/未实现 对照清单

| 原始需求 | 状态 | 说明 |
|---|---|---|
| 先快速读 `design.md + schema.sql + cleanup_service.py + alembic 0009` 后开写报告 | 已实现 | 已读取四类文件，并补充读取 `_control/v3/07-v3-scope-final.md`、business-goals §5.2、0008、admin_collection_service 作为必要证据。 |
| 审查重点 1：tenant_companies FK 字段名 / 0014 未真正处理 FK 切换 | 已实现 | 见 B-01。 |
| 审查重点 2：cleanup_service SQL 是否完整 | 已实现 | 见 B-02、B-05、H-02、H-03、M-02。 |
| 审查重点 3：alembic 0009a 拆分策略是否能跑 | 已实现 | 见 B-03、B-04。 |
| 审查重点 4：4 类公司数据流是否对齐 business-goals §5.2 | 已实现 | 方向正确但实现链路有阻塞；见“已验证正确”和 B-02/B-05。 |
| 审查重点 5：5 字段 ADD COLUMN 是否真的不锁表 | 已实现 | 见 H-01。 |
| 输出落盘到 `_control/reviews/codex-code-review-v3-data-foundation-design.md` | 已实现 | 本文件即落盘报告。 |
| 不修改被审文件 | 已实现 | 未修改 `openspec/changes/v3-data-foundation/design.md`、schema、cleanup_service、alembic 文件。 |
| 不写代码 | 已实现 | 仅新增审查报告 Markdown。 |
| 每 finding 带文件路径或行号 | 已实现 | 各 finding 均含路径与行号；未完全确认处用“⚠️/需确认”语义标注在正文。 |

---

## 7. Blocker 逐项展开

### 7.1 B-01 tenant_companies 字段名/FK

- design.md 当前写法把字段命名作为“运维待确认”。
- 这不应留到运维阶段。
- 原因：代码生成、SQL 编写、测试断言、API 字段映射都会依赖这个字段名。
- 当前仓库已有明确事实。
- `schema.sql` 行 390：`CREATE TABLE tenant_companies`。
- `schema.sql` 行 393：`company_id uuid NOT NULL REFERENCES shared_companies(id)`。
- `schema.sql` 行 407：`UNIQUE (tenant_id, company_id)`。
- 因此当前生产基线语义是“租户公司视图通过 `company_id` 指向 shared company”。
- `design.md` 行 523-529 使用 `shared_company_id`。
- 这不是简单命名差异。
- 它会影响 `INSERT` 列名。
- 它会影响 `ON CONFLICT` 目标。
- 它会影响索引名称。
- 它会影响后续 tenant_contacts / group_members / scoring / sending 的 join。
- 当前服务层也已围绕 `tc.company_id` 编写。
- `tenant_query_service.py` 搜索结果显示 `JOIN shared_companies sc ON sc.id = tc.company_id`。
- `tenant_ops_service.py` 搜索结果也显示同样 join 形态。
- `tenant_messaging_service.py` 搜索结果也显示同样 join 形态。
- 如果 0014 新增 `shared_company_id`，会产生双字段并存。
- 双字段并存会让旧代码读 `company_id`、新 cleanup 写 `shared_company_id`。
- 结果是租户页面读不到新写入数据。
- 如果 0014 不新增该字段而直接按 design SQL 执行，则迁移/运行时会报 undefined column。
- 最小修订是接受现状字段名 `company_id`。
- 不建议为了语义更清晰而重命名。
- V3 当前目标是 KISS 和降低迁移风险。
- 若将来要重命名，应另开专门 migration，并全仓同步改 SQL。
- 本次 design.md 应删掉“待运维确认”作为签字阻塞。
- 可保留 staging 校验项：确认 `tenant_companies.company_id` 存在且 FK 指向 `shared_companies(id)`。

### 7.2 B-02 tendata text PK 与 cleanup_queue bigint 冲突

- V3 business-goals 的核心链路是腾道进入干净库。
- `_control/v3/00-v3-business-goals.md` 行 88-91 明确 raw → clean → tenant，且干净库唯一来源是腾道。
- design.md 同意这个方向。
- 但当前队列表设计无法承载腾道主键。
- `design.md` 行 170-172：`raw_table text` + `raw_row_id bigint`。
- `design.md` 行 199-221：`tendata_raw_companies` 主键为 `tid text PRIMARY KEY`。
- text 主键不能无损塞进 bigint。
- 现有代码已经踩到这个问题。
- `collection_service.py` 行 105-108 注释说明 `tid` 是 text PK，不能进入 `cleanup_queue.raw_row_id bigint`。
- `collection_service.py` 行 224-229 对 tendata 只 upsert raw，不 enqueue。
- `cleanup_service.py` 行 160-166 读取 tendata 时还写 `WHERE id = :id`。
- 设计表没有 `id` 列。
- 所以即便强行 enqueue，cleanup_service 也查不到 raw 行。
- 这是主链路阻断，不是边缘 bug。
- 推荐修订队列表，而不是给 tendata 另造 bigint surrogate id。
- 最小方案：把 `raw_row_id bigint` 改为 `raw_row_pk text`。
- `waimaotong` 如果未来回归，可把 bigint id cast 成 text。
- `lixiaoyun` 如果仅审计，可不入队。
- cleanup_service 根据 `raw_table` 决定 lookup 字段。
- 对 tendata：`WHERE tid = :raw_row_pk`。
- 对 lixiaoyun：如果仍入队，则 `WHERE id::text = :raw_row_pk` 或 `source_id = :raw_row_pk`。
- 同步修正 `UNIQUE (raw_table, raw_row_pk)`。
- 同步修正 admin health reconcile。
- 同步修正 collection_service `_enqueue_cleanup` 参数类型。
- 没有这项修订，不应签字。

### 7.3 B-03 0009a Alembic revision 链

- design.md 试图避开原 0009 的破坏性 drop。
- 这个目标正确。
- 原 0009 行 19-22 确实 drop 了四张关键表。
- 问题是 design.md 使用“0009a”这个新名字，但没有处理 Alembic 链。
- Alembic 不按文件名自然排序执行。
- Alembic 按 `revision` / `down_revision` 图执行。
- 当前原 0009 的 revision id 是 `20260430_0009`。
- 当前 0010 的 down_revision 是 `20260430_0009`。
- 如果新增一个 `0009a` revision，例如 `20260506_0009a`，0010 不会自动接上它。
- 如果删除原 0009，0010 会找不到父 revision。
- 如果保留原 0009，又新增 0009a，可能出现分叉或重复建表。
- design.md 行 393-404 的链路只是人类阅读顺序，不是 Alembic 可执行图。
- 推荐策略一：重写原 0009 文件内容，但保留 `revision = "20260430_0009"`。
- 这适用于生产尚未跑过 0009 的前提。
- 当前 design.md 行 394 写生产停 0006，但仍标“推断，需运维确认”。
- 因此应先确认生产没有跑 0009。
- 若确认未跑，重写 0009 是最简单方案。
- 推荐策略二：如果原 0009 已被任何环境视为不可改历史，则新建 replacement revision。
- replacement 方案必须同步改 0010 的 down_revision。
- replacement 方案还必须处理本地/测试库已跑旧 0009 的回退或重建。
- design.md 目前没有给出这些操作。
- 因此迁移策略不可签字。

### 7.4 B-04 0012 不能跳过

- design.md 行 401 写 0012 跳过。
- 业务上跳过外贸通 raw contacts 可以理解。
- 但 Alembic 线性链不能跳过中间 revision。
- rg 结果显示 0012 的 down_revision 是 0011。
- rg 结果显示 0013 的 down_revision 是 0012。
- 如果执行 `alembic upgrade head`，Alembic 会执行 0012。
- 如果手工不执行 0012，Alembic 无法自然到 0013。
- design.md 行 724 又写 `alembic upgrade head`。
- 所以文档内部自相矛盾。
- 最小修订方案：保留 0012 revision，但改为空 migration。
- 空 migration 的 upgrade/downgrade 都只 `pass`。
- 这样 0013 链路不需要变。
- 另一方案：修改 0013 down_revision 为 0011。
- 但这会改变历史链，风险略高。
- 如果 0012 已在任何环境执行过，修改链路还要处理版本表状态。
- 因此推荐空 migration。
- design.md 还需说明 0012 业务“跳过”与 Alembic“执行空节点”的区别。

### 7.5 B-05 cleanup_service fan-out 语义

- design.md 行 523-529 的 fan-out SQL 过于简化。
- 它从 `collection_keywords WHERE id = :keyword_id` 取 tenant。
- 这只能覆盖一个 keyword 行。
- 当前现有 cleanup_service 是按 task 关联表找租户。
- `cleanup_service.py` 行 237-247 使用 `collection_task_keywords`。
- 这个方向更接近任务 fan-out。
- 但 V3 还有跨租户历史复用要求。
- `_control/v3/00-v3-business-goals.md` 行 80-82 要求 B 租户配置同关键词时立即看到 A 当年历史数据。
- `_control/v3/07-v3-scope-final.md` 行 81 把 UC-11 fan-out 归 `v3-collection-pushback`。
- 因此本 change 至少要定义边界。
- 边界 A：cleanup_service 只负责当前 task 的 tenant fan-out。
- 边界 B：KeywordMaster 历史 fan-out 后续 change 负责。
- 如果采用边界 A，design.md 不应写“fan-out 到所有命中租户”。
- 如果采用边界 B，本 change 必须提供可复用的 shared → tenant fan-out 函数。
- SQL 还必须写现有字段 `company_id`。
- SQL 还必须决定 `keyword_id` 与 `matched_keywords` 谁是真源。
- 当前 design.md 同时引用 `matched_keywords`，但现有 schema 无该列。
- 这会使 cleanup_service 改造无法按 50-100 行完成。

---

## 8. 签字前必须修订清单

1. 将 `tenant_companies.shared_company_id` 全部改为 `tenant_companies.company_id`，或明确另开全仓重命名迁移。
2. 将 `ON CONFLICT (tenant_id, shared_company_id)` 改为 `ON CONFLICT (tenant_id, company_id)`。
3. 明确 `tenant_companies.matched_keywords` 是否本 change 新增。
4. 如果新增 `matched_keywords`，明确类型为 `jsonb` 还是 `text[]`。
5. 如果不新增 `matched_keywords`，删除 §4.2 中所有数组合并 SQL。
6. 修改 `cleanup_queue.raw_row_id bigint`，使其支持 `tendata_raw_companies.tid text`。
7. 修改 cleanup_service tendata lookup，从 `WHERE id = :id` 改成 `WHERE tid = :raw_row_pk`。
8. 明确 tendata raw 入队由 collection-pushback 还是 data-foundation 实施。
9. 明确 lixiaoyun raw 是否入 cleanup_queue；如入队，增加 skipped 状态或指标。
10. 明确 0009 处理方式：保留 revision id 重写 partial，或 replacement revision。
11. 明确 0010/0011/0013 的 down_revision 是否需要改。
12. 明确 0012 是空 migration 还是改链路，不可写“跳过”。
13. 将 shared company 去重索引改为 UNIQUE，或删除 UPSERT 说法。
14. 给 `company_sources.source_type` 增加 `tendata`/`tengdao` 命名映射说明。
15. 补充 admin_collection_service 从 `clean_companies` 切到 `shared_companies` 的任务。
16. 补充 admin raw 页面隐藏/移除 waimaotong 的任务。
17. 补充 health reconcile 对 tendata text PK 的任务。
18. 修改 `contact_count` 统计 SQL，避免引用不存在的 `tenant_contacts.shared_company_id`。
19. 修正 `has_china_pcb_supplier` 恒 true 的伪推断逻辑。
20. 统一 OpenRouter key 来源：admin 表密文或 k8s secret 二选一。
21. 说明 `ADD COLUMN DEFAULT` 的真实锁语义。
22. 索引创建策略写明是否 `CONCURRENTLY`。
23. staging 验证加入 `EXPLAIN` 或迁移时长实测。
24. staging 验证加入 `tenant_companies.company_id` 写入后页面可读。
25. staging 验证加入 tendata raw 入队后 cleanup_service 可消费。
26. staging 验证加入 0008 competitor enrichment 字段仍存在。
27. staging 验证加入 0012 处理方式与 Alembic current/head 一致。
28. 回滚预案加入 Alembic revision 链修订后的具体 downgrade 命令。
29. 回滚预案加入 `collection_keywords` 字段删除造成数据不可逆的恢复文件路径。
30. 将“50-100 行改造”改成“cleanup_service + admin_collection_service + migration + tests”范围。

---

## 9. 本次审查边界

- 已读取：`openspec/changes/v3-data-foundation/design.md`。
- 已读取：`backend/03_database/schema.sql`。
- 已读取：`backend/app/services/cleanup_service.py`。
- 已读取：`backend/alembic/versions/20260430_0009_phase1_collection_schema.py`。
- 已补充读取：`_control/v3/07-v3-scope-final.md`。
- 已补充读取：`_control/v3/00-v3-business-goals.md` §5.2 附近。
- 已补充读取：`20260429_0008_competitor_enrichment.py`。
- 已补充读取：`admin_collection_service.py` clean/raw/health 相关片段。
- 未读取生产数据库。
- 未读取任何 `.env` 或 secret。
- 未访问工作区外路径。
- 未修改被审文件。
- 未修改 schema。
- 未修改 cleanup_service。
- 未修改 Alembic migration。
- 本报告只基于当前工作区文件事实。
- 生产当前 alembic version 仍需运维核验。
- 生产 PostgreSQL 版本仍需运维核验。
- 生产表数据量仍需运维核验。
- 如生产已经跑过 0009，B-03 的推荐方案需要重新评估。
- 如生产 `tenant_companies` 与当前 schema.sql 不一致，B-01 仍成立，但修订方向需以生产 dump 为准。

---

## 10. 可签字条件

- B-01 已在 design.md 中修正，并明确 `tenant_companies` FK 字段名。
- B-02 已在 design.md 中修正，并给出 tendata 入队可执行 SQL。
- B-03 已在 design.md 中修正，并给出 Alembic revision 链唯一方案。
- B-04 已在 design.md 中修正，并消除“跳过 0012”和 `upgrade head` 的矛盾。
- B-05 已在 design.md 中修正，并明确 fan-out 边界与字段类型。
- H-01 已修正为准确的 PostgreSQL DDL 风险描述。
- H-02 已补唯一约束或改掉 UPSERT 语义。
- H-03 已明确 `matched_keywords` 归属。
- H-06 已把 admin API 改造纳入任务范围。
- staging 验证步骤能覆盖 raw → cleanup → shared → tenant 的真实 SQL。
- 回滚方案能对应修订后的 Alembic 链路。
- 完成以上条件后，可再进入实施前签字审。
