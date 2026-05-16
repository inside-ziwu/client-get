# Codex Review · design.md · Round 4

## 0. 总体结论

本轮只验证用户指定的 4 项，不重审 Round 1/2/3 已关闭 finding。

结论：**不建议签字**。Round 3 残留的 2 项已经大体清干净，但 2026-05-06 新增的 `competitor_companies` 同行重构仍有 3 个阻塞问题：

1. §1.0 仍残留“租户级”口径，与“平台级 / 关键词级”目标冲突。
2. 0014 downgrade 对 V3 新写入的 `tenant_id = NULL` 数据不可逆，执行 `ALTER tenant_id SET NOT NULL` 会失败。
3. §4.5 只写了“拿到同行结果后的去重写入”，没有写“调用励销云前按 keyword_normalized 短路”，因此还不能保证同关键词跨租户复用能节省 stage 1 API 调用。

另外有 2 个中风险一致性问题：`collection_service` 当前调用链仍按 `tenant_id -> keyword_id` 和 `competitor_contacts.tenant_id NOT NULL` 运行，设计没有交代兼容改法；§3.6 的普通索引注释仍提 `CONCURRENTLY`，虽比 Round 3 清晰，但还有注释歧义。

## 1. 验证表

| 项 | 状态 | 证据(行号) |
|---|---:|---|
| Round 3 §2.1 H-01：CONCURRENTLY 注释 / SQL / §3.6 一致 | ⚠️ | `design.md:539-540` 已写“默认停服窗口普通 CREATE INDEX；大表在 Alembic 外用 CONCURRENTLY + autocommit”；`design.md:596` 风险说明也一致。但 `design.md:554` 仍在当前普通 `CREATE INDEX` 代码块内写“建议使用 CONCURRENTLY；需在 autocommit 块外”，措辞仍可能误导实施者。 |
| Round 3 §2.2 M-05：lixiaoyun “标 done 跳过”旧表述 | ✅ | `rg "标 done"` 仅命中 `design.md:199`，语义是“原设计让励销云 raw 入队然后标 done 跳过”这一历史错误说明；当前执行规则在 `design.md:735-740` 和 `design.md:1194` 均改为误入队则 mark failed 报警。 |
| 同行重构 §1.0 4 类公司数据表 ① 同行 | ❌ | `design.md:26-30` 表格已写“关键词级 / 平台级、同关键词跨租户复用”；但业务流图仍在 `design.md:55` 写 `competitor_companies` 是“租户级，永不可见”；生命周期表 `design.md:102` 仍写去重是 `UNIQUE (tenant_id, company_name)`，没有同步为关键词级。 |
| 同行重构 §2.5b / §2.5c | ⚠️ | `design.md:332-361` 已补 schema.sql + 0008 enrichment 现状；`design.md:364-390` 已写 `keyword_normalized` + `tenant_id DROP NOT NULL` + 新 UNIQUE 索引。但 `design.md:353` 把 `esdate` 写成 `date`，实际 0008 是 `varchar(50)`；`design.md:388-390` 说旧 UNIQUE 保留做历史兜底可以接受，但未说明新 NULL 行不会被旧 UNIQUE 约束。 |
| 同行重构 §3.6 0014 upgrade | ✅ | `design.md:563-575` 明确加 `keyword_normalized`、放宽 `tenant_id nullable=True`、创建 `uq_competitor_companies_keyword_company` 和普通 keyword 索引。 |
| 同行重构 §3.6 0014 downgrade | ❌ | `design.md:578-582` 先 drop 索引，再 `tenant_id nullable=False`，再 drop `keyword_normalized`。若 upgrade 后已有 V3 新数据 `tenant_id = NULL`，`SET NOT NULL` 会失败；downgrade 缺少删除、回填或隔离 V3 NULL 数据的步骤。 |
| 同行重构 §4.5 collection_service 写入逻辑 | ⚠️ | `design.md:844-907` 已写按 `keyword_normalized + company_name` 查重、新写入 `tenant_id=NULL`、stage 2 按 keyword 读取。但该伪代码发生在 `raw_competitor` 已经返回之后，不能支撑 `design.md:904` 所说“B 租户命中后跳过励销云调用”。 |
| 业务问题：同关键词跨租户复用 | ❌ | `design.md:902-907` 写了目标效果；但缺少调用励销云前的短路查询与任务状态分支。只靠 `upsert_competitor_v3()` 不能减少 API 调用，因为函数输入已经是励销云返回的 competitor。 |
| 业务问题：tenant_id NULL 兼容历史数据 | ⚠️ | `design.md:371-390` 对 upgrade 兼容历史数据的方向正确；历史 `tenant_id IS NOT NULL` 行保留，V3 新行用 `tenant_id=NULL`。但 downgrade 不兼容，见本表 downgrade 项。 |
| 业务问题：不破坏 collection_service 现有调用 | ⚠️ | 现有 `collection_service.py:626-628` / `:642-647` 按 tenant 循环调用 `_upsert_competitor(conn, tenant_id, competitor)` 并写 `competitor_contacts(tenant_id)`；现有 `_upsert_competitor` SQL 在 `collection_service.py:673-681` 使用 `ON CONFLICT (tenant_id, company_name)`。设计新签名 `design.md:859` 改成 `(keyword_normalized, raw_competitor)`，但没有说明调用方和 contacts 写入如何迁移。 |

