## Context

当前系统为单实例部署：一套后端 + 一套 admin/tenant 前端 + 一套 Worker，连接同一个 PostgreSQL 数据库。已有完整的多租户隔离（tenant_id + RLS），但没有"实例"层级的隔离概念。

现在需要部署第二套实例（Instance B），与 Instance A 共享同一个数据库。两个实例的管理员、租户、用户完全独立，但全局数据池（clean_companies 等）和参考数据共享。

关键约束：
- Instance B 初始账户为空，需要通过初始化脚本创建第一个管理员
- 两个实例域名不同（Instance B 不使用 `.xinanpcb.com` 子域名，Cookie 天然隔离）
- 每个实例各跑一套 Worker
- 每个实例配置独立的 JWT_SECRET 和 EngageLab 凭证
- 管理员邮箱全局唯一，租户用户邮箱允许跨实例重复

## Goals / Non-Goals

**Goals:**
- 在同一数据库上支持多个独立实例，每个实例有独立的账户体系和平台配置
- 现有部署（Instance A）零影响——所有新增列默认值 `'default'`，无需数据迁移
- JWT 密钥隔离 + iid claim 纵深防御，防止跨实例 token 复用
- Worker 按实例隔离，只处理本实例租户的任务

**Non-Goals:**
- 不改动前端代码（前端仅需指向不同后端 URL）
- 不改动任何业务表（tenant_companies、emails 等通过 tenant_id 自然隔离）
- 不改动全局数据池和参考数据表
- 不实现运行时动态切换实例
- 不实现实例间数据迁移或同步
- 不实现实例生命周期管理（退役、租户迁移等）——当前是一次性部署

## Decisions

### D1: instance_id 和 JWT_SECRET 均作为环境变量注入

**选择**: 后端通过 `CLIENTGET_INSTANCE_ID` 读取实例标识（默认 `"default"`），通过 `CLIENTGET_JWT_SECRET` 读取 JWT 密钥。每个实例 MUST 配置独立的密钥值。

**理由**: 独立 JWT_SECRET 从密码学层面隔离 token——Instance A 签发的 token 在 Instance B 无法通过签名验证。iid claim 作为纵深防御，即使密钥意外相同也能在应用层拦截。

**备选方案**: 共享 JWT_SECRET + 仅靠 iid claim 隔离——安全性弱，依赖每个中间件都正确检查 iid，遗漏一处就全线失守。

### D2: 需要 instance_id 的表（含子表关系）

**选择**: 以下表加 `instance_id TEXT NOT NULL DEFAULT 'default'`：

| 类别 | 需要 instance_id 列的表 | 不需要（通过 FK 关联父表） |
|------|-------------------------|---------------------------|
| 身份 | `platform_users`、`tenants` | `users`、`user_roles`（通过 tenant_id FK） |
| 预热配置 | `warmup_rules` | `warmup_rule_levels`（通过 rule_id FK） |
| 评分模板 | `platform_scoring_templates` | `platform_scoring_template_versions`（通过 FK） |
| 邮件模板 | `platform_email_templates` | — |
| AI 配置 | `ai_models`、`ai_scene_defaults` | — |
| 数据源 | `data_sources`、`data_source_credentials` | — |

**理由**: 子表始终通过 FK JOIN 父表操作（如 `DELETE FROM warmup_rule_levels WHERE rule_id = :rule_id`），不存在独立按 instance_id 查询的场景。冗余列增加 INSERT 同步成本，无收益。

### D3: JWT token + service token 均加入 iid claim

**选择**: `create_access_token`、`create_refresh_token`、`create_service_token` 均在 claims 中加入 `iid`。中间件 `get_current_platform_user`、`get_current_tenant_user`、`get_current_service` 均校验 `iid`。认证中间件的 DB 查询也加 `instance_id` 过滤（纵深防御）。

**理由**: Service token 用于 Worker 与 internal API 通信。如果 service token 不含 iid，Instance B 的 Worker 理论上可以调用 Instance A 的 internal API。

### D4: 唯一约束和索引变更完整清单

**选择**:

| 表 | 原约束 | 新约束 |
|----|--------|--------|
| `tenants` | `UNIQUE(slug)` | `UNIQUE(instance_id, slug)` |
| `warmup_rules` | `UNIQUE INDEX (is_active) WHERE is_active` | `UNIQUE INDEX (instance_id) WHERE is_active` |
| `platform_scoring_templates` | `UNIQUE INDEX (industry) WHERE is_active` | `UNIQUE INDEX (instance_id, industry) WHERE is_active` |
| `ai_scene_defaults` | `UNIQUE(scene)` | `UNIQUE(instance_id, scene)` |
| `data_sources` | `UNIQUE(source_type)` | `UNIQUE(instance_id, source_type)` |
| `data_source_credentials` | FK `REFERENCES data_sources(source_type)` | 重建 FK 为 `REFERENCES data_sources(id)` 或复合 FK |
| `ai_models` | `UNIQUE(provider, model_id)` | `UNIQUE(instance_id, provider, model_id)` |
| `platform_users` | `UNIQUE(email)` | 保持全局唯一（不加 instance_id） |

