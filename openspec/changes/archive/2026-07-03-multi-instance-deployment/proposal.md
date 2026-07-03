## Why

系统已趋于稳定，需要部署第二套实例（Instance B）给新的运营团队使用。两套实例共享同一个 PostgreSQL 数据库（全局数据池如 clean_companies 共享），但账户体系完全独立——Instance B 的管理员、租户、用户全部从零开始，不继承 Instance A 的任何账户数据。

## What Changes

### 数据库层
- `platform_users`、`tenants` 表新增 `instance_id` 列，用于区分实例归属
- `tenants` 的 `slug` 唯一约束从 `UNIQUE(slug)` 改为 `UNIQUE(instance_id, slug)`
- `platform_users.email` 保持全局唯一（不允许同邮箱在两个实例当管理员）
- 平台配置表（`warmup_rules`、`platform_scoring_templates`、`platform_email_templates`、`ai_models`、`ai_scene_defaults`、`data_sources`、`data_source_credentials`）新增 `instance_id` 列（子表 `warmup_rule_levels`、`platform_scoring_template_versions` 通过 FK 关联父表，不需要独立的 `instance_id` 列）

### 认证层
- JWT token（access + refresh）新增 `instance_id` claim
- 中间件强制校验 token 的 `instance_id` 与后端 `CLIENTGET_INSTANCE_ID` 配置一致
- 管理端 API 校验操作的 `tenant_id` 是否属于当前实例

### 应用层
- 所有管理端 API（租户管理、平台用户管理、平台配置 CRUD、Dashboard 统计）绑定 `instance_id` 过滤
- `_sync_platform_template_to_tenants` 只同步当前实例的租户

### Worker 层
- Worker 注入 `CLIENTGET_INSTANCE_ID` 环境变量
- 邮件发送、邮件状态同步、数据修复等查询通过 `tenants.instance_id` 限制候选租户
- advisory lock 加 instance_id 区分

### 部署层
- 新增后端容器（INSTANCE_ID=instance_b）+ 两个前端容器（admin/tenant，指向新后端）
- Worker 每实例各跑一套

## Non-Goals

- 不改动任何业务表（tenant_companies、emails、sending_plans 等通过 tenant_id 自然隔离）
- 不改动全局数据池（clean_companies、clean_contacts、keyword_master、raw 数据表）
- 不改动参考数据（countries、country_holidays、position_classification_*）
- 不改动前端代码（前端只需指向不同的后端 URL）
- 不实现实例间数据迁移或同步功能
- 不实现运行时动态切换实例（instance_id 由环境变量固定）

## Capabilities

### New Capabilities
- `instance-isolation`: 实例隔离核心能力——instance_id 列、认证校验、管理端 API 过滤、Worker 隔离

### Modified Capabilities
- `refresh-token`: JWT token 新增 instance_id claim，refresh 流程增加实例校验

## Impact

| 影响范围 | 具体内容 |
|----------|----------|
| 数据库 | 9 张表新增 `instance_id` 列；7 个唯一约束/索引变更；一步迁移（`NOT NULL DEFAULT 'default'`） |
| 后端认证 | `auth_service.py`、`jwt.py`、`dependencies.py` 修改登录/校验逻辑 |
| 管理端 API | `admin_config_service.py`、`tenant_service.py` 所有查询绑定 instance_id |
| Worker | `sending.py`、`reconciliation.py`、`wmt_lineage_repair.py` 查询加实例过滤 |
| 配置 | `config.py` 新增 `CLIENTGET_INSTANCE_ID` 配置项 |
| 部署 | Sealos 新建 3 个容器（backend + admin + tenant）+ Worker 容器 |
| 跨模块依赖顺序 | 数据库迁移 → 后端代码 → Worker 代码 → 部署新实例 |