## 2. 同行重构技术正确性分析

### 2.1 设计目标是对的

用户指出“同行公司”业务上不是租户私有数据，这个判断正确。

现有 schema 明确是租户级：

- `schema.sql:490-500`：`competitor_companies.tenant_id uuid NOT NULL`，并且 `UNIQUE (tenant_id, company_name)`。
- 现有 `collection_service.py:673-681` 也是按 `tenant_id + company_name` upsert。

如果 A/B 两个租户配置同一个关键词，当前结构会重复保存同一批中国同行，也会重复触发励销云 stage 1。这确实是设计偏差。

Round 4 新增方向：

- `design.md:371-374`：新增 `keyword_normalized`，并允许 `tenant_id NULL`。
- `design.md:377-379`：新增 `UNIQUE (keyword_normalized, company_name)` partial index。
- `design.md:883-890`：新写入用 `tenant_id=NULL` 标记平台级数据。
- `design.md:907`：stage 2 按 `keyword_normalized` 读取同行输入，不再按 tenant 过滤。

这些方向能把“同关键词同公司”从租户级重复行改成关键词级共享行。

### 2.2 schema 兼容性：upgrade 基本可行，downgrade 不完整

upgrade 兼容历史数据：

- 历史行保留 `tenant_id IS NOT NULL`，`keyword_normalized` 留 NULL。
- V3 新行写 `tenant_id=NULL`，`keyword_normalized IS NOT NULL`。
- 新 UNIQUE 索引只覆盖 `keyword_normalized IS NOT NULL` 的 V3 新行。

但 downgrade 现在不可执行：

- `design.md:581` 直接把 `tenant_id` 改回 NOT NULL。
- 如果生产已经有任意 V3 新同行行 `tenant_id=NULL`，PostgreSQL 会拒绝 SET NOT NULL。
- `design.md:582` 随后 drop `keyword_normalized`，但这一步在前一步失败后不会执行。

可行修订必须三选一：

1. downgrade 明确删除 V3 平台级同行行：`DELETE FROM competitor_companies WHERE tenant_id IS NULL`，再 SET NOT NULL。
2. downgrade 要求先人工 ETL，把 NULL 行复制 / 归属到某个 tenant，再 SET NOT NULL。
3. 声明 0014 downgrade 对平台级同行数据是破坏性回滚，并在代码块里显式执行破坏性清理。

当前只写“恢复 NOT NULL”不够。

### 2.3 业务效果：当前文档还没有真正保证“跳过励销云调用”

`design.md:902-905` 的业务效果写得很明确：

- A 租户首次关键词写入 100 行。
- B 租户同关键词命中后跳过励销云调用，节省 API 配额。

但 §4.5 的伪代码入口是：

