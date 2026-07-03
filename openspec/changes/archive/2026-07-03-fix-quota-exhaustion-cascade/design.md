# Design — fix-quota-exhaustion-cascade

## 背景与约束

- 发送 worker（[backend/app/workers/sending.py](../../backend/app/workers/sending.py)）是单进程循环：`run_once` 每轮选一个到期域名、领取一封邮件、调用 EngageLab 发送。域名节流状态 `domain_clocks` 已是内存态。
- 取件机制（`claim_due_emails`，[backend/app/services/tenant_messaging_service.py](../../backend/app/services/tenant_messaging_service.py)）按 `sequence_enrollments.next_step_due_at` 选人，每次领取**新建**一行 `queued` 邮件并发送；全库没有任何代码消费 `emails.scheduled_at`（该列读写均属 `sending_plans`）。任何「重发既有邮件行」的设计都与取件模型不兼容。
- `mark_email_failed` 当前对任何失败都：邮件置 `failed` → 释放 `domain_daily_usage.reserved_count` → 按 `is_permanent` 终止 enrollment 或安排重试。「失败释放配额」正是空转循环的成因。
- 事故错误签名已用 2026-07-02 生产日志校准（tasks 1.1 完成）：HTTP 400，响应体 `{"code": 30877, "message": "mail failed to send. 552 {'code':-7,'message':'your account balance is not enough,please recharge soon',...}"}`。注意文案是「账户余额不足、请充值」而非「日配额耗尽」——档位额度可能为预付费余额型，未证实次日自动重置（见 D2 与 Open Questions）。
- 生产 Postgres 会话时区已实测为 **UTC**：`domain_daily_usage.usage_date = CURRENT_DATE` 的现状窗口是 UTC 日（北京时间 08:00 翻转），与「北京自然日」的业务语义错位 8 小时。
- 项目约定 KISS：不引入新表、不引入分布式协调。

## 关键决策

### D1. 配额类错误识别：区分「日配额耗尽」与「瞬时限流」，代码内常量配置

`_classify_provider_error` 签名扩展为接收 `status_code` 与 `error_message`。判定顺序：

1. `error_message` 不区分大小写命中 `QUOTA_KEYWORDS`（额度耗尽语义，**已用 2026-07-02 生产日志校准**：`balance is not enough`、`recharge soon`、`"code": 30877`（EngageLab 额度不足错误码），另保留 `daily quota`、`quota exceeded`、`配额`、`余额不足`、`已达上限` 兜底）→ **配额类**（`error_type='quota'`、`error_category='quota'`、`is_permanent=False`），触发当天熔断；
2. `status_code` 命中 `QUOTA_STATUS_CODES`（常量，保持为空——实测额度耗尽走 HTTP 400，太泛不可作码级白名单，识别依赖上面的文本特征）→ 配额类，同上；
3. `status_code == 429` 或 `error_message` 命中 `RATE_LIMIT_SIGNALS`（`rate limit`、`too many requests`）→ **瞬时限流**：维持临时错误、走既有重试链（15m/1h/4h），**不直接熔断**——429 通常是秒/分钟级限流，现行代码即按临时处理，可优雅吸收突发；一次 429 就停发整天是行为回退；
4. **升级规则**：同一域名 10 分钟窗口内「瞬时限流 + 配额类」判定累计 ≥3 次 → 视为配额耗尽，升级为当天熔断（计数为 worker 内存态）；
5. 其余维持现有显式分类（401/403/5xx 临时、422 永久 invalid）；
6. **未知 4xx 默认从永久失败改为临时失败**（`is_permanent=False`）。

不做成环境变量/数据库配置：常量随代码走，改规则走正常发版，符合 KISS；日志校准发生在实施期（tasks 1.x）。

### D2. 熔断状态：worker 内存态，按域名记录暂停至次日北京时间零点

`SendingWorker` 新增 `self.domain_quota_paused: dict[str, datetime]`（domain_id → 恢复时间）与限流升级计数器（domain_id → 最近 10 分钟命中时间列表），均为内存态。

