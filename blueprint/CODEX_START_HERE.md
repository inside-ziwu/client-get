# CODEX_START_HERE.md — ClientGet 后端从 0 开发启动说明

你现在拿到的是 `clientget_backend_blueprint_v2_self_audited.zip`。这个包不是普通参考资料，而是 ClientGet 后端从 0 开始开发的最终蓝图。当前项目后端代码尚未编写，你的任务是根据新版包完整实现后端代码、数据库迁移、服务逻辑、测试、运行说明和前端 API 对接能力。

请进入“长程自主编程模式”：不要只搭脚手架，不要只写部分模块，不要停在 TODO，不要把明显能从文档推出的事情反复问用户。持续推进，直到后端达到可运行、可测试、可接入两个前端应用的状态。

---

## 1. 最高优先级规则

1. 以新版包内的修复后文档为准，不要直接按原始 `00-14` 文档写代码。
2. 原始资料只用于追溯，不是实现真源。
3. 如果原始文档、旧系统文档、前端 mock 行为、API 设计之间出现冲突，按以下优先级判断：

   ```text
   00_SOURCE_OF_TRUTH_DECISIONS.md
   > 09_self_audit/SELF_AUDIT_REPORT.md
   > 01_final_repaired_docs/*
   > 02_architecture/*
   > 03_database/schema.sql + RLS_POLICY_MATRIX.md
   > 04_api/API_CONTRACT.md + FASTAPI_ROUTE_ORDERING.md
   > 05_services/*
   > 06_frontend_alignment/*
   > 07_implementation_plan/*
   > 00_original_sources/*
   ```

4. 不要把 `business-flows-v2.html` 里的旧口径直接实现为代码；它只作为业务起点。特别注意：公司去重、域名预热、自助充值、AI 计费、角色枚举、API 前缀、采集服务通信方式均已被新版包修订。
5. 不要等用户确认已经在新版包中被明确修复的内容。只有在所有修复后文档都没有给出口径，且继续实现会造成不可逆架构分歧时，才向用户提问。
6. 只要问题不是阻塞项，就先采用合理默认值，并记录在 `docs/ASSUMPTIONS.md`。

---

## 2. 先读这些文件，按顺序读

在写代码前，先完整阅读以下文件：

```text
00_SOURCE_OF_TRUTH_DECISIONS.md
09_self_audit/SELF_AUDIT_REPORT.md

01_final_repaired_docs/REPAIR_COVERAGE_FOR_ALL_UPLOADED_DOCS.md
01_final_repaired_docs/07_REQUIREMENTS_SPEC_REPAIRED.md
01_final_repaired_docs/09_DATABASE_DESIGN_REPAIRED.md
01_final_repaired_docs/10_API_DESIGN_REPAIRED.md
01_final_repaired_docs/11_FRONTEND_ARCHITECTURE_REPAIRED.md
01_final_repaired_docs/12_COLLECTION_SERVICE_REPAIRED.md
01_final_repaired_docs/13_AI_INTEGRATION_REPAIRED.md
01_final_repaired_docs/14_DATA_MIGRATION_REPAIRED.md

02_architecture/BACKEND_ARCHITECTURE.md
02_architecture/SECURITY_RLS_AUTH_ARCHITECTURE.md

03_database/schema.sql
03_database/RLS_POLICY_MATRIX.md

04_api/API_CONTRACT.md
04_api/FASTAPI_ROUTE_ORDERING.md

05_services/AI_BILLING_SERVICE_SPEC.md
05_services/COLLECTION_SERVICE_SPEC.md
05_services/SCORING_SERVICE_SPEC.md
05_services/SENDING_SERVICE_SPEC.md
05_services/WEBHOOK_SERVICE_SPEC.md
05_services/DOMAIN_WARMUP_SERVICE_SPEC.md
05_services/MIGRATION_SERVICE_SPEC.md

06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md

07_implementation_plan/DEVELOPMENT_PLAN.md
07_implementation_plan/TASKS.yaml
07_implementation_plan/ACCEPTANCE_TEST_PLAN.md
```

读完以后再开始写代码。不要跳过 `09_self_audit/SELF_AUDIT_REPORT.md`，里面记录了 v1 蓝图被修正的问题，尤其是 RLS 覆盖、AI 计费状态机、FastAPI 路由顺序和机器可读文件一致性。

---

## 3. 目标交付物

你需要生成一个完整后端仓库，至少包含：

