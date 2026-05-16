# Self Audit Report

## 1. 审查口径

本次自审按“没有任何后端源码，Codex/Claude Code 是否能从 0 开始写后端”的标准检查，而不是按“文档看起来是否完整”检查。

检查项：

1. 原始资料是否完整保留。
2. 最终实现真源是否唯一。
3. 需求、UI、前端、API、数据库、服务逻辑是否能闭环。
4. 多租户/RLS/认证是否有可执行约束。
5. AI 计费、采集 lease、发送幂等、Webhook 幂等是否能落库。
6. 机器可读任务和 API 是否不会误导代码 Agent。

## 2. 发现并已修复的问题

| 编号 | 问题 | 风险 | 修复 |
|---|---|---|---|
| SA-001 | `schema.sql` 中 `collection_task_keywords`、`intelligence_sources`、`audit_logs` 带 tenant 语义但未列入 RLS enablement。 | 代码 Agent 可能漏掉隔离策略。 | 已在 `schema.sql` 补 RLS enablement，并新增 `03_database/RLS_POLICY_MATRIX.md`。 |
| SA-002 | AI 计费状态机写了 `provider_called`，但 schema / machine-readable 状态未包含。 | 状态机与表约束不一致，落库会失败。 | 已补 `provider_called`，并将 `ai_usage_logs.actual_cost` 改为结算前可为空。 |
| SA-003 | AI 调用失败时 usage log 口径不一致。 | 无法追踪 failed attempt 或与结算状态冲突。 | 已改为“每次 AI 调用先建 attempt log；失败标记 `released_full`、`actual_cost=0`、不计可计费用量”。 |
| SA-004 | FastAPI 静态路由与 `/{id}` 动态路由存在潜在遮蔽。 | `/companies/filters`、`/emails/stats` 可能被错误匹配成 id。 | 新增 `04_api/FASTAPI_ROUTE_ORDERING.md`，并要求验收测试覆盖。 |
| SA-005 | 机器可读 API routes 不够完整。 | Agent 若优先读 YAML，可能漏端点。 | 已重写 `machine_readable/api_routes.yaml`，并声明 `API_CONTRACT.md` 仍为主真源。 |

## 3. 仍需 Owner 确认但不阻塞开发

详见 `08_references/OWNER_OPEN_QUESTIONS.md`：EngageLab inbound/reply、腾道/励销云 API 文档、预热档位是否调整等。

## 4. 当前结论

修复后，本包可以作为后端从 0 实现的蓝图。但仍不等同于可运行源码：代码 Agent 需要基于本包生成 FastAPI 项目、Alembic migration、服务实现和测试。