- 触发：命中 D1 配额类或升级规则时，`paused_until = 次日北京时间 00:00`（换算为 UTC 存储）。
- **额度恢复模型的不确定性**：实测错误文案为「余额不足、请充值」，档位额度可能是预付费余额型而非每日自动重置。若次日额度未恢复，worker 恢复后首封邮件即再次被拒并重新熔断——每域名每天一次探测调用，代价有界；真正恢复依赖充值/提档（见 Open Questions）。注意与 D3 连续 defer 上限的交互：额度持续未恢复约 3 天后，积压邮件将逐步降级到重试链并最终终止 enrollment——这是毒药防护的代价，额度型停摆需在 3 天内人工介入。
- 生效：`run_once` 在构建候选域名列表后、`_select_due_domain` 之前过滤掉 `now < paused_until` 的域名；全部被熔断时按 idle 逻辑休眠。过期条目顺手清理。
- **恢复是被动的**：过零点后由下一轮领取循环自然拾起；idle 轮询间隔为秒级（`idle_poll_seconds=5`），实际恢复延迟仅数秒，无需主动定时器。
- 日志：触发时记 `quota_circuit_open`（domain_id、paused_until、触发错误摘要）；恢复后首轮记 `quota_circuit_closed`。
- **worker 重启丢失熔断状态是可接受的**：重启后最多多试一封，配额错误会立刻重新触发熔断。用一次多余的 API 调用换掉持久化状态的复杂度。限流升级计数与 defer 连续计数（见 D3）同此权衡。

### D3. 配额类错误的邮件处理：删除未发出的邮件行，恢复由 enrollment 推迟驱动

新增 service 方法 `defer_email_for_quota(conn, email_id, resume_at)`，配额类错误时替代 `mark_email_failed`：

- `emails`：**删除**该未发出的邮件行（`sent_at`/`engagelab_message_id` 均为 NULL，无任何回执；保留只会产生永久滞留的 queued 孤儿行，且使 `targets = COUNT(*)` 对同一次逻辑发送计 2 次，恰与本 change 的统计修正目标冲突）；
- `email_send_locks`：置 `released`（不是 `failed`），`email_id` 置 NULL 与现有 claim 复用逻辑一致；
- `domain_daily_usage`：照常释放 `reserved_count`（域名已熔断，释放不会引发新领取）；
- `sequence_enrollments`：`next_step_due_at = resume_at`（次日北京零点），**不增加** `send_attempt_count`，状态保持 `active`。

次日恢复后由 `claim_due_emails` 按原步骤**重新生成**邮件行并发送——与取件机制「每次领取新建行」的既有模型同载体，不引入第二条重发路径。

**连续 defer 上限（防毒药邮件死循环）**：若某封邮件的永久性错误恰好含泛化配额关键词（如 "recipient limit exceeded"），无上限的 defer 会让它每天霸占队首、每天熔断整个域名。同一 enrollment 连续配额 defer 达 **3 次**后，后续配额类错误降级为临时失败处理（消耗 `send_attempt_count`、走重试链，耗尽后按既有逻辑终止）。计数为 worker 内存态（重启重置，权衡同 D2——重启后毒药邮件最多再获得一轮 defer，循环仍会在 3 天内被打破）。

### D4. 仪表盘口径：全部三处「已发送」统一剔除 failed

仪表盘同页共有三处「已发送」语义的统计，全部沿用 `status NOT IN ('draft','pending','queued')` 旧口径，必须一起修，否则同屏数字互相矛盾：

1. `email_stats_by_date_range`（summary 与 daily 两处 SQL）——发送统计卡；
2. `plan_overview` 的 `emails_sent`（两处 SQL：按计划/租户级）——计划概览卡；
3. `daily_quota` 的今日已发送——每日配额卡。

过滤条件统一改为：

```sql
COUNT(*) FILTER (WHERE status NOT IN ('draft','pending','queued','failed')) AS sent
```

`billing = sent` 与各百分比公式不动，分母自动联动。`targets` 维持 `COUNT(*)`。前端零改动。口径为查询时过滤，历史区间自动按新口径展示，无需数据回溯。

同步更新既有测试 [backend/tests/test_dashboard_email_stats.py](../../backend/tests/test_dashboard_email_stats.py) 与主 spec `openspec/specs/dashboard-email-stats/spec.md`（归档时由 delta 合入）。

### D5. 本地配额窗口对齐北京自然日

`domain_daily_usage` 的读写全部使用 `usage_date = CURRENT_DATE`（会话时区 UTC → 北京 08:00 翻转），与熔断「次日北京零点恢复」错位 8 小时：恢复时本地余量可能立刻顶住（恢复实际推迟到 08:00），或一个北京日内跨两个 UTC 窗口放行近 2 倍 `daily_limit`，导致熔断周期性复发。

统一将 `domain_daily_usage` 相关的日期改为北京自然日，**日期在 Python 侧计算后作为参数传入**（模块级 helper 按 `ZoneInfo("Asia/Shanghai")` 从注入的 `now_utc` 求当日日期，参照 `admin_collection_service._BEIJING_TZ` 先例），不在 SQL 端做时区表达式——原因：仓库测试体系为纯 mock（SQL 端表达式不可测，Python 参数可直接断言），且 asyncpg 对 `:param::type` 转换有已知陷阱（docs/solutions/runtime-errors/asyncpg-named-param-cast-syntax-error-20260507.md）。

