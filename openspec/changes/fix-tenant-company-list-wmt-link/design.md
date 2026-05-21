## Context

`20260519_0045` 已把 tenant 公司列表从旧 `clean_companies` 切到 `waimaotong_clean_companies`。这个方向保持不变：tenant 用户看到的公司必须来自外贸通清洗后数据。

当前断点不在列表页，而在可见关系生成：

```
tenant_keyword
  -> lixiaoyun_api_companies.keyword_master_id
  -> lixiaoyun_api_clean_companies.keyword_master_ids
  -> waimaotong_raw_companies.source_competitor
  -> waimaotong_clean_companies.sys_company_id
  -> tenant_companies.clean_company_id = waimaotong_clean_companies.id
```

线上实际状态：

- `waimaotong_clean_companies.keyword_master_ids` 全为空。
- `tenant_companies.clean_company_id` 大量仍是旧 `clean_companies.id`。
- `fan_out.py` 仍从 `clean_company_keywords` 写入旧 clean id。
- `waimaotong_raw_companies.source_competitor` 是 wmt 数据回到 lixiaoyun 来源同行的关键字段。
- 当前有 25 条 wmt clean 没能通过 clean 表直接串回关键词，其中 16 条可从 lixiaoyun raw fallback 补回，9 条需要补标准来源身份。

## Goals / Non-Goals

**Goals:**

- tenant 公司列表只展示匹配当前租户 active 关键词的 wmt clean companies。
- 修复 `tenant_companies.clean_company_id`，使其全部指向 `waimaotong_clean_companies.id`。
- 建立可复用的 wmt lineage fan-out 逻辑，替代旧 clean fan-out 写入路径。
- 对当前线上采集字段缺失造成的数据做一次性补全，补齐后再生成 tenant 可见关系。
- 对无法解释血缘的 wmt clean 输出诊断，不允许静默进入 tenant 列表。

**Non-Goals:**

- 不回退 0045，不再把 tenant 列表切回 `clean_companies`。
- 不依赖旧 `clean_company_keywords` 作为 tenant 列表主路径。
- 不用模糊匹配自动写 tenant 可见关系。
- 不修改外部采集程序；仅在本系统内补全血缘、修复关系、防止旧 fan-out 再污染。

## Decisions

### D1: tenant 可见关系以 wmt clean 为唯一公司主体

`tenant_companies.clean_company_id` 字段名保持不变，但语义必须是 `waimaotong_clean_companies.id`。所有新写入路径都必须遵守该语义。

不新增第二套 `tenant_wmt_companies` 表，避免大范围重命名和前端改动。通过测试和诊断保护字段语义。

### D2: 主血缘链路使用 source_competitor 反查 lixiaoyun clean

主路径：

```sql
waimaotong_clean_companies wc
JOIN waimaotong_raw_companies wr
  ON wr.sys_company_id = wc.sys_company_id
JOIN lixiaoyun_api_clean_companies lx
  ON lower(trim(wr.source_competitor)) = lower(trim(lx.entname_eng))
```

再用 `lx.keyword_master_ids` 与 `tenant_keyword.keyword_master_id` 匹配，生成 tenant 可见关系。

选择 `entname_eng` 而不是 `entname`，因为线上验证中 `source_competitor` 是英文同行名，`entname` 为中文公司名。

### D3: clean 缺失时允许 raw fallback

当 `source_competitor` 没有匹配 `lixiaoyun_api_clean_companies.entname_eng`，但能精确匹配 `lixiaoyun_api_companies.entname_eng` 时，可以使用 raw 表的 `keyword_master_id` 作为 fallback。

当前 `APCB ELECTRONICS (KUNSHAN) CO., LTD.` 属于这个类别：16 条 wmt clean 可从 lixiaoyun raw 补回 `电路板` 关键词。

### D4: 未确认来源不得模糊归因

`SHENZHEN KINWONG ELECTRONIC CO LTD` 这类无法精确匹配 clean/raw 的 source competitor，不允许用 `pg_trgm similarity` 或 ILIKE 自动归因。原因是相似名称可能对应多个集团、分公司或地区实体。

处理方式：

- 进入 unresolved lineage 清单。
- 若业务确认标准来源，可通过一次性补全脚本写入明确映射。
- 补齐后再进入 fan-out。

### D5: 一次性数据补全与日常 fan-out 分开

一次性补全负责修复当前线上脏数据：

- 从 raw fallback 补齐 APCB 的关键词血缘。
- 对 Kinwong 类记录补齐标准来源身份或保留 unresolved。
- 清理或隐藏旧 clean id 悬空 `tenant_companies`。
- 按新 lineage 重建 `tenant_companies`。

日常 fan-out 负责后续新数据：

