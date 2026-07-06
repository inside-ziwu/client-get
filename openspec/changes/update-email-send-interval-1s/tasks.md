## 1. 后端发送间隔默认值

- [x] 1.1 修改 `backend/app/services/tenant_messaging_service.py`：`create_sending_plan()` 默认 `send_strategy.interval_seconds` 改为 `[1, 1]`
- [x] 1.2 修改 `backend/app/workers/sending.py`：`_delay_seconds()` 缺失/非法配置 fallback 改为 `[1, 1]`

## 2. 数据库迁移

- [x] 2.1 新增 Alembic migration `backend/alembic/versions/20260701_0001_set_email_send_interval_1s.py`
- [x] 2.2 migration upgrade：将 `sending_plans.send_strategy` 默认值改为 `{"interval_seconds":[1,1]}`，并回填既有计划的 `interval_seconds` 为 `[1,1]`
- [x] 2.3 migration downgrade：恢复数据库默认值为变更前默认；不自动恢复既有计划历史区间，并在注释中说明

## 3. 测试

- [x] 3.1 新增/更新发送计划创建测试，确认未显式传 `send_strategy` 时保存 `[1,1]`
- [x] 3.2 新增/更新 worker 延迟测试，确认 `[1,1]` 返回 1，缺失/非法配置 fallback 返回 1
- [x] 3.3 运行相关后端测试

## 4. 验证与生产准备

- [x] 4.1 本地只读确认（2026-07-05 dev：`sending_plans.send_strategy` 默认 `{"interval_seconds":[1,1]}`，既有 3 条计划全为 `[1,1]`）
- [x] 4.2 记录生产执行方式：后端镜像启动自动执行 `alembic upgrade head`，或用户明确触发后手动迁移
- [x] 4.3 生产只读确认（2026-07-05 prod：`sending_plans.send_strategy` 默认 `[1,1]`，既有 24 条计划全为 `[1,1]`）
