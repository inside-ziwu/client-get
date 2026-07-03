## Why

2026-07-02 配额级联事故（见 change `fix-quota-exhaustion-cascade`）中，13,940 个 `sequence_enrollments` 因 EngageLab 余额不足错误被误判为永久失败而终止，对应约 13,950 封邮件被打成 `failed`（`sent_at`/`engagelab_message_id` 全为 NULL，实际一封未发出）。这批联系人的发送序列不会自动恢复——不修复则永久漏发。用户已决策立项修复，**优先级后置于 `fix-quota-exhaustion-cascade` 上线**（避免在无熔断保护下重发再次触发级联）。

## What Changes

- 一次性数据修复：将事故中被误杀的 enrollment（2026-07-02 UTC 窗口内、attempt=0 或未耗尽重试、错误源为配额/余额类）恢复为 `active` 并重新排期 `next_step_due_at`（按域名日配额分批摊开，避免单日洪峰再次撞额度）。
- 事故遗留的 failed 邮件行按 `fix-quota-exhaustion-cascade` 确立的口径处理（不计入已发送/计费；是否删除孤儿行在 design 阶段定夺）。
- 修复脚本为一次性运维操作，幂等、可回滚（先备份受影响行），执行属生产写操作，必须由用户明确触发。

## Non-Goals

- 不修改发送/熔断/口径逻辑（`fix-quota-exhaustion-cascade` 负责）。
- 不处理事故窗口之外的历史 failed 数据。

## Capabilities

### New Capabilities

- `quota-incident-data-repair`: 2026-07-02 事故受影响 enrollment 的识别、恢复、重排期与验证。

### Modified Capabilities

（无）

## Impact

| 范围 | 影响 |
|------|------|
| 数据库 | 一次性 UPDATE（enrollment 状态/排期），先备份；无 schema 变更 |
| 后端 | 修复脚本（`backend/scripts/` 或一次性 SQL），不改常驻代码 |
| 前置依赖 | `fix-quota-exhaustion-cascade` 已上线（熔断保护就位）+ EngageLab 余额已充值 |
| 触发方式 | 用户明确触发（生产写操作） |

受影响数据基线（2026-07-03 生产库实测）：enrollment 13,940 个（attempt=0 的 13,913 个 + 走过重试链的 27 个）、failed 邮件 13,950 封，全部属租户 019dc238-c4c9-7de8-842f-8d46731481c1。design/specs/tasks 在启动实施时再补齐。
