---
title: "feat: 多实例部署——共享数据库、独立账户体系"
type: feat
date: 2026-06-25
origin: openspec/changes/multi-instance-deployment/specs/instance-isolation/spec.md
---

# feat: 多实例部署——共享数据库、独立账户体系

## Summary

在同一 PostgreSQL 数据库上支持多个独立实例，每个实例有独立的账户体系（platform_users、tenants）、平台配置（warmup_rules、ai_models 等）和 Worker。全局数据池（clean_companies、keyword_master）跨实例共享。通过独立 JWT_SECRET + iid claim 纵深防御实现 token 隔离。

## Problem Frame

系统已稳定运行，现需为新运营团队部署第二套实例（Instance B）。两套实例共享底层数据（采集到的公司/联系人），但账户和平台配置完全独立——Instance B 从零开始，不继承 Instance A 的任何管理员、租户或配置数据。

---

## Requirements

**账户与认证隔离**

- R1. 后端通过 `CLIENTGET_INSTANCE_ID` 环境变量识别当前实例，默认值 `"default"`
- R2. 每个实例配置独立的 `CLIENTGET_JWT_SECRET`
- R3. 管理员登录按 instance_id 过滤 platform_users
- R4. 租户登录按 instance_id 过滤 tenants
- R5. JWT access_token、refresh_token、service_token 均包含 `iid` claim
- R6. 认证中间件（platform、tenant、service）校验 `iid` 一致性，DB 查询加 instance_id 纵深防御
- R7. refresh 端点校验 iid + DB 查询按 instance_id 过滤

**管理端 API 隔离**

- R8. 租户管理 API（list/get/create/update）绑定 instance_id
- R9. 平台用户管理 API 绑定 instance_id
- R10. 平台配置 API（warmup_rules、scoring_templates、email_templates、ai_models、ai_scene_defaults、data_sources、data_source_credentials）绑定 instance_id
- R11. Dashboard 统计只计当前实例
- R12. 模板同步只影响当前实例租户

**Worker 与 Internal API 隔离**

- R13. Worker 查询（list_running_domain_ids、claim_due_emails、recover_stale_locks、reconcile_once、wmt_lineage_repair fan-out）通过 tenants.instance_id 限制
- R14. Internal API（claim_due_emails、collection_credentials）按 instance_id 过滤，service token 校验 iid
- R15. advisory lock 区分实例级（加 instance_id hash）和全局（保持互锁）

**数据库与初始化**

- R16. 一步迁移：10 张表加 `instance_id TEXT NOT NULL DEFAULT 'default'`，变更所有 UNIQUE/partial unique index/FK
- R17. 初始化脚本创建 Instance B 管理员（密码通过 `INIT_ADMIN_PASSWORD` 环境变量注入）+ 完整平台配置

---

## Key Technical Decisions

- KTD1. **独立 JWT_SECRET 而非共享**：密码学层面隔离 token，即使 iid 校验遗漏也无法跨实例使用。环境变量 `CLIENTGET_JWT_SECRET` 取代原 `JWT_SECRET`。
- KTD2. **子表不加 instance_id**：`warmup_rule_levels`、`platform_scoring_template_versions` 始终通过 FK JOIN 父表，无独立查询场景，冗余列增加维护成本。
- KTD3. **一步迁移而非两步**：PG 11+ ADD COLUMN with DEFAULT 是 metadata-only，不需要 table rewrite，无需 nullable 中间态。
- KTD4. **advisory lock 分两类**：实例级 lock（wmt_lineage_repair）用 `pg_catalog.hashtext(instance_id)` 组合 lock key；全局 lock（tenant_ops_service 保护 clean_* 去重）保持互锁。
- KTD5. **platform_users.email 保持全局唯一**：管理员池极小，邮箱别名可覆盖需求，避免"哪个实例的管理员"混淆。
- KTD6. **测试策略**：所有 instance_id 隔离测试用 AsyncMock 模拟 DB，通过 `get_settings()` mock 注入不同 instance_id，验证 SQL 参数包含正确的 instance_id 值。

