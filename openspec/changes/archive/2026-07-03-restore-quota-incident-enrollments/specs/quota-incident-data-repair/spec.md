## ADDED Requirements

### Requirement: 修复集 MUST 以事故窗口 failed 邮件实时反查

修复脚本 MUST 以 `emails.created_at ∈ [2026-07-02 00:00Z, 2026-07-03 00:00Z)` 且 `emails.status='failed'` 反查关联的 `sequence_enrollments.status='failed'` 得到修复集，执行时实时计算（基线约 13,941 个 enrollment / 13,942 封邮件），MUST NOT 硬编码 id 清单；`bounced`/`active` 状态的 enrollment MUST NOT 进入修复集。

#### Scenario: 基线规模核对

- **GIVEN** 生产库处于事故后状态
- **WHEN** 以 dry-run 运行脚本
- **THEN** 输出修复集规模（enrollment 数、邮件数、按计划分布）且与基线量级一致，不做任何写操作

#### Scenario: 非修复对象排除

- **GIVEN** 事故窗口内存在 enrollment 状态为 `bounced` 或 `active` 的邮件记录
- **WHEN** 计算修复集
- **THEN** 这些 enrollment 不在修复集内

### Requirement: 恢复动作 MUST 原子完成备份、恢复与删除

执行模式下脚本 MUST 在单一事务内依次完成：(1) 修复集的 enrollment 与 failed 邮件全列快照到 `backup_quota_incident_{enrollments,emails}_<时间戳>` 备份表；(2) enrollment 恢复为 `status='active'`、`send_attempt_count=0`、`last_skip_reason=NULL`、`next_step_due_at=:resume_at`（默认执行时刻，全部恢复到最早可发）；(3) 删除修复集对应的 failed 邮件行。任一步失败 MUST 整体回滚。

#### Scenario: 正常执行

- **GIVEN** 修复集非空且前置确认通过
- **WHEN** 以 `--execute --confirm RESTORE-20260702` 运行
- **THEN** 备份表行数等于修复集规模；enrollment 全部变为 active、attempt=0、due=resume_at；failed 邮件行删除数等于备份数；输出各步行数

#### Scenario: 中途失败整体回滚

- **GIVEN** 事务中任一语句失败（如备份表名冲突）
- **WHEN** 执行修复
- **THEN** enrollment 与 emails 均保持执行前状态，无部分生效

### Requirement: 脚本 MUST 默认只读且执行需二重确认

不带参数运行 MUST 为 dry-run（零写操作）；执行 MUST 同时提供 `--execute` 与 `--confirm RESTORE-20260702`，且 `--env prod` 必须显式书写；执行前 MUST 打印前置自查（熔断已部署 A/B、余额已充值）并等待人工确认。

#### Scenario: 缺少确认词拒绝执行

- **GIVEN** 仅提供 `--execute` 而无 `--confirm`
- **WHEN** 运行脚本
- **THEN** 拒绝执行并提示确认词要求，零写操作

### Requirement: 修复 MUST 幂等

修复完成后再次运行，修复集 MUST 为空（enrollment 已 active、failed 行已删），脚本以 no-op 结束且不报错。

#### Scenario: 二次运行 no-op

- **GIVEN** 修复已成功执行一次
- **WHEN** 再次以相同参数运行（dry-run 或 execute）
- **THEN** 输出修复集为 0，不产生任何写操作
