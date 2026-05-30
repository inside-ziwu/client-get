---
date: 2026-05-30
topic: sending-throttle-reliability
---

# 逐封节流与发送可靠性

## Summary

在现有 SendingWorker 基础上补齐三项能力：逐封节流（消费已有的 `send_strategy.interval_seconds` 配置，每封邮件间随机延迟 30-120 秒）、有限重试（区分临时/永久错误，防止无限循环）、崩溃恢复（释放死锁的 `email_send_locks`）。单 worker 进程内按域名独立节流，无需为每个域名单独部署容器。

---

## Problem Frame

当前 SendingWorker 已经实现了逐封发送（单收件人 API 调用）、并发防护（`FOR UPDATE SKIP LOCKED` + `email_send_locks`）、时区感知发送、域名每日配额限制。但实际发送时，一次 claim 最多 20 封并以最快速度连发，缺少逐封间隔延迟。对外发邮件场景，这种行为容易被邮箱服务商识别为批量营销，导致域名信誉受损。

同时存在三个生产可靠性缺口：发送失败后无限重试（没有 `attempt_count` 和上限）、worker 崩溃导致 `email_send_locks` 永久死锁（ON CONFLICT 条件不接受 `locked` 状态）、发送失败后域名每日配额不回收。

---

## Key Decisions

**Claim-one-send-one 模型。** 每次 `run_once` 只 claim 1 封邮件，发完后根据该 plan 的 `send_strategy.interval_seconds` 随机 sleep。这比"claim 一批再逐封发"更简单——节流就是 worker 循环的自然节奏，不需要在发送循环内注入额外逻辑。

**单 worker 多域名轮转。** worker 进程内维护每个域名的独立节流时钟。每次迭代选择"下次可发送时间最早且已到期"的域名，claim 该域名的 1 封邮件。域名之间不互相等待，单部署即可支持多域名并行发送。

**不引入消息队列。** 数据库队列（`sequence_enrollments` + `email_send_locks`）已经满足当前规模需求。不引入 Redis、Celery、RabbitMQ 等外部依赖。

---

## Requirements

**逐封节流**

R1. worker 每次 claim 1 封邮件（`limit=1`），发送完成后更新该域名的"下次可发送时间"为 `now() + random(interval_seconds[0], interval_seconds[1])`。若 `send_strategy` 或 `interval_seconds` 为 null/缺失，fallback 到默认值 `[30, 120]`。只有在所有域名的"下次可发送时间"都未到期时，worker 才 sleep 到最早到期的时间点。发完域名 A 后如果域名 B 已到期，立即处理 B，不 sleep。

R2. 单 worker 内按域名独立节流。每个域名维护独立的"下次可发送时间"（内存状态，重启后重置为 now()）。worker 每次选择下次可发送时间最早且已到期的域名，claim 该域名的 1 封邮件发送。域名没有待发邮件时自动跳过，不阻塞其他域名。

R3. `claim_due_emails` 查询增加 `domain_id` 过滤条件，支持 worker 按域名 claim。返回结果须包含 `domain_id` 和 `send_strategy`（当前未返回），供 worker 更新域名节流时钟和读取 `interval_seconds`。

**失败重试**

R4. `sequence_enrollments` 增加 `send_attempt_count` 字段（默认 0），每次发送尝试（无论成功失败）+1。发送成功后，enrollment 推进到下一步时 `send_attempt_count` 重置为 0。同时需在迁移中将 `sequence_enrollments.status` 枚举约束增加 `'failed'` 值——与 `completed` 同属 worker 设置的内部终态，表示"当前步骤重试耗尽"。

R5. 临时错误（网络超时、EngageLab 5xx、API 限流 429）最多重试 3 次。重试间隔递增：第 1 次失败后 15 分钟，第 2 次失败后 1 小时，第 3 次失败后 4 小时。超过 3 次后 enrollment 标记为 `failed`。错误分类依据：`EngageLabSendError.status_code`（5xx 和 429 为临时）、`httpx` 网络异常（超时、连接拒绝）为临时。

R6. 永久错误（EngageLab 返回 4xx 且非 429，如硬退信、无效邮箱、被标记垃圾邮件）立即将 enrollment 标记为 `failed`，不重试。前置依赖：`EngageLabSendError` 需携带 `status_code` 属性（当前为纯字符串异常，需先改造）。

R7. 永久错误发生时，将对应 `tenant_contacts.contact_status` 更新为对应失败状态（如硬退信 → `bounced`，无效邮箱 → `invalid`）。`contact_status` 枚举可能需要追加新值。后续 plan 的收件人筛选可据 `contact_status` 自动排除不可发送的联系人。

**崩溃恢复**

R8. worker 启动时执行一次 stale lock 清理：将 `email_send_locks` 中 `status = 'locked'` 且 `locked_at` 超过 30 分钟的记录释放为 `released`，使对应 enrollment 可被重新 claim。

R9. stale lock 清理同时将对应的 `emails` 记录（`status = 'queued'`）标记为 `failed`（`error_code = 'STALE_LOCK'`），确保不产生孤立的 queued 邮件。

**配额回收**

R10. 发送失败后，将该封邮件之前通过 `reserve_domain_quota` 预扣的配额归还（`domain_daily_usage.reserved_count - 1`）。

**幂等性保护**

R11. 发送 API 调用使用确定性幂等键（`enrollment_id:step_id`），而非随机 `email_id`。确保 stale lock 恢复后重新 claim 时，即使生成了新的 email_id，EngageLab 也能识别为同一封邮件并去重。前置依赖：确认 EngageLab API 是否支持 idempotency key 机制。

