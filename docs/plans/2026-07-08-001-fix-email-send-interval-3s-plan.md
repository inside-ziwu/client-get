---
title: Email Send Interval 3s - Plan
date: 2026-07-08
type: fix
topic: email-send-interval-3s
artifact_contract: ce-unified-plan/v1
artifact_readiness: requirements-only
product_contract_source: ce-brainstorm
execution: code
---

# Email Send Interval 3s - Plan

## Goal Capsule

- **Objective:** 将发送计划每封邮件之间的固定发送间隔从 1 秒调整为 3 秒。
- **Product authority:** 用户明确要求“每封邮件之间的间隔从原来的 1s 调整到 3s”。
- **Open blockers:** 无。

## Product Contract

### Summary

发送计划的单封邮件间隔统一改为固定 3 秒。
新建计划默认值、worker fallback、数据库默认值、既有计划数据与系统规格必须保持一致。

### Requirements

- R1. 新建发送计划未显式传入 `send_strategy` 时，系统必须保存 `send_strategy.interval_seconds = [3, 3]`。
- R2. 调用方显式传入合法 `send_strategy` 时，系统必须保留调用方提供的策略，不因为默认值调整而覆盖。
- R3. 发送 worker 在缺失或无效 `send_strategy.interval_seconds` 时，必须 fallback 到固定 3 秒。
- R4. 数据库迁移必须将 `sending_plans.send_strategy.interval_seconds` 的列默认值设为 `{"interval_seconds":[3,3]}`。
- R5. 数据库迁移必须将既有发送计划的 `send_strategy.interval_seconds` 回填为 `[3, 3]`。
- R6. `docs/specs/email-send-interval/spec.md` 必须同步反映 3 秒行为真相。
- R7. 仓库内静态数据库 schema 参考必须同步为 `{"interval_seconds":[3,3]}`，避免从 schema 文件初始化时回到旧默认。

### Acceptance Examples

- AE1. 当租户创建发送计划且 payload 不包含 `send_strategy` 时，保存参数中的 `send_strategy` 必须为 `{"interval_seconds":[3,3]}`。
- AE2. 当 sending worker 计算缺失或格式错误的发送策略时，结果必须为 3 秒。
- AE3. 当新迁移应用后，未来直接插入 `sending_plans` 且未提供 `send_strategy` 的记录必须使用 `{"interval_seconds":[3,3]}`。

### Scope Boundaries

- 不调整按域名发送节流、每日额度、重试延迟、步骤间 `delay_days` 或前端页面流程。
- 不执行线上迁移、镜像构建、镜像推送或 Sealos 更新。

### Sources / Research

- `backend/app/services/tenant_messaging_service.py` 当前创建发送计划默认值为 `{"interval_seconds": [1, 1]}`。
- `backend/app/workers/sending.py` 当前 worker fallback 为 `[1, 1]`。
- `backend/alembic/versions/20260701_0001_set_email_send_interval_1s.py` 当前数据库默认值和既有数据已迁到 `[1,1]`。
- `backend/03_database/schema.sql` 当前静态 schema 默认值仍是历史 `[30,120]`。
- `backend/tests/test_email_send_interval.py` 当前覆盖 1 秒默认值和 fallback。
- `docs/specs/email-send-interval/spec.md` 当前规格写明 1 秒行为。
