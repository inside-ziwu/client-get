## Context

`waimaotong_raw_companies` 表当前 66 列，其中 13 列零引用；`waimaotong_raw_contacts` 表当前 29 列，其中 8 列零引用。这些后加新业务扩展列通过 `ALTER TABLE ADD COLUMN` 直接加到线上库，不在 Alembic 迁移历史中。本次通过一个 Alembic revision 物理删除共 21 列。

## Goals / Non-Goals

**Goals:**
- 物理删除两张表共 21 个未使用列，减少表宽度
- 通过 Alembic revision 管理此变更，使迁移历史可追溯
- downgrade 可回滚（加回列结构，数据不可恢复）

**Non-Goals:**
- 不处理其他表
- 不重构现有列命名或类型
- 不回填已丢失数据

## Decisions

### D1: 单个 Alembic revision 一次性删除全部 13 列

**选择**：一个 revision，21 条 `ALTER TABLE DROP COLUMN`（两张表合并处理）。

**替代方案**：按表分两个 revision。

**理由**：两张表的待删列性质相同（后加、零引用、预留未启用），统一处理减少迁移文件数量。

### D2: 执行前先查线上非空数据

**选择**：在 upgrade 函数中不做数据备份，但在实施前手动查询线上这 21 列是否有非空数据。

**理由**：如果列中有数据，删除即永久丢失。需要在执行迁移前确认数据状况，人工判断是否需要先导出。

### D3: downgrade 只恢复列结构

**选择**：downgrade 加回 21 列（含正确类型和默认值），但不恢复数据。

**理由**：`DROP COLUMN` 是不可逆的数据操作。downgrade 恢复结构即可满足回滚需求，数据恢复依赖数据库备份。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 线上列中存在非空数据被永久删除 | 实施前执行 SQL 查询确认 21 列的非空行数；如有数据，先导出再删 |
| 大表 DDL 锁表 | PostgreSQL `DROP COLUMN` 仅标记列为不可见，不重写表，几乎瞬时完成，无锁表风险 |
| 未来业务需要这些字段 | downgrade 可加回结构；字段定义已记录在 proposal.md 中，可随时重建 |
