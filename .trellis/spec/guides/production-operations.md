# 生产运维约定

> 红线（生产默认只读、外部副作用由用户触发、`.env` 手动维护）见 [AGENTS.md](../../../AGENTS.md) §1，本文是执行细则。技能入口：`/db-verify`（真库验证 / 只读体检）、`/release`（发布构建）。

## 连接纪律

- 两条连接串在 `backend/.env.local`：`CLIENTGET_DEV_DATABASE_URL`（Neon，可写可断言）与 `CLIENTGET_PROD_DATABASE_URL`（Sealos，只读）。脚本内读取，**不得打印**（展示打码 `:****@`）。
- 生产连接建立后立即 `conn.read_only = True` 并 `SHOW transaction_read_only` 复核；不要用 startup `options`（Neon pooler 会拒绝）。
- 只读体检：聚合 + 时间窗过滤（分区裁剪），禁止无窗口 `LIKE` 拖全表；样本截断，不含客户数据；断言"某模式归零"时必须带对照组证明正常模式仍在。

## 生产写操作三段式（逐次授权）

1. **只读摸图**：自省列名（`information_schema.columns`）、查 FK 图（`pg_constraint WHERE confrelid='<表>'::regclass AND contype='f'`）、查引用计数，不凭想当然。
2. **展示并等确认**：完整 SQL + 预告影响行数，取得用户针对该次操作的明确确认。
3. **单事务执行 + 回读对账**：`rowcount ≠ 预告值即回滚`；被引用的行停用而不删除；大批量分批 + 幂等；提交后重新 SELECT 验证终态、做分布对账、抽查单条真实记录。

先例：2026-07-23 模板 `&amp;` 清洗（7 行 replace）；2026-07-03 评分重算 34,473 行（dry-run 矩阵 → 执行 → GROUP BY 对账）。

## 高危开关与禁令

- `WMT_LINEAGE_REPAIR_ENABLED`（客户池修复）是高危批量写路径：激活或参数变更按上面三段式逐项审批。
- 禁止对生产迁移重复手工 DROP 或 downgrade（#75）。
- A、B 两实例共用同一物理数据库：只操作 B 也要审计 A 的在途发送负载。

## 备份与恢复

- 备份 / 恢复工具与生产同 PostgreSQL 主版本（`postgres:16` 容器内的 `pg_dump` / `pg_restore`）；归档经 stdout 流式加密落盘，不留明文。
- 恢复前安装目标表用到的扩展（如 `citext`），分 pre-data → data → post-data 三段，补父表桩与触发器函数；脚本 `set -euo pipefail` 并处理 SIGPIPE。
- 删生产表前把加密归档、校验值、恢复对账和销毁日期作为审批门禁。

## 发布

- 流程：push GitHub → Actions `workflow_dispatch` 构建 → 阿里云 ACR → Sealos 手动更新镜像 tag；全量发布 = 5 个构建（backend 共用 + 两实例各一套 admin / tenant），细节见 README §7。
- Actions 的 `date -u` 是 UTC：北京时间凌晨触发会生成前一天的 tag，撞同名 tag 时 Sealos 可能沿用缓存镜像——核对 tag 再更新。
- 发布后用 openapi 指纹确认容器已更新，再做行为验证。

## 日志取证

见 [../backend/logging-guidelines.md](../backend/logging-guidelines.md)「线上取证」：按字段过滤、起点精确、面板 UTC。
