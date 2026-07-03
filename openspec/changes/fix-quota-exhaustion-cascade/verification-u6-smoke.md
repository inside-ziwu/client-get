# U6 Neon 开发库冒烟记录（2026-07-03）

按计划 U6 的三组断言在 Neon 开发库（`CLIENTGET_DEV_DATABASE_URL`，owner 角色）执行，**20/20 通过**；全部合成数据已清理、翻转的 enrollment 已还原（终态核对：残留 smoke 邮件 0、enrollment 恢复 completed、合成日期行 0、claim 生成邮件 0）。不触发任何真实发送。

## (a) 口径组 — 6/6

- email_stats：9 封样本（2 delivered + 1 opened + 1 bounced + 2 failed + 1 queued + 边界样本）→ targets=6、sent=4、billing=4、delivered_percent=75.0（窗口内 6 封口径）
- plan_overview（计划级）emails_sent Δ=+6（9 封中剔除 2 failed + 1 queued）
- daily_quota used Δ=+1：北京今日窗口内 delivered 计入；failed 不计；北京昨日 23:30（today_start−30min）的 delivered 不计——**16:00Z aware-datetime 边界验证通过**

## (b) 窗口组 — 5/5

- 首次预留经 INSERT 回退分支放行；预留/释放均落在指定北京日行
- `now_utc=15:59Z` 与 `16:01Z` 的预留分别归属 2027-02-11 / 2027-02-12 两个北京日行
- AE9 强覆盖：前一北京日行 reserved=daily_limit（满额）时，新日首次预留正常放行（恢复不被前一日余量阻塞）

## (c) defer 回路组 — 9/9（全 change 唯一全新 SQL 写路径的真实语义验证）

- claim（真实八表 join 链）领取成功 → `defer_email_for_quota`：邮件行删除（分区表双条件）、锁 released 且 email_id 置 NULL、预留配额回退到领取前、enrollment 保持 active / next_step_due_at=次日北京零点 / attempt 不变
- defer 返回的 resume_at 为 ISO 字符串（JSON 安全，P0-1 回归点）
- 次日回路闭环：推迟到期后重新 claim → 锁经 ON CONFLICT 复用重新 locked、生成全新 id 的邮件行

执行脚本与完整输出：会话 scratchpad `u6_smoke.py` / `u6-smoke-output.txt`（关键结论已如上沉淀；脚本为一次性验证工具，不入库）。