---

## Scope Boundaries

### Deferred to Follow-Up Work

- 前端代码改动（前端只需指向不同后端 URL）
- 实例生命周期管理（退役、租户迁移、实例枚举）
- 数据库层面 RLS 强制 instance_id 隔离
- cookie domain 可配置化（当前通过前提假设——Instance B 使用独立域名——规避）

---

## Implementation Units

### U1. Settings 类添加 instance_id 配置

**Goal:** 后端通过环境变量读取 instance_id（R1）

**Files:** `backend/app/core/config.py`, `backend/tests/test_instance_config.py`

**Approach:** 在 Settings 类添加 `instance_id: str = Field(default="default", alias="CLIENTGET_INSTANCE_ID")`

**Execution note:** TDD——先写测试验证默认值和自定义值

**Test scenarios:**
1. 未设置 `CLIENTGET_INSTANCE_ID` 时，`get_settings().instance_id` 返回 `"default"`
2. 设置 `CLIENTGET_INSTANCE_ID=instance_b` 时，返回 `"instance_b"`

**Verification:** 测试通过，`get_settings().instance_id` 可用

---

### U2. JWT_SECRET 改为每实例独立

**Goal:** 每个实例配置独立的 JWT 密钥（R2）

**Dependencies:** U1

**Files:** `backend/app/core/config.py`, `backend/tests/test_instance_config.py`

**Approach:** 将 `jwt_secret` 的 alias 改为 `CLIENTGET_JWT_SECRET`，保留原 `JWT_SECRET` 作为 fallback（`validation_alias=AliasChoices`）

**Test scenarios:**
1. 设置 `CLIENTGET_JWT_SECRET` 时使用新值
2. 仅设置 `JWT_SECRET` 时向后兼容
3. 两者都设置时 `CLIENTGET_JWT_SECRET` 优先

**Verification:** 测试通过，conftest.py 中的 `JWT_SECRET` 仍可用

---

### U3. create_access_token 注入 iid claim

**Goal:** access_token 包含 instance_id（R5 部分）

**Dependencies:** U1

**Files:** `backend/app/security/jwt.py`, `backend/tests/test_jwt.py`

**Approach:** `create_access_token` 内部从 `get_settings().instance_id` 读取并注入 `iid` 到 payload

**Execution note:** TDD——先在 test_jwt.py 添加测试

**Test scenarios:**
1. 生成的 access_token 解码后包含 `"iid"` 字段
2. `iid` 值与 `get_settings().instance_id` 一致
3. 调用方传入的 claims 中已有 `iid` 时不被覆盖（防御性检查：应被覆盖还是报错？选择覆盖——服务端 instance_id 为准）

**Verification:** test_jwt.py 全部通过

---

### U4. create_refresh_token 注入 iid claim

**Goal:** refresh_token 包含 instance_id（R5 部分）

**Dependencies:** U1

**Files:** `backend/app/security/jwt.py`, `backend/tests/test_jwt.py`

**Approach:** 同 U3，在 create_refresh_token 中注入 `iid`

**Test scenarios:**
1. 生成的 refresh_token 解码后包含 `"iid"` 和 `"type": "refresh"`
2. `iid` 值与 settings.instance_id 一致

**Verification:** test_jwt.py 全部通过

---

### U5. service token 注入 iid claim

**Goal:** service_token 包含 instance_id（R5 部分）

**Dependencies:** U1

**Files:** `backend/app/security/jwt.py`, `backend/tests/test_jwt.py`

**Approach:** service token 使用 `create_access_token` 生成（当前代码模式），U3 的改动自动覆盖。本单元验证 service token 场景。

**Test scenarios:**
1. 用 `{"kind": "service", "service_name": "sending-worker", "scopes": [...]}` 生成的 token 解码后包含 `iid`

**Verification:** test_jwt.py 通过

---

### U6. get_current_platform_user 校验 iid

**Goal:** 平台管理员认证中间件校验 token 的 instance_id（R6 部分）

