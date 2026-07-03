# Design: fix-tenant-warmup-level-hardcode

## Context

`POST /admin/api/v1/tenants` 创建租户时可携带 `sender_domain` + `warmup_level`（D-031），在 `domain_warmup_status` 建立预热初始化行。现状三处硬编码：

- `backend/app/schemas/tenants.py:17`：`warmup_level` Pydantic 约束 `ge=1, le=6`；
- `backend/app/services/tenant_service.py:263-269`：服务层再次钳制 `max(1, min(6, level))`，日限取写死映射 `{1:50, 2:100, 3:200, 4:500, 5:1000, 6:2000}`；
- 初始化 INSERT 只写 `warmup_level` / `daily_limit`，缺 `warmup_rule_id` / `level_changed_at`。

真实档位体系：`warmup_rules`（按 `instance_id` 隔离，`is_active` 标记激活规则，每实例由 `put_warmup_rules` 维护单条激活规则）+ `warmup_rule_levels`（`rule_id, level, daily_limit, …`）。生产激活规则已 19 档。管理端"添加域名"（`admin_config_service.create_tenant_domain:1481-1501`）已按规则表校验并取真实 `daily_limit`，是本次对齐的参照实现。

`domain_warmup_status.daily_limit` 的下游消费：

- `tenant_messaging_service.py:2241-2294`：发送日配额台账（`daily_send_usage`）建行时从该字段取值，直接决定当日可发量；
- `tenant_query_service.py:966-974`：仪表盘每日配额汇总。

DB 层 CHECK 已由迁移 `20260510_0037` 放开为 `warmup_level >= 1`，无 DB 阻碍。

## Goals / Non-Goals

**Goals:**

- 创建租户携带 `sender_domain` 时，档位合法性以**当前实例激活预热规则**的档位表为准（任意档数，不再假设 1-6）；
- `domain_warmup_status` 初始化行的 `daily_limit` 取 `warmup_rule_levels.daily_limit` 真实值，并补写 `warmup_rule_id`、`level_changed_at`，与管理端添加域名口径一致；
- 非法档位显式失败（422），不再静默降档。

**Non-Goals:**

- 不回填存量 `domain_warmup_status` 数据；
- 不写 `domain_warmup_history`；
- 不改管理端添加/更新域名逻辑与前端；
- 不做预热规则缺失时的自动兜底（建规则/默认档位）。

## Decisions

### D1. 校验放在服务层事务内，schema 只放开上限

`TenantCreateRequest.warmup_level` 去掉 `le=6`、保留 `ge=1`；档位存在性在 `tenant_service.create_tenant` 事务内查库校验。

- 理由：`create_tenant` 除 API 外还被 `backend/scripts/seed_demo_data.py` 调用，服务层校验对所有入口生效；档位表是运行时数据，Pydantic 静态约束本就表达不了。
- 备选（API 层查库校验）：否——拆散事务边界，且 seed 入口绕过。

### D2. 由服务端解析"当前实例激活规则"，payload 不新增 rule_id 字段

查询（参数 `instance_id = get_settings().instance_id`，`tenant_service` 已有该依赖）：

```sql
SELECT wr.id AS rule_id, wrl.daily_limit
FROM warmup_rules wr
JOIN warmup_rule_levels wrl ON wrl.rule_id = wr.id
WHERE wr.instance_id = :instance_id
  AND wr.is_active = true
  AND wrl.level = :warmup_level
ORDER BY wr.updated_at DESC
LIMIT 1
```

- 理由：管理端添加域名时用户显式选规则（传 `warmup_rule_id`），而创建租户表单只选档位；每实例单激活规则的语义由 `put_warmup_rules` 维护，服务端解析即可，不给 API 增加冗余字段。`ORDER BY … LIMIT 1` 是对"意外多条激活规则"的确定性防御。
- 备选（payload 增加 `warmup_rule_id`）：否——改 API 契约、前端，超出修复面。

### D3. 查不到即 422 失败，整个租户创建回滚

无激活规则或档位不存在 → `raise AppError(code="VALIDATION_ERROR", status_code=422)`，消息指引检查预热规则配置。异常发生在 `create_tenant` 事务内，租户/用户/模板等前序写入一并回滚，不产生半成品租户。

- 理由：静默降档正是本 bug 根源；参照实现（`create_tenant_domain`）同样 422。
- 备选（回退到 1 档或最近档位继续创建）：否——重现静默错误数据。

### D4. 初始化行补齐 `warmup_rule_id` / `level_changed_at`，保留 `ON CONFLICT DO NOTHING`

INSERT 列扩为 `(id, tenant_id, domain, verification_status, warmup_rule_id, warmup_level, daily_limit, level_changed_at)`，`level_changed_at = now()`。`ON CONFLICT (tenant_id, domain) DO NOTHING` 保留（新租户 id 下冲突实际不可达，幂等保护无害）。

- 理由：与管理端添加域名建立的行口径一致，后续升降档、历史追溯依赖 `warmup_rule_id`。

### D5. 测试用 AsyncMock 序列模拟，不依赖真实 DB

新增 `backend/tests/test_tenant_create_warmup.py`，沿用 `test_domain_crud_service.py` 的模式：`conn.execute = AsyncMock(side_effect=[…])` 按调用序断言 INSERT 参数 / 异常。schema 用例直接实例化 `TenantCreateRequest` 验证 `warmup_level=7` 通过、`0` 拒绝。

- 理由：仓库既有服务层测试均为此风格（无 DB fixture），保持一致。
- 注意：`create_tenant` 的 `conn.execute` 调用序列会因新增档位查询而变化，实施时需确认既有测试（如 `test_tenant_instance_isolation.py`）对该序列的 mock 是否受影响，受影响则同步修正。

## Risks / Trade-offs

- [环境无激活预热规则时，带域名创建租户会 422] → `init_instance.py` / 种子迁移保证每实例一条激活规则，生产 A/B 已有 19 档规则；错误消息明确指引先配置预热规则。不带域名的创建不受影响。
- [行为收紧（BREAKING）：原静默降档成功的请求现在失败] → 已知调用方仅管理端表单（档位选项来自规则接口，不会传不存在档位）与 seed 脚本（3 档，种子规则覆盖）；此收紧正是修复目标。
- [事务内新增一次 SELECT] → 仅 `sender_domain` 非空时执行，单行索引查询，可忽略。
- [多条激活规则的异常数据] → `ORDER BY updated_at DESC LIMIT 1` 保证确定性，行为与 `list_warmup_rules` 排序一致。

## Migration Plan

无数据库迁移。常规后端发布（镜像构建 → Sealos 更新 tag），回滚即回退镜像。前置条件（生产已满足）：各实例存在激活预热规则。

## Open Questions

无——修复方向已明确，关键取舍见 D1-D5。
