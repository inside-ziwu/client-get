## Context

EngageLab webhook 推送丢失约 50% 的 delivered/bounced 事件，导致邮件状态卡在 `sent`。现有 `scripts/backfill_email_status.py` 能手动修复，但需要人工介入。需要自动化为定时 worker。

现有代码资产：
- `scripts/backfill_email_status.py`：已有完整的 EngageLab API 查询 + 数据库更新逻辑（STATUS_MAP、联动更新等）
- `integrations/engagelab.py`：`query_email_status()` 方法，支持分批查询（每批 20 个 ID）
- `workers/sending.py`：Worker 模式参考（`run_once()` + runner script）

## Goals / Non-Goals

**Goals:**
- 自动对账 `status='sent'` 的邮件，周期性补齐真实投递状态
- 复用现有 backfill 脚本逻辑，保持更新行为一致

**Non-Goals:**
- 不补录 open/click 事件（EngageLab status API 不提供）
- 不修改 webhook 处理逻辑
- 不做前端改动

## Decisions

### 1. 复用 backfill 脚本逻辑，提取到 service 层

**选择**：将 `backfill_email_status.py` 的核心逻辑提取到 `services/email_reconciliation_service.py`，worker 和手动脚本共用。

**理由**：backfill 脚本已经过生产验证，逻辑完整（STATUS_MAP、delivered/bounced 分支、联动更新 enrollments/contacts/companies）。提取后 worker 调用 service，手动脚本也可改为调用 service。

### 2. Worker 实现为 `run_once()` 循环

**选择**：和 `SendingWorker` 同样的模式——`ReconciliationWorker.run_once()` + runner script。

**理由**：项目现有 worker 统一用这个模式，部署到 Sealos 时用 `python -m scripts.run_reconciliation_worker` 启动。

### 3. 对账范围：sent_at 超过 30 分钟的 `status='sent'` 邮件

**选择**：每轮只处理 `sent_at < now() - 30min AND status = 'sent'` 的邮件，避免和 webhook 回调竞争。

**理由**：EngageLab 正常 webhook 在发送后几秒内到达。30 分钟后还停在 sent 就可以确认是 webhook 丢失。

### 4. 按 send_date（CST）分组查询 EngageLab API

**选择**：EngageLab `query_email_status` API 要求传 `send_date` 参数，按北京时间日期分组。

**理由**：API 限制，必须按日期查。将 emails.sent_at 转为 CST 日期后分组。

### 5. 对账频率：每 10 分钟一轮

**选择**：worker 每 10 分钟执行一次 `run_once()`。

**理由**：对账不需要实时性，10 分钟间隔足够及时又不会频繁调用 EngageLab API。

## Risks / Trade-offs

- [EngageLab API 限流] → 分批查询（每批 20 ID），且 10 分钟间隔降低频率
- [和 webhook 同时写入同一封邮件] → 30 分钟窗口避免竞争；即使并发写入，delivered/bounced 是幂等操作（sent → delivered 无论谁先写都正确）
- [EngageLab API 返回 status=18（发送中）] → 跳过，下一轮再查