涉及：claim 的配额门、预留、释放（`_release_reserved_quota`）、以及 daily_quota 卡片的今日统计（含 `tenant_query_service.py` 的 `date.today()`）。`daily_limit` 取值与预热策略不变（仍在 Non-Goals），只对齐窗口时区，使本地配额、熔断周期、EngageLab 档位周期三者同频。

## 备选方案与取舍

| 备选 | 未采纳原因 |
|------|-----------|
| 熔断状态持久化到数据库（如 domain_daily_usage 加列） | 需要 schema 变更与迁移；重启丢状态的代价仅为一次多余 API 调用，不值得 |
| 指数退避探测恢复 | 用户已选「暂停到次日」；EngageLab 配额按天重置，探测无收益且持续制造失败 |
| 配额错误沿用 mark_email_failed + 重试链 | 重试链上限 3 次（15m/1h/4h），撑不到次日配额重置，仍会终止 enrollment |
| 配额 defer 保留邮件行回 queued 等待重发 | 取件机制不消费 emails.scheduled_at 且每次领取新建行——旧行会成为孤儿、次日重复建行、targets 翻倍计数 |
| 识别规则做成环境变量 | 规则变更频率极低，常量+发版足够，避免配置漂移 |

## 风险与缓解

- **误判风险**：关键词过宽把普通业务错误当配额类。缓解分三层：日配额关键词保守、瞬时限流（429/rate limit）默认走重试链不熔断、同一 enrollment 连续 defer 3 次后降级为临时失败——单封误判邮件最多让域名多停 3 天，不会形成无限逐日封锁。
- **漏判风险**：EngageLab 配额错误不含已知关键词 → 行为退化为「临时失败 + 重试链」，比现状（永久终止）仍好得多；重试耗尽才终止。上线前用当晚 Sealos 日志校准（tasks 1.x），上线后按 tasks 7.2 的反向信号核对补漏。
- **多域名共享档位**：档位配额是账户级，域名 A 触发熔断时域名 B 也必然撞限。按 spec 熔断只影响触发域名，B 会在自己第一封被拒后立刻熔断，最多多付出域名数 - 1 次 API 调用，可接受。
- **结构性超量**：事故数字显示日目标（22,679）约为档位配额（≈8,700）的 2.6 倍。熔断只防级联失败，不解决缺口——被推迟的积压会逐日增长。该问题超出本 change 范围，见文末 Open Questions。

## 测试策略

- 分类单测：日配额关键词（含中文、大小写）、429/rate limit 走重试链不熔断、10 分钟 ≥3 次升级熔断、未知 4xx 临时、422 永久，五类判定；
- worker 单测（现有 `SendingWorker` 已注入 clock/sleep/provider，可直接模拟）：配额错误触发熔断并 defer、熔断期跳过该域名但不影响其他域名、跨天后自动恢复、**重启后熔断态丢失但首封错误即重新熔断**、连续 defer 3 次后降级临时失败；
- service 单测：`defer_email_for_quota` 的行删除 + 锁释放 + 配额回退 + enrollment 推迟且 attempt 不变；
- 配额窗口单测：`usage_date` 按北京日读写（UTC 会话下跨 16:00Z 边界的行为）；
- dashboard 统计测试：三处「已发送」剔除 failed 后 targets/sent/billing/百分比断言（对齐 [backend/tests/test_dashboard_email_stats.py](../../backend/tests/test_dashboard_email_stats.py)）。

## Open Questions（评审遗留，2026-07-03 已收敛）

- **熔断的运营可见性**——**已决策：暂不立项**。保留在此作为已知盲区：唯一外露信号是 `quota_circuit_open/closed` 结构化日志，靠日志 + 人工巡检；若再次发生额度停摆事故，重新评估。（adversarial 评审 → 用户决策，2026-07-03）
- **额度缺口**——**已决策：用户充值恢复额度**（实测错误为「账户余额不足、请尽快充值」，EngageLab code 30877，预付费余额型）。遗留观察项：日发送目标（事故日 22,679）与档位额度的长期匹配，若充值后仍频繁触发熔断，说明缺口结构性存在，需提档或压量。（adversarial 评审 + tasks 1.1 日志实证 → 用户决策，2026-07-03）
- **事故数据修复**——**已决策：立项后置**，见 change `restore-quota-incident-enrollments`（依赖本 change 上线 + 余额充值到位后由用户触发）。
