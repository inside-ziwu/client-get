## 1. 修复脚本

- [x] 1.1 实现 `backend/scripts/restore_quota_incident_enrollments.py`：dry-run 默认（修复集规模/按计划分布/待删邮件数/resume_at 预览）、`--execute` + `--confirm RESTORE-20260702` 二重确认、`--env prod|dev` 显式选库、单事务（备份两表 → enrollment 恢复 → failed 行删除）、幂等（修复集为空即 no-op）；ruff 全绿

## 2. 开发库演练

- [x] 2.1 已于 2026-07-03 完成：伪造 3 样本 → dry-run 识别 3/3 → execute 备份 3+3/恢复 3/删除 3/剩余 0 → 字段断言 PASS（active/attempt=0/due 已设/skip_reason 清空）→ 二跑 no-op → 演练数据与备份表清理零残留

## 3. 生产 dry-run（只读，可先行）

- [x] 3.1 已于 2026-07-03 完成：修复集 enrollment=13,941 / 邮件=13,942，与基线一致；按计划分布：美国客户C轮开发信 9,974、美国客户开发信 3,803、美国关键词客户A轮 126、美国客户B轮 37、英国客户AB级首封 1（全部 running）

## 4. 生产执行（用户显式触发）

- [x] 4.1 前置确认(2026-07-03 用户确认:双实例已部署+充值到账)：fix-quota-exhaustion-cascade 已部署 A/B 两实例 + EngageLab 余额充值到账（外部操作，由用户确认）
- [x] 4.2 `--env prod --execute --confirm RESTORE-20260702` 执行，输出（备份表名、各步行数）存档进本 change

## 5. 执行后验证与归档

- [x] 5.1 验证(见下方执行记录)：恢复数=dry-run 预告数、备份表行数=删除数、仪表盘 2026-07-02 targets 回落约 13,942、次日观察 worker 消化节奏与 `quota_circuit_*` 日志
- [ ] 5.2 openspec verify → 归档本 change

## 执行记录（2026-07-03 08:44 UTC）

- 备份表：`backup_quota_incident_enrollments_20260703_084452`（13,941 行）、`backup_quota_incident_emails_20260703_084452`（13,942 行）
- 恢复 enrollment 13,941 / 删除 failed 邮件行 13,942，单事务提交，剩余修复集 0
- 执行后验证：13,941 全部 active；仪表盘 2026-07-02 targets 22,679 → 8,737（sent=8,729，口径回真）
- worker（新镜像）即时接管：以「当地非工作时间」批量改期——2026-07-03 为美国独立日观察假日（7/4 落周六），叠加周末，全部积压排到 **2026-07-06 13:00Z（美国周一上午 9 点）**与自然波峰同日；届时由本地日限额（9,000/日）+ 熔断自然节流，预计 2-3 天消化完毕
