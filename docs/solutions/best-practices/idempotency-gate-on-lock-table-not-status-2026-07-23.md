---
title: 回调幂等闸门放单写入方的锁表，不放多写入方共享的业务状态列
date: 2026-07-23
category: best-practices
module: backend_sending
problem_type: design_decision
component: internal_ops
severity: high
applies_when:
  - "为外部服务回写端点（mark-sent / mark-failed 类）补幂等保护"
  - "多个写入方（worker、webhook、对账任务）会推进同一张表的状态列"
tags: [idempotency, callback, webhook, state-machine, email_send_locks]
---

# 回调幂等闸门放单写入方的锁表，不放多写入方共享的业务状态列

## Context

`/internal/api/v1/sending/emails/{id}/mark-sent|mark-failed` 原本无幂等：重复回调会重复 `sent_count + 1`、虚耗 3 次重试预算、重复释放域名配额（PR #86 修复）。通用幂等表 `service_idempotency_keys` 已于同日随 PR #84 拆除（全仓零调用方），不可复建。

直觉方案是给 `emails.status` 加门槛（`WHERE status = 'queued'`），但 EngageLab webhook 的 `_apply_email_updates` 会**无条件**把 `emails.status` 推进到 `delivered/opened` 等后续态——delivered 事件先于 mark-sent 到达时（网络重试下常见），状态门槛会把**首次**回调误判为重复：enrollment 不推进、序列卡死、`sent_count` 漏计。比重复计数更糟。

## Guidance

1. **闸门放只有发送链路自己写的表**：`email_send_locks` 上
   `UPDATE ... SET status='sent' WHERE email_id=:id AND status='locked' RETURNING id`。
   0 行 = 重复/迟到回调 → 直接返回 `{"email_id", "status": <emails 当前态>, "duplicate": true}`，跳过全部副作用。webhook 与对账服务不碰锁表，锁状态是「回调是否已处理」的唯一可靠标记。
2. **条件更新 + RETURNING 天然防并发**：两个并发重复回调靠行锁串行化，恰好一个拿到返回行；不需要先 SELECT 再判断（TOCTOU）。
3. **跨尝试迟到回调自动被挡**：重试 claim 会把锁行 `email_id` 换成新一轮的 email id，旧 id 的迟到回调匹配不到行。
4. **业务状态列的推进加前置态门槛防回退**：`SET status = CASE WHEN status='queued' THEN 'sent' ELSE status END`（mark-sent）、`AND status='queued'`（mark-failed）——webhook 已推进的状态不被回写倒退。`recover_stale_locks` 是同款先例。

## Why This Matters

「用状态列判重」隐含单写入方假设；本系统同一行有三个写入方（发送回写、webhook、对账），任何一个抢跑都会使状态列失去「已处理回调」的语义。锁表生命周期（locked → sent/failed/released）只有发送链路推进，才是可靠闸门。

## When to Apply

- 见 frontmatter `applies_when`；反例：单写入方的表用状态列门槛即可，不必引入额外表。

## Related

- PR #86（实现与测试）、PR #84(拆除通用幂等表的决策)
- `docs/solutions/conventions/sql-semantics-verification-under-pure-mock-tests.md`（本次闸门 SQL 的 Neon 真库断言即按该约定执行）
