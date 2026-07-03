## 前提假设

本方案基于以下前提假设：

1. **实例间无强密码学隔离**：两个实例通过独立的 `CLIENTGET_JWT_SECRET` 环境变量配置各自的 JWT 密钥。iid claim 作为纵深防御，但核心安全边界是密钥隔离。
2. **Instance B 使用独立域名**：Instance B 不使用 `.xinanpcb.com` 子域名，Cookie 天然隔离，不存在 refresh_token cookie 跨实例共享风险。
3. **两实例使用不同 EngageLab 账户**：各自配置独立的 API 凭证和 webhook URL，邮件回调天然按实例隔离。
4. **管理员邮箱全局唯一**：`platform_users.email` 保持 `UNIQUE(email)` 全局约束。同一个人管理两套实例需使用不同邮箱。理由：避免"这个管理员到底属于哪个实例"的混淆，且管理员池极小（<10 人），使用邮箱别名即可覆盖需求。

---

## ADDED Requirements

### Requirement: 后端 SHALL 通过环境变量识别当前实例

系统 MUST 从环境变量 `CLIENTGET_INSTANCE_ID` 读取当前实例标识（`str`，默认值 `"default"`），在 `Settings` 类中以 `instance_id` 属性暴露。该值在进程生命周期内不变。

系统 MUST 从环境变量 `CLIENTGET_JWT_SECRET` 读取当前实例的 JWT 密钥。每个实例 MUST 配置独立的密钥值。

#### Scenario: 环境变量已设置

- **GIVEN** 环境变量 `CLIENTGET_INSTANCE_ID=instance_b`
- **WHEN** 后端启动并读取配置
- **THEN** `get_settings().instance_id` 返回 `"instance_b"`

#### Scenario: 环境变量未设置

- **GIVEN** 环境变量 `CLIENTGET_INSTANCE_ID` 未设置
- **WHEN** 后端启动并读取配置
- **THEN** `get_settings().instance_id` 返回 `"default"`

---

### Requirement: 管理员登录 SHALL 按 instance_id 过滤

`platform_login` MUST 在查询 `platform_users` 时加 `WHERE instance_id = :instance_id` 条件，只匹配当前实例的管理员。

#### Scenario: 本实例管理员登录成功

- **GIVEN** Instance A（`INSTANCE_ID=default`）存在管理员 admin@example.com
- **WHEN** 在 Instance A 的后端调用 `POST /admin/api/v1/auth/login`，提供正确的 email 和 password
- **THEN** 登录成功，返回 access_token 和 refresh_token

#### Scenario: 其他实例管理员无法登录

- **GIVEN** 管理员 admin@example.com 属于 Instance A（`instance_id=default`）
- **WHEN** 在 Instance B（`INSTANCE_ID=instance_b`）的后端调用 `POST /admin/api/v1/auth/login`，提供相同的 email 和 password
- **THEN** 返回 401，错误码 `INVALID_CREDENTIALS`

---

### Requirement: 租户登录 SHALL 按 instance_id 过滤

`tenant_login` MUST 在查询 `tenants` 时加 `WHERE t.instance_id = :instance_id` 条件，只匹配当前实例的租户。

#### Scenario: 本实例租户用户登录成功

- **GIVEN** Instance A 存在租户 slug=demo，该租户下有用户 user@example.com
- **WHEN** 在 Instance A 的后端调用 `POST /api/v1/auth/login?slug=demo`
- **THEN** 登录成功，返回 access_token

#### Scenario: 同名 slug 在不同实例互不干扰

- **GIVEN** Instance A 和 Instance B 各有一个 slug=demo 的租户，各自有不同的用户
- **WHEN** 在 Instance B 的后端调用 `POST /api/v1/auth/login?slug=demo`，使用 Instance B 租户的用户凭证
- **THEN** 登录成功，token 中 `tid` 为 Instance B 的租户 ID

#### Scenario: 其他实例租户无法登录

- **GIVEN** 租户 slug=demo 只存在于 Instance A
- **WHEN** 在 Instance B 的后端调用 `POST /api/v1/auth/login?slug=demo`
- **THEN** 返回 401，错误码 `INVALID_CREDENTIALS`

---

### Requirement: JWT token SHALL 包含 instance_id claim

`create_access_token`、`create_refresh_token` 和 `create_service_token` MUST 在 claims 中加入 `iid` 字段，值为当前后端的 `instance_id`。

#### Scenario: access_token 包含 iid

- **GIVEN** 后端 `INSTANCE_ID=instance_b`
- **WHEN** 管理员或租户用户登录成功
- **THEN** 签发的 access_token 解码后包含 `"iid": "instance_b"`

#### Scenario: refresh_token 包含 iid