- 按 wmt lineage 生成 tenant 可见关系。
- 遇到 unresolved lineage 只记录诊断，不写 tenant 可见关系。

### D6: 旧 fan_out.py 必须改造或停用

旧 `fan_out.py` 当前从 `clean_company_keywords` 读取旧 `clean_companies.id` 并写入 `tenant_companies.clean_company_id`。这会继续污染 0045 后的新语义。

本 change 必须使旧路径不再写旧 clean id。可选做法：

- 直接改造为 wmt lineage fan-out。
- 或将旧函数改为 no-op 并记录 warning，再由新服务接管。

优先推荐改造为 wmt lineage fan-out，减少重复入口。

### D7: 后续 WMT 重建由定时 repair 自愈

线上 `waimaotong_clean_companies` 可能由外部流程直接重建或批量更新，系统不能假设该表的 bigint `id` 长期稳定。接受短暂空窗：WMT 写入后最多几分钟内由后台 repair 修复。

后台 repair 每轮执行：

1. 规范化 `waimaotong_clean_companies.keyword_master_ids`：将 NULL 视为空数组，并补齐列默认值/NOT NULL 约束。
2. 按 D2/D3 回写当前 WMT 公司血缘。
3. 按 active `tenant_keyword` 写入当前 WMT id 到 `tenant_companies`。
4. 隐藏 stale visible 关系：`tenant_companies.clean_company_id` 已无法 JOIN 当前 `waimaotong_clean_companies.id` 的记录。
5. 输出本轮统计：血缘回写数、fan-out 新增/恢复数、stale 隐藏数、unresolved 数。

repair 必须幂等，可重复执行；多实例部署时使用 PostgreSQL advisory lock 避免并发重建互相踩踏。

### D8: 轻量稳定键防御

本 change 不大改 `tenant_companies` 主模型，不新增第二套关系表。防御重点放在：

- repair 用 `waimaotong_clean_companies.sys_company_id` 串回 WMT raw，再通过 `source_competitor` 找关键词血缘。
- 诊断 stale relation 时明确区分“当前 WMT id 不存在”与“有当前 WMT 但无关键词血缘”。
- 后续若要彻底消除 `id` 过期问题，再单独评估给 `tenant_companies` 增加稳定键字段（如 `wmt_sys_company_id`）。

## Risks / Trade-offs

- **Risk: source_competitor 名称不稳定** -> 使用精确规范化匹配，未命中进入 unresolved 清单，不自动模糊写入。
- **Risk: 一次性补数影响线上租户可见数据** -> 先 dry-run 输出每租户将新增/删除数量，经确认后再执行写入。
- **Risk: 旧 fan-out 仍被调用** -> 测试覆盖：调用 fan-out 后 `tenant_companies.clean_company_id` 必须能 JOIN wmt 表，不能 JOIN only old clean 表。
- **Risk: wmt raw 与 clean 可能一对多** -> 以 `sys_company_id` 为主连接键，写入 tenant_companies 使用 `(tenant_id, clean_company_id)` 幂等约束。
- **Risk: 生产脚本误删用户私有状态** -> 默认隐藏/修复悬空旧关系，不删除业务状态；如需删除必须单独确认。

## Migration Plan

1. 增加 wmt lineage repair worker：支持单轮执行和后台循环。
2. 增加 Alembic 修复：`keyword_master_ids` NULL → `{}`，并设为 `NOT NULL DEFAULT '{}'`。
3. 增加测试覆盖 clean 主路径、raw fallback、unresolved 诊断、旧/stale relation 隐藏、重复 repair 幂等。
4. 本地或线上快照验证：
   - repair 前 API 等价 JOIN 为 0。
   - repair 后 active 租户 JOIN 非 0，且只包含当前 active keyword 匹配的 WMT 公司。
5. 用户显式授权后，对生产库执行 dry-run。
6. 用户确认 dry-run 输出后，执行 write 模式或部署后台 repair。
7. 重启/部署后验证 tenant 列表：
   - `t-019dc236` 预计约 319 条。
   - `t-019dc238` 预计约 507 条。

Rollback:

- 修复脚本必须在执行前导出受影响的 `tenant_companies` 快照。
- 回滚时恢复快照，或将本次新增的 tenant relation 按批次标识隐藏。
- 生产执行前不自动触发镜像构建和 Sealos 更新。

## Open Questions

- `SHENZHEN KINWONG ELECTRONIC CO LTD` 应映射到哪一个 lixiaoyun clean/raw 标准实体？需要业务确认，不能靠模糊匹配自动决定。
- 是否需要把补齐后的 keyword lineage 回写到 `waimaotong_clean_companies.keyword_master_ids`，还是只通过查询视图/服务实时计算？建议回写，便于后续诊断和减少 JOIN 成本。
