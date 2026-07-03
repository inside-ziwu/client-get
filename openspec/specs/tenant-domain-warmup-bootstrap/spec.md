# tenant-domain-warmup-bootstrap Specification

## Purpose

创建租户时发件域名预热记录（`domain_warmup_status`）的初始化能力：档位以当前实例激活预热规则（`warmup_rules` + `warmup_rule_levels`）为准，日发送上限取档位表真实值，初始化行与管理端"添加域名"口径一致。硬编码档位（1-6）与日限映射的修复决策见归档 change `fix-tenant-warmup-level-hardcode`。

## Requirements

### Requirement: 创建租户携带发件域名时档位 MUST 对照当前实例激活预热规则校验

创建租户（`POST /admin/api/v1/tenants`，请求体含 `sender_domain` 非空、`warmup_level`）时，系统 MUST 在当前实例（`instance_id`）的激活预热规则（`warmup_rules.is_active = true`）的档位表（`warmup_rule_levels`）中校验 `warmup_level` 存在；系统 MUST NOT 对档位做静默钳制或降档。校验与写入 MUST 在同一数据库事务内完成。

请求字段：`warmup_level` 为正整数（≥1），上限不再固定为 6，以激活规则实际档位为准；`sender_domain` 为空时 `warmup_level` 被忽略。

#### Scenario: 选择激活规则中存在的高档位（如 19 档规则的 7 档）

- **GIVEN** 当前实例激活预热规则包含 7 档（`warmup_rule_levels` 存在 `level = 7`）
- **WHEN** 创建租户请求携带 `sender_domain = "mail.example.com"`、`warmup_level = 7`
- **THEN** 租户创建成功，`domain_warmup_status` 初始化行的 `warmup_level = 7`

#### Scenario: 档位在激活规则中不存在

- **GIVEN** 当前实例激活预热规则不含 99 档
- **WHEN** 创建租户请求携带 `sender_domain` 且 `warmup_level = 99`
- **THEN** 返回 422（错误码 `VALIDATION_ERROR`，响应为统一错误 JSON，消息指引检查预热规则配置），且不写入 `domain_warmup_status`，租户创建整体回滚（不产生半成品租户）

#### Scenario: 当前实例无激活预热规则

- **GIVEN** 当前实例不存在 `is_active = true` 的预热规则
- **WHEN** 创建租户请求携带 `sender_domain`
- **THEN** 返回 422（错误码 `VALIDATION_ERROR`），租户创建整体回滚

#### Scenario: 不携带发件域名时不做档位校验

- **WHEN** 创建租户请求 `sender_domain` 为空（缺省或空串）
- **THEN** 不查询预热规则、不写入 `domain_warmup_status`，租户正常创建

### Requirement: 预热初始化行 MUST 记录激活规则关联与真实日限

`sender_domain` 非空且档位校验通过时，系统写入 `domain_warmup_status` 初始化行 MUST 满足：`daily_limit` 取激活规则该档位的 `warmup_rule_levels.daily_limit`（MUST NOT 使用任何硬编码日限映射）；`warmup_rule_id` MUST 记录为激活规则 id；`level_changed_at` MUST 记录为写入时刻；`verification_status` 保持 `pending`。

#### Scenario: 日限取自档位表真实值

- **GIVEN** 激活规则 7 档的 `daily_limit = 8000`
- **WHEN** 创建租户携带 `sender_domain`、`warmup_level = 7` 成功
- **THEN** 初始化行 `daily_limit = 8000`、`warmup_rule_id` 为激活规则 id、`level_changed_at` 非空，后续发送日配额台账按 8000 取值

#### Scenario: 同一激活规则不同档位取各自日限（边界：最低档）

- **GIVEN** 激活规则 1 档的 `daily_limit = 50`
- **WHEN** 创建租户携带 `sender_domain`、`warmup_level = 1`（缺省值）成功
- **THEN** 初始化行 `daily_limit = 50`，而非硬编码映射值

### Requirement: 创建租户请求 schema SHALL 不再固定档位上限

`TenantCreateRequest.warmup_level` SHALL 仅约束为 ≥1 的整数（缺省 1），SHALL NOT 以 Pydantic 常量上限（`le=6`）拒绝高档位；档位存在性由服务层按激活规则校验。

#### Scenario: 高档位通过请求校验进入服务层

- **WHEN** 请求体 `warmup_level = 7`
- **THEN** 请求 schema 校验通过（是否成功由服务层档位校验决定）

#### Scenario: 非法档位仍被 schema 拒绝（边界）

- **WHEN** 请求体 `warmup_level = 0` 或负数
- **THEN** 请求 schema 校验失败（422），不进入服务层