**Dependencies:** U3

**Files:** `backend/app/security/dependencies.py`, `backend/tests/test_auth_instance_isolation.py`

**Approach:** 解码 token 后校验 `payload.get("iid") == get_settings().instance_id`，不一致返回 403。DB 查询加 `AND instance_id = :instance_id`。

**Execution note:** TDD——新建 test_auth_instance_isolation.py

**Test scenarios:**
1. token 的 iid 与当前实例匹配 → 认证通过
2. token 的 iid 与当前实例不匹配 → 返回 403 FORBIDDEN
3. token 缺少 iid 字段 → 返回 403（向后兼容过渡期可考虑宽松，但 spec 要求严格）
4. DB 查询参数包含 `instance_id`

**Verification:** 测试通过，现有 test_auth_refresh.py 不受影响（conftest 设置默认 instance_id）

---

### U7. get_current_tenant_user 校验 iid

**Goal:** 租户用户认证中间件校验 token 的 instance_id（R6 部分）

**Dependencies:** U3

**Files:** `backend/app/security/dependencies.py`, `backend/tests/test_auth_instance_isolation.py`

**Approach:** 同 U6，在 tenant 认证路径中校验 iid

**Test scenarios:**
1. token 的 iid 匹配 → 认证通过
2. token 的 iid 不匹配 → 返回 403

**Verification:** 测试通过

---

### U8. require_service_scopes 校验 iid

**Goal:** service token 认证校验 instance_id（R6、R14 部分）

**Dependencies:** U5

**Files:** `backend/app/security/internal.py`, `backend/tests/test_auth_instance_isolation.py`

**Approach:** 在 `require_service_scopes` 解码 token 后校验 `iid`

**Test scenarios:**
1. service token 的 iid 匹配 → 认证通过
2. service token 的 iid 不匹配 → 返回 403

**Verification:** 测试通过

---

### U9. platform_login 按 instance_id 过滤

**Goal:** 管理员登录只匹配当前实例（R3）

**Dependencies:** U1

**Files:** `backend/app/services/auth_service.py`, `backend/tests/test_auth_login.py`

**Approach:** `platform_login` 的 SQL 加 `AND instance_id = :instance_id`，参数从 `get_settings().instance_id` 读取

**Execution note:** TDD——在 test_auth_login.py 中添加 instance_id 隔离测试

**Test scenarios:**
1. 查询 SQL 的参数字典包含 `instance_id` 键
2. 本实例管理员 → 登录成功
3. 管理员存在但 instance_id 不匹配 → 返回 401 INVALID_CREDENTIALS

**Verification:** test_auth_login.py 全部通过

---

### U10. tenant_login 按 instance_id 过滤

**Goal:** 租户登录只匹配当前实例（R4）

**Dependencies:** U1

**Files:** `backend/app/services/auth_service.py`, `backend/tests/test_auth_login.py`

**Approach:** `tenant_login` 的 SQL 加 `AND t.instance_id = :instance_id`

**Test scenarios:**
1. 查询 SQL 的参数字典包含 `instance_id` 键
2. 本实例租户用户 → 登录成功
3. 租户存在但 instance_id 不匹配 → 返回 401

**Verification:** test_auth_login.py 全部通过

---

### U11. refresh 端点校验 iid + instance_id 过滤

**Goal:** refresh 流程完整的实例隔离（R7）

**Dependencies:** U4, U6

**Files:** `backend/app/api/admin/auth.py`, `backend/tests/test_auth_refresh.py`

**Approach:** 
1. `decode_refresh_token` 后校验 `iid` 与当前实例匹配
2. 查询 `platform_users` 时加 `AND instance_id = :instance_id`
3. `create_access_token` 已自动注入 `iid`（U3）

**Test scenarios:**
1. 有效 refresh_token 且 iid 匹配 → 返回新 access_token（含 iid）
2. refresh_token 的 iid 不匹配 → 返回 403
3. DB 查询参数包含 instance_id

**Verification:** test_auth_refresh.py 全部通过