```text
backend/
  app/
    main.py
    config.py
    dependencies.py
    database/
    models/
    schemas/
    repositories/
    services/
    api/
      admin/
      tenant/
      internal/
      webhooks/
    workers/
    integrations/
    security/
    utils/
  alembic/
  tests/
  scripts/
  docs/
  pyproject.toml
  README.md
  .env.example
  docker-compose.yml
  Dockerfile
```

具体技术栈以新版包架构为准。默认采用：

```text
Python 3.11+
FastAPI
PostgreSQL 16+
SQLAlchemy 2.x async 或 asyncpg repository pattern
Alembic
Pydantic v2
pytest + pytest-asyncio
httpx
bcrypt/passlib 或 argon2/bcrypt 密码哈希
PyJWT 或 python-jose
```

如果你选择不同库，必须保证与蓝图兼容，并在 `docs/IMPLEMENTATION_NOTES.md` 说明原因。

---

## 4. 实现范围

必须完成以下后端能力。

### 4.1 基础设施

- FastAPI 应用入口。
- 配置管理。
- 数据库连接池。
- 请求 ID。
- 结构化日志。
- 错误响应统一格式。
- CORS 白名单。
- 健康检查。
- OpenAPI 文档。
- Dockerfile。
- docker-compose，本地启动 PostgreSQL + 后端。
- `.env.example`。
- Alembic migration。
- 测试运行脚本。

### 4.2 数据库

必须按 `03_database/schema.sql` 和 `03_database/RLS_POLICY_MATRIX.md` 实现：

- UUID v7 主键策略。
- tenants/users/user_roles。
- platform admin 与 tenant roles 分离。
- shared company pool。
- tenant companies。
- scoring templates/versioning。
- contact rules。
- groups/group members。
- email templates。
- sending plans。
- sequence steps/enrollments。
- emails 分区表。
- email events。
- intelligence sources/articles/publications/subscriptions。
- collection keywords/tasks。
- AI models/scene defaults/usage logs。
- balance transactions。
- domain warmup status/history。
- notifications。
- audit logs 分区表。
- RLS policies。
- 必要索引。
- Webhook 幂等索引。
- 发送幂等锁表或等价机制。
- AI 预授权/结算相关字段。
- collection task lease 字段。

不要把 schema.sql 当作可以裸跑的最终生产 SQL。应该拆成合理的 Alembic migrations，并保证 `alembic upgrade head` 可执行。

### 4.3 认证与授权

实现：

- Admin 登录：`/admin/api/v1/auth/login`。
- Tenant 登录：`/t/{slug}/api/v1/auth/login`。
- Tenant JWT 中必须包含 `sub`, `tid`, `slug`, `roles`, `iat`, `exp`。
- Admin JWT 使用 `roles=["platform_admin"]`。
- Tenant 角色只允许 `admin / operator / viewer`。
- URL slug 与 JWT tenant_id 必须交叉验证。
- Tenant API 使用启用 RLS 的连接，并在请求事务内设置 `app.current_tenant_id`。
- 禁止 handler 直接绕过 tenant scoped connection。
- 登录失败锁定策略。
- 首次登录强制改密。
- RBAC 权限矩阵。

### 4.4 Admin API

按 `04_api/API_CONTRACT.md` 实现 Admin 端：

- 数据源管理。
- 平台评分模板管理。
- 情报源管理。
- 平台邮件模板管理。
- 域名预热规则。
- AI 配置：models / pricing / scene-defaults。
- 租户管理。
- 租户用户管理。
- 租户域名管理。
- 租户余额手动充值。
- 采集任务监控。
- 平台统计仪表盘。

Admin API 前缀固定为：

```text
/admin/api/v1/*
```

### 4.5 Tenant API

按 `04_api/API_CONTRACT.md` 和 `06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md` 实现 Tenant 端：

- 认证与当前用户。
- 首次登录向导所需接口。
- Dashboard。
- 公司列表。
- 公司详情。
- 批量导入。
- 黑名单。
- 优选客户。
- 联系人默认设置。
- 群组管理。
- 邮件模板。
- AI 生成邮件模板。
- 发送计划列表/创建/详情。
- 发送计划步骤。
- 收件人 preview / lock / append。
- start / schedule / pause / resume / cancel。
- 邮件监控。
- 邮件统计。
- AI 分析。
- 情报中心。
- 关键词设置。
- 评分规则设置。
- 联系人规则设置。
- AI capabilities。
- billing balance / transactions / usage。
- 团队管理。
- 通知。

