## Why

当前发送计划默认单封邮件间隔为 5-10 秒随机，无法满足用户要求的固定 1 秒发送节奏。由于邮件发送间隔同时存在于新建计划默认值、worker fallback、数据库默认值和既有计划数据中，需要统一修改，避免不同路径产生不一致行为。

## What Changes

- 将新建发送计划的默认 `send_strategy.interval_seconds` 从 `[5, 10]` 改为 `[1, 1]`。
- 将发送 worker 在缺失或非法 `send_strategy.interval_seconds` 时的 fallback 从 `[30, 120]` 改为 `[1, 1]`。
- 新增 Alembic 迁移，将 `sending_plans.send_strategy` 数据库默认值改为 `{"interval_seconds":[1,1]}`。
- 在同一迁移中更新既有发送计划数据，将现有计划的 `send_strategy.interval_seconds` 统一为 `[1, 1]`。
- 补充测试，覆盖计划创建默认值、worker fallback 和固定 1 秒延迟。

## Non-Goals

- 不调整发送计划步骤之间的 `delay_days`，第一步立即、后续步骤天数逻辑保持不变。
- 不调整域名每日发送配额、预热档位或 EngageLab 通道配置。
- 不新增前端可配置发送间隔入口，本次只统一系统默认与既有数据。
- 不改变 worker 每轮只领取一封邮件、按域名维护发送时钟的调度模型。

## Capabilities

### New Capabilities

- `email-send-interval`: 发送计划单封邮件间隔 SHALL 统一为固定 1 秒，并覆盖新建默认、worker fallback、数据库默认和既有计划数据。

### Modified Capabilities

- 无。

## Impact

| 范围 | 影响 |
| --- | --- |
| 后端服务 | `backend/app/services/tenant_messaging_service.py` 新建计划默认 `send_strategy` 改为 `[1,1]` |
| Worker | `backend/app/workers/sending.py` fallback 间隔改为 `[1,1]` |
| 数据库 | 新增 Alembic migration，修改 `sending_plans.send_strategy` 默认值并回填既有计划 |
| 测试 | 更新/新增后端测试验证 1 秒间隔行为 |
| 生产数据 | 部署迁移后，生产库既有发送计划同步为固定 1 秒间隔 |
| 前端 | 无 UI 行为变更 |

## Dependencies and Order

1. 先修改后端默认值与 worker fallback。
2. 再新增数据库迁移，确保未来无显式 `send_strategy` 的 insert 仍为 1 秒。
3. 再补测试并运行验证。
4. 最后在部署/迁移执行后确认生产既有计划数据已回填。

## Control Mapping

- 决策编号：D-email-send-interval-1s
- 能力域：C-email-sending
