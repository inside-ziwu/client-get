# Codex Review · design.md · Round 5

## 0. 总体结论

本轮只验证 Round 4 报告列出的 5 项残留：H-01、H-02、H-03、M-01、M-02。

结论：**可以针对这 5 项签字**。

残留阻塞：**无**。

非阻塞瑕疵：0014 downgrade 代码注释写“详 §12 R8 风险”，但 §12 实际新增破坏性回滚风险是 R9。风险表本身已正确新增 R9，因此不影响本轮签字，但建议顺手把注释改成 R9，避免后续读者跳错风险项。

本轮未重审 Round 1/2/3/4 已关闭 finding，未审 proposal/tasks，也未修改 `openspec/changes/v3-data-foundation/design.md`。

## 1. 5 项验证表

| ID | 状态 | 证据(行号) |
|---|---:|---|
| H-01 0014 downgrade 兼容 V3 NULL 数据 | ✅ | `design.md:578-586` 的 downgrade 已先 drop 新索引，再执行 `DELETE FROM competitor_companies WHERE tenant_id IS NULL`，然后才 `tenant_id nullable=False` 和 drop `keyword_normalized`。这解决了 Round 4 指出的 PostgreSQL `SET NOT NULL` 会因 V3 平台级 NULL 行失败的问题。 |
| H-01 §12 风险表加 R9（破坏性回滚） | ✅ | `design.md:1392` 已新增 `R9`：明确 0014 downgrade 是破坏性回滚，会删除 `tenant_id IS NULL` 的平台级同行数据，并要求回滚前 pg_dump 备份。 |
| H-02 §4.5 调用前短路：新增 `get_or_collect_competitors()` | ✅ | `design.md:848-856` 明确 §4.5 目标是“关键词级去重 + 调用前短路”，且强调仅入库去重不能减少 API 调用，必须在调用励销云前判断是否已有同关键词同行清单。 |
| H-02 先按 `keyword_normalized` COUNT 检查，足够则跳过励销云 | ✅ | `design.md:860-879` 新增 `get_or_collect_competitors(conn, keyword_normalized, task_id)`，在调用励销云前执行 `SELECT COUNT(*) FROM competitor_companies WHERE keyword_normalized = $1`；`design.md:873-879` 写明 `existing_count >= STAGE1_MIN_COMPETITORS_THRESHOLD` 时返回 `api_called: False`。 |
| H-02 `upsert_competitor_v3()` 仅在调用后用 | ✅ | `design.md:881-886` 只有在 Step 2 真调 `lixiaoyun_provider.search_competitors()` 后，Step 3 才循环调用 `upsert_competitor_v3()`；`design.md:903-955` 将该函数限定为关键词级写入/更新函数。 |
| H-03 §1.0 业务流图统一平台级 / 关键词级 | ✅ | `design.md:54-56` 已把业务流图中 `competitor_companies` 标为“平台级 / 关键词级，永不可见”，不再残留 Round 4 的“租户级”。 |
| H-03 §1.0 生命周期表去重列改为关键词级 | ✅ | `design.md:95-102` 生命周期表中 ① 同行的去重已改成 `UNIQUE (keyword_normalized, company_name) WHERE keyword_normalized IS NOT NULL`，并说明旧 `UNIQUE(tenant_id, company_name)` 只作历史数据兜底。 |
| H-03 §1.0 关键澄清写明“V3 重构” | ✅ | `design.md:87-92` 的关键澄清已写“励销云数据由 collection_service.py:673 直接写 ① 同行”，并明确“V3 重构：从租户级改关键词级”。 |
| M-01 §4.5 拆调用链改造清单 | ✅ | `design.md:895-901` 已把调用方改造拆成清单：`_get_tenant_keyword_map()` 改为 `_get_keyword_normalized_for_task(task_id)`；逐 tenant 循环 upsert 改为单次 `upsert_competitor_v3()`；stage 2 buyer_lookup task 改为按 `keyword_normalized` 创建。 |
| M-01 partial save / enriched save / contacts 保存兼容说明 | ✅ | `design.md:895` 明确覆盖 `save_competitors_partial / save_competitor_enriched`；`design.md:957-968` 单独说明 `competitor_contacts` 现状、V3 决策与改造点。 |
| M-01 明确 `competitor_contacts` V3 期间不写 | ✅ | `design.md:957-968` 明确 `competitor_contacts.tenant_id NOT NULL` 与平台级同行冲突；V3 决策是 `collection_service` 不写 `competitor_contacts`，并删除 `save_competitor_enriched` 中写 contacts 的代码。 |
| M-02 §2.5b `esdate` 字段类型 | ✅ | `design.md:349-353` 的 0008 enrichment 字段清单已写 `ADD COLUMN esdate varchar(50)`，并注明 0008 实际类型是 `varchar(50)`。 |

### 1.1 H-01 细核

Round 4 的 H-01 有两个验收点：downgrade SQL 必须能处理 V3 新写入的 `tenant_id IS NULL` 行；风险表必须写清这是破坏性回滚。

`design.md:581-584` 已把删除 NULL 行放在恢复 NOT NULL 之前，顺序正确。

`design.md:584` 的 SQL 文本与本轮要求一致：`DELETE FROM competitor_companies WHERE tenant_id IS NULL`。

`design.md:585` 再执行 `tenant_id nullable=False`，因此不会再被 V3 NULL 行卡住。