- **GIVEN** 后端 `INSTANCE_ID=default`
- **WHEN** 管理员登录成功
- **THEN** 签发的 refresh_token 解码后包含 `"iid": "default"` 和 `"type": "refresh"`

#### Scenario: service_token 包含 iid

- **GIVEN** 后端 `INSTANCE_ID=instance_b`
- **WHEN** Worker 签发 service token
- **THEN** service_token 解码后包含 `"iid": "instance_b"` 和 `"kind": "service"`

---

### Requirement: 认证中间件 SHALL 校验 token 的 instance_id

`get_current_platform_user`、`get_current_tenant_user` 和 `get_current_service` MUST 校验 token 中的 `iid` 与当前后端 `instance_id` 一致，不一致时返回 403。

`get_current_platform_user` 的 DB 查询 MUST 加 `AND instance_id = :instance_id` 条件，作为纵深防御。

#### Scenario: token 实例匹配

- **GIVEN** 后端 `INSTANCE_ID=default`，用户持有 `iid=default` 的 token
- **WHEN** 调用任意需要认证的 API
- **THEN** 认证通过，正常处理请求

#### Scenario: token 实例不匹配

- **GIVEN** 后端 `INSTANCE_ID=instance_b`，用户持有 `iid=default` 的 token
- **WHEN** 调用任意需要认证的 API
- **THEN** 返回 403，错误码 `FORBIDDEN`，消息提示实例不匹配

#### Scenario: service token 实例不匹配

- **GIVEN** 后端 `INSTANCE_ID=instance_b`，Worker 持有 `iid=default` 的 service token
- **WHEN** 调用 internal API
- **THEN** 返回 403，错误码 `FORBIDDEN`

---

### Requirement: refresh 端点 SHALL 校验 iid 并按 instance_id 过滤

`POST /admin/api/v1/auth/refresh` MUST：
1. 校验 refresh_token 中的 `iid` 与当前后端 `instance_id` 一致
2. 查询 `platform_users` 时加 `AND instance_id = :instance_id` 条件
3. 签发新 access_token 时注入当前实例的 `iid` claim

#### Scenario: 有效 refresh token 且实例匹配

- **GIVEN** 用户持有未过期的 refresh_token，且 `iid` 与当前实例匹配
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 200，body 包含新的 `access_token`（含 `iid` claim）

#### Scenario: refresh token 实例不匹配

- **GIVEN** 用户持有 `iid=default` 的 refresh_token，但当前后端 `INSTANCE_ID=instance_b`
- **WHEN** 调用 `POST /admin/api/v1/auth/refresh`
- **THEN** 返回 403，拒绝签发新 token

---

### Requirement: Internal API SHALL 按 instance_id 过滤

以下 internal API 端点 MUST 在查询时通过 `JOIN tenants ON tenants.instance_id = :instance_id` 限制候选租户：
- `POST /internal/api/v1/sending/due-emails/claim` — 领取待发邮件
- `GET /internal/api/v1/collection/credentials/{source_type}` — 获取采集凭证（按 instance_id 过滤 `data_source_credentials`）

Service token 认证 MUST 校验 `iid` claim。

#### Scenario: Internal API 只返回本实例数据

- **GIVEN** Instance A 和 Instance B 各有待发邮件
- **WHEN** Instance B 的 Worker 通过 service token 调用 `POST /internal/api/v1/sending/due-emails/claim`
- **THEN** 只返回 Instance B 的待发邮件

#### Scenario: 跨实例 service token 被拒绝

- **GIVEN** Instance A 的 service token（`iid=default`）
- **WHEN** 发送到 Instance B 的 internal API
- **THEN** 返回 403

---

### Requirement: 管理端租户 API SHALL 按 instance_id 过滤

以下管理端 API MUST 在查询和创建时绑定当前实例的 `instance_id`：
- `list_tenants` — 只返回当前实例的租户
- `get_tenant` — 校验租户属于当前实例
- `create_tenant` — 创建时设置 `instance_id`
- `update_tenant` — 校验租户属于当前实例

#### Scenario: 列出租户只显示当前实例

- **GIVEN** Instance A 有 3 个租户，Instance B 有 2 个租户
- **WHEN** 在 Instance B 的管理端调用 `GET /admin/api/v1/tenants`
- **THEN** 只返回 Instance B 的 2 个租户

#### Scenario: 创建租户绑定当前实例

- **GIVEN** 后端 `INSTANCE_ID=instance_b`
- **WHEN** 管理端调用 `POST /admin/api/v1/tenants` 创建新租户
- **THEN** 新租户的 `instance_id` 为 `instance_b`

#### Scenario: 无法操作其他实例的租户

- **GIVEN** 租户 X 属于 Instance A
- **WHEN** Instance B 的管理端调用 `GET /admin/api/v1/tenants/{tenant_x_id}`
- **THEN** 返回 404