Tenant API 前缀固定为：

```text
/t/{slug}/api/v1/*
```

前端路由不带 slug，只有 API 路径带 slug。

### 4.6 Internal API

实现独立 Internal API：

```text
/internal/api/v1/*
```

必须支持服务身份认证、服务名校验、scope 校验和请求幂等。

必须实现：

- 采集任务 claim。
- 采集任务 heartbeat。
- 采集任务 submit_result。
- 数据源凭证拉取。
- 批量 upsert companies。
- 批量 upsert contacts。
- 批量 upsert competitors。
- 拉取可调度关键词。
- 评分触发/补评。
- 发送任务拉取与状态回写。

主系统不得信任采集服务上传的 `tenant_ids`。租户归属必须由主系统根据本地 collection task / keyword 关系重新解析。

### 4.7 Webhook

实现：

```text
/webhooks/engagelab
```

必须完成：

- 签名校验或 shared secret 校验。
- `engagelab_event_id` 幂等去重。
- 原始事件入库。
- emails 状态推进。
- sequence_enrollments 状态推进。
- tenant_contacts 状态推进。
- 事务内完成全部状态更新。
- 支持 webhook 重试。
- 不重复推进状态。

如果 EngageLab inbound/reply 解析资料不足，回复正文相关逻辑保留字段和接口，但不要伪造不可验证实现。实现事件型 replied 状态即可，并在 `docs/OPEN_QUESTIONS.md` 标记“回复正文解析依赖 EngageLab inbound 能力确认”。

### 4.8 AI 计费

必须实现新版包确定的状态机：

```text
authorized
provider_called
settled_exact
settled_charge
settled_release
released_full
```

规则：

1. 调用模型前先做预授权 hold。
2. hold 成功后才允许调用 OpenRouter。
3. 拿到 provider 响应后按真实 token 结算。
4. 实际费用大于预估费用时补扣差额。
5. 实际费用小于预估费用时释放差额。
6. provider 调用失败且没有可计费输出时释放全部 hold。
7. 如果 provider 成功但本地结算失败，必须基于 `authorization_txn_id` 幂等重试结算，禁止再次调用模型。
8. 情报摘要均摊时，每个租户各自预授权和结算。
9. Operator/Viewer 不直接读取余额金额，只读取 `ai-capabilities`。
10. Admin 可以读取余额和流水。

### 4.9 采集服务

后端主系统必须提供采集服务通信接口。采集服务可以先实现为同仓库 worker 或独立模块，但架构上要支持独立部署。

必须实现 lease 机制：

```text
pending -> running -> completed
                 -> failed -> pending retry
                 -> cancelled
```

要求：

- claim 后返回 lease。
- heartbeat 续租。
- submit_result 必须校验 lease。
- lease 过期回写要被拒绝。
- submit_result 在同一事务内落结果、结束任务、释放 lease。
- 多实例并发 claim 不得领取同一任务。
- keyword 聚合必须按 keyword + countries hash 聚合。
- source_type 固定为 `waimao_tong / tengdao / lixiaoyun`。

### 4.10 发送服务

必须实现：

- 创建发送计划。
- 收件人 preview。
- 启动前 lock recipients。
- 自动排除黑名单、退订、待补全、无有效邮箱。
- 每个公司默认联系人逻辑。
- sequence_enrollments。
- 域名验证与每日额度校验。
- 发送幂等：同一 enrollment + step 只能发一次。
- EngageLab send adapter。
- 发送失败重试。
- 暂停、恢复、取消。
- 运行中只允许追加收件人和修改未来未执行步骤。
- 已发送对象不可回改。

### 4.11 域名预热

必须实现动态指标驱动 6 档，不要实现旧固定天数版本。

必须支持：

- DNS 验证状态。
- warmup level。
- daily limit。
- bounce/open/complaint 指标。
- 升档/降档。
- history snapshot。
- 租户多个域名独立预热。
- 同一租户所有发送计划共享域名当日额度。

### 4.12 数据迁移

虽然当前后端从 0 写，但要保留迁移工具结构，支持未来从旧系统数据导入。

实现：

- 迁移脚本目录。
- id mapping 逻辑。
- 旧 12 表到新表的映射脚本骨架。
- dry-run。
- row count 校验。
- sample 校验。
- rollback 说明。

---

## 5. 前端对接要求

