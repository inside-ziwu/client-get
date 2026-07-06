## 1. 数据库迁移

- [x] 1.1 新增 Alembic 迁移文件 `backend/alembic/versions/20260701_0002_email_events_provider_event_id_text.py`，将 `email_events.provider_event_id` 从 `varchar(100)` 修改为 `text`
- [x] 1.2 在迁移中保留现有数据、`idx_email_events_provider_unique` 唯一索引和 `idx_email_events_email` 查询索引语义
- [x] 1.3 同步更新 `backend/03_database/schema.sql`，将基线 schema 中 `provider_event_id varchar(100)` 改为 `provider_event_id text`

## 2. 后端一致性检查

- [x] 2.1 检查 `backend/app/services/webhook_service.py` 中 provider event id 生成和入库逻辑，确认无需截断、hash 或改写原值
- [x] 2.2 确认 `ON CONFLICT DO NOTHING` 仍基于 `source + provider_event_id` 唯一索引完成幂等处理
- [x] 2.3 检查是否存在代码层字段长度约束；如存在，同步调整为不限制业务长度

## 3. 验证

- [x] 3.1 在开发数据库执行迁移：`cd backend && .venv/bin/python -m alembic upgrade head`
- [x] 3.2 增加或补充 webhook 相关测试，覆盖长度超过 100 字符的 `provider_event_id` 成功写入 `email_events`
- [x] 3.3 验证重复的超长 `provider_event_id` 事件不会重复入库，仍返回重复事件或等效幂等成功状态
- [x] 3.4 执行匹配的后端测试；若无法运行，记录原因和替代手工验收结果

## 4. 部署与收尾

- [x] 4.1 部署前确认迁移只涉及字段类型放宽，不会删除或截断生产数据
- [x] 4.2 上线部署：迁移随 alembic head `20260625_0100` 已上线（2026-07-05 只读核验生产 `email_events.provider_event_id` 已为 `text`）
- [x] 4.3 生产字段已为 `text`，`value too long for type character varying(100)` 截断错误在结构上不再可能出现（2026-07-05 只读核验）
- [x] 4.4 收尾对照见 OpenSpec 退役收尾（AGENTS.md §7.3）；`test_webhook_service_engagelab_provider_event_id.py` 2 项通过