---

### Requirement: 管理端平台用户 API SHALL 按 instance_id 过滤

`list_platform_users` 和 `create_platform_user` MUST 绑定当前实例的 `instance_id`。

#### Scenario: 列出管理员只显示当前实例

- **GIVEN** Instance A 有 2 个管理员，Instance B 有 1 个管理员
- **WHEN** 在 Instance B 的管理端调用列出管理员
- **THEN** 只返回 Instance B 的 1 个管理员

#### Scenario: 创建管理员绑定当前实例

- **GIVEN** 后端 `INSTANCE_ID=instance_b`
- **WHEN** 管理端创建新管理员
- **THEN** 新管理员的 `instance_id` 为 `instance_b`

---

### Requirement: 管理端平台配置 API SHALL 按 instance_id 过滤

以下平台配置的 CRUD 操作 MUST 绑定当前实例的 `instance_id`：
- `warmup_rules`（子表 `warmup_rule_levels` 通过 `rule_id` FK 关联，不需要独立的 `instance_id` 列）
- `platform_scoring_templates`（子表 `platform_scoring_template_versions` 通过 FK 关联，不需要独立的 `instance_id` 列）
- `platform_email_templates`
- `ai_models` 及 `ai_scene_defaults`
- `data_sources` 及 `data_source_credentials`

`_sync_platform_template_to_tenants` MUST 只同步当前实例的租户。

#### Scenario: 列出预热规则只显示当前实例

- **GIVEN** Instance A 有 2 套预热规则，Instance B 有 1 套
- **WHEN** 在 Instance B 的管理端查看预热规则
- **THEN** 只返回 Instance B 的 1 套

#### Scenario: 创建平台配置绑定当前实例

- **GIVEN** 后端 `INSTANCE_ID=instance_b`
- **WHEN** 管理端创建新的评分模板
- **THEN** 模板的 `instance_id` 为 `instance_b`

#### Scenario: 模板同步仅影响本实例租户

- **GIVEN** Instance A 有 3 个租户，Instance B 有 2 个租户
- **WHEN** Instance B 修改平台评分模板并触发同步
- **THEN** 只有 Instance B 的 2 个租户收到更新

---

### Requirement: 管理端 Dashboard SHALL 只统计当前实例

`get_platform_dashboard` MUST 只统计当前实例的以下指标：
- 租户总数、活跃租户数
- 用户总数
- 发送计划数（running/completed）
- 邮件发送总量
- 域名数及预热状态分布

所有涉及 `tenants`、`users`、`sending_plans`、`emails`、`domain_warmup_status` 的统计查询 MUST 通过 `tenants.instance_id` 或直接 `instance_id` 过滤。

#### Scenario: Dashboard 数据按实例隔离

- **GIVEN** Instance A 有 10 个租户，Instance B 有 3 个租户
- **WHEN** Instance B 的管理端查看 Dashboard
- **THEN** 显示租户数 3（非 13）

---

### Requirement: Worker SHALL 只处理当前实例的租户任务

Worker 通过 `CLIENTGET_INSTANCE_ID` 环境变量获取实例标识。以下查询 MUST 通过 `JOIN tenants ON tenants.instance_id = :instance_id` 限制候选租户：
- `list_running_domain_ids` — sending_worker（邮件发送）
- `claim_due_emails` — sending_worker（邮件发送）
- `recover_stale_locks` — sending_worker（释放超时锁时只操作本实例的锁）
- `reconcile_once` — reconciliation_worker（邮件状态同步）
- `wmt_lineage_repair` fan-out 查询 — wmt_lineage_repair_worker（数据修复）

#### Scenario: 邮件 Worker 只发送本实例邮件

- **GIVEN** Instance A 有 sending_plan P1（running），Instance B 有 sending_plan P2（running）
- **WHEN** Instance B 的 sending_worker 执行 `list_running_domain_ids`
- **THEN** 只返回 P2 关联的 domain_id

#### Scenario: 邮件状态同步只处理本实例

- **GIVEN** Instance A 和 Instance B 各有 stuck 邮件
- **WHEN** Instance B 的 reconciliation_worker 执行 `reconcile_once`
- **THEN** 只处理 Instance B 的 stuck 邮件

#### Scenario: 数据修复只扫描本实例租户

- **GIVEN** Instance A 有 5 个 active 租户，Instance B 有 2 个 active 租户
- **WHEN** Instance B 的 wmt_lineage_repair_worker 执行 fan-out
- **THEN** 只对 Instance B 的 2 个租户执行修复

#### Scenario: 释放超时锁只操作本实例

- **GIVEN** Instance A 和 Instance B 各有 stale email_send_locks
- **WHEN** Instance B 的 sending_worker 执行 `recover_stale_locks`
- **THEN** 只释放 Instance B 租户的 stale locks