**理由**: 管理员邮箱全局唯一——管理员池极小（<10 人），使用邮箱别名即可覆盖"同一人管理两套实例"的需求。避免"这个管理员到底属于哪个实例"的混淆。

### D5: Worker 按实例隔离 + advisory lock 分类

**选择**: 每个实例部署独立的 Worker 容器。Worker 查询通过 `JOIN tenants ON tenants.instance_id = :instance_id` 限制候选租户。

Advisory lock 分两类：
- **实例级 lock**（如 `wmt_lineage_repair`）：lock key 加入 `pg_catalog.hashtext(instance_id)`，实例间不互锁
- **全局 lock**（如 `tenant_ops_service` 保护 clean_companies 去重）：保持全局互锁，因为 clean_* 是共享表

**理由**: 共享 Worker 运维模糊且无法为不同实例配置不同发送策略。全局 lock 必须跨实例互锁以保证去重正确性。

### D6: 一步迁移

**选择**: `ALTER TABLE ADD COLUMN instance_id TEXT NOT NULL DEFAULT 'default'` + 同步变更所有 UNIQUE 约束。

**理由**: PostgreSQL 11+ 对有 DEFAULT 的 ADD COLUMN 是 metadata-only 操作，不需要 table rewrite，现有行自动获得默认值。无需分两步，无需 nullable 中间态，无需回填。

### D7: 生产环境 instance_id 守卫策略（2026-07-02 用户确认）

**选择**: `APP_ENV=production` 时要求 `CLIENTGET_INSTANCE_ID` 环境变量**显式存在**（值允许为 `'default'`），未设置则启动失败。Instance A 生产在 Sealos 显式配置 `CLIENTGET_INSTANCE_ID=default`。

**理由**: 迁移将生产存量数据全部标为 `'default'`，Instance A 的合法身份就是 `default`（与 D6"无需回填"一致）。守卫的意义是防止 Instance B 漏配环境变量后静默以 default 身份运行、看到 Instance A 的数据——校验"显式设置"即可达成，无需禁止 `default` 值本身。

**备选方案（已否决）**: 禁止生产使用 `default` 值——迫使 Instance A 改用真实 ID 并回填存量数据，与"零影响"目标冲突，且部署时守卫会让现有生产容器直接启动失败。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 管理端 API 遗漏 instance_id 过滤 | Instance B 管理员看到 Instance A 的租户 | 所有管理端查询统一通过 helper 函数注入 instance_id 条件；代码审查重点关注 |
| Worker 查询遗漏 instance_id JOIN | Worker 处理了其他实例的任务 | 完整隔离清单：list_running_domain_ids、claim_due_emails、recover_stale_locks、reconcile_once、wmt_lineage_repair fan-out |
| 平台配置表遗漏 | 新实例创建租户时引用了 Instance A 的 warmup_rule 等 | 部署前用初始化脚本为 Instance B 创建完整平台配置 |
| data_source_credentials FK 重建 | FK 引用 `data_sources(source_type)` 在 UNIQUE 变更后失效 | 迁移中同步重建 FK 为引用 `data_sources(id)` |
| Internal API / Webhook 遗漏 | 跨实例数据泄露 | Internal API 加 service token iid 校验；Webhook 通过独立 EngageLab 账户天然隔离 |

## Migration Plan

### 部署步骤

1. **数据库迁移**: 加 `instance_id NOT NULL DEFAULT 'default'` 列 + 变更所有唯一约束和索引 + 重建 FK
2. **部署新后端代码**: Instance A 后端升级（带 instance_id 逻辑，`INSTANCE_ID=default`，独立 `JWT_SECRET`）
3. **验证 Instance A**: 确认现有功能不受影响
4. **为 Instance B 初始化数据**: 初始化脚本插入管理员（密码通过环境变量注入）+ 平台配置
5. **部署 Instance B**: 后端容器（`INSTANCE_ID=instance_b`，独立 `JWT_SECRET` 和 EngageLab 凭证）+ 前端容器 + Worker 容器

### 回滚策略

- 迁移回滚：`DROP COLUMN instance_id` + 恢复原始唯一约束（不影响现有功能）
- 代码回滚：回退到不含 instance_id 逻辑的版本（`DEFAULT 'default'` 保证旧代码不报错）
- Instance B 回滚：直接停止容器，数据留在数据库不影响 Instance A

## Open Questions

- Instance B 的具体域名和 SSL 证书配置（由运维确定）
- Instance B 的 EngageLab 账户是否已准备好（影响邮件功能可用时间）
- Instance B 的初始平台配置是复制 Instance A 的还是全新配置
- ~~`data_source_credentials` 的 FK 重建策略：改为引用 `data_sources(id)` 还是复合 FK `(instance_id, source_type)`~~ → 已实现为复合 FK `(instance_id, source_type)`（已在开发库验证）
