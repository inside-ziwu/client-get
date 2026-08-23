# 后端开发规范（backend/）

> FastAPI + PostgreSQL（asyncpg / psycopg）+ Alembic + 后台 worker。本目录是写后端代码前必读的规范入口。安全红线（生产只读、外部副作用、`.env`、租户隔离）以仓库根 [AGENTS.md](../../../AGENTS.md) §1 为准，本目录只写"怎么做"。

## 规范索引

| 文件 | 内容 | 何时读 |
|---|---|---|
| [directory-structure.md](./directory-structure.md) | 目录布局、分层规则、路由组与鉴权上下文、worker 形态、命名 | 新增或改动任何后端文件前 |
| [api-guidelines.md](./api-guidelines.md) | Pydantic 收参、响应包装、路由顺序、与前端契约同步、internal / webhook | 改 API |
| [database-guidelines.md](./database-guidelines.md) | 手写 SQL 约定、租户 / 实例隔离过滤、数据模型事实、迁移纪律、分区、时区、常见错误 | 写 SQL / 迁移 / 脚本 |
| [domain-rules.md](./domain-rules.md) | 关键行为口径表、多实例硬约束、认证 | 动发送、评分、统计、隔离相关逻辑 |
| [workers.md](./workers.md) | 发送 / 对账 / 修复 worker 的工程模式与可靠性机制 | 改 worker 或新增后台任务 |
| [error-handling.md](./error-handling.md) | `AppError`、错误响应结构、分层职责、外部服务错误 | 抛 / 接异常 |
| [logging-guidelines.md](./logging-guidelines.md) | JSON 日志、结构化事件、不得记录的内容、线上取证 | 写日志 / 查日志 |
| [quality-guidelines.md](./quality-guidelines.md) | 门禁、测试模式、真库验证纪律、禁止模式、评审清单 | 提交前 |

## 开发前检查清单（Pre-Development Checklist）

- [ ] 读 directory-structure.md：改动落在正确的层——route 只做胶水，SQL 只在 services
- [ ] 涉及租户 / 平台数据：对照 database-guidelines.md「隔离过滤」表，SQL 显式带 `tenant_id` / `instance_id`，并保留或新增隔离测试
- [ ] 涉及 schema：一个 alembic revision；按 database-guidelines.md 核对存量数据与 FK 链
- [ ] 涉及发送、评分、统计、时区、两实例：对照 domain-rules.md，不擅改口径
- [ ] 新增 / 修改端点：Pydantic model 收参；按 api-guidelines.md 同步 `shared-types` / `shared-api`
- [ ] 确认是否触碰 AGENTS.md §1 红线（生产写、`.env`、外部副作用）——触碰则先取得用户确认
- [ ] 过一遍 [../guides/index.md](../guides/index.md) 的思考触发器

## 质量检查（Quality Check）

- [ ] `cd backend && uv run pytest -q` 通过；`ruff` 无新增告警
- [ ] SQL 语义 / 时区窗口 / 状态机 / 分区改动：附 Neon 开发库断言记录（quality-guidelines.md「真库验证纪律」）
- [ ] 隔离相关改动有测试锁定
- [ ] 响应结构变化已同步前端类型
- [ ] 日志不含凭证与客户数据
- [ ] 收尾按 [../guides/delivery-checklist.md](../guides/delivery-checklist.md)