---

### U12. Alembic 迁移——添加 instance_id 列

**Goal:** 10 张表添加 instance_id 列（R16 部分）

**Dependencies:** 无

**Files:** `backend/alembic/versions/YYYYMMDD_HHMM_add_instance_id.py`

**Approach:** 单个迁移文件，为 `platform_users`、`tenants`、`warmup_rules`、`platform_scoring_templates`、`platform_email_templates`、`ai_models`、`ai_scene_defaults`、`data_sources`、`data_source_credentials` 添加 `instance_id TEXT NOT NULL DEFAULT 'default'`

**Patterns to follow:** 现有迁移文件格式，如 `backend/alembic/versions/20260523_0100_add_sender_email_to_domain.py`

**Test scenarios:**
1. 迁移文件包含所有 10 张表的 ADD COLUMN 语句
2. 所有列为 `NOT NULL DEFAULT 'default'`
3. downgrade 方法正确删除列

**Verification:** `alembic upgrade head` 在开发环境执行成功，`alembic downgrade -1` 可回滚

---

### U13. Alembic 迁移——变更 UNIQUE 约束和索引

**Goal:** 所有受影响的唯一约束和索引加入 instance_id（R16 部分）

**Dependencies:** U12

**Files:** `backend/alembic/versions/YYYYMMDD_HHMM_update_instance_constraints.py`

**Approach:** 第二个迁移文件（依赖 U12），变更：
- `tenants`: `UNIQUE(slug)` → `UNIQUE(instance_id, slug)`
- `warmup_rules`: partial unique index → `UNIQUE(instance_id) WHERE is_active`
- `platform_scoring_templates`: partial unique index → `UNIQUE(instance_id, industry) WHERE is_active`
- `ai_scene_defaults`: `UNIQUE(scene)` → `UNIQUE(instance_id, scene)`
- `data_sources`: `UNIQUE(source_type)` → `UNIQUE(instance_id, source_type)`
- `ai_models`: `UNIQUE(provider, model_id)` → `UNIQUE(instance_id, provider, model_id)`
- `data_source_credentials`: 重建 FK

**Test scenarios:**
1. 迁移包含所有 7 个约束变更
2. downgrade 恢复原始约束

**Verification:** 开发环境迁移执行成功

---

### U14. list_tenants 按 instance_id 过滤