```python
async def upsert_competitor_v3(conn, keyword_normalized, raw_competitor):
```

这个函数已经拿到了 `raw_competitor`，说明励销云调用已经发生。

要真的解决业务问题，需要在 stage 1 调用外部 API 之前增加分支：

1. 根据当前 task / collection_keyword 拿到 `keyword_normalized`。
2. 查询 `competitor_companies WHERE keyword_normalized = :kw` 是否已有足够同行。
3. 如已有，直接创建 / 推进 buyer_lookup stage 2，输入现有同行清单。
4. 如没有，才调用励销云 stage 1，并按 §4.5 写入平台级同行。

否则 §4.5 只能去重写库，不能减少跨租户重复采集。

### 2.4 collection_service 调用兼容性仍缺设计

现有代码路径有两个事实：

- `save_competitors_partial()`：`collection_service.py:626-628` 通过 `_get_tenant_keyword_map()` 拿 tenant，再逐 tenant 调 `_upsert_competitor()`。
- `save_competitor_enriched()`：`collection_service.py:642-647` 同样逐 tenant upsert competitor，并把联系人写入 `competitor_contacts`。

新设计把 `_upsert_competitor` 变成关键词级：

- `design.md:859`：签名只收 `keyword_normalized, raw_competitor`。
- `design.md:887-889`：INSERT 时 `tenant_id=NULL`。

缺口：

1. 当前 `_get_tenant_keyword_map()` 只返回 `tenant_id -> keyword_id`，不是 `keyword_normalized`。
2. 当前 `competitor_contacts` 由 0008 创建，`tenant_id NOT NULL`；平台级 competitor 后，contacts 是否仍按 tenant 存、是否改为平台级、是否不再保存，都没有说明。
3. 当前 `ON CONFLICT (tenant_id, company_name)` 要改成新索引逻辑；这会影响 partial/enriched 两条保存路径。

这不是代码实现细节，而是避免现有调用断裂的设计前置条件。

### 2.5 §1.0 仍会误导实现者

本轮特别要求检查 §1.0，但这里仍有明显残留：

- `design.md:26-30` 表格写对了：关键词级 / 平台级。
- `design.md:55` 图里仍写“租户级，永不可见”。
- `design.md:91` 写 `collection_service.py:673` “已实现，本 change 不改”，但 `design.md:835` 和 `design.md:844-907` 又把 collection_service 同行写入列为本轮新增改造。
- `design.md:102` 生命周期表仍把同行去重写成 `UNIQUE (tenant_id, company_name)`。

这 4 处会让实现者不确定到底是“只改 schema”还是“同步改 collection_service 调用链”。

### 2.6 Round 3 残留状态

H-01：

- 已从 Round 3 的“注释说 CONCURRENTLY、SQL 不用、另处说停服窗口”大冲突，收敛为“默认停服窗口普通索引；大表 Alembic 外 CONCURRENTLY”。
- 但 `design.md:554` 的注释仍放在普通索引 SQL 上，建议改成：“默认停服窗口普通 CREATE INDEX；如不停服则不要执行本段，改用 Alembic 外 autocommit + CREATE INDEX CONCURRENTLY”。

M-05：

- `design.md:199` 只是历史错误说明，不是当前执行方案。
- `design.md:735-740` 和 `design.md:1194` 已统一为误入队标 failed 报警。
- 这项可以关闭。

## 3. 新引入问题

### H-01：0014 downgrade 对 `tenant_id=NULL` 平台级同行数据不可逆

证据：

- `design.md:883-890` 新写入 `tenant_id=NULL`。
- `design.md:578-582` downgrade 直接 `tenant_id nullable=False`。

影响：

- 一旦已有 V3 新同行数据，downgrade 会失败。
- 这违反 PM checklist `design.md:1331` “§2 数据模型变更可逆（downgrade 完整）”。

建议：

- 在 downgrade 中明确处理 `tenant_id IS NULL` 行。
- 同时在 §12 R8 里补充“回滚会删除或迁移平台级同行数据”的风险。

