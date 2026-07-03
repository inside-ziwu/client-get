## 1. 数据库迁移

- [x] 1.1 创建 Alembic 迁移：为 `platform_users`、`tenants`、`warmup_rules`、`platform_scoring_templates`、`platform_email_templates`、`ai_models`、`ai_scene_defaults`、`data_sources`、`data_source_credentials` 添加 `instance_id TEXT NOT NULL DEFAULT 'default'` 列
- [x] 1.2 同一迁移中变更唯一约束：`tenants` 从 `UNIQUE(slug)` 改为 `UNIQUE(instance_id, slug)`
- [x] 1.3 同一迁移中变更 partial unique index：`warmup_rules` 从 `UNIQUE(is_active) WHERE is_active` 改为 `UNIQUE(instance_id) WHERE is_active`
- [x] 1.4 同一迁移中变更 partial unique index：`platform_scoring_templates` 从 `UNIQUE(industry) WHERE is_active` 改为 `UNIQUE(instance_id, industry) WHERE is_active`
- [x] 1.5 同一迁移中变更 UNIQUE 约束：`ai_scene_defaults` 从 `UNIQUE(scene)` 改为 `UNIQUE(instance_id, scene)`；`data_sources` 从 `UNIQUE(source_type)` 改为 `UNIQUE(instance_id, source_type)`；`ai_models` 从 `UNIQUE(provider, model_id)` 改为 `UNIQUE(instance_id, provider, model_id)`
- [x] 1.6 同一迁移中重建 `data_source_credentials` 的 FK（实现为复合 FK `(instance_id, source_type)` 引用 `data_sources(instance_id, source_type)`）
- [x] 1.7 在开发环境执行迁移，验证现有功能不受影响（2026-07-02 逐项核查：9 表 instance_id 列齐全且存量均为 default、全部复合唯一约束/部分索引/复合 FK 在库、235 项测试通过；迁移链已重排为 20260614_0002 → 20260701_0001 → 20260701_0002 → 20260625_0100）

## 2. 后端配置

- [x] 2.1 在 `backend/app/core/config.py` 的 `Settings` 类中添加 `instance_id: str = Field(default="default", alias="CLIENTGET_INSTANCE_ID")`
- [x] 2.2 将 `jwt_secret` 的环境变量别名改为 `CLIENTGET_JWT_SECRET`（AliasChoices 兼容旧 `JWT_SECRET`），确保每个实例可配置独立的 JWT 密钥；另有生产守卫：`APP_ENV=production` 时必须显式设置 `CLIENTGET_INSTANCE_ID`（值允许为 `default`，见 design.md D7）

## 3. 认证层改造

- [x] 3.1 修改 `backend/app/security/jwt.py`：`create_access_token` 自动注入 `iid` claim（从 `get_settings().instance_id` 读取）
- [x] 3.2 修改 `backend/app/security/jwt.py`：`create_refresh_token` 自动注入 `iid` claim
- [x] 3.3 service token 的 `iid` 校验在 `internal.py` 服务端实现；签发方为外部服务（本仓库无 `create_service_token`），**部署注意**：外部签发方需在 token claims 中同步加入 `iid`，否则调用 internal API 将返回 403
- [x] 3.4 修改 `backend/app/security/dependencies.py`：`get_current_platform_user` 校验 token 的 `iid` 与当前 `instance_id` 一致（不一致返回 403），且 DB 查询加 `AND instance_id = :instance_id`
- [x] 3.5 修改 `backend/app/security/dependencies.py`：`get_current_tenant_user` 校验 token 的 `iid` 与当前 `instance_id` 一致（不一致返回 403）
- [x] 3.6 修改 `backend/app/security/internal.py`：service token 认证校验 `iid` 与当前 `instance_id` 一致
- [x] 3.7 修改 `backend/app/services/auth_service.py`：`platform_login` 查询加 `WHERE instance_id = :instance_id`
- [x] 3.8 修改 `backend/app/services/auth_service.py`：`tenant_login` 查询加 `WHERE t.instance_id = :instance_id`
- [x] 3.9 修改 `backend/app/api/admin/auth.py`：`refresh` 端点校验 refresh_token 的 `iid` 与当前 `instance_id` 一致；DB 查询加 `AND instance_id = :instance_id`；签发新 access_token 注入 `iid`