---

### Requirement: advisory lock SHALL 区分实例隔离与全局互锁

Worker 中存在两类 advisory lock，MUST 区分处理：

1. **实例级 lock**（如 `wmt_lineage_repair` 的全局修复锁）：lock key MUST 包含 instance_id 信息（使用 `pg_catalog.hashtext(instance_id)` 与原始 lock key 组合），避免不同实例的 Worker 互相阻塞。
2. **全局 lock**（如 `tenant_ops_service` 保护 clean_companies 去重的 lock）：MUST 保持全局互锁，不加 instance_id 区分——因为 clean_* 表是跨实例共享的，两个实例同时写入同一公司时需要互锁防止重复。

#### Scenario: 实例级 lock 不互锁

- **GIVEN** Instance A 和 Instance B 各跑一个 wmt_lineage_repair Worker
- **WHEN** 两个 Worker 同时尝试获取 advisory lock
- **THEN** 各自获取各自的 lock，互不阻塞

#### Scenario: 全局 lock 跨实例互锁

- **GIVEN** Instance A 和 Instance B 的 Worker 同时尝试写入同一个 clean_company
- **WHEN** 两个 Worker 同时尝试获取 tenant_ops 的 advisory lock（相同 lock_key）
- **THEN** 只有一个获取成功，另一个等待——保证去重正确性

---

### Requirement: 数据库迁移 SHALL 保持向后兼容

数据库迁移 SHALL 保持向后兼容：迁移一步完成，为所有需要隔离的表添加 `instance_id TEXT NOT NULL DEFAULT 'default'` 列。PostgreSQL 11+ 对有 DEFAULT 的 ADD COLUMN 不需要 table rewrite，现有行自动获得默认值 `'default'`，现有代码的 INSERT 不指定 instance_id 时也会由 DEFAULT 填充。

同一迁移中 MUST 变更以下唯一约束和索引：

| 表 | 原约束 | 新约束 |
|----|--------|--------|
| `tenants` | `UNIQUE(slug)` | `UNIQUE(instance_id, slug)` |
| `warmup_rules` | `UNIQUE INDEX (is_active) WHERE is_active` | `UNIQUE INDEX (instance_id) WHERE is_active` |
| `platform_scoring_templates` | `UNIQUE INDEX (industry) WHERE is_active` | `UNIQUE INDEX (instance_id, industry) WHERE is_active` |
| `ai_scene_defaults` | `UNIQUE(scene)` | `UNIQUE(instance_id, scene)` |
| `data_sources` | `UNIQUE(source_type)` | `UNIQUE(instance_id, source_type)` |
| `data_source_credentials` | FK `REFERENCES data_sources(source_type)` | 重建 FK 为 `REFERENCES data_sources(id)` 或通过 `(instance_id, source_type)` 复合 FK |
| `ai_models` | `UNIQUE(provider, model_id)` | `UNIQUE(instance_id, provider, model_id)` |

不需要加 `instance_id` 的子表（通过 FK 关联父表隔离）：
- `warmup_rule_levels`（通过 `rule_id` FK 关联 `warmup_rules`）
- `platform_scoring_template_versions`（通过 FK 关联 `platform_scoring_templates`）

#### Scenario: 迁移不影响现有代码

- **GIVEN** 当前生产环境运行旧版本代码
- **WHEN** 执行迁移
- **THEN** 所有现有功能正常运行，新列有默认值 `'default'`，唯一约束已更新

---

### Requirement: Instance B 初始管理员 SHALL 通过初始化脚本创建

系统 MUST 提供一个独立 Python 脚本（非 Alembic 迁移），为 Instance B 插入第一个 `platform_user`（`instance_id='instance_b'`），以及完整的平台配置初始数据（warmup_rules、platform_scoring_templates 等）。

管理员密码 MUST 通过环境变量 `INIT_ADMIN_PASSWORD` 注入，不得硬编码在脚本中。

#### Scenario: Instance B 初始化后可登录

- **GIVEN** 初始化脚本已执行，环境变量 `INIT_ADMIN_PASSWORD` 已设置，Instance B 的管理员 admin@sales.example.com 已创建
- **WHEN** 在 Instance B 的管理端登录
- **THEN** 登录成功，Dashboard 显示 0 个租户

#### Scenario: Instance B 有完整的平台配置

- **GIVEN** Instance B 初始化脚本已执行
- **WHEN** Instance B 管理员创建第一个租户并配置域名
- **THEN** 可正常选择预热规则、评分模板等平台配置

#### Scenario: 密码未通过环境变量提供时脚本拒绝运行

- **GIVEN** 环境变量 `INIT_ADMIN_PASSWORD` 未设置
- **WHEN** 运行初始化脚本
- **THEN** 脚本报错退出，不创建任何数据
