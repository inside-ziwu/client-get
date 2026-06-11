## Context

公司列表查询（`tenant_query_service.py` 的 `companies_page()`）涉及 4 张表 JOIN：

```
waimaotong_clean_companies wc
  JOIN tenant_companies tc ON tc.clean_company_id = wc.id AND tc.tenant_id = :tenant_id
  LEFT JOIN waimaotong_raw_companies wr_raw ON wr_raw.sys_company_id = wc.sys_company_id
  LEFT JOIN lixiaoyun_api_clean_companies lxc ON lower(trim(lxc.entname_eng)) = lower(trim(wr_raw.source_competitor))
```

第 3 个 LEFT JOIN 的条件 `lower(trim(...))` 是函数表达式。迁移 `20260519_0047` 已创建 partial index `idx_lx_clean_entname_eng_lower`（带 `WHERE entname_eng IS NOT NULL AND entname_eng != ''`），但 **EXPLAIN ANALYZE 确认该 partial index 在 LEFT JOIN 场景下不被查询规划器使用**——PostgreSQL 无法从 JOIN ON 条件推断 partial predicate 被满足，导致全表扫描。

上次尝试（ccb5ecf）通过 LATERAL JOIN 重写 SQL 绕过全表扫描，但生产上线后公司列表返回 0 条数据。已回退。

`waimaotong_raw_companies.sys_company_id` 无索引（迁移文件在回退时被删，生产索引状态未知）。

## Goals / Non-Goals

**Goals:**
- 公司列表查询从 3.6s 降至亚秒级
- 不改变查询结果集（零行为变更）
- 安全部署，零停机窗口

**Non-Goals:**
- 不修改 SQL 查询语句
- 不引入新的查询模式（LATERAL JOIN、物化视图、缓存等）
- 不优化 COUNT 查询（COUNT 不涉及 lxc 表 JOIN）
- 不处理 raw/lxc JOIN 可能存在的一对多行放大问题（后续单独 change）

## Decisions

### D1: 替换 partial index 为完整函数索引

**选择**: DROP 现有 `idx_lx_clean_entname_eng_lower`（partial），重建为无 WHERE 条件的完整函数索引

**验证**: EXPLAIN ANALYZE 已确认 partial index 不被 LEFT JOIN 使用（Seq Scan on lixiaoyun_api_clean_companies）

**替代方案**:
- LATERAL JOIN 重写：已证明在生产环境数据分布下会导致 0 条结果
- 保持 partial index + 改 SQL 加 WHERE：违反 non-goal（不改 SQL）
- 新增冗余列（预计算 `entname_eng_normalized`）：需要回填 + 触发器维护，复杂度高

### D2: 先建新索引再删旧索引（零停机）

**选择**: 用新名字 `idx_lxc_entname_eng_lower_full` 先 CREATE INDEX CONCURRENTLY，验证 planner 使用后再 DROP 旧 partial index

**理由**: 如果先 DROP 再 CREATE，中间窗口期线上查询无任何索引可用，性能可能更差。先建后删是索引替换的标准最佳实践。

### D3: 补建 sys_company_id 索引

**选择**: 无论生产是否已有该索引，都补建 Alembic 迁移文件，使用 `IF NOT EXISTS` 避免冲突

**理由**: 这是第 2 个 LEFT JOIN 的连接列，缺少索引也会导致全表扫描。是必要项而非附带项。

### D4: 使用 CONCURRENTLY + autocommit 模式

**选择**: 所有 `CREATE INDEX` 使用 `CONCURRENTLY` 选项，Alembic 迁移使用 `autocommit` 模式

**理由**: CONCURRENTLY 避免锁表；autocommit 避免 Alembic 事务内 CONCURRENTLY 失败。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 完整函数索引未被查询规划器使用 | 部署前在开发库跑 `EXPLAIN ANALYZE` 验证 Index Scan |
| `CONCURRENTLY` 在 Alembic 事务内失败 | 迁移文件使用 `autocommit` 模式（`op.execute()` + `op.get_context().autocommit_block()`） |
| 生产已有 `sys_company_id` 索引导致迁移报错 | 使用 `IF NOT EXISTS` |
| `CONCURRENTLY` 失败留下 invalid index | 迁移前检查并清理 invalid index |
| raw/lxc JOIN 一对多导致行重复 | 本次不处理（非索引问题），记为后续 change |

## Migration Plan

1. 编写 Alembic 迁移文件（执行顺序见下）
2. 在开发库（Neon）执行迁移，验证索引创建成功
3. 在开发库跑 `EXPLAIN (ANALYZE, BUFFERS)` 确认新索引被使用
4. 部署后端镜像到生产（`alembic upgrade head` 自动执行）
5. 验证生产查询性能

**迁移执行顺序**:
```
Step 1: CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lxc_entname_eng_lower_full
        ON lixiaoyun_api_clean_companies (lower(trim(entname_eng)))
Step 2: CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wmt_raw_sys_company_id
        ON waimaotong_raw_companies (sys_company_id)
Step 3: DROP INDEX IF EXISTS idx_lx_clean_entname_eng_lower  (旧 partial index)
```

**回滚**: 删除新索引 + 重建旧 partial index 即可，不影响任何功能。