两个前端已经部署，但当前数据是 mock：

```text
Admin:  https://client-get-admin.vercel.app/
Tenant: https://client-get-tenant.vercel.app/
```

后端必须严格对齐新版包内的前端映射：

```text
06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md
04_api/API_CONTRACT.md
04_api/FASTAPI_ROUTE_ORDERING.md
```

特别注意：

1. Admin 与 Tenant 是两个独立 React 应用。
2. Admin API：`/admin/api/v1/*`。
3. Tenant API：`/t/{slug}/api/v1/*`。
4. Tenant 前端路由不携带 slug。
5. 登录页由用户输入 slug。
6. 响应 JSON 使用 snake_case。
7. 成功响应使用 `{ "data": ... }`。
8. 分页响应使用 `{ "data": [...], "pagination": {...} }`。
9. 错误响应使用 `{ "error": { "code", "message", "details", "request_id" } }`。
10. FastAPI 静态路由必须先于动态 `/{id}` 路由注册。例如：
    - `/companies/filters` 必须先于 `/companies/{id}`
    - `/emails/stats` 必须先于 `/emails/{id}`
    - `/email-templates/ai-generate` 必须先于 `/email-templates/{id}`

---

## 6. 开发顺序

按 P0 → P1 → P2 推进，不要乱序。

### P0 — 必须先完成

1. 项目脚手架。
2. 配置系统。
3. 数据库连接。
4. Alembic 初始化。
5. 核心 schema migrations。
6. RLS policies。
7. 认证与 RBAC。
8. Admin/Tenant 路由骨架。
9. 统一错误响应。
10. 健康检查。
11. 基础测试框架。
12. 租户创建。
13. Tenant 登录。
14. 当前用户 `/auth/me`。
15. AI 余额与流水基础结构。
16. collection task lease 基础结构。
17. 发送计划基础结构。
18. webhook 幂等基础结构。

### P1 — 业务闭环

1. Admin 配置类 API。
2. Tenant 公司/客户/群组 API。
3. 评分模板与联系人规则。
4. 采集 Internal API。
5. 评分服务。
6. AI 计费完整状态机。
7. 邮件模板与 AI 生成。
8. 发送计划六步向导 API。
9. 发送服务。
10. EngageLab webhook。
11. Dashboard 与邮件监控。
12. 情报中心。
13. 通知。
14. 审计日志。

### P2 — 完整生产化

1. 数据迁移工具。
2. 分区维护脚本。
3. PII 脱敏任务。
4. 监控指标。
5. 更完整的 worker 调度。
6. 端到端集成测试。
7. 文档完善。
8. 性能索引校验。
9. docker-compose 一键本地跑通。

---

## 7. 长程编程工作循环

你必须按以下循环持续工作：

```text
1. 读当前阶段任务
2. 实现代码
3. 写或更新测试
4. 运行测试
5. 修复失败
6. 更新进度文件
7. 进入下一阶段
```

每完成一个阶段，更新：

```text
docs/AGENT_PROGRESS.md
```

内容包括：

```markdown
# Agent Progress

## Current phase
...

## Completed
- ...

## Tests passed
- ...

## Known issues
- ...

## Assumptions
- ...

## Next actions
- ...
```

不要在一个阶段没测试前进入下一阶段。不要写“待实现”后跳过。

如果上下文窗口、运行时间或工具限制导致你即将中断，必须先写好 `docs/AGENT_PROGRESS.md` 和 `docs/NEXT_SESSION_PROMPT.md`，让下一轮可以无缝继续。`NEXT_SESSION_PROMPT.md` 必须包含：

```markdown
你正在继续 ClientGet 后端开发。
先读 docs/AGENT_PROGRESS.md。
继续未完成的下一项任务。
不要重做已完成内容。
继续运行测试并修复失败，直到全部验收通过。
```

---

## 8. 禁止事项

不要做以下事情：

1. 不要只生成目录不写业务代码。
2. 不要只写模型不写 API。
3. 不要只写 API 不写 service。
4. 不要只写 service 不写测试。
5. 不要保留明显未完成的 TODO。
6. 不要把旧系统 9 状态 email_plans 流水线照搬到新系统。
7. 不要使用旧角色 `sales / observer`。
8. 不要让 Tenant API 绕过 RLS。
9. 不要让 Admin API 使用 tenant scoped connection。
10. 不要信任 Internal API 上传的 tenant_ids。
11. 不要用公司名称作为唯一去重真源。
12. 不要实现固定天数域名预热。
13. 不要实现 Phase 1 租户自助充值，除非新版包明确要求。
14. 不要在 AI provider 成功后因本地结算失败而再次调用模型。
15. 不要忽略 webhook 幂等。
16. 不要忽略发送幂等。
17. 不要在动态路由前注册静态路由之后才定义静态路由。
18. 不要将凭证明文落库。
19. 不要让 Operator/Viewer 读取具体 AI 余额。
20. 不要把 mock 数据当作后端真实逻辑。