**Goal:** 列出租户只返回当前实例（R8 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/tenant_service.py`, `backend/tests/test_tenant_instance_isolation.py`

**Execution note:** TDD——新建 test_tenant_instance_isolation.py

**Test scenarios:**
1. list_tenants 的 SQL 参数包含 `instance_id`
2. 返回结果只包含当前实例的租户

**Verification:** 测试通过

---

### U15. get_tenant / update_tenant 校验 instance_id

**Goal:** 获取和更新租户时校验归属（R8 部分）

**Dependencies:** U14

**Files:** `backend/app/services/tenant_service.py`, `backend/tests/test_tenant_instance_isolation.py`

**Test scenarios:**
1. get_tenant SQL 包含 `AND instance_id = :instance_id`
2. update_tenant SQL 包含 `AND instance_id = :instance_id`
3. 操作其他实例的租户 → 返回 404

**Verification:** 测试通过

---

### U16. create_tenant 绑定 instance_id

**Goal:** 创建租户时写入 instance_id，slug 查重加 instance_id（R8 部分）

**Dependencies:** U14

**Files:** `backend/app/services/tenant_service.py`, `backend/tests/test_tenant_instance_isolation.py`

**Test scenarios:**
1. INSERT 语句包含 instance_id 列
2. slug 查重 SQL 包含 `AND instance_id = :instance_id`
3. 不同实例可创建同名 slug 的租户

**Verification:** 测试通过

---

### U17. list/create platform_users 绑定 instance_id

**Goal:** 平台用户管理按实例隔离（R9）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Execution note:** TDD——新建 test_admin_instance_isolation.py

**Test scenarios:**
1. list_platform_users SQL 参数包含 `instance_id`
2. create_platform_user INSERT 包含 instance_id
3. 只返回当前实例的管理员

**Verification:** 测试通过

---

### U18. warmup_rules CRUD 绑定 instance_id

**Goal:** 预热规则按实例隔离（R10 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. list_warmup_rules SQL 包含 `WHERE instance_id = :instance_id`
2. create_warmup_rule INSERT 包含 instance_id
3. update/delete 操作加 `AND instance_id = :instance_id`

**Verification:** 测试通过

---

### U19. platform_scoring_templates CRUD 绑定 instance_id

**Goal:** 评分模板按实例隔离（R10 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. list/create/update/delete 操作的 SQL 均包含 instance_id 过滤
2. `_sync_platform_template_to_tenants` 的 SQL 包含 `WHERE tenants.instance_id = :instance_id`

**Verification:** 测试通过

---

### U20. platform_email_templates CRUD 绑定 instance_id

**Goal:** 邮件模板按实例隔离（R10 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. list/create/update/delete SQL 包含 instance_id

**Verification:** 测试通过

---

### U21. ai_models / ai_scene_defaults CRUD 绑定 instance_id

**Goal:** AI 配置按实例隔离（R10 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. list_ai_models SQL 包含 instance_id
2. ai_scene_defaults 查询/创建/更新包含 instance_id

**Verification:** 测试通过

---

### U22. data_sources / data_source_credentials CRUD 绑定 instance_id

**Goal:** 数据源配置按实例隔离（R10 部分）

**Dependencies:** U1, U12, U13

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. list_data_sources SQL 包含 instance_id
2. data_source_credentials 查询/创建包含 instance_id
3. 操作其他实例的数据源凭证 → 不返回结果

**Verification:** 测试通过

---

### U23. get_platform_dashboard 按 instance_id 统计

**Goal:** Dashboard 只统计当前实例（R11）

**Dependencies:** U1, U12

**Files:** `backend/app/services/admin_config_service.py`, `backend/tests/test_admin_instance_isolation.py`

**Test scenarios:**
1. 租户数统计 SQL 包含 `tenants.instance_id`
2. 用户数统计通过 `JOIN tenants` 限制
3. 发送计划数、邮件总量、域名数统计均包含 instance_id 过滤

**Verification:** 测试通过

---

### U24. sending_worker 查询加 instance_id 过滤

**Goal:** 邮件 Worker 只处理本实例任务（R13 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/tenant_messaging_service.py`, `backend/tests/test_sending_worker.py`

**Approach:** `list_running_domain_ids`、`claim_due_emails`、`recover_stale_locks` 的 SQL 加 `JOIN tenants ON ... AND tenants.instance_id = :instance_id`

**Test scenarios:**
1. list_running_domain_ids SQL 参数包含 instance_id
2. claim_due_emails SQL 参数包含 instance_id
3. recover_stale_locks SQL 参数包含 instance_id（通过 JOIN tenants 或 sending_plans→tenants 链路）

**Verification:** test_sending_worker.py 全部通过

---

### U25. reconciliation_worker 查询加 instance_id 过滤