`design.md:1392` 已把“删除平台级同行数据”写成 R9 风险，且给出回滚前备份的缓解措施。

判定：H-01 通过。

### 1.2 H-02 细核

Round 4 的 H-02 核心不是“写入去重”，而是“调用外部 API 前短路”。

`design.md:854` 明确写出“仅入库去重不能减少 API 调用”。

`design.md:860-879` 的新入口函数在调用 `lixiaoyun_provider` 前先 COUNT。

`design.md:873` 用 `STAGE1_MIN_COMPETITORS_THRESHOLD` 作为“已有足够同行”的阈值。

`design.md:875-879` 返回 `api_called: False`，语义上能支持跨租户同关键词复用。

`design.md:881-886` 显示 `upsert_competitor_v3()` 只在真实调用励销云后才执行。

`design.md:974-976` 用 A/B 租户同关键词场景明确展示 B 租户跳过 API。

判定：H-02 通过。

### 1.3 H-03 细核

Round 4 的 H-03 是 §1.0 口径不统一：同一文档里既写平台级，又残留租户级。

`design.md:26-30` 顶部表格已把 ① 同行写成关键词级 / 平台级。

`design.md:54-56` 业务流图也同步为平台级 / 关键词级。

`design.md:87-92` 关键澄清写明 V3 重构是从租户级改关键词级。

`design.md:95-102` 生命周期表把去重约束改为 `keyword_normalized + company_name`。

本轮未发现 §1.0 对 ① 同行继续写“租户级”的残留。

判定：H-03 通过。

### 1.4 M-01 细核

Round 4 的 M-01 是担心只改 upsert 函数，现有 `collection_service` 调用链会断。

`design.md:895-901` 已把调用链改造拆成三项：关键词获取、去掉逐租户循环、stage 2 按关键词创建任务。

`design.md:895` 明确覆盖 partial save 与 enriched save 两条路径。

`design.md:957-968` 单独处理 `competitor_contacts`，不是把 contacts 保存问题留给实现者猜。

`design.md:961` 明确 V3 决策是不写 `competitor_contacts`。

`design.md:968` 明确改造点是删除 `save_competitor_enriched` 中写 contacts 的代码。

判定：M-01 通过。

### 1.5 M-02 细核

Round 4 的 M-02 只要求核对 §2.5b 的 0008 enrichment 字段类型。

`design.md:349-353` 已把 `esdate` 写为 `varchar(50)`。

该行还写了“0008 实际类型是 varchar(50)”，说明这是按实际 migration 修正，不是临时文本替换。

本轮没有扩展审查其他 `esdate` 语义，因为验证清单限定在 §2.5b。

判定：M-02 通过。

## 2. 新引入问题（如有）

### L-01：0014 downgrade 注释引用了错误风险编号

状态：⚠️ 低风险，不阻塞签字。

证据：

- `design.md:581-584` 的 downgrade 注释写“详 §12 R8 风险”。
- `design.md:1391-1392` 显示 R8 是“历史数据并存”，R9 才是“0014 downgrade 是破坏性回滚”。

影响：

- 风险表已正确新增 R9，破坏性回滚风险本身已覆盖。
- 只是代码注释跳转编号错误，可能让实施者读到相邻但不精确的风险项。

建议：

- 把 `design.md:583` 的“详 §12 R8 风险”改成“详 §12 R9 风险”。

## 3. 无技术背景版摘要

1. Round 4 要修的 5 项，本轮核查后都已修到位：同行公司现在按“平台级 / 关键词级”复用，不再按租户重复保存。

2. 最关键的 API 节省逻辑已经补上：系统会先查同关键词是否已有足够同行，有就跳过励销云调用，不再只是“调用后去重入库”。

3. 回滚风险也已写清：如果回滚 0014，会删除 V3 期间平台级同行数据；文档已把它列入 R9 风险，只剩一个注释编号小错。

## 4. 原始需求对照

| 原始需求 | 已实现 / 未实现 |
|---|---|
| 只验证 Round 4 报告 5 项 | 已实现；仅核查 H-01、H-02、H-03、M-01、M-02。 |
| H-01 downgrade 加 `DELETE FROM competitor_companies WHERE tenant_id IS NULL` | 已实现；见 `design.md:581-584`。 |
| H-01 §12 风险表加 R9（破坏性回滚） | 已实现；见 `design.md:1392`。 |
| H-02 §4.5 新增 `get_or_collect_competitors()` | 已实现；见 `design.md:859-892`。 |
| H-02 调用励销云前按 `keyword_normalized` COUNT 短路 | 已实现；见 `design.md:865-879`。 |
| H-02 `upsert_competitor_v3()` 仅在调用后使用 | 已实现；见 `design.md:881-886` 与 `design.md:903-955`。 |
| H-03 §1.0 平台级口径全统一 | 已实现；见 `design.md:54-56`、`design.md:87-92`、`design.md:95-102`。 |
| M-01 拆 collection_service 调用链改造清单 | 已实现；见 `design.md:895-901`。 |
| M-01 明确 `competitor_contacts` V3 期间不写 | 已实现；见 `design.md:957-968`。 |
| M-02 §2.5b 写 `esdate varchar(50)` | 已实现；见 `design.md:349-353`。 |
| 不修改任何被审文件 | 已遵守；只新增本 Round 5 报告。 |
| 不重审 Round 1/2/3/4 已 ✅ finding | 已遵守。 |
| 报告 100-200 行 | 已实现；本报告 152 行。 |
