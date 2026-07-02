## Context

邮件发送 worker 当前每轮只领取一封待发邮件，并按域名维护下一次可发送时间。单封发送间隔来自发送计划的 `send_strategy.interval_seconds`，新建计划默认路径写入 `[5,10]`，worker 缺失配置时 fallback 为 `[30,120]`，数据库列默认也是 `[30,120]`。用户要求将单封邮件发送间隔全量统一为固定 1 秒。

本次变更涉及后端服务、worker、Alembic 迁移和既有数据回填，属于邮件发送链路变更，需要保持行为简单且可验证。

## Goals / Non-Goals

**Goals:**

- 所有新建发送计划默认写入 `{"interval_seconds":[1,1]}`。
- worker 在缺失或非法配置时也按 1 秒间隔调度。
- 数据库默认值与服务层默认值一致。
- 既有发送计划数据在迁移后统一为 1 秒间隔。
- 测试覆盖默认值、fallback 和固定 1 秒延迟。

**Non-Goals:**

- 不新增 UI 配置入口。
- 不改发送步骤 `delay_days`。
- 不改域名每日配额、预热档位、工作时间规则或 EngageLab API 调用。
- 不重构 worker 调度模型。

## Decisions

### D1: 保留 `interval_seconds` 双元素数组结构

选择：继续使用 `send_strategy.interval_seconds = [low, high]`，固定 1 秒表达为 `[1,1]`。

理由：现有 worker 已支持 low/high 相同值，保留结构可以最小化代码、数据和测试改动，也兼容已有 JSON 读取逻辑。

替代方案：新增 `interval_seconds: 1` 标量字段。放弃原因是会增加 worker 兼容分支和数据迁移复杂度，收益不足。

### D2: 数据迁移同时修改默认值与既有数据

选择：新增 Alembic migration，将 `sending_plans.send_strategy` 默认值改为 `{"interval_seconds":[1,1]}`，并更新既有计划的 `send_strategy.interval_seconds`。

理由：用户要求包含全部场景；仅改代码会导致既有计划继续按旧间隔发送。

替代方案：只更新 running/draft 计划。放弃原因是会留下历史计划数据不一致，后续恢复或复制计划时可能重新带出旧间隔。

### D3: worker fallback 也改为固定 1 秒

选择：当 `send_strategy` 缺失、格式非法或为空时，worker fallback 使用 `[1,1]`。

理由：避免任何异常路径落回 30-120 秒，保证系统行为一致。

替代方案：只依赖数据库/服务默认值。放弃原因是 worker 仍可能处理老数据或手动写入的异常数据。

## Risks / Trade-offs

- [发送速率提高带来通道压力] → 域名每日配额仍由 `domain_daily_usage` 和预热档位控制，单封间隔只改变发送节奏，不放大每日总量。
- [既有计划数据回填影响历史记录] → 只更新 `sending_plans.send_strategy`，不修改已发送 `emails` 记录。
- [回滚后数据仍为 1 秒] → downgrade 可恢复数据库默认值，但不自动恢复每条计划的旧区间；如需业务回滚，应执行单独数据修复脚本。

## Migration Plan

1. 代码发布包含服务默认值和 worker fallback 修改。
2. Alembic migration 修改 `sending_plans.send_strategy` 默认值并回填既有计划。
3. 本地验证迁移后：
   - 新建计划默认 `interval_seconds=[1,1]`
   - 既有计划 `send_strategy->interval_seconds` 为 `[1,1]`
   - worker `_delay_seconds()` 返回 1
4. 生产部署时由后端镜像启动自动执行 `alembic upgrade head`，或按需手动执行迁移。

## Open Questions

- 无。