### H-02：跨租户复用只写了入库去重，没有写调用前短路

证据：

- `design.md:859` 的函数需要 `raw_competitor`。
- `design.md:904` 却承诺 B 租户同关键词时“跳过励销云调用”。

影响：

- 实现者按当前伪代码写，只能减少重复行，不能减少 API 调用。
- 用户提出的问题核心是“同行应平台级 / 关键词级复用”，不只是唯一索引。

建议：

- §4.5 增加 `get_or_collect_competitors(keyword_normalized)` 流程。
- 明确已有同行时如何创建 stage 2 buyer_lookup task。

### H-03：§1.0 仍把同行写成租户级

证据：

- `design.md:55` 写“租户级，永不可见”。
- `design.md:102` 写 `UNIQUE (tenant_id, company_name)`。

影响：

- 与 `design.md:26-30` / `design.md:364` / `design.md:844` 的关键词级重构冲突。

建议：

- §1.0 全部改成“平台级 / 关键词级，永不对 tenant 暴露”。
- 生命周期表去重改成 `UNIQUE (keyword_normalized, company_name) WHERE keyword_normalized IS NOT NULL`。

### M-01：collection_service 现有调用链兼容说明不足

证据：

- 现有 `collection_service.py:626-628`、`:642-647` 逐 tenant upsert。
- 现有 `collection_service.py:673-681` 按 `(tenant_id, company_name)` conflict。
- 设计新函数 `design.md:859` 不再接 tenant_id。

影响：

- 实现时可能只改 `_upsert_competitor()`，导致调用方参数、联系人保存、stage 2 输入都断。

建议：

- §4.5 拆出调用链改造清单：partial save、enriched save、contacts 保存、buyer_lookup task 创建。
- 明确 `competitor_contacts` 是否保留租户级；若保留，说明平台级 competitor 与租户级 contacts 的关系。

### M-02：0008 enrichment 字段类型引用有误

证据：

- `design.md:353` 写 `esdate date`。
- 实际 `20260429_0008_competitor_enrichment.py:15` 是 `esdate varchar(50)`。

影响：

- 如果按 design 直接写 migration 或测试断言，会和现有 schema 不一致。

建议：

- §2.5b 按实际 0008 字段类型修正。

## 4. 无技术背景版摘要

Round 3 剩下的两处旧问题基本清掉了：励销云不会再被描述成“入队后标 done”，索引锁表说明也比之前准确。

但新的“同行公司改成平台级 / 关键词级”还没写严谨。现在文档一边说同行是平台级，一边还在图里写租户级；一边说 B 租户同关键词可以跳过励销云调用，一边只写了拿到励销云结果之后如何去重入库。

最关键的是回滚：新方案会写 `tenant_id=NULL` 的平台级同行数据，但 downgrade 又直接把 `tenant_id` 改回必填，这在数据库里会失败。

所以本轮不建议签字。修完 §1.0 口径、0014 downgrade、collection_service 调用前复用流程后，可以再做一轮很窄的 Round 5 验证。

## 5. 原始需求对照

| 原始需求 | 已实现 / 未实现 |
|---|---|
| 只验证 Round 3 H-01 / M-05 残留 | 已实现；H-01 仍有轻微注释歧义，M-05 可关闭。 |
| 验证同行重构 4 处修订是否一致 | 已实现；§1.0 与 §3.6 downgrade 不一致，§4.5 业务流程不完整。 |
| 判断同行重构是否真的解决业务问题 | 已实现；当前设计只能解决部分 schema 去重，未完整解决调用前跨租户复用。 |
| 不重审 Round 1/2/3 已关闭 finding | 已遵守；仅引用必要上下文。 |
| 不审 proposal/tasks/其他 change | 已遵守；未审 proposal/tasks。 |
| 不修改被审文件 | 已遵守；未修改 `openspec/changes/v3-data-foundation/design.md`。 |
| 输出到指定 Round 4 报告路径 | 已实现；本文件即 `_control/reviews/codex-code-review-v3-data-foundation-design-round4.md`。 |
