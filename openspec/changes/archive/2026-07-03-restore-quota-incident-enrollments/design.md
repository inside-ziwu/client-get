# Design — restore-quota-incident-enrollments

## 背景与约束

- 修复对象基线（2026-07-03 生产实测）：事故窗口（`emails.created_at ∈ [2026-07-02 00:00Z, 2026-07-03 00:00Z)`）内 `status='failed'` 的邮件 13,942 封，关联 `status='failed'` 的 enrollment 13,941 个（attempt=0 的 13,912 + 被错误消耗过重试的 29），分布在 5 个 running 计划。1 个 bounced、8 个 active 的 enrollment 不在修复集内。
- 生产写操作，必须由用户显式触发；执行前置：`fix-quota-exhaustion-cascade` 已部署到 A/B 两实例（熔断保护就位）+ EngageLab 余额已充值确认。
- 熔断与本地日限额（9,000）已上线，恢复后即使额度不足也只会有界地推迟，不会重演级联。

## 关键决策

### D1. 修复集识别：以事故窗口 failed 邮件反查 enrollment，执行时实时计算

以 `emails`（窗口 + `status='failed'`）JOIN `sequence_enrollments`（`status='failed'`）得到修复集——不硬编码 id 清单，执行时实时查询（基线 13,941，允许小幅漂移）。`bounced`/`active` 状态的 enrollment 天然排除。

### D2. 恢复动作：active + 归零重试 + 全部恢复到最早可发（用户决策）

`status='active'`、`send_attempt_count=0`（29 个非零值系配额错误错误消耗，一并归零）、`last_skip_reason=NULL`、`next_step_due_at=:resume_at`（参数，默认执行时刻）。用户已决策**不分批摊开**：全部恢复到最早可发，由本地日限额 + 熔断自然节流。已知副作用：claim 按 `next_step_due_at ASC` 领取，积压会排在自然到期（含 07-06 波峰 2,857）之前消化，自然流量顺延数日。

### D3. failed 邮件行：备份后删除（用户决策）

先 `CREATE TABLE backup_quota_incident_{emails,enrollments}_<ts> AS SELECT ...` 全列快照（对齐仓库 `backup_wmt_identity_*` 命名惯例），再按窗口 + `status='failed'` + 修复集批量 DELETE（`emails` 无入向外键，已验证；`created_at` 窗口条件命中分区裁剪）。语义与新熔断机制「配额错误不留失败记录」一致，`targets` 不再对同一次发送双计。审计经备份表回溯。

### D4. 安全形态：默认 dry-run、显式二重确认、单事务、幂等

脚本 `backend/scripts/restore_quota_incident_enrollments.py`：
- 默认 **dry-run**（只读）：输出修复集规模、按计划分布、将删除的邮件数、resume_at 取值；
- `--execute` 需叠加 `--confirm RESTORE-20260702`（防误触），执行前打印前置自查清单（部署/余额）要求人工确认；
- 备份 + UPDATE + DELETE 在**单事务**内原子完成，任一步失败整体回滚；
- **幂等**：二次运行时修复集为空（enrollment 已 active、failed 行已删），自然 no-op；
- 连接串取 `CLIENTGET_PROD_DATABASE_URL` / `CLIENTGET_DEV_DATABASE_URL`（`--env prod|dev`），生产执行要求 `--env prod` 显式书写；
- 执行输出（含备份表名、各步行数）存档进本 change。

## 验证策略

- 开发库演练：在 Neon 伪造 3 个事故形态的 enrollment+failed 邮件，`--env dev --execute` 全流程断言（备份表建立、恢复字段、删除、幂等二跑 no-op）；
- 生产 dry-run（只读）核对修复集与基线一致；
- 生产执行后：恢复数与 dry-run 一致、备份表行数=删除数、仪表盘 07-02 targets 下降约 13,942、次日观察 worker 正常消化（`quota_circuit_*` 日志按预期节流）。