## 4. 管理端 API 改造——租户管理

- [x] 4.1 修改 `tenant_service.py`：`list_tenants` 加 `WHERE instance_id = :instance_id`
- [x] 4.2 修改 `tenant_service.py`：`get_tenant` 加 `AND instance_id = :instance_id` 校验
- [x] 4.3 修改 `tenant_service.py`：`create_tenant` 创建时写入 `instance_id`；slug 查重加 `AND instance_id = :instance_id`
- [x] 4.4 修改 `tenant_service.py`：`update_tenant` 加 `AND instance_id = :instance_id` 校验
- [x] 4.5 修改管理端租户用户/域名操作 API：校验目标 `tenant_id` 属于当前实例（通过 JOIN `tenants.instance_id`）

## 5. 管理端 API 改造——平台用户管理

- [x] 5.1 修改 `admin_config_service.py`：`list_platform_users` 加 `WHERE instance_id = :instance_id`
- [x] 5.2 修改 `admin_config_service.py`：`create_platform_user` 创建时写入 `instance_id`

## 6. 管理端 API 改造——平台配置

- [x] 6.1 修改 `admin_config_service.py`：warmup_rules CRUD 绑定 `instance_id`（列出、创建、更新、删除）
- [x] 6.2 修改 `admin_config_service.py`：warmup_rule_levels CRUD 通过 JOIN `warmup_rules.instance_id` 过滤（子表本身不加 instance_id 列）
- [x] 6.3 修改 `admin_config_service.py`：platform_scoring_templates CRUD 绑定 `instance_id`
- [x] 6.4 修改 `admin_config_service.py`：platform_scoring_template_versions CRUD 通过 JOIN 父表过滤（子表本身不加 instance_id 列）
- [x] 6.5 修改 `admin_config_service.py`：platform_email_templates CRUD 绑定 `instance_id`
- [x] 6.6 修改 `admin_config_service.py`：ai_models / ai_scene_defaults CRUD 绑定 `instance_id`
- [x] 6.7 修改 `admin_config_service.py`：data_sources / data_source_credentials CRUD 绑定 `instance_id`
- [x] 6.8 修改 `admin_config_service.py`：`_sync_platform_template_to_tenants` 只同步当前实例租户
- [x] 6.9 修改 `admin_config_service.py`：`get_platform_dashboard` 统计加 `instance_id` 过滤（租户数、用户数、发送计划数、邮件总量、域名数）

## 7. Internal API 改造

- [x] 7.1 `claim_due_emails` 端点：`require_service_scopes` 校验 service token `iid` 与当前实例一致，service 层查询按 `tenants.instance_id` 限制候选租户
- [x] 7.2 `list_collection_credentials` 端点：`internal_ops_service.py` 按 `instance_id` 过滤 `data_source_credentials`

## 8. Worker 实例隔离

- [x] 8.1 Worker 实例标识通过 `get_settings().instance_id`（`CLIENTGET_INSTANCE_ID`）在 service 层生效，Worker 容器需注入该环境变量
- [x] 8.2 修改 `tenant_messaging_service.py`：`list_running_domain_ids` 加 `JOIN tenants WHERE instance_id = :instance_id`
- [x] 8.3 修改 `tenant_messaging_service.py`：`claim_due_emails` 加 `JOIN tenants WHERE instance_id = :instance_id`
- [x] 8.4 修改 `tenant_messaging_service.py`：`recover_stale_locks` 加 `JOIN tenants WHERE instance_id = :instance_id`（只释放本实例的 stale lock）
- [x] 8.5 修改 `email_reconciliation_service.py`：`reconcile_once` 查询加 instance_id 过滤
- [x] 8.6 修改 `wmt_lineage_repair.py`：fan-out 查询加 `WHERE tenants.instance_id = :instance_id`
- [x] 8.7 修改 `wmt_lineage_repair.py`：advisory lock key 加入 `pg_catalog.hashtext(instance_id)` 组合（实例级 lock）；**2026-07-03 生产修正**：key 需 `CAST(:key AS bigint)`——hashtext 返回 int4，int4 相加溢出（生产报 `integer out of range`，仅影响 lineage repair 后台循环，已修复并验证）
- [x] 8.8 确认 `tenant_ops_service.py` 的 advisory lock 保持全局互锁（保护 clean_* 表去重，不加 instance_id）