---

## 9. 测试要求

至少实现以下测试。

### 9.1 单元测试

- 密码哈希与登录。
- JWT 生成与解析。
- RBAC。
- AI 费用计算。
- AI 预授权与结算。
- AI 失败释放。
- 域名预热升降档。
- collection lease claim/heartbeat/submit。
- 发送计划状态机。
- webhook 幂等处理。
- route ordering。

### 9.2 集成测试

- Admin 创建租户。
- Tenant 登录。
- Tenant slug 与 JWT tid 不匹配时返回 403。
- Tenant A 不能读取 Tenant B 数据。
- Viewer 不能创建/修改。
- Operator 不能访问 admin-only 设置。
- Admin 手动充值。
- AI capabilities。
- 邮件模板 AI 生成扣费。
- 采集任务 claim 并 submit result。
- 公司入池并关联租户。
- 发送计划从 draft 到 running。
- recipients lock 排除黑名单/退订/待补全。
- webhook delivered/opened/replied 推进状态。
- duplicate webhook 不重复写入。
- duplicate sending attempt 不重复发信。

### 9.3 数据库/RLS 测试

- app_user 无法直接 select shared_companies。
- Tenant A 无法 select Tenant B 的 tenant_companies。
- audit_logs 允许 insert/select，不允许 update/delete。
- intelligence_articles 只能通过 tenant publication 视图访问。
- collection task lease 过期后不能 submit。
- emails 分区游标按 created_at + id 排序。

### 9.4 API 合同测试

- 响应结构统一。
- 错误结构统一。
- 分页结构统一。
- `/companies/filters` 不被 `/companies/{id}` 捕获。
- `/emails/stats` 不被 `/emails/{id}` 捕获。
- `/email-templates/ai-generate` 不被 `/email-templates/{id}` 捕获。

---

## 10. 本地运行验收

最终至少要做到：

```bash
cp .env.example .env
docker compose up -d postgres
alembic upgrade head
pytest
uvicorn app.main:app --reload
```

并且以下端点可用：

```text
GET  /health
POST /admin/api/v1/auth/login
POST /admin/api/v1/tenants
POST /t/{slug}/api/v1/auth/login
GET  /t/{slug}/api/v1/auth/me
GET  /t/{slug}/api/v1/dashboard/overview
GET  /t/{slug}/api/v1/companies
GET  /t/{slug}/api/v1/prospects
GET  /t/{slug}/api/v1/email-templates
GET  /t/{slug}/api/v1/sending-plans
GET  /t/{slug}/api/v1/emails/stats
GET  /t/{slug}/api/v1/ai-capabilities
```

---

## 11. 最终交付检查清单

完成后确认：

```text
[ ] 后端可启动
[ ] Alembic 可从空库迁移到最新版本
[ ] pytest 通过
[ ] Admin 登录可用
[ ] Tenant 登录可用
[ ] RLS 测试通过
[ ] Admin 创建租户可用
[ ] Tenant API 和 slug 校验可用
[ ] AI 计费状态机可用
[ ] 采集 lease 可用
[ ] 发送幂等可用
[ ] webhook 幂等可用
[ ] 域名预热逻辑可用
[ ] 前端页面需要的 API 都有实现或有明确 mock-compatible response
[ ] README 写清本地启动方式
[ ] docs/AGENT_PROGRESS.md 写明完成情况
[ ] docs/ASSUMPTIONS.md 写明所有默认假设
[ ] docs/OPEN_QUESTIONS.md 只保留真正需要用户确认的问题
```

---

## 12. 开始执行

现在开始：

1. 解压 `clientget_backend_blueprint_v2_self_audited.zip`。
2. 按本文第 2 节读取文件。
3. 初始化后端项目。
4. 从 P0 开始实现。
5. 持续写代码、测试、修复，直到第 11 节所有检查项通过。
6. 不要中途停在“下一步建议”。直接继续做下一步。
