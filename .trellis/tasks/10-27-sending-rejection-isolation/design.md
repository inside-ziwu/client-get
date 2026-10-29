# 技术设计：先修接单回写，再完善拒发分类

## 决策与优先级
本次实际事故不是三个坏收件人拖住队列。P0 修复 message id 长度和“已接单误重试”；P1 结构化错误证据和分类。第四封为什么被归类为 quota 缺上游原文，必须明确保留未知，不以取消熔断代替调查。下面的契约已在本 worktree 落地为迁移、服务、worker、测试和 dry-run 工具。生产迁移、修数、真实发信和部署仍未执行。

## P0-A：兼容性数据库修复
在当前 Alembic head 后新增一个 revision，将分区父表 emails.engagelab_message_id 改为 TEXT，确认所有现有分区与未来分区继承；保留现有索引及等值匹配。不要截断为 100/255，截断会破坏 webhook 和对账关联。

```sql
ALTER TABLE emails ALTER COLUMN engagelab_message_id TYPE text;
```

同一 revision 可包含后述锁字段/约束变更；实施时先摸清真实约束，禁止猜约束名。downgrade 必须先判断 length>100，存在时拒绝；不能截断回滚。分区 DDL 会持锁，开发库预演锁和索引行为，生产另行展示 SQL、影响分区和锁范围取得本次确认。A、B 共库，迁移不能只按 B 的负载评估。

## P0-B：把外部接单与本地回写分成两个阶段
边界原则：只有“明确没有被服务商接受”的错误可以进入发送重试。拿到 provider id 后任何 DB/计数/序列异常都只重试本地回写，不再次调用 send_email，不释放成功发送占用的额度、不增加 send_attempt_count、不计入限流。

建议复用 email_send_locks 持久化阶段（不改 emails 对外状态枚举）：
- 新增 dispatching、accepted_pending、uncertain 锁状态，均禁止 ON CONFLICT 重抢；原 locked/sent/failed/released 保留。
- 新增 provider_message_id TEXT、provider_accepted_at TIMESTAMPTZ、dispatch_started_at TIMESTAMPTZ、quota_usage_date DATE。若有 CHECK 约束，升级其允许集。字段按发送尝试清空，禁止复用旧回执。
- claim_due_emails 继续按租户/实例、工作窗口、额度和现有锁领取；记录本次 quota_usage_date，避免跨北京零点释放错日账本。
- 在外部 POST 前独立提交 locked→dispatching。提交失败则不调用服务商。
- provider 成功：独立短事务 CAS dispatching→accepted_pending，同时存完整 id 与接单时间。之后 mark_email_sent 在同一事务完成现有所有状态推进，锁 accepted_pending→sent。只成功一次，重复回写返回 duplicate。
- 回执写入失败：进程内对同一回执做有限重试（建议 1、5、30 秒）；之后阻止该发送尝试重发并发出高优先级安全事件。数据库不可用期间不能声称已持久化回执；已提交的 dispatching 状态用于重启后保守隔离。
- mark_email_sent 失败：保留 accepted_pending 和回执；后续独立恢复循环只调用本地 finalize，不调用外部 send。其他可用收件人可继续。
- 明确 provider 拒绝：按分类走原失败/配额路径，支持从 dispatching CAS；永久收件人错误终止 enrollment，临时错误有限延迟，明确 quota 延期并熔断。
- 超时、断连、2xx 无 id 等结果不确定：dispatching→uncertain，禁止自动外发重试；只有服务商只读查询确认未接单后，才可按正常窗口恢复。未知请求不能被当成“明确拒绝”。
- recover_stale_locks 仅回收未外发的 locked。超时 dispatching 改为 uncertain；accepted_pending 只做本地恢复；不能 30 分钟后释放并重发。已有部署遗留 locked 需按上线时间分界保守核对。

恢复查询和所有新/改 SQL 必须显式 tenant_id、instance_id（通过 tenants join），CAS 同时核对 email_id、enrollment_id、step_id；不顺带全仓重构。contact 状态不能因本地写库错误改 invalid。

## P1：准确区分错误并留下可用证据
EngageLabSendError 增加 provider_code、http_status（可保留 status_code 兼容）、安全的 message 分类摘要、retry_after。解析 JSON code/message；不要依赖 SQL 异常字符串或任意出现“配额/已达上限”的文本来定性。

| 类型 | 行为 | 联系人状态 | 域名熔断 |
|---|---|---|---|
| 接单后写库失败 | 回执持久化、本地恢复 | 不改无效 | 不计限流 |
| 确认收件人永久无效 | 当前 enrollment 终止；对应租户联系人 invalid/bounced | 依明确语义 | 否 |
| 收件人级策略拒绝 | 停该 enrollment；不得泛化为地址不存在 | 没有明确无效证据则不改 | 否 |
| 收件人临时错误 | 现有 15 分钟/1 小时/4 小时有限重试，继续其他人 | 不改 | 否 |
| 明确账号/域名额度不足 | 保留暂停、配额延期 | 不改 | 是，沿用当前策略 |
| 429 / 明确频控 | 保留限流保护，本次不擅改恢复周期 | 不改 | 现有十分钟三次规则 |
| 401/403 或未知业务码 | 不自动判坏地址；安全摘要告警，依已核实契约处理 | 不改 | 不能靠换收件人绕过账号错误 |
| 外发结果不确定 | uncertain，查询核实，不自动重发 | 不改 | 不计三次限流 |

