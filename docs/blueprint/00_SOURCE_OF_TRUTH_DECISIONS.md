# 00 Source of Truth Decisions（最终实现真源）

本文件解决 `business-flows-v2.html`、00-06 现有系统文档、07-14 设计文档之间的冲突。后续写代码时，若任一原始文档与本文件冲突，以本文件为准。

## 1. 文档优先级

| 优先级 | 文档/目录 | 用途 |
|---|---|---|
| P0 | 本包 `00_SOURCE_OF_TRUTH_DECISIONS.md` 与 `01_final_repaired_docs/*` | 最终实现口径。 |
| P1 | 本包 `03_database/schema.sql`、`04_api/API_CONTRACT.md`、`05_services/*` | 后端落地规格。 |
| P2 | 原始 `07_REQUIREMENTS_SPEC.md`、`08_UI_SPEC.md`、`10_API_DESIGN.md` | 需求与 UI/API 输入。 |
| P3 | `business-flows-v2.html` | 原始需求故事线；其中已被 07/本包修正的矛盾不再采用。 |
| P4 | 原始 00-06 | 旧系统资料与迁移参考，不作为新系统直接实现口径。 |

## 2. 核心修复结论

### 2.1 双应用与 API 前缀

- Admin 前端：平台运营后台。
- Tenant 前端：租户业务后台。
- Admin API：`/admin/api/v1/*`。
- Tenant API：`/t/{slug}/api/v1/*`。
- Internal API：`/internal/api/v1/*`。
- Webhook：`/webhooks/{provider}`。
- **前端路由不承载 slug**；Tenant 登录表单输入 slug，登录后 slug 进入 JWT 与前端 auth store。

### 2.2 角色与身份

Tenant 侧只有三种机器角色：

```text
admin / operator / viewer
```

平台运营身份独立：

```text
platform_admin
```

不要把 `platform_admin` 混入 tenant `user_role` enum。建议新增 `platform_users` 表。

### 2.3 多租户隔离

- Tenant 业务表全部带 `tenant_id` 并启用 RLS。
- shared pool 表（`shared_companies`、`shared_contacts`、`company_sources`）不直接暴露给 app_user。
- Tenant API 必须：path slug → tenant → 校验 JWT tid → `SET LOCAL app.current_tenant_id` → handler 使用同一连接。
- Admin API 使用独立 `admin_pool` 与平台身份，允许绕过 RLS。

### 2.4 公司去重与数据源

- 同源权威去重键：`company_sources(source_type, source_id)`。
- 跨源合并优先级：domain 完全匹配 → name_en 相似度 → 新建公司。
- `source_type` 机器枚举统一为：`waimao_tong / tengdao / lixiaoyun`。
- 前端展示别名：A01/B01/C01 由 `data_sources.alias_code` 提供。

### 2.5 采集服务

- 采集服务独立部署，通过 Internal API 与主系统通信，不引入消息队列。
- 采集任务按 `(keyword_normalized, countries_hash, source_types)` 聚合。
- 采集服务不得传入并决定 tenant_ids；主系统必须基于本地 `collection_task_keywords` 反解归属。
- `lease_id` 是执行资格，不是普通字段。claim / heartbeat / submit_result 必须校验 lease。

### 2.6 评分

- 新评分：规则为主 + LLM 辅助维度。
- 评级：S/A/B/C/D。
- 励销云反查得到的精准客户默认 S 级，但仍应产生评分记录，标注 `is_precise_customer=true`。
- 余额不足时：纯规则维度照常；LLM 维度置为 pending，`company_scores.llm_pending=true` 或任务进入待补评队列。

### 2.7 邮件与发送计划

旧系统 `email_plans` 的 9 状态流水线废弃。新系统：

- `sending_plans` 只管理发送。
- `sequence_steps` 管理序列步骤。
- `sequence_enrollments` 管理每个收件人的执行状态。
- `sending_plan_recipients` 是收件人快照 + append-only 新增。
- 分区表 `emails` 不能单靠 unique 保证幂等；必须新增非分区幂等表 `email_send_locks`。

### 2.8 AI 计费

统一采用预授权状态机：

```text
authorized -> provider_called -> settled_exact / settled_charge / settled_release
             \-> released_full when provider failed with no billable output
```

实现要求：

1. 调用前冻结/预扣估算金额。
2. Provider 成功后按真实 usage 结算。
3. 实际费用 > 预授权，补扣差额；实际费用 < 预授权，释放差额。
4. Provider 失败且无有效输出，释放全部预授权。
5. 已有 provider 响应但本地结算失败时，只能重试结算，禁止再次调用模型。

### 2.9 域名预热

最终采用动态指标驱动 6 档，而不是固定天数。默认档位：

```text
50 / 100 / 200 / 500 / 1000 / 4000 封/天
```

晋升条件由 `warmup_rule_levels` 配置：送达率、退信率、投诉率、最低停留天数。若 Owner 另行确认，可调整默认值。

### 2.10 Phase 1 支付

Phase 1 不实现租户自助支付。AI 余额由平台运营在 Admin 端手动充值。若 UI 原型出现自助充值入口，后端先返回能力态 `self_recharge_available=false`。

### 2.11 EngageLab inbound/reply

EngageLab 是否支持 inbound 邮件解析仍需确认。Phase 1 默认实现：

- outbound send；
- delivery/open/click/bounce/unsubscribe webhook；
- reply 事件若 provider 支持则入库；若不支持，系统显示“回复处理待接入”。

## 3. 默认技术栈

| 层 | 选择 |
|---|---|
| Backend | Python 3.11+ + FastAPI + Pydantic v2 |
| DB | PostgreSQL 16+ + RLS + Alembic |
| Async DB | asyncpg 或 SQLAlchemy 2.0 async |
| Auth | JWT HS256 Phase 1，24h，无 refresh token |
| Password | bcrypt/argon2id，禁止默认密码留存 |
| AI | OpenRouter OpenAI-compatible API |
| Mail | EngageLab |
| Collection | Python async service + Internal API |
| Tests | pytest + pytest-asyncio + httpx AsyncClient |