**可观测性**

R12. worker 的每个关键操作输出结构化日志：域名选择（选了哪个域名、为什么）、发送结果（成功/失败、耗时）、节流 sleep（持续时长）、错误分类结果（临时/永久、attempt_count）、stale lock 恢复（恢复了几条、对应哪些 enrollment）。日志格式与现有 `run_once` 返回的 JSON 摘要保持一致。

---

## Key Flows

- F1. **正常发送流程**
  - **Trigger:** worker 循环迭代开始。
  - **Steps:** 查询各域名节流时钟 → 选择最早到期的域名 → claim 该域名 1 封邮件 → 调 EngageLab 发送 → mark_email_sent → 推进 enrollment → 更新该域名节流时钟 → sleep 随机间隔 → 下一次迭代。
  - **Covers R1, R2, R3.**

- F2. **临时失败与重试**
  - **Trigger:** EngageLab 返回 5xx 或网络超时。
  - **Steps:** mark_email_failed → send_attempt_count + 1 → 检查是否超过 3 次 → 未超过则设置 next_step_due_at 为递增间隔 → 超过则标记 enrollment failed → 归还域名配额。
  - **Covers R4, R5, R10.**

- F3. **永久失败**
  - **Trigger:** EngageLab 返回硬退信/无效邮箱等不可重试错误码。
  - **Steps:** mark_email_failed → enrollment 立即标记 failed → 更新 tenant_contacts 状态标记 → 归还域名配额。
  - **Covers R6, R7, R10.**

- F4. **Worker 启动恢复**
  - **Trigger:** worker 进程启动。
  - **Steps:** 扫描 locked 超过 30 分钟的 email_send_locks → 释放为 released → 对应 emails 标记 failed(STALE_LOCK) → 进入正常循环。
  - **Covers R8, R9.**

---

## Acceptance Examples

- AE1. **单域名逐封节流。** 域名 A 有 5 封待发邮件，plan 的 `interval_seconds = [30, 120]`。worker 发送第 1 封后 sleep 47 秒（随机值），发第 2 封后 sleep 93 秒，以此类推。5 封邮件发送总耗时约 3-10 分钟。
  **Covers R1.**

- AE2. **双域名轮转。** 域名 A 和 B 各有待发邮件。worker 发完域名 A 的 1 封（节流时钟设为 67 秒后），立即检查域名 B 的节流时钟已到期，发域名 B 的 1 封（节流时钟设为 104 秒后）。67 秒后域名 A 到期，发 A 的下一封。两个域名各自保持 30-120 秒间隔，互不阻塞。
  **Covers R1, R2, R3.**

- AE3. **临时错误递增重试。** 第 1 次发送因网络超时失败，`send_attempt_count = 1`，15 分钟后重试。第 2 次仍失败，`send_attempt_count = 2`，1 小时后重试。第 3 次仍失败，`send_attempt_count = 3`，4 小时后重试。第 4 次仍失败，enrollment 标记 `failed`，不再重试。
  **Covers R4, R5.**

- AE4. **永久错误立即放弃。** EngageLab 返回"invalid email address"错误码。enrollment 立即标记 `failed`（不论 `send_attempt_count` 是多少），对应 tenant_contact 的 `invalid_email` 标记为 true。
  **Covers R6, R7.**

- AE5. **崩溃恢复。** worker 进程在发送 email_id=abc 的过程中被 kill。email_send_locks 中 abc 的状态为 `locked`，locked_at 为 35 分钟前。新 worker 启动时检测到此记录，释放锁为 `released`，对应 email 标记为 `failed(STALE_LOCK)`。下次 claim 时 enrollment 可被重新领取，新的 email 使用确定性幂等键 `enrollment_id:step_id`（与原始请求相同），EngageLab 识别为重复请求并去重。
  **Covers R8, R9, R11.**

---

## Scope Boundaries

- 不引入外部消息队列（Redis、Celery、RabbitMQ）
- 不自动化预热曲线——`domain_warmup_status.daily_limit` 继续由人工管理
- 不改变现有 `send_strategy` 的 JSON 结构，仅消费已有的 `interval_seconds` 字段
- 不做发送优先级排序（如某些 plan 优先发送）——当前按 `next_step_due_at ASC` 即可
- 不做发送速度的 UI 配置——`interval_seconds` 已在 plan 创建时设置

---

## Dependencies / Assumptions

- EngageLab API 的 HTTP 状态码遵循标准语义（4xx=客户端错误，5xx=服务端错误，429=限流），可作为临时/永久错误分类依据
- EngageLab API 支持某种形式的 idempotency key 或去重机制（需确认；若不支持，R11 降级为"接受极低概率的重复发送风险"）
- 单 worker 进程足以覆盖当前及短期内的发送规模（多域名总量 <1000封/天）

---

## Sources / Research

- 参考项目 [sysdev-ft-marketing](https://github.com/aoqi-ai/sysdev-ft-marketing) 的调研结论：数据库队列 + eligibility polling 模型，逐封同步发送，无消息队列。其缺陷（无行级锁、无逐封 sleep）在本项目中已部分解决或本次补齐。
- 现有 worker 实现：`backend/app/workers/sending.py`（123 行）
- 现有 claim 逻辑：`backend/app/services/tenant_messaging_service.py:1544`（`claim_due_emails`）
- 现有失败处理：`backend/app/services/tenant_messaging_service.py:1954`（`mark_email_failed`，当前无限重试）
- `send_strategy.interval_seconds` 默认值 `[30, 120]`：`backend/alembic/versions/20260529_0002` 迁移文件