错误码映射必须带官方来源或经过核实的真实响应结构；不要猜 308xx 含义，不把所有 400/422 都当作无效收件人。现有“422 一律 invalid”改为依据明确收件人语义，否则按未知处理。缺少映射时先补证据再扩大永久拒绝规则。

日志：run_sending_worker.py 初始化 configure_logging；新增 send_accepted、send_finalize_failed、send_outcome_uncertain、send_rejected、quota_circuit_open 事件。字段白名单为 instance_id/tenant_id/domain_id/email_id、phase、http_status、provider_code、error_class、decision、resume_at、message_id_length。禁止原始 message id（可能嵌邮箱）、SQL 参数、凭证、原始异常 str。轮次 print 的 reason 同样使用安全码，不能只修 logger 而继续泄露参数。

## 历史修复与运维
扩列不能自动修好历史失败。针对 10-23 至事故期间同类错误，先从受控日志/服务商只读查询核对接单时间、原始 ID 和结果；在进程内关联，不把客户数据写入仓库。恢复前按租户、enrollment、step 汇总，区分同一步多次已经接单与单次接单。默认禁止批量重新发送这些 failed。

修复脚本默认 dry-run，仅输出数量及内部标识；生产应用须单次 SQL 和预告数量经确认。不能直接调用普通 mark_email_sent：旧锁已 failed/复用，该方法会幂等跳过。需专门修复事务锁住目标 enrollment/步骤，保留每次尝试审计，将已确认接单记录补齐、按实际结果更新状态；序列只推进一次，计划计数按既有“邮件数”口径重算，额度按真实接单日对账；多次已接单不抹去。无充分对应关系的条目保留隔离待核实，不能猜测补 sent。

真正额度错误的后续动作由日志码决定：余额不足需处理服务商账户余额，日额度需调整服务商额度或等重置，误分类才改映射。改收件人跳过逻辑不能代替这些操作。

## 兼容与回滚
Schema 扩容向后兼容；新增锁阶段不与旧 worker 混跑。发布前停止旧领取并核对在途，按批准流程先迁移再更新所有受影响 worker。回滚代码前处理 accepted_pending/dispatching/uncertain，保留扩容和新字段，禁止直接降回 varchar(100)。这些生产动作仍未执行。

## 落地时补上的技术决定

- CHECK 名使用快照里的 `email_send_locks_status_check`。`status` 保持 `varchar(20)`，`accepted_pending` 16 字符，不扩列宽。
- 新领取始终写入 `quota_usage_date`（领取时刻的北京日期）。该列为空表示迁移前遗留锁：超时后改为 `uncertain`，不释放额度、不重发。新 `locked` 且 `dispatch_started_at` 为空，才是崩溃在 POST 之前，超时后释放并退回 `quota_usage_date` 当天的额度。
- `recover_stale_locks` 仍是每个进程一次。每一轮另有 `isolate_timed_out_dispatches` 把超时 `dispatching` 转为 `uncertain`。`accepted_pending` 不在这两条回收里释放。
- 领取候选的 `NOT EXISTS` 排除 `locked` / `sent` / `dispatching` / `accepted_pending` / `uncertain`，避免被占住的报名占满 `candidate_limit`。
- 本地 `idempotency_key` 映射为官方 `request_id`。超过 128 字符就省略，不截断。官方去重约 1 小时；跨日防重只靠锁。
- `RECIPIENT_PERMANENT_CODES` 与 `RECIPIENT_POLICY_CODES` 保持为空。已删除「配额 / 已达上限 / daily quota / quota exceeded」这类宽泛关键词。裸 422 不标 invalid。
- 回执持久化失败按 1、5、30 秒重试；仍失败则留在 `dispatching`。部分索引：`idx_email_send_locks_accepted_pending`、`idx_email_send_locks_dispatching`。
- 第四封的上游业务码仍然未知。TEXT 扩容不消除配额熔断。历史工具默认 dry-run，`--apply` 直接拒绝；不能把本地 failed 次数当成服务商接单次数。
- 未外发的新 `locked` 不能只等进程重启。`release_unsent_locks` 按 worker 时钟节流（60 秒）回收超过 30 分钟、有 `quota_usage_date`、`dispatch_started_at` 和回执都为空的锁，并退回原占用日。旧锁和已进入 `dispatching` / `uncertain` / `accepted_pending` 的行不在这里释放。
- `accepted_pending` 增加 `finalize_not_before`。每轮最多租约 20 条；本地回写失败把该条推迟 60 秒，下一轮才能处理更后面的已接单记录。成功推进仍只发生一次，恢复不调用 `send_email`。
- `sent_at`、`last_step_sent_at`、`next_step_due_at`、`completed_at` 使用 `provider_accepted_at`。回执重试不改写这个时间。`updated_at` 用恢复当时。下一步若已早于现在，领取时仍受当前工作窗口约束。