## 9. Instance B 初始化

- [x] 9.1 编写独立 Python 初始化脚本 `backend/scripts/init_instance.py`：为 Instance B 插入第一个 `platform_user`，密码通过环境变量 `INIT_ADMIN_PASSWORD` 注入
- [x] 9.2 初始化脚本包含完整平台配置：创建 warmup_rules、platform_scoring_templates、platform_email_templates、ai_models、ai_scene_defaults、data_sources 等（均设目标 `instance_id`）
- [x] 9.3 初始化脚本在 `INIT_ADMIN_PASSWORD` 未设置时拒绝运行；管理员邮箱已存在时显式报错退出（不静默跳过）

## 10. 验证与部署

- [x] 10.1 Instance A 功能验证：自动化测试(最终 292+ 项)通过;2026-07-03 生产升级后登录、租户管理、配置管理、采集、评分、发送均正常运行(以生产回归替代开发环境手工并行验证)
- [x] 10.2 Instance B 独立运行验证:以生产环境完整验收替代开发环境(见 10.14)
- [x] 10.3 验证跨实例隔离：Instance B 管理端无法看到 Instance A 的租户和配置（由 `test_auth_instance_isolation.py` 平台/租户用户 iid 校验测试覆盖;生产 B 管理端租户列表仅见 B 租户,实测确认）
- [x] 10.4 验证跨实例 token 无法复用：独立 JWT_SECRET 签名验证失败 + iid 缺失/不匹配返回 403（由 `test_jwt.py`、`test_auth_instance_isolation.py` 覆盖）
- [x] 10.5 验证 Worker 隔离：运行时确认——B Worker 仅领取 B 租户任务并完成发送(2026-07-03 测试邮件 delivered),A Worker 同期正常处理 A 任务互不干扰
- [x] 10.6 验证 refresh 端点隔离：跨实例 refresh_token 返回 403（由 `test_auth_refresh.py::TestRefreshInstanceFilter` 覆盖）
- [x] 10.7 验证 Internal API 隔离：跨实例 service token 返回 403（由 `test_auth_instance_isolation.py::TestServiceTokenIidValidation` 覆盖）
- [x] 10.8 部署 Instance A 到生产（2026-07-03,`CLIENTGET_INSTANCE_ID=default`,迁移 20260625_0100 落库,存量数据零影响;唯一生产事故为 advisory lock int4 溢出,当日热修见 8.7）
- [x] 10.9 Instance B 后端容器已创建（`CLIENTGET_INSTANCE_ID=instance_b`、独立 `CLIENTGET_JWT_SECRET`、`COOKIE_DOMAIN=<B 后端完整主机名>`、`ALLOWED_ORIGINS=<两个前端 origin>`）;**EngageLab 端点按账户数据中心选择**:B 账户属土耳其数据中心,`ENGAGELAB_BASE_URL=https://emailapi-tr.engagelab.com`(新加坡为 email.api.engagelab.cc,配错数据中心表现为 401 code 30000)
- [x] 10.10 Instance B admin 前端:`clientget-admin:2026.07.03-instanceB-r3`(构建参数 `api_url` + `tenant_portal_url`);「后台管理地址」的租户端入口已改为构建期 `tenant_portal_url` 输入（`NEXT_PUBLIC_TENANT_PORTAL_BASE_URL`,留空回退 A 域名）
- [x] 10.11 Instance B tenant 前端:`clientget-tenant:2026.07.03-instanceB-r2`（`api_url` 指向 B 后端）
- [x] 10.12 Instance B Worker 容器已创建（与 B 后端同镜像同环境变量,公网关闭）
- [x] 10.13 初始化完成:管理员 sales08@xxhpcb.com + 全套平台配置 7/7 落库（init 脚本 schema 对齐修复后,已在开发库预演验证）
- [x] 10.14 端到端验收通过（2026-07-03）:B 管理员登录 → 创建租户「刘辉」→ 租户登录 → 配置域名 email.newpcb.net(DNS 验证通过)→ 发送测试邮件 **delivered**,webhook `sent`/`delivered` 事件回流入库;实例隔离、cookie 域、CORS 均实测正常