**Goal:** 邮件状态同步只处理本实例（R13 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/services/email_reconciliation_service.py`, `backend/tests/test_reconciliation_instance.py`

**Execution note:** TDD——新建测试文件

**Test scenarios:**
1. reconcile_once 的 stuck 邮件查询 SQL 包含 instance_id 过滤
2. 只处理本实例的 stuck 邮件

**Verification:** 测试通过

---

### U26. wmt_lineage_repair fan-out 加 instance_id 过滤

**Goal:** 数据修复只扫描本实例租户（R13 部分）

**Dependencies:** U1, U12

**Files:** `backend/app/workers/wmt_lineage_repair.py`, `backend/tests/test_wmt_repair_instance.py`

**Execution note:** TDD——新建测试文件

**Test scenarios:**
1. fan-out 查询 SQL 包含 `WHERE tenants.instance_id = :instance_id`
2. 只对本实例的 active 租户执行修复

**Verification:** 测试通过

---

### U27. advisory lock 区分实例级和全局

**Goal:** 实例级 lock 加 instance_id hash，全局 lock 保持互锁（R15）

**Dependencies:** U1, U26

**Files:** `backend/app/workers/wmt_lineage_repair.py`, `backend/tests/test_wmt_repair_instance.py`

**Approach:** `_ADVISORY_LOCK_KEY` 与 `pg_catalog.hashtext(instance_id)` 组合（如 XOR 或加法）。`tenant_ops_service.py` 的 lock 不改动。

**Test scenarios:**
1. wmt_lineage_repair 的 advisory lock SQL 包含 instance_id 相关的 hash 计算
2. 不同 instance_id 生成不同的 lock key
3. tenant_ops_service 的 advisory lock 不包含 instance_id（确认未被改动）

**Verification:** 测试通过

---

### U28. Internal API claim_due_emails 加 instance_id 过滤

**Goal:** Internal API 按实例隔离（R14 部分）

**Dependencies:** U8, U24

**Files:** `backend/app/api/internal/ops.py`, `backend/tests/test_internal_instance.py`

**Execution note:** TDD——新建测试文件

**Test scenarios:**
1. claim_due_emails 端点的 service token 校验 iid（U8 已覆盖）
2. 底层查询通过 instance_id 过滤（U24 已覆盖）
3. 端点集成测试：跨实例 service token → 403

**Verification:** 测试通过

---

### U29. Internal API collection_credentials 加 instance_id 过滤

**Goal:** 采集凭证按实例隔离（R14 部分）

**Dependencies:** U8, U22

**Files:** `backend/app/api/internal/ops.py`, `backend/tests/test_internal_instance.py`

**Test scenarios:**
1. collection_credentials 查询 data_source_credentials 时包含 instance_id 过滤
2. 跨实例 service token → 403

**Verification:** 测试通过

---

### U30. Instance B 初始化脚本

**Goal:** 创建 Instance B 第一个管理员和完整平台配置（R17）

**Dependencies:** U12, U13

**Files:** `backend/scripts/init_instance.py`, `backend/tests/test_init_instance.py`

**Approach:** 独立 Python 脚本，读取环境变量 `INIT_ADMIN_PASSWORD`、`CLIENTGET_INSTANCE_ID`、`CLIENTGET_DEV_DATABASE_URL`，插入 platform_user + warmup_rules + platform_scoring_templates + platform_email_templates + ai_models + ai_scene_defaults + data_sources

**Execution note:** TDD——先测试脚本的参数验证和 SQL 生成逻辑

**Test scenarios:**
1. `INIT_ADMIN_PASSWORD` 未设置 → 脚本拒绝运行（sys.exit(1)）
2. 脚本生成的 INSERT 语句包含正确的 instance_id
3. platform_user 的 password_hash 是 hashed 值（非明文）
4. 脚本幂等——重复运行不报错（ON CONFLICT DO NOTHING 或先检查）

**Verification:** 测试通过，开发环境可执行

---

### U31. conftest.py 更新——测试环境兼容

**Goal:** 确保所有现有测试在新 instance_id 体系下继续通过

**Dependencies:** U1, U2

**Files:** `backend/tests/conftest.py`

**Approach:** 在 conftest.py 中添加 `os.environ.setdefault("CLIENTGET_INSTANCE_ID", "default")` 和 `os.environ.setdefault("CLIENTGET_JWT_SECRET", "test-secret-key-for-unit-tests")`

**Test scenarios:**
1. 所有现有 25 个测试文件仍然通过
2. 新增的 instance isolation 测试可以通过 mock 覆盖 instance_id

**Verification:** `pytest` 全部通过，无回归

---

## Risks & Dependencies

| 风险 | 严重性 | 缓解 |
|------|--------|------|
| 管理端 API 遗漏 instance_id 过滤导致跨实例数据泄露 | 高 | 每个 API 函数有对应的测试用例验证 SQL 参数包含 instance_id |
| data_source_credentials FK 重建可能影响现有数据 | 中 | 迁移在开发环境先验证，生产环境在维护窗口执行 |
| conftest.py 修改导致现有测试回归 | 低 | U31 作为独立单元，全量运行现有测试 |
| JWT_SECRET 环境变量重命名导致部署中断 | 中 | 保留原 `JWT_SECRET` 作为 fallback（AliasChoices） |

---

## System-Wide Impact

- **认证体系**：所有 JWT token 新增 iid claim，所有认证中间件新增 iid 校验。需确认 tenant 端的 auth 流程也正确处理 iid。
- **数据库**：10 张表新增列，7 个唯一约束变更，1 个 FK 重建。迁移不可逆（downgrade 会丢失 instance_id 数据）。
- **Worker**：5 个查询入口加 instance_id 过滤。Worker 部署时必须配置 `CLIENTGET_INSTANCE_ID`，否则默认处理 Instance A 的任务。
- **部署配置**：每个实例需要独立的 `CLIENTGET_INSTANCE_ID`、`CLIENTGET_JWT_SECRET`、EngageLab 凭证。

---

## Open Questions

- `data_source_credentials` FK 重建策略：改为引用 `data_sources(id)` 还是复合 FK `(instance_id, source_type)`？需要在实施迁移时根据现有查询模式决定。
- Instance B 的初始平台配置数据来源：复制 Instance A 的还是全新配置？影响 U30 脚本的实现。

---

## Engineering Review Decisions

以下决策来自 `/plan-eng-review`（2026-06-25）：

- **D1 — conftest 前置**：U31（conftest.py 更新）移到 U1 之前执行，作为所有测试的前置条件。
- **D2 — 迁移合并**：U12 和 U13 合并为一个 Alembic 迁移文件（与 KTD3 一步迁移一致）。
- **D3 — instance_id 传递**：Service 方法直接调用 `get_settings().instance_id`，与现有 jwt.py 模式一致。测试通过 monkeypatch 注入。
- **D5 — 生产 fail fast**（Codex outside voice）：生产环境（`APP_ENV != local`）未配置 `CLIENTGET_INSTANCE_ID` 时启动报错退出。开发环境保留默认值 `"default"`。
- **D6 — 旧 token 掉线策略**（Codex outside voice）：上线后旧 token（不含 iid）直接返回 403，用户重新登录即可。用户池极小（<10 人），不需要过渡期。

## NOT in scope

- 前端代码改动（前端只需指向不同后端 URL，CORS 通过环境变量配置）
- 实例生命周期管理（退役、租户迁移）
- 数据库层面 RLS 强制 instance_id 隔离（应用层 WHERE 条件 + 测试覆盖为当前方案）
- 集成测试（双实例真实数据库测试）——当前项目测试全部用 AsyncMock，可作为 follow-up
- 全局数据池写入冲突策略——现有 advisory lock（tenant_ops_service）已处理
- cookie domain 可配置化——通过前提假设（Instance B 使用独立域名）规避

## What already exists

| 现有能力 | 计划复用方式 |
|----------|-------------|
| tenant_id + RLS 多租户隔离 | instance_id 隔离是同一模式在更高层级的复用 |
| JWT 签发/验证基础设施 | 只需注入 iid claim |
| Worker DI 架构 | 通过 `get_settings()` 读取 instance_id |
| conftest.py 环境变量模式 | 添加 CLIENTGET_INSTANCE_ID / CLIENTGET_JWT_SECRET |
| admin_config_service 的 CRUD 模式 | 所有平台配置 API 加 WHERE instance_id 条件 |
| advisory lock 模式 | 区分实例级和全局两类 |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 6 decisions (D1-D6), 0 critical gaps |
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |

**CODEX:** gpt-5.5 ran plan review — 20+ findings, 2 accepted (D5 fail fast, D6 token 掉线策略), rest addressed in NOT in scope or existing architecture.

**VERDICT:** ENG CLEARED — ready to implement.

NO UNRESOLVED DECISIONS
