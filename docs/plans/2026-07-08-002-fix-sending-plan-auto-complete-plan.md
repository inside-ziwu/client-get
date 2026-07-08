---
title: Sending Plan Auto Complete - Plan
date: 2026-07-08
type: fix
topic: sending-plan-auto-complete
artifact_contract: ce-unified-plan/v1
artifact_readiness: requirements-only
product_contract_source: ce-brainstorm
execution: code
---

# Sending Plan Auto Complete - Plan

## Goal Capsule

- **Objective:** 当运行中的发送计划已经没有 `active` 或 `paused` 的收件人序列时，自动将计划推进为 `completed`，并回填数据库中已经满足该条件的历史计划。
- **Product authority:** 用户确认计划完成只看计划下的 `sequence_enrollments.status` 聚合结果：只要仍存在 `active` 或 `paused`，计划就不能完成；如果不存在任何 `active` 或 `paused`，计划就应该完成。后续打开、点击、回复、退信、退订等事件不阻止计划完成。
- **Open blockers:** 无。

---

## Product Contract

### Summary

发送计划的完成状态由该计划下的收件人序列状态决定。

一个 `running` 计划只要满足以下条件，就必须推进为 `completed`：

- 至少存在 1 条 `sequence_enrollments`。
- 不存在任何 `status IN ('active', 'paused')` 的 `sequence_enrollments`。

数据库中已有的 `running` 计划也必须按同一条件回填为 `completed`。

### Problem Frame

当前系统已经会在单个收件人序列结束时更新 `sequence_enrollments.status`，例如最后一步发送成功后变为 `completed`，永久失败后变为 `failed`，回复、退信、退订后变为对应终局状态。

但计划级别没有统一聚合逻辑，因此当一个计划下的所有收件人序列都已经不再是 `active` 或 `paused` 时，`sending_plans.status` 仍可能停留在 `running`。

这会导致业务上已经结束的发送计划，在界面和数据中仍显示为执行中。历史数据库里已经满足完成条件的计划也会继续保留错误状态。

### Key Decisions

- **完成判断只看 enrollment 状态。** 本需求不按邮件数量、发送批次、每日额度、步骤数量或后续互动事件判断计划是否完成。
- **`active` 阻塞完成。** 只要计划下存在任意 `active` enrollment，说明该计划仍有收件人序列处于发送链路中，计划不得完成。
- **`paused` 阻塞完成。** 只要计划下存在任意 `paused` enrollment，说明该计划仍有暂停中的收件人序列，计划不得完成。
- **非 `active` / `paused` 均不阻塞完成。** `completed`、`failed`、`cancelled`、`replied`、`bounced`、`unsubscribed` 等状态都表示该收件人序列不再阻塞计划完成。
- **只推进 `running` 计划。** 自动完成不得修改草稿、排期、暂停、取消或已完成计划。
- **空计划不自动完成。** 没有任何 enrollment 的计划不得被自动推进为 `completed`。
- **历史数据同口径回填。** 数据库里已有的 `running` 计划按完全相同的条件回填。

### Requirements

- R1. 系统必须在 `running` 计划至少存在 1 条 enrollment，且不存在任何 `active` 或 `paused` enrollment 时，将该计划状态推进为 `completed`。
- R2. 系统必须在计划自动完成时写入 `completed_at`，并更新 `updated_at`。
- R3. 任一 `active` enrollment 存在时，计划不得自动完成。
- R4. 任一 `paused` enrollment 存在时，计划不得自动完成。
- R5. `completed`、`failed`、`cancelled`、`replied`、`bounced`、`unsubscribed` enrollment 均不得阻塞计划自动完成。
- R6. 自动完成不得作用于非 `running` 计划。
- R7. 没有任何 enrollment 的计划不得被自动推进为 `completed`。
- R8. 后续 webhook 或对账事件可以继续更新邮件状态或 enrollment 的终局原因，但不得让已完成计划回退到 `running`。
- R9. 数据库中既有的 `running` 计划如果满足 R1 条件，必须通过迁移/回填推进为 `completed` 并写入 `completed_at`。
- R10. 数据库回填不得修改没有 enrollment、存在 `active` enrollment、存在 `paused` enrollment、或非 `running` 状态的计划。

### Acceptance Examples

- AE1. **Covers R1, R2, R5.** Given 一个 `running` 计划已有多个 enrollment，且它们分别为 `completed`、`failed`、`bounced`，When 系统执行计划完成检查，Then 该计划变为 `completed` 并写入 `completed_at`。
- AE2. **Covers R3.** Given 一个 `running` 计划存在至少一条 `active` enrollment，When 系统执行计划完成检查，Then 该计划保持 `running`。
- AE3. **Covers R4.** Given 一个 `running` 计划存在至少一条 `paused` enrollment，When 系统执行计划完成检查，Then 该计划保持 `running`。
- AE4. **Covers R6.** Given 一个 `paused` 计划的所有 enrollment 都不是 `active` 或 `paused`，When 系统执行计划完成检查，Then 该计划保持 `paused`。
- AE5. **Covers R7.** Given 一个 `running` 计划没有任何 enrollment，When 系统执行计划完成检查，Then 该计划保持 `running`。
- AE6. **Covers R8.** Given 一个计划已经是 `completed`，When 后续 webhook 或对账把某个 enrollment 更新为 `replied`、`bounced` 或 `unsubscribed`，Then 该计划仍保持 `completed`。
- AE7. **Covers R9, R10.** Given 数据库中已有一个 `running` 计划，且它至少有一条 enrollment 并且不存在 `active` 或 `paused` enrollment，When 回填迁移执行，Then 该计划变为 `completed`；不满足该条件的计划保持原状态。

### Scope Boundaries

- 不改变单封邮件 `emails.status` 的状态机。
- 不改变单个收件人 `sequence_enrollments.status` 的状态机。
- 不改变条件型步骤的现有状态机；仍处于 `active` 的 enrollment 必须继续阻塞计划完成。
- 不新增前端按钮、手动完成入口或计划状态展示文案。
- 本需求包含数据库迁移/回填脚本定义；不由本次普通实施自动执行生产迁移、镜像构建、镜像推送或 Sealos 更新。

### Sources / Research

- `backend/03_database/schema.sql` 定义 `sending_plans.status` 允许 `completed`，`sequence_enrollments.status` 允许 `active`、`completed`、`replied`、`bounced`、`unsubscribed`、`paused`、`cancelled`、`failed`。
- `backend/app/services/tenant_messaging_service.py` 当前 `mark_email_sent` 会在最后一步发送成功后把单个 enrollment 置为 `completed`，但不会同步完成计划。
- `backend/app/services/tenant_messaging_service.py` 当前 `mark_email_failed` 会在永久失败或重试耗尽后把单个 enrollment 置为 `failed`。
- `backend/app/services/webhook_service.py` 当前 webhook 会在 `replied`、`bounced`、`unsubscribed` 时终止单个 enrollment。
- `backend/app/services/email_reconciliation_service.py` 当前对账会在确认退信时把单个 enrollment 置为 `bounced`。
- `backend/app/workers/sending.py` 当前 worker 只从 `running` 计划中领取 `active` enrollment。
- `backend/alembic/versions/20260708_0001_set_email_send_interval_3s.py` 是当前最新迁移之一，后续回填迁移需要接在现有迁移链之后。
