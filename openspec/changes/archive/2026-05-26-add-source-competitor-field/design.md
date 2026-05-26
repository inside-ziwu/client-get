## Context

公司数据链路：`peer_companies`（同行公司）→ 外贸通反查买家 → `waimaotong_raw_companies`（含 `source_competitor`）→ 清洗 → `waimaotong_clean_companies`。

当前 tenant 端公司列表和详情查询只访问 `waimaotong_clean_companies`（通过 `tenant_companies` 关联），未 JOIN `waimaotong_raw_companies`，因此无法获取来源同行信息。

数据现状：
- `waimaotong_raw_companies`：3194 条，100% 有 `source_competitor`
- `waimaotong_clean_companies`：2372 条
- 通过 `sys_company_id` 关联，覆盖率 99.96%
- 每个 clean 公司目前对应 1 个来源同行

## Goals / Non-Goals

**Goals:**
- 在现有列表和详情查询中透传 `source_competitor` 字段到前端

**Non-Goals:**
- 不新增数据库迁移
- 不做数据冗余
- 不支持按来源同行筛选

## Decisions

### D1: JOIN 取值 vs 冗余字段

选择 LEFT JOIN `waimaotong_raw_companies` 取 `source_competitor`。

理由：两表数据量极小（3k / 2k），JOIN 性能影响可忽略。冗余方案需要新增迁移、回填脚本和同步逻辑，复杂度不值得。

### D2: LEFT JOIN vs INNER JOIN

选择 LEFT JOIN。极少数 clean 公司可能无法匹配到 raw 记录（0.04%），此时 `source_competitor` 返回 null，不影响其他字段展示。

### D3: JOIN 条件

使用 `waimaotong_raw_companies.sys_company_id = waimaotong_clean_companies.sys_company_id`。经验证这是唯一有效的关联字段（real_id 和 company_id 匹配数为 0）。

## Risks / Trade-offs

- [一个 clean 对应多条 raw] → 若未来同一 `sys_company_id` 在 raw 表有多条记录，JOIN 会产生重复行。当前数据为一对一，暂不处理；若出现需加 DISTINCT ON 或子查询取最新。
- [raw 表无索引] → `waimaotong_raw_companies.sys_company_id` 无索引，但 3k 行全表扫描耗时微秒级，不需要专门加索引。
