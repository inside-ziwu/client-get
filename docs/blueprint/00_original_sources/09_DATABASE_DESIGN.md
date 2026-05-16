# 09 数据库设计文档

> **文档版本**: v1.0
> **创建日期**: 2026-04-17
> **输入文档**: `01_DATA_MODEL.md`（现有表结构）、`07_REQUIREMENTS_SPEC.md`（需求规格）、`08_UI_SPEC.md`（界面规格）
> **目标读者**: AI Agent（可解析结构化DDL）+ 人类开发者（可理解设计意图）

---

## 目录

1. [总体架构与设计原则](#1-总体架构与设计原则)
2. [平台层表设计](#2-平台层表设计)
3. [共享数据池表设计](#3-共享数据池表设计)
4. [租户业务表 — 公司与评分](#4-租户业务表--公司与评分)
5. [租户业务表 — 联系人与群组](#5-租户业务表--联系人与群组)
6. [租户业务表 — 邮件系统](#6-租户业务表--邮件系统)
7. [租户业务表 — 情报系统](#7-租户业务表--情报系统)
8. [系统支撑表](#8-系统支撑表)
9. [RLS 策略设计](#9-rls-策略设计)
10. [索引策略](#10-索引策略)
11. [分区策略](#11-分区策略)
12. [现有表迁移路径](#12-现有表迁移路径)
13. [ER 关系图](#13-er-关系图)
14. [附录](#14-附录)

---

## 1. 总体架构与设计原则

### 1.1 设计决策汇总

以下 11 项决策通过苏格拉底式提问确认，构成整个数据库设计的基础：

| # | 决策领域 | 结论 | 理由 |
|---|---------|------|------|
| D1 | 多租户隔离 | **PostgreSQL RLS（全租户敏感表）+ 共享池 SECURITY DEFINER 视图** | 数据库层强制隔离；ai_usage_logs 等计费表也启用 RLS；shared_companies / shared_contacts 由租户视图（v_tenant_visible_companies 等）通过 SECURITY DEFINER 函数代理访问，原表仅平台角色可直查 |
| D2 | 主键策略 | **UUID v7** | 时间有序、分布式友好、不暴露业务量 |
| D3 | 评分规则存储 | **JSONB** | 整体读写场景，灵活且一次读取 |
| D4 | 序列邮件建模 | **独立表** | sequence_steps + sequence_enrollments，支持精确状态追踪 |
| D5 | 联系人规则存储 | **JSONB** | 与评分规则一致，整体读写场景 |
| D6 | 软删除范围 | **仅核心实体** | 公司/联系人/计划/模板/群组软删除，配置类硬删除 |
| D7 | 审计日志 | **独立 audit_logs 表** | 统一记录所有实体增删改，按月分区 |
| D8 | 跨数据源去重 | **合并 + company_sources 关联表** | 共享池每家公司一条记录，关联表记录数据源来源 |
| D9 | 时间字段 | **全部 timestamptz** | PostgreSQL 最佳实践，应用层负责时区转换 |
| D10 | 分区策略 | **高增长表按月分区** | emails / audit_logs / intelligence_articles |
| D11 | 情报文章存储 | **全部存 DB** | Phase 1 数据量可控，简化架构 |

### 1.2 技术栈约定

| 项目 | 约定 |
|------|------|
| 数据库 | PostgreSQL 16+ |
| 主键类型 | `UUID` (v7, 应用层生成) |
| 时间字段 | `TIMESTAMPTZ`, 存储 UTC, 应用层转换显示 |
| JSON字段 | `JSONB`（非 JSON） |
| 字符串 | `VARCHAR(n)` 有明确上限的用约束，无上限的用 `TEXT` |
| 金额 | `NUMERIC(12,4)` — 人民币，支持到分以下（token 计费需要） |
| 枚举 | PostgreSQL `ENUM` 类型，变更频率低的状态用枚举，变更频率高的用 `VARCHAR` + CHECK |
| 软删除 | 核心实体表含 `deleted_at TIMESTAMPTZ DEFAULT NULL`（见下方清单） |
| 通用字段 | 所有有状态变更的表包含 `created_at` + `updated_at`；追加型表（company_sources, group_members, email_events, balance_transactions 等）仅含 `created_at` |
| 触发器 | `updated_at` 通过触发器自动更新 |
| RLS | 租户隔离表启用 RLS，平台管理表不启用 |

> **软删除表清单**：以下表含 `deleted_at` 字段，支持软删除：
> - `tenant_companies` — 租户退池公司（可恢复）
> - `tenant_contacts` — 租户退池联系人（可恢复）
> - `groups` — 群组删除（可恢复）
> - `email_templates` — 模板删除（可恢复）
> - `sending_plans` — 发送计划删除（可恢复）
> - `intelligence_sources` — 情报源删除（可恢复）
>
> **不使用软删除的表**：追加型日志表（emails, email_events, audit_logs, balance_transactions）、配置表（scoring_templates, contact_rules, ai_models）、关系表（group_members, sending_plan_recipients）等。这些表通过状态字段（如 `status='archived'`）或直接物理删除管理生命周期。

### 1.3 表分层架构

```
┌─────────────────────────────────────────────────────┐
│                  平台层 (Platform)                     │
│  tenants / users / user_roles / ai_models /          │
│  ai_usage_logs / data_source_credentials /           │
│  platform_email_templates                            │
│  ───── 无 RLS（ai_usage_logs / users / user_roles 除外，已修订启用 RLS）─── │
├─────────────────────────────────────────────────────┤
│               共享数据池 (Shared Pool)                  │
│  shared_companies / company_sources / shared_contacts │
│  company_blacklist / competitor_companies             │
│  ───── shared_companies/shared_contacts/company_sources │
│        无 RLS（租户通过 SECURITY DEFINER 视图访问）；     │
│        company_blacklist/competitor_companies 有 RLS    │
│        （含 tenant_id，租户级过滤）─────                  │
├─────────────────────────────────────────────────────┤
│               租户业务层 (Tenant)                       │
│  tenant_companies / scoring_templates /               │
│  scoring_template_versions / company_scores /         │
│  contact_rules / tenant_contacts / groups /           │
│  group_members / email_templates / sending_plans /    │
│  sending_plan_recipients / sequence_steps /           │
│  sequence_enrollments / emails / email_events /       │
│  intelligence_sources / intelligence_articles /       │
│  intelligence_article_publications /                  │
│  intelligence_subscriptions                           │
│  ───── 全部启用 RLS (tenant_id) ─────                  │
├─────────────────────────────────────────────────────┤
│               系统支撑层 (System)                       │
│  audit_logs / notifications / domain_warmup_status /  │
│  domain_warmup_history / collection_tasks /           │
│  collection_keywords / balance_transactions           │
│  ───── 按需启用 RLS ─────                              │
└─────────────────────────────────────────────────────┘
```

### 1.4 UUID v7 生成约定

应用层（Python）使用 `uuid7` 库生成，保证时间有序性：

```python
# Python 示例
from uuid_extensions import uuid7

new_id = uuid7()  # 时间有序的 UUID v7
```

数据库层提供兜底默认值（需要 pg_uuidv7 扩展或应用层保证）：

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 注意：PostgreSQL 原生不支持 UUID v7，主键值应由应用层生成
-- 数据库层仅做类型约束
```

### 1.5 通用触发器

```sql
-- updated_at 自动更新触发器函数
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 用法：对每张表创建触发器
-- CREATE TRIGGER set_updated_at
--   BEFORE UPDATE ON <table_name>
--   FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
```

---

### 1.6 DDL 执行顺序说明

> **重要**：本文档按逻辑分层排列表定义，但部分表存在前向引用（FK 引用了尚未定义的表）。
> 实际执行 DDL 时，须调整为以下依赖拓扑序：
>
> 1. 通用函数（§1.5 `trigger_set_updated_at`）
> 2. 平台层（§2）：`tenants` → `users` → `user_roles` → `ai_models` → `platform_email_templates` → `data_source_credentials`
> 3. 系统支撑-前置（§8.3, §8.6）：**`domain_warmup_status`** → **`balance_transactions`**（被 §2.5 和 §6.2 引用）
> 4. 平台层-后置（§2.5）：`ai_usage_logs`（引用 `balance_transactions`）
> 5. 共享池（§3）：`shared_companies` → `company_sources` → `shared_contacts` → `competitor_companies`
> 6. 租户-公司评分（§4 + §5.1 + §3.4）：`collection_keywords`（§8.5，被 `tenant_companies.keyword_id` 引用）→ `tenant_companies` → `scoring_templates` → `scoring_template_versions` → `company_scores` → `contact_rules`（§5.1）→ `company_blacklist`（§3.4）
> 7. 租户-联系人（§5）：`tenant_contacts` → `groups` → `group_members`
> 8. 租户-邮件（§6）：`email_templates` → `sending_plans`（引用 `domain_warmup_status`）→ `sending_plan_recipients` → `sequence_steps` → `sequence_enrollments` → `emails` → `email_events`
> 9. 租户-情报（§7）：`intelligence_sources` → `intelligence_articles` → `intelligence_subscriptions` → `intelligence_article_publications`
>    - ⚠ `intelligence_articles` 无 FK 指向 `intelligence_sources`（`source_id` 无 FK 约束，应用层保证引用完整性）。此处依赖为**逻辑顺序**（先有源再有文章），非数据库强制。
> 10. 系统支撑-剩余（§8）：`audit_logs` → `notifications` → `domain_warmup_history` → `collection_tasks`
> 11. RLS 策略（§9）、索引（§10）、分区（§11）

---

## 2. 平台层表设计

> 平台层表不启用 RLS（`ai_usage_logs` / `users` / `user_roles` 除外，已修订启用 RLS — 见 §9.3），由超级管理员和系统内部服务访问。

### 2.1 tenants — 租户

```sql
CREATE TABLE tenants (
  id              UUID PRIMARY KEY,  -- 应用层生成 UUID v7
  name            VARCHAR(100) NOT NULL,
  slug            VARCHAR(50)  NOT NULL UNIQUE,  -- URL友好标识，如 "acme-corp"
  industry        VARCHAR(100) NOT NULL,          -- 租户所属行业（已确认：租户=单行业）
  status          VARCHAR(20)  NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'suspended', 'archived')),
  -- 计费相关
  balance         NUMERIC(12,4) NOT NULL DEFAULT 0
                  CHECK (balance >= 0),  -- 不允许透支；如需透支策略，移除此约束并改为应用层控制
  -- 配置
  settings        JSONB NOT NULL DEFAULT '{}',  -- 租户级配置（预留扩展）
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE tenants IS '租户表，每个租户对应一个付费客户组织';
COMMENT ON COLUMN tenants.slug IS 'URL友好标识，用于子域名或路径区分';

-- 租户删除策略说明：
-- ⚠ 租户不做物理删除（CASCADE 风险过大，涉及 30+ 张业务表）。
-- 停用/注销租户时：UPDATE tenants SET status = 'archived', updated_at = NOW() WHERE id = :tenant_id;
-- archived 租户的处理：
--   1. 应用层登录校验拒绝 archived 租户的用户登录
--   2. RLS 无需修改（租户已无法生成合法 session variable）
--   3. 定期清理任务（可选）：对 archived > 90 天的租户，批量清理业务数据（分表操作，非 CASCADE）
COMMENT ON COLUMN tenants.industry IS '租户所属行业，影响评分和情报推送';
COMMENT ON COLUMN tenants.balance IS 'AI功能余额（人民币），Phase 1 仅手动充值';
```

### 2.2 users — 用户

```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  email           VARCHAR(255) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  name            VARCHAR(100) NOT NULL,
  status          VARCHAR(20)  NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'disabled')),
  must_change_pwd BOOLEAN NOT NULL DEFAULT true,  -- 首次登录强制改密码
  last_login_at   TIMESTAMPTZ,
  -- 暴力破解防护
  failed_login_count INTEGER NOT NULL DEFAULT 0,   -- 连续登录失败次数，成功登录后重置为 0
  locked_until       TIMESTAMPTZ DEFAULT NULL,     -- 账户锁定截止时间（NULL = 未锁定）
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- 邮箱在租户内唯一（标准 SaaS 多租户模式）；同一邮箱可在多个租户被邀请
  -- 登录流程：前端统一访问 /login，显式输入 tenant slug；
  -- 仅 Tenant API 路径承载 slug（/t/{slug}/api/v1/...），
  -- 再以 (tenant_id, email) 查询用户。不支持仅凭 email 全局登录。
  UNIQUE (tenant_id, email)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE users IS '系统用户，属于某个租户。邮箱在租户内唯一';
COMMENT ON COLUMN users.must_change_pwd IS '首次登录向导第一步：强制修改密码';
COMMENT ON COLUMN users.email IS '租户内唯一；登录时需配合 tenant_id（或 slug）联合查询';
COMMENT ON COLUMN users.failed_login_count IS '连续失败次数，成功登录重置。建议阈值：5次失败 → locked_until = NOW() + 15min';
COMMENT ON COLUMN users.locked_until IS '锁定截止时间，应用层登录前检查 locked_until > NOW() 则拒绝';
```

> **RLS 与登录流程的兼容方案**：
> `users` 表启用 RLS（见 §9.3），但登录时 `tenant_id` 尚未设入会话变量，RLS 策略会阻止查询。解决方案（任选其一）：
> 1. **登录专用角色**：创建 `auth_service` 角色，仅授予 `users` 表 SELECT 权限且 `BYPASSRLS`。认证服务连接池使用该角色，验证通过后切换到 `app_user` 并设置 `tenant_id`。
> 2. **额外 RLS 策略**：为 `users` 表添加第二条 policy：`USING (email = current_setting('app.current_email', true))`，登录时仅设置 `app.current_email`，验证通过后再设置 `app.current_tenant_id`。
> 3. **登录查询绕过 RLS**：认证服务使用数据库函数（`SECURITY DEFINER`）执行登录查询，函数以表 owner 身份运行，不受 RLS 限制。
>
> 推荐方案 1（最小权限 + 职责清晰）。实施时须确保 `auth_service` 角色的连接池与 `app_user` 连接池物理隔离。

### 2.3 roles — 角色（RBAC）

```sql
-- 已确认三角色：admin / operator / viewer
CREATE TYPE user_role AS ENUM ('admin', 'operator', 'viewer');

CREATE TABLE user_roles (
  id          UUID PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id   UUID NOT NULL REFERENCES tenants(id),
  role        user_role NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (user_id, tenant_id, role)  -- 同一租户下同一用户不能重复同一角色
);

COMMENT ON TABLE user_roles IS '用户角色关联，RBAC 三角色：admin(管理员)/operator(业务员)/viewer(只读观察者)';
COMMENT ON COLUMN user_roles.role IS 'admin=全部权限, operator=业务操作, viewer=只读';
```

### 2.4 ai_models — AI 模型注册

```sql
CREATE TABLE ai_models (
  id              UUID PRIMARY KEY,
  provider        VARCHAR(50) NOT NULL,  -- 'openrouter'
  model_id        VARCHAR(100) NOT NULL, -- 'deepseek/deepseek-chat' 等
  display_name    VARCHAR(100) NOT NULL,
  model_type      VARCHAR(30) NOT NULL
                  CHECK (model_type IN ('scoring', 'email_generation', 'intelligence', 'general')),
  -- 计费
  input_price     NUMERIC(10,6) NOT NULL,  -- 每 1K token 输入价格（人民币）
  output_price    NUMERIC(10,6) NOT NULL,  -- 每 1K token 输出价格（人民币）
  -- 状态
  is_active       BOOLEAN NOT NULL DEFAULT true,
  config          JSONB NOT NULL DEFAULT '{}',  -- 模型特定配置（temperature, max_tokens 等）
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (provider, model_id)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON ai_models
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE ai_models IS '平台可用的AI模型注册表，运营后台管理';
COMMENT ON COLUMN ai_models.model_type IS '模型用途分类，决定在哪些场景可选';
COMMENT ON COLUMN ai_models.input_price IS '每1K token输入价格（人民币），用于租户计费';
```

### 2.5 ai_usage_logs — AI 调用计费日志

```sql
CREATE TABLE ai_usage_logs (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  user_id         UUID REFERENCES users(id),  -- 可为空（系统自动任务）
  model_id        UUID NOT NULL REFERENCES ai_models(id),
  -- 调用信息
  usage_type      VARCHAR(30) NOT NULL
                  CHECK (usage_type IN ('scoring', 'email_generation', 'intelligence_summary', 'other')),
  entity_type     VARCHAR(50),    -- 关联实体类型：'company' / 'email' / 'article'
                  CHECK (entity_type IS NULL OR entity_type IN (
                    'company', 'contact', 'plan', 'template', 'email',
                    'scoring_template', 'intelligence_source', 'article'
                  )),
  entity_id       UUID,           -- 关联实体ID
  -- token 消耗
  input_tokens    INTEGER NOT NULL DEFAULT 0,
  output_tokens   INTEGER NOT NULL DEFAULT 0,
  total_tokens    INTEGER NOT NULL DEFAULT 0,
  -- 费用（余额变动统一由 balance_transactions 单一来源记账）
  cost                NUMERIC(12,4) NOT NULL,  -- 本次调用费用（人民币）
  balance_transaction_id UUID REFERENCES balance_transactions(id),  -- 关联余额流水（⚠ 前向引用，DDL执行顺序见 §1.6）
  -- 时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ai_usage_logs IS 'AI调用计费明细，每次LLM调用记录一条。余额变动由 balance_transactions 唯一记账，避免双写不一致';
COMMENT ON COLUMN ai_usage_logs.cost IS '本次调用费用（人民币），由 token数 × 模型单价 计算（单价单位：元/1K token）';
COMMENT ON COLUMN ai_usage_logs.balance_transaction_id IS '指向 balance_transactions 中本次扣费记录，事务内同时写入';
```

### 2.6 data_source_credentials — 数据源凭证（平台级）

> 07 Phase 0 / Phase 1 要求平台运营管理外贸通/腾道/砺销云的账号密码池。多账号轮换以规避单账号限流。

```sql
CREATE TABLE data_source_credentials (
  id                      UUID PRIMARY KEY,
  source_type             VARCHAR(20) NOT NULL
                          CHECK (source_type IN ('waimao_tong', 'tengdao', 'lixiaoyun')),
  account_no              VARCHAR(50) NOT NULL,         -- 账号编号（如 "A01" / "B01"）
  username                VARCHAR(200) NOT NULL,
  password_encrypted      TEXT NOT NULL,                -- 应用层加密后存储（AES-256-GCM，密钥通过环境变量注入，见下方说明）
  extra_credentials       JSONB NOT NULL DEFAULT '{}',  -- 其他凭证字段（token/sess/uid 等）⚠ 必须加密后存入，禁止明文；加密方式同 password_encrypted
  -- 轮换与限流
  rotation_order          INTEGER NOT NULL DEFAULT 0,   -- 轮换序号（小者优先）
  daily_quota             INTEGER,                       -- 该账号每日调用上限（NULL 表示无限制）
  current_day_used        INTEGER NOT NULL DEFAULT 0,
  current_day_reset_at    DATE,
  -- 状态
  is_active               BOOLEAN NOT NULL DEFAULT true,
  last_used_at            TIMESTAMPTZ,
  last_error_at           TIMESTAMPTZ,
  last_error_message      TEXT,
  consecutive_error_count INTEGER NOT NULL DEFAULT 0,
  -- 加密密钥版本（明文存储，用于密钥轮换时判断用哪个密钥解密）
  -- ⚠ 不能存在加密字段内，否则解密时无法知道该用哪个密钥版本
  encryption_key_version  INTEGER NOT NULL DEFAULT 1,
  -- 时间
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (source_type, account_no)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON data_source_credentials
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE INDEX idx_data_source_credentials_active
  ON data_source_credentials(source_type, rotation_order)
  WHERE is_active = true;

COMMENT ON TABLE data_source_credentials IS '数据源账号凭证池（平台级），支持多账号轮换。Phase 1 必备';
COMMENT ON COLUMN data_source_credentials.password_encrypted IS '加密存储，密钥由环境变量管理。绝不明文落库';
COMMENT ON COLUMN data_source_credentials.rotation_order IS '轮换序号，调度器按序选择当日未达上限的可用账号';
```

> **凭证加密方案（Phase 1）**：
> - 算法：**AES-256-GCM**（对称加密 + 认证标签，防篡改）
> - 密钥管理：加密密钥通过环境变量 `CREDENTIAL_ENCRYPTION_KEY` 注入，不落库、不入代码仓库
> - 存储格式：`password_encrypted` 字段存储 `base64(nonce || ciphertext || auth_tag)`
> - Python 实现：使用 `cryptography` 库的 `AESGCM`（**不使用 Fernet**，因为 Fernet 底层为 AES-128-CBC，不满足 AES-256-GCM 要求）
> - 密钥轮换：更换密钥时需批量解密-重加密。密钥版本通过明文列 `encryption_key_version` 追踪（不存在加密字段内部，避免循环依赖）

### 2.7 platform_email_templates — 平台官方邮件模板

```sql
CREATE TABLE platform_email_templates (
  id              UUID PRIMARY KEY,
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  category        VARCHAR(50) NOT NULL,  -- 模板分类：'initial_contact' / 'follow_up' / 'industry_news' 等
  subject         TEXT NOT NULL,          -- 邮件主题模板（含变量占位符）
  body_html       TEXT NOT NULL,          -- 邮件正文HTML模板
  body_text       TEXT,                   -- 纯文本版本
  variables       JSONB NOT NULL DEFAULT '[]',  -- 可用变量列表
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON platform_email_templates
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE platform_email_templates IS '平台官方邮件模板（只读），租户可查看但不可修改';
COMMENT ON COLUMN platform_email_templates.variables IS '模板中可用的变量列表，如 [{name: "company_name", label: "公司名称"}]';
```

---

## 3. 共享数据池表设计

> 共享数据池存储从各数据源采集的原始公司和联系人数据。不启用 RLS，租户通过 `tenant_companies` 视图间接访问。

### 3.1 shared_companies — 共享公司池

```sql
CREATE TABLE shared_companies (
  id                  UUID PRIMARY KEY,
  -- 基本信息（合并后的权威数据）
  name                VARCHAR(500) NOT NULL,      -- 公司名称
  name_en             VARCHAR(500),               -- 英文名称
  country             VARCHAR(100),
  region              VARCHAR(100),               -- 省/州
  city                VARCHAR(100),
  address             TEXT,
  website             VARCHAR(500),
  domain              VARCHAR(255),               -- 主域名（从 website 提取）
  -- 行业信息
  industry            VARCHAR(200),
  industry_tags       JSONB DEFAULT '[]',         -- 行业标签数组
  -- 规模信息
  employee_count      VARCHAR(50),                -- '1-50' / '51-200' / '201-500' 等
  annual_revenue      VARCHAR(100),               -- 营收区间
  established_year    INTEGER,
  -- 外贸信息
  export_countries    JSONB DEFAULT '[]',         -- 出口国家列表
  product_keywords    JSONB DEFAULT '[]',         -- 产品关键词
  hs_codes            JSONB DEFAULT '[]',         -- HS编码列表
  -- 元数据
  data_completeness   NUMERIC(3,2) DEFAULT 0,     -- 数据完整度 0.00~1.00
  last_enriched_at    TIMESTAMPTZ,                -- 最后一次数据丰富时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON shared_companies
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE shared_companies IS '共享公司池，跨数据源合并后每家公司一条记录';
COMMENT ON COLUMN shared_companies.domain IS '从website提取的主域名，用于邮件发送和去重辅助';
COMMENT ON COLUMN shared_companies.data_completeness IS '数据完整度评分，字段填充比例';
```

### 3.2 company_sources — 公司数据源关联

```sql
CREATE TABLE company_sources (
  id                  UUID PRIMARY KEY,
  company_id          UUID NOT NULL REFERENCES shared_companies(id),
  -- 数据源信息
  source_type         VARCHAR(20) NOT NULL
                      CHECK (source_type IN ('waimao_tong', 'tengdao', 'lixiaoyun')),
  source_id           VARCHAR(200) NOT NULL,  -- 数据源中的原始ID
  -- 原始数据快照
  raw_data            JSONB NOT NULL DEFAULT '{}',  -- 该数据源返回的原始字段
  -- 时间
  first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- 首次从该数据源采集到
  last_synced_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- 最后同步时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (source_type, source_id)  -- 同一数据源同一ID只能关联一次
);

CREATE INDEX idx_company_sources_company ON company_sources(company_id);

COMMENT ON TABLE company_sources IS '公司与数据源的关联表，记录每条公司数据来自哪些数据源';
COMMENT ON COLUMN company_sources.source_id IS '数据源中的原始ID，去重主键';
COMMENT ON COLUMN company_sources.raw_data IS '数据源返回的原始JSON，用于数据溯源和字段优先级合并';
```

### 3.3 shared_contacts — 共享联系人池

```sql
CREATE TABLE shared_contacts (
  id                  UUID PRIMARY KEY,
  company_id          UUID NOT NULL REFERENCES shared_companies(id),
  -- 基本信息
  name                VARCHAR(200),
  name_en             VARCHAR(200),
  email               VARCHAR(255),
  phone               VARCHAR(50),
  -- 职位信息
  title               VARCHAR(200),          -- 职位名称
  department          VARCHAR(100),          -- 部门
  seniority_level     VARCHAR(30),           -- 'c_level' / 'vp' / 'director' / 'manager' / 'staff'
  -- 数据源
  source_type         VARCHAR(20) NOT NULL
                      CHECK (source_type IN ('waimao_tong', 'tengdao', 'lixiaoyun')),
  source_contact_id   VARCHAR(200),          -- 数据源中的联系人原始ID
  -- 元数据
  is_valid_email      BOOLEAN DEFAULT NULL,  -- 邮箱验证状态：null=未验证
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (company_id, email)  -- 同一公司同一邮箱不重复
  -- ⚠ 注意：PostgreSQL UNIQUE 允许多个 NULL email，即同公司可有多条 email=NULL 的联系人记录
  -- 如需防止无邮箱联系人重复入库，考虑额外的 UNIQUE (company_id, source_type, source_contact_id) 约束
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON shared_contacts
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE shared_contacts IS '共享联系人池，关联到共享公司';
COMMENT ON COLUMN shared_contacts.seniority_level IS '职级层次，用于联系人规则筛选';
```

### 3.4 company_blacklist — 公司黑名单（租户级）

> 07 场景⑨/⑩ + 08 公司列表"加入黑名单"按钮的语义承载。区别于 `tenant_companies.status='excluded'`（业务流程外排除），黑名单在采集入池前就过滤。

```sql
CREATE TABLE company_blacklist (
  id                  UUID PRIMARY KEY,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  shared_company_id   UUID REFERENCES shared_companies(id),  -- 已入共享池的精确匹配
  match_domain        VARCHAR(255),                          -- 按域名匹配（覆盖未入池公司）
  match_name_pattern  VARCHAR(500),                          -- 按公司名模糊匹配
  reason              TEXT NOT NULL,
  blocked_by          UUID NOT NULL REFERENCES users(id),
  blocked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- 时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CHECK (shared_company_id IS NOT NULL OR match_domain IS NOT NULL OR match_name_pattern IS NOT NULL)
);

CREATE INDEX idx_company_blacklist_tenant ON company_blacklist(tenant_id);
CREATE INDEX idx_company_blacklist_company ON company_blacklist(tenant_id, shared_company_id)
  WHERE shared_company_id IS NOT NULL;
CREATE INDEX idx_company_blacklist_domain ON company_blacklist(tenant_id, match_domain)
  WHERE match_domain IS NOT NULL;

COMMENT ON TABLE company_blacklist IS '租户级公司黑名单，采集去重和评分入池时优先过滤';
COMMENT ON COLUMN company_blacklist.match_name_pattern IS '公司名模糊匹配模式，语义为 ILIKE 包含匹配（应用层拼接 %%pattern%%）。⚠ 安全要求：禁止用户直接输入正则表达式；应用层须转义 LIKE 特殊字符（%_）；匹配查询应设 statement_timeout 防止恶意长模式';
```

### 3.5 competitor_companies — 竞品公司（排除库）

```sql
CREATE TABLE competitor_companies (
  id                UUID PRIMARY KEY,
  tenant_id         UUID NOT NULL REFERENCES tenants(id),
  shared_company_id UUID REFERENCES shared_companies(id),  -- 已入共享池则精确匹配
  company_name      VARCHAR(500) NOT NULL,                 -- 兼容未入池场景的字符串匹配
  domain            VARCHAR(255),
  reason            TEXT,                                  -- 排除原因
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, company_name)
);

CREATE INDEX idx_competitor_companies_shared
  ON competitor_companies(tenant_id, shared_company_id)
  WHERE shared_company_id IS NOT NULL;

COMMENT ON TABLE competitor_companies IS '竞品/排除公司库，采集和评分时自动排除。优先按 shared_company_id 精确匹配，未入池时回退到名称匹配';
```

---

## 4. 租户业务表 — 公司与评分

> 以下表全部启用 RLS，通过 `tenant_id` 隔离。

### 4.1 tenant_companies — 租户公司视图

```sql
CREATE TABLE tenant_companies (
  id                  UUID PRIMARY KEY,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  company_id          UUID NOT NULL REFERENCES shared_companies(id),
  -- 租户视角数据
  status              VARCHAR(20) NOT NULL DEFAULT 'pending_score'
                      CHECK (status IN (
                        'pending_score',    -- 待评分（余额不足时）
                        'scoring',          -- 评分中
                        'scored',           -- 已评分
                        'selected',         -- 已入选优选客户
                        'in_plan',          -- 已加入发送计划
                        'contacted',        -- 已发送邮件
                        'replied',          -- 已收到回复
                        'converted',        -- 已转化
                        'excluded'          -- 已排除
                      )),
  grade               CHAR(1) CHECK (grade IN ('S', 'A', 'B', 'C', 'D')),
  total_score         NUMERIC(5,2),         -- 综合评分 0~100
  -- 来源追溯
  keyword_id          UUID REFERENCES collection_keywords(id),  -- 触发采集的关键词ID
  collection_task_id  UUID,                 -- 采集任务ID
  -- 租户备注
  notes               TEXT,
  tags                JSONB DEFAULT '[]',   -- 租户自定义标签
  -- 软删除 + 时间
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, company_id)  -- 同一租户不重复关联同一公司
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_companies
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE tenant_companies IS '租户的公司视图，连接共享池与租户业务。每个租户看到的是自己关键词采集到的公司';
COMMENT ON COLUMN tenant_companies.status IS '公司在该租户业务流程中的状态';
COMMENT ON COLUMN tenant_companies.grade IS '评分等级 S/A/B/C/D，由评分规则计算得出';
```

### 4.2 scoring_templates — 评分规则模板

```sql
CREATE TABLE scoring_templates (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            VARCHAR(200) NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,  -- 是否为当前生效的模板
  -- 规则定义（JSONB，已确认 D3 决策）
  -- 结构示例见附录 14.1
  dimensions      JSONB NOT NULL,
  -- 等级阈值
  grade_thresholds JSONB NOT NULL DEFAULT '{
    "S": 90, "A": 75, "B": 60, "C": 40, "D": 0
  }',
  -- 版本管理
  version         INTEGER NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON scoring_templates
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 每个租户最多一个活跃模板
CREATE UNIQUE INDEX idx_scoring_templates_active
  ON scoring_templates(tenant_id) WHERE is_active = true;

COMMENT ON TABLE scoring_templates IS '租户评分规则模板，dimensions字段用JSONB存储完整规则定义';
COMMENT ON COLUMN scoring_templates.dimensions IS '评分维度定义，结构见附录14.1';
COMMENT ON COLUMN scoring_templates.grade_thresholds IS '等级分数阈值，S≥90, A≥75, B≥60, C≥40, D<40';
```

### 4.3 scoring_template_versions — 评分模板历史版本

> 评分模板每次修改自动归档；company_scores 引用具体版本而非当前活跃模板，保证历史评分可重现。

```sql
CREATE TABLE scoring_template_versions (
  id                UUID PRIMARY KEY,
  template_id       UUID NOT NULL REFERENCES scoring_templates(id),
  tenant_id         UUID NOT NULL REFERENCES tenants(id),
  version           INTEGER NOT NULL,
  -- 完整快照
  dimensions        JSONB NOT NULL,
  grade_thresholds  JSONB NOT NULL,
  -- 变更元数据
  changed_by        UUID REFERENCES users(id),
  change_reason     TEXT,
  snapshotted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (template_id, version)
);

CREATE INDEX idx_scoring_template_versions_tenant ON scoring_template_versions(tenant_id);
CREATE INDEX idx_scoring_template_versions_template ON scoring_template_versions(template_id);

COMMENT ON TABLE scoring_template_versions IS '评分模板历史快照，每次 scoring_templates UPDATE 触发器自动 INSERT';
```

### 4.4 company_scores — 公司评分明细

```sql
CREATE TABLE company_scores (
  id                  UUID PRIMARY KEY,
  tenant_company_id   UUID NOT NULL REFERENCES tenant_companies(id),
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  template_id         UUID NOT NULL REFERENCES scoring_templates(id),
  template_version_id UUID NOT NULL REFERENCES scoring_template_versions(id),  -- 精确到版本
  -- 评分结果
  total_score         NUMERIC(5,2) NOT NULL,
  grade               CHAR(1) NOT NULL CHECK (grade IN ('S', 'A', 'B', 'C', 'D')),
  -- 各维度评分明细（JSONB，与 template 版本的 dimensions 对应）
  dimension_scores    JSONB NOT NULL,
  -- LLM 辅助评分（语义匹配度维度）
  llm_score           NUMERIC(5,2),           -- LLM 给出的语义匹配分
  llm_reasoning       TEXT,                   -- LLM 评分理由
  llm_model_id        UUID REFERENCES ai_models(id),
  llm_usage_log_id    UUID,                   -- 关联AI调用记录
  -- 补评追踪（07 场景⑨：余额不足→pending_score→充值后补评）
  is_retry            BOOLEAN NOT NULL DEFAULT false,
  retry_count         INTEGER NOT NULL DEFAULT 0,
  related_score_id    UUID REFERENCES company_scores(id),  -- 首评的引用（补评时填）
  -- 时间
  scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- 防止并发评分产生重复：同一公司同一模板版本仅保留一条评分（补评除外）
  -- ⚠ PostgreSQL 不支持表级 UNIQUE 约束带 WHERE，须用 CREATE UNIQUE INDEX
);

CREATE UNIQUE INDEX idx_company_scores_unique_non_retry
  ON company_scores (tenant_company_id, template_version_id)
  WHERE (is_retry = false);

COMMENT ON TABLE company_scores IS '公司评分明细记录，每次评分生成一条';
COMMENT ON COLUMN company_scores.dimension_scores IS '各维度评分明细，结构: [{dimension_id, name, score, weight, weighted_score, matched_rules}]';
COMMENT ON COLUMN company_scores.llm_score IS '仅语义匹配维度使用LLM，其余维度为规则计算';
```

---

## 5. 租户业务表 — 联系人与群组

### 5.1 contact_rules — 联系人筛选规则

```sql
CREATE TABLE contact_rules (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            VARCHAR(200) NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  -- 规则定义（JSONB，已确认 D5 决策）
  -- 结构示例见附录 14.2
  rules           JSONB NOT NULL,
  -- 版本管理
  version         INTEGER NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON contact_rules
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE UNIQUE INDEX idx_contact_rules_active
  ON contact_rules(tenant_id) WHERE is_active = true;

COMMENT ON TABLE contact_rules IS '租户联系人筛选规则，rules字段用JSONB存储A/B/C/D分级条件';
COMMENT ON COLUMN contact_rules.rules IS '联系人筛选规则定义，结构见附录14.2';
```

### 5.2 tenant_contacts — 租户联系人

```sql
CREATE TABLE tenant_contacts (
  id                  UUID PRIMARY KEY,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  tenant_company_id   UUID NOT NULL REFERENCES tenant_companies(id),
  contact_id          UUID NOT NULL REFERENCES shared_contacts(id),
  -- 租户视角
  grade               CHAR(1) CHECK (grade IN ('A', 'B', 'C', 'D')),
  status              VARCHAR(20) NOT NULL DEFAULT 'available'
                      CHECK (status IN ('available', 'in_plan', 'contacted', 'replied', 'bounced', 'unsubscribed')),
  -- 软删除 + 时间
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, contact_id)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_contacts
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE tenant_contacts IS '租户联系人视图，连接共享联系人池与租户业务';
COMMENT ON COLUMN tenant_contacts.grade IS '联系人等级A/B/C/D，由联系人规则计算';
```

### 5.3 groups — 群组

```sql
CREATE TABLE groups (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  -- 自动规则（可选，为空则为手动群组）
  auto_rules      JSONB,  -- 自动纳入条件，如 {"grade_in": ["S","A"], "min_score": 75}
  -- 统计缓存
  member_count    INTEGER NOT NULL DEFAULT 0,  -- ⚠ 冗余计数：需通过触发器或应用层在 group_members INSERT/DELETE 时同步
  -- 软删除 + 时间
  deleted_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON groups
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE groups IS '收件人群组，用于组织优选客户。嵌入在优选客户页面左侧栏';
COMMENT ON COLUMN groups.auto_rules IS '自动群组的纳入规则，null表示手动群组';
```

### 5.4 group_members — 群组成员

```sql
CREATE TABLE group_members (
  id                  UUID PRIMARY KEY,
  group_id            UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  tenant_contact_id   UUID NOT NULL REFERENCES tenant_contacts(id),
  added_by            VARCHAR(10) NOT NULL DEFAULT 'manual'
                      CHECK (added_by IN ('manual', 'auto')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (group_id, tenant_contact_id)
);

COMMENT ON TABLE group_members IS '群组成员关联表';
COMMENT ON COLUMN group_members.added_by IS '加入方式：manual=手动添加, auto=自动规则匹配';
```

---

## 6. 租户业务表 — 邮件系统

### 6.1 email_templates — 租户邮件模板

```sql
CREATE TABLE email_templates (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  -- 来源
  source_type     VARCHAR(20) NOT NULL DEFAULT 'custom'
                  CHECK (source_type IN ('custom', 'platform_copy')),
  platform_template_id UUID REFERENCES platform_email_templates(id),  -- 如果是从平台模板复制的
  -- 模板内容
  name            VARCHAR(200) NOT NULL,
  category        VARCHAR(50) NOT NULL,
  subject         TEXT NOT NULL,
  body_html       TEXT NOT NULL,
  body_text       TEXT,
  variables       JSONB NOT NULL DEFAULT '[]',
  -- AI 生成相关
  is_ai_generated BOOLEAN NOT NULL DEFAULT false,
  ai_prompt       TEXT,  -- 生成该模板时的 prompt
  -- 软删除 + 时间
  deleted_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON email_templates
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE email_templates IS '租户邮件模板（双层体系：platform_copy来自平台模板，custom为租户自建）';
```

### 6.2 sending_plans — 发送计划

```sql
CREATE TABLE sending_plans (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  created_by      UUID NOT NULL REFERENCES users(id),
  -- 基本信息
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled')),
  -- 收件人来源
  recipient_source VARCHAR(20) NOT NULL
                  CHECK (recipient_source IN ('group', 'manual', 'filter')),
  recipient_config JSONB NOT NULL,  -- 收件人筛选配置
  -- 发送策略
  send_strategy   JSONB NOT NULL DEFAULT '{
    "timezone_aware": true,
    "preferred_hours": [9, 17],
    "daily_limit": 100,
    "interval_minutes": 5
  }',
  -- 域名/发件人
  sender_name     VARCHAR(200),
  sender_email    VARCHAR(255),
  domain_id       UUID REFERENCES domain_warmup_status(id),  -- 关联域名预热（⚠ 前向引用，DDL执行顺序见 §1.6）
  -- 统计缓存
  total_recipients INTEGER NOT NULL DEFAULT 0,
  sent_count       INTEGER NOT NULL DEFAULT 0,  -- ⚠ 冗余计数：需通过触发器或应用层在 emails INSERT(status='sent') 时同步
  -- 计划时间
  scheduled_at    TIMESTAMPTZ,  -- 计划开始时间
  started_at      TIMESTAMPTZ,  -- 实际开始时间
  completed_at    TIMESTAMPTZ,  -- 完成时间
  -- 软删除 + 时间
  deleted_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON sending_plans
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE sending_plans IS '发送计划（6步向导创建：基本信息→收件人→模板→策略→序列→确认）';
COMMENT ON COLUMN sending_plans.send_strategy IS '发送策略配置：时区感知、时间窗口、频率限制等';
COMMENT ON COLUMN sending_plans.sender_email IS '⚠ 应用层保存前必须校验：sender_email 的域名部分必须与 domain_warmup_status 中 verification_status=verified 的已验证域名匹配，否则拒绝创建计划';
```

### 6.3 sending_plan_recipients — 计划有效收件人

> 计划启动时先将 `recipient_config` 解算后的最终收件人锁定为启动快照，避免规则变化导致收件人漂移；
> 与 `07_REQUIREMENTS_SPEC.md` 保持一致，执行中允许以 append-only 方式补充新增收件人。

```sql
CREATE TABLE sending_plan_recipients (
  id                  UUID PRIMARY KEY,
  plan_id             UUID NOT NULL REFERENCES sending_plans(id) ON DELETE CASCADE,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  tenant_contact_id   UUID NOT NULL REFERENCES tenant_contacts(id),
  -- 快照来源
  source_type         VARCHAR(20) NOT NULL
                      CHECK (source_type IN ('group', 'manual', 'filter')),
  source_ref          UUID,                 -- 群组ID/筛选条件ID，按 source_type 解释
  locked_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  appended_after_start BOOLEAN NOT NULL DEFAULT false,  -- false=启动快照，true=运行中追加
  -- 排除标记（启动后被移出）
  excluded_at         TIMESTAMPTZ,
  excluded_reason     VARCHAR(100),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (plan_id, tenant_contact_id)
);

CREATE INDEX idx_sending_plan_recipients_plan ON sending_plan_recipients(plan_id);
CREATE INDEX idx_sending_plan_recipients_tenant ON sending_plan_recipients(tenant_id);

COMMENT ON TABLE sending_plan_recipients IS '发送计划当前有效收件人列表；包含启动快照和运行中追加对象，调度器以此表为准';
```

### 6.4 sequence_steps — 序列步骤定义

```sql
CREATE TABLE sequence_steps (
  id              UUID PRIMARY KEY,
  plan_id         UUID NOT NULL REFERENCES sending_plans(id) ON DELETE CASCADE,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  -- 步骤信息
  step_number     INTEGER NOT NULL,          -- 步骤序号，1=首封, 2=跟进1, ...
  template_id     UUID NOT NULL REFERENCES email_templates(id),
  -- 触发条件
  delay_days      INTEGER NOT NULL DEFAULT 0, -- 距上一步的间隔天数（首封为0）
  condition_type  VARCHAR(20) NOT NULL DEFAULT 'no_reply'
                  CHECK (condition_type IN (
                    'always',      -- 无条件发送（仅首封）
                    'no_reply',    -- 未回复才发
                    'no_open',     -- 未打开才发
                    'opened',      -- 打开了才发（升级内容）
                    'clicked'      -- 点击了才发
                  )),
  -- AI 个性化
  use_ai_personalization BOOLEAN NOT NULL DEFAULT false,
  ai_instructions TEXT,  -- AI 个性化指令
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (plan_id, step_number),
  -- 步骤数上限（防止无限序列拖垮调度器）
  CHECK (step_number BETWEEN 1 AND 10),
  -- 首封必须无条件发送，否则调度器会因"未回复"等待空回复而永不触发
  CHECK (
    (step_number = 1 AND condition_type = 'always' AND delay_days = 0)
    OR step_number > 1
  )
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON sequence_steps
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE sequence_steps IS '发送计划中的序列步骤定义（已确认D4：独立表建模）';
COMMENT ON COLUMN sequence_steps.step_number IS '步骤序号，1为首封邮件';
COMMENT ON COLUMN sequence_steps.delay_days IS '距上一步的间隔天数，首封为0';
COMMENT ON COLUMN sequence_steps.condition_type IS '触发条件：决定在什么情况下发送此步骤';
```

### 6.5 sequence_enrollments — 收件人序列进度

```sql
CREATE TABLE sequence_enrollments (
  id                  UUID PRIMARY KEY,
  plan_id             UUID NOT NULL REFERENCES sending_plans(id),
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  tenant_contact_id   UUID NOT NULL REFERENCES tenant_contacts(id),
  -- 进度追踪
  current_step        INTEGER NOT NULL DEFAULT 1,
  status              VARCHAR(20) NOT NULL DEFAULT 'active'
                      CHECK (status IN (
                        'active',       -- 进行中
                        'completed',    -- 所有步骤完成
                        'replied',      -- 收到回复，自动退出
                        'bounced',      -- 邮件退信，自动退出
                        'unsubscribed', -- 退订
                        'paused',       -- 暂停
                        'cancelled'     -- 取消
                      )),
  -- 时间节点
  enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_step_sent_at   TIMESTAMPTZ,
  next_step_due_at    TIMESTAMPTZ,  -- 下一步计划发送时间
  completed_at        TIMESTAMPTZ,
  -- 时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (plan_id, tenant_contact_id)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON sequence_enrollments
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE sequence_enrollments IS '收件人在序列中的进度追踪';
COMMENT ON COLUMN sequence_enrollments.current_step IS '当前所在步骤序号';
COMMENT ON COLUMN sequence_enrollments.next_step_due_at IS '下一步计划发送时间，调度器据此触发';
```

### 6.6 emails — 邮件发送记录（按月分区）

```sql
CREATE TABLE emails (
  id                  UUID NOT NULL,
  tenant_id           UUID NOT NULL REFERENCES tenants(id),
  plan_id             UUID REFERENCES sending_plans(id),
  step_id             UUID REFERENCES sequence_steps(id),
  step_number         INTEGER,                   -- 冗余字段：序列步骤序号（避免 JOIN sequence_steps）
  template_id         UUID REFERENCES email_templates(id),  -- 冗余字段：模板效果对比查询直读
  enrollment_id       UUID REFERENCES sequence_enrollments(id),
  tenant_contact_id   UUID NOT NULL REFERENCES tenant_contacts(id),
  -- 发送信息
  from_email          VARCHAR(255) NOT NULL,
  from_name           VARCHAR(200),
  to_email            VARCHAR(255) NOT NULL,
  to_name             VARCHAR(200),
  subject             TEXT NOT NULL,
  body_html           TEXT NOT NULL,
  body_text           TEXT,
  -- 回复内容（07 场景⑬：邮件往来需展示回复正文）
  reply_message_id    VARCHAR(200),              -- 回复邮件的外部 message id
  reply_from_email    VARCHAR(255),
  reply_subject       TEXT,
  reply_body_text     TEXT,
  reply_received_at   TIMESTAMPTZ,
  -- 状态
  status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK (status IN (
                        'pending',        -- 待发送
                        'queued',         -- 已加入队列
                        'sent',           -- 已发送
                        'delivered',      -- 已投递
                        'opened',         -- 已打开
                        'clicked',        -- 已点击
                        'replied',        -- 已回复
                        'bounced',        -- 退信
                        'complained',     -- 投诉
                        'unsubscribed',   -- 已退订
                        'failed'          -- 发送失败
                      )),
  -- AI 个性化
  is_ai_personalized  BOOLEAN NOT NULL DEFAULT false,
  ai_usage_log_id     UUID,  -- 关联AI调用记录
  -- EngageLab 相关
  engagelab_message_id VARCHAR(100),  -- EngageLab 返回的消息ID
  -- 时间节点
  scheduled_at        TIMESTAMPTZ,
  sent_at             TIMESTAMPTZ,
  delivered_at        TIMESTAMPTZ,
  opened_at           TIMESTAMPTZ,
  clicked_at          TIMESTAMPTZ,
  replied_at          TIMESTAMPTZ,
  bounced_at          TIMESTAMPTZ,
  -- 时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- PK 必须包含分区键（PostgreSQL 分区表硬性要求）
  PRIMARY KEY (id, created_at),
  -- 去重约束：同一入组同一步骤只发一次（分区表 UNIQUE 必须含分区键）
  -- ⚠ 局限：created_at 为分区键，不同时间戳可绕过此约束。
  --   应用层须在发送前执行: SELECT 1 FROM emails WHERE enrollment_id = ? AND step_id = ? LIMIT 1
  --   数据库层约束仅作为最后防线，不能替代应用层幂等检查。
  UNIQUE (enrollment_id, step_id, created_at)
) PARTITION BY RANGE (created_at);

-- 创建初始分区（示例）
-- CREATE TABLE emails_2026_04 PARTITION OF emails
--   FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

COMMENT ON TABLE emails IS '邮件发送记录（按月分区，已确认D10），记录每封邮件的完整生命周期';
COMMENT ON COLUMN emails.status IS '邮件状态，由EngageLab webhook回调更新';
COMMENT ON COLUMN emails.body_html IS '⚠ 安全要求：应用层存储前必须 HTML sanitize（推荐 bleach/ammonia），移除 script/iframe/event handler 等危险标签；管理后台预览回复内容时使用 sandboxed iframe + CSP 隔离';

-- ⚠ 性能说明：emails 表含 6 个 FK（plan_id, step_id, template_id, enrollment_id, tenant_contact_id, tenant_id），
-- INSERT 时 PostgreSQL 逐一校验 FK 存在性。Phase 1 日发送量 < 10K，每次 INSERT 增加约 1-2ms 延迟可接受。
-- 若未来日发送量 > 100K，可考虑：(1) 批量 INSERT; (2) 异步校验; (3) 移除低价值 FK 改为应用层保证。
```

### 6.7 email_events — 邮件事件追踪

```sql
CREATE TABLE email_events (
  id              UUID PRIMARY KEY,
  email_id        UUID NOT NULL,  -- 不加 FK 因为分区表
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  -- 事件信息
  event_type      VARCHAR(20) NOT NULL
                  CHECK (event_type IN (
                    'sent', 'delivered', 'opened', 'clicked',
                    'replied', 'bounced', 'complained', 'unsubscribed'
                  )),
  -- 事件详情
  metadata        JSONB DEFAULT '{}',  -- 事件元数据（IP、User-Agent、点击URL等）
  -- 来源
  source          VARCHAR(20) NOT NULL DEFAULT 'engagelab'
                  CHECK (source IN ('engagelab', 'system')),
  engagelab_event_id VARCHAR(100),
  -- 时间
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE email_events IS '邮件事件流水，由EngageLab webhook推送';
COMMENT ON COLUMN email_events.metadata IS '事件详情，如打开时的IP/UA、点击的URL等';
```

> **metadata PII 保留策略**：
> `metadata` 中可能包含 IP 地址和 User-Agent 等个人可识别信息（PII）。要求：
> 1. **90 天脱敏**：定时任务在事件创建 90 天后，将 `metadata` 中的 `ip`、`user_agent` 字段置空或哈希化（保留统计价值，移除可识别性）
> 2. **按角色过滤**：应用层返回 metadata 时，viewer 角色不可见 IP/UA 字段；仅 admin 可查看完整 metadata
> 3. **与 §11.3 数据保留策略配合**：email_events 温数据（3~12个月）中的 metadata 应已完成 PII 脱敏

> **跨表状态流转对齐说明**：
>
> | 事件来源 | emails.status | sequence_enrollments.status | tenant_contacts.status |
> |----------|--------------|---------------------------|----------------------|
> | 系统入队 | `pending` → `queued` | — | `available` → `in_plan` |
> | EngageLab 回调 `sent` | → `sent` | — | → `contacted` |
> | EngageLab 回调 `delivered` | → `delivered` | — | — |
> | EngageLab 回调 `opened` | → `opened` | — | — |
> | EngageLab 回调 `clicked` | → `clicked` | — | — |
> | EngageLab 回调 `replied` | → `replied` | → `replied` | → `replied` |
> | EngageLab 回调 `bounced` | → `bounced` | → `bounced` | → `bounced` |
> | EngageLab 回调 `complained` | → `complained` | _(应用层判断是否退出)_ | — |
> | EngageLab 回调 `unsubscribed` | → `unsubscribed` | → `unsubscribed` | → `unsubscribed` |
> | 系统错误 | → `failed` | — | — |
>
> `emails.status` 含 `pending`/`queued`/`failed` 三个系统内部状态，不出现在 `email_events.event_type` 中。
> 应用层负责在收到 webhook 时级联更新 `sequence_enrollments` 和 `tenant_contacts` 的状态。

> **Webhook 处理事务边界**：
> 收到 EngageLab webhook 回调时，以下操作必须在**同一数据库事务**内完成：
> 1. `INSERT INTO email_events` — 记录原始事件
> 2. `UPDATE emails SET status = ...` — 更新邮件状态
> 3. `UPDATE sequence_enrollments SET status = ...`（如适用）— 更新序列进度
> 4. `UPDATE tenant_contacts SET status = ...`（如适用）— 更新联系人状态
>
> 若任一步骤失败，整个事务回滚，webhook 返回 5xx 让发送方重试。
> 应用层须实现 webhook **幂等处理**：通过 `engagelab_event_id` 去重，避免重复回调导致状态错乱。

---

## 7. 租户业务表 — 情报系统

### 7.1 intelligence_sources — 情报源

```sql
CREATE TABLE intelligence_sources (
  id              UUID PRIMARY KEY,
  tenant_id       UUID REFERENCES tenants(id),  -- NULL = 平台级情报源（Admin API 管理），非 NULL = 租户自定义源（预留）
  -- 情报源信息
  name            VARCHAR(200) NOT NULL,
  source_type     VARCHAR(20) NOT NULL
                  CHECK (source_type IN ('rss', 'website', 'manual')),
  url             TEXT,
  -- 采集配置
  fetch_config    JSONB NOT NULL DEFAULT '{
    "frequency_hours": 24,
    "selector": null
  }',
  -- 行业分类
  industry_tags   JSONB DEFAULT '[]',
  -- 状态
  is_active       BOOLEAN NOT NULL DEFAULT true,
  last_fetched_at TIMESTAMPTZ,
  error_count     INTEGER NOT NULL DEFAULT 0,  -- 连续采集失败次数
  -- 软删除 + 时间
  deleted_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_sources
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE intelligence_sources IS '情报源配置，支持RSS/网页/手动导入';
COMMENT ON COLUMN intelligence_sources.fetch_config IS '采集配置：频率、CSS选择器等';
```

### 7.2 intelligence_articles — 情报文章（按月分区）

```sql
CREATE TABLE intelligence_articles (
  id                  UUID NOT NULL,
  source_id           UUID,  -- 情报源被删除后保留文章（SET NULL），文章不随源删除
  -- 注：tenant_id 已迁移至 intelligence_article_publications（多对多归属，详见下表）
  -- 文章内容
  title               VARCHAR(500) NOT NULL,
  url                 TEXT,
  author              VARCHAR(200),
  published_at        TIMESTAMPTZ,
  -- 原文 + AI摘要（已确认D11：全部存DB）
  content_raw         TEXT,            -- 原始内容
  content_summary     TEXT,            -- AI 生成的摘要
  -- AI 分类
  ai_category         VARCHAR(100),    -- AI 分类标签
  ai_tags             JSONB DEFAULT '[]',
  ai_relevance_score  NUMERIC(3,2),    -- AI 相关性评分 0~1
  ai_model_id         UUID REFERENCES ai_models(id),
  ai_usage_log_id     UUID,
  -- 状态
  status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processed', 'published', 'archived')),
  -- 时间
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- PK 必须包含分区键（PostgreSQL 分区表硬性要求）
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE intelligence_articles IS '情报文章（按月分区），含原文和AI摘要。归属关系见 intelligence_article_publications';
COMMENT ON COLUMN intelligence_articles.ai_relevance_score IS 'AI评估的行业相关性 0~1';
COMMENT ON COLUMN intelligence_articles.source_id IS '来源情报源ID，源被删除后置 NULL（文章保留）。不加 FK 因为分区表 + 跨租户共享场景，应用层保证引用完整性';

-- ⚠ 安全关键：app_user 禁止直接 SELECT 本表（无 tenant_id，存在跨租户泄漏风险）
-- 租户必须通过 v_tenant_articles 视图访问（见 §9.4）
REVOKE ALL ON intelligence_articles FROM app_user;
```

### 7.3 intelligence_article_publications — 情报文章租户归属（多对多）

> `intelligence_articles` 本身无 `tenant_id`（文章可跨租户共享）。归属关系通过本表实现多对多映射：
> 一篇文章可"发布"到多个租户的情报流中，每个租户独立维护已读/归档状态。

```sql
CREATE TABLE intelligence_article_publications (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  article_id      UUID NOT NULL,  -- 不加 FK 因为 intelligence_articles 是分区表
  article_created_at TIMESTAMPTZ NOT NULL,  -- 用于跨分区定位文章
  -- 租户侧状态
  status          VARCHAR(20) NOT NULL DEFAULT 'unread'
                  CHECK (status IN ('unread', 'read', 'starred', 'archived')),
  read_at         TIMESTAMPTZ,
  -- 推送来源
  matched_by      VARCHAR(30)
                  CHECK (matched_by IN ('subscription', 'manual', 'system')),
  subscription_id UUID REFERENCES intelligence_subscriptions(id),
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, article_id)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_article_publications
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE INDEX idx_article_publications_tenant ON intelligence_article_publications(tenant_id);
CREATE INDEX idx_article_publications_article ON intelligence_article_publications(article_id);
CREATE INDEX idx_article_publications_status ON intelligence_article_publications(tenant_id, status);

COMMENT ON TABLE intelligence_article_publications IS '情报文章的租户归属（多对多），每条记录代表一篇文章"发布"到一个租户的情报流';
COMMENT ON COLUMN intelligence_article_publications.article_created_at IS '文章的 created_at，用于与分区表 intelligence_articles 联合查询';
COMMENT ON COLUMN intelligence_article_publications.matched_by IS '匹配来源：subscription=自动订阅匹配, manual=手动推送, system=系统推荐';
```

> **注意**：本表引用了 `intelligence_subscriptions(id)`，DDL 执行时须确保 `intelligence_subscriptions` 已先创建。
> 建议执行顺序：`intelligence_sources` → `intelligence_articles` → `intelligence_subscriptions` → `intelligence_article_publications`。

### 7.4 intelligence_subscriptions — 情报订阅/推送配置

```sql
CREATE TABLE intelligence_subscriptions (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  -- 订阅配置
  industry_tags   JSONB NOT NULL DEFAULT '[]',  -- 关注的行业标签
  min_relevance   NUMERIC(3,2) DEFAULT 0.5,     -- 最低相关性阈值
  -- 推送配置
  notify_enabled  BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_subscriptions
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE intelligence_subscriptions IS '用户的情报订阅偏好，控制站内消息推送';
```

---

## 8. 系统支撑表

### 8.1 audit_logs — 审计日志（按月分区）

```sql
CREATE TABLE audit_logs (
  id              UUID NOT NULL,
  tenant_id       UUID REFERENCES tenants(id),  -- 平台操作可为空
  user_id         UUID REFERENCES users(id),    -- 系统操作可为空
  -- 操作信息
  action          VARCHAR(20) NOT NULL
                  CHECK (action IN ('create', 'update', 'delete', 'login', 'logout', 'export', 'other')),
  entity_type     VARCHAR(50) NOT NULL   -- 'company' / 'plan' / 'template' 等
                  CHECK (entity_type IN (
                    'tenant', 'user', 'company', 'contact', 'group',
                    'plan', 'template', 'email', 'scoring_template',
                    'intelligence_source', 'intelligence_subscription',
                    'keyword', 'domain', 'blacklist', 'competitor'
                  )),
  entity_id       UUID,
  -- 变更内容
  old_value       JSONB,                  -- 变更前（仅 update/delete）
  new_value       JSONB,                  -- 变更后（仅 create/update）
  -- 请求上下文
  ip_address      INET,
  user_agent      TEXT,
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- PK 必须包含分区键（PostgreSQL 分区表硬性要求）
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE audit_logs IS '审计日志（已确认D7：独立审计表，按月分区）';

-- ⚠ 审计完整性：RLS 策略只允许 app_user INSERT + SELECT，禁止 UPDATE/DELETE（不创建对应 policy）
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

CREATE POLICY audit_insert_only ON audit_logs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY audit_select ON audit_logs
  FOR SELECT USING (tenant_id = current_tenant_id());
-- 不创建 UPDATE/DELETE policy → app_user 无法修改/删除审计记录
```

### 8.2 notifications — 站内消息

```sql
CREATE TABLE notifications (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  -- 消息内容
  title           VARCHAR(200) NOT NULL,
  content         TEXT NOT NULL,
  category        VARCHAR(30) NOT NULL
                  CHECK (category IN (
                    'scoring_complete',    -- 评分完成
                    'plan_complete',       -- 发送计划完成
                    'reply_received',      -- 收到回复
                    'balance_low',         -- 余额不足
                    'intelligence',        -- 情报推送
                    'system'               -- 系统通知
                  )),
  -- 关联实体（可选）
  entity_type     VARCHAR(50)
                  CHECK (entity_type IS NULL OR entity_type IN (
                    'company', 'contact', 'plan', 'email',
                    'scoring_template', 'intelligence_source', 'article'
                  )),
  entity_id       UUID,
  -- 状态
  is_read         BOOLEAN NOT NULL DEFAULT false,
  read_at         TIMESTAMPTZ,
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE notifications IS '站内消息（铃铛下拉，最近20条）';
```

### 8.3 domain_warmup_status — 域名预热状态

```sql
CREATE TABLE domain_warmup_status (
  id                    UUID PRIMARY KEY,
  tenant_id             UUID NOT NULL REFERENCES tenants(id),
  domain                VARCHAR(255) NOT NULL,
  -- DNS 验证（07 场景⑦ Step 2，预热前置条件）
  spf_record            TEXT,
  dkim_record           TEXT,
  dmarc_record          TEXT,
  verification_status   VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (verification_status IN ('pending', 'verifying', 'verified', 'failed')),
  dns_verified_at       TIMESTAMPTZ,
  dns_last_checked_at   TIMESTAMPTZ,
  -- 预热状态（动态指标驱动6档，已确认）
  warmup_level          INTEGER NOT NULL DEFAULT 1 CHECK (warmup_level BETWEEN 1 AND 6),
  daily_limit           INTEGER NOT NULL DEFAULT 10,  -- 当前每日发送上限
  -- 指标追踪（当前快照）
  total_sent            INTEGER NOT NULL DEFAULT 0,
  bounce_rate           NUMERIC(5,4) DEFAULT 0,
  complaint_rate        NUMERIC(5,4) DEFAULT 0,
  open_rate             NUMERIC(5,4) DEFAULT 0,
  -- 时间
  level_changed_at      TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, domain)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON domain_warmup_status
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE domain_warmup_status IS '域名预热当前状态。需 verification_status=verified 才允许发送';
COMMENT ON COLUMN domain_warmup_status.warmup_level IS '预热等级1~6，根据发送指标动态调整。历史变化见 domain_warmup_history';

-- 8.3.1 域名预热历史快照（08 域名预热中心需要趋势图）
CREATE TABLE domain_warmup_history (
  id                UUID PRIMARY KEY,
  warmup_status_id  UUID NOT NULL REFERENCES domain_warmup_status(id) ON DELETE CASCADE,
  tenant_id         UUID NOT NULL REFERENCES tenants(id),
  domain            VARCHAR(255) NOT NULL,
  -- 快照
  warmup_level      INTEGER NOT NULL,
  daily_limit       INTEGER NOT NULL,
  total_sent        INTEGER NOT NULL,
  bounce_rate       NUMERIC(5,4),
  complaint_rate    NUMERIC(5,4),
  open_rate         NUMERIC(5,4),
  -- 变化原因
  change_type       VARCHAR(20) NOT NULL
                    CHECK (change_type IN ('level_up', 'level_down', 'daily_snapshot', 'manual_adjust')),
  change_reason     TEXT,
  changed_by        UUID REFERENCES users(id),  -- 系统自动则为 NULL
  -- 时间
  snapshot_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domain_warmup_history_status ON domain_warmup_history(warmup_status_id, snapshot_at);
CREATE INDEX idx_domain_warmup_history_tenant ON domain_warmup_history(tenant_id, domain, snapshot_at);

COMMENT ON TABLE domain_warmup_history IS '域名预热历史快照，按日生成 + 升降级事件触发';
```

### 8.4 collection_tasks — 采集任务

```sql
CREATE TABLE collection_tasks (
  id              UUID PRIMARY KEY,
  -- 任务信息
  scheduled_for   DATE NOT NULL DEFAULT CURRENT_DATE,  -- 调度日期（按日去重）
  normalized_keyword VARCHAR(200) NOT NULL,           -- 归一化关键词，如 trim/lower 后结果
  display_keyword VARCHAR(200) NOT NULL,              -- 展示给运营/日志的原始关键词
  source_type     VARCHAR(20) NOT NULL
                  CHECK (source_type IN ('waimao_tong', 'tengdao', 'lixiaoyun')),
  keyword_ids     JSONB NOT NULL,                     -- 本次去重任务覆盖的 collection_keywords.id 列表
  -- 状态
  status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  lease_owner     VARCHAR(100),                       -- 领取任务的服务实例标识
  lease_expires_at TIMESTAMPTZ,                       -- claim/lease 模式的租约过期时间
  -- 结果统计
  total_found     INTEGER DEFAULT 0,
  new_companies   INTEGER DEFAULT 0,
  duplicate_count INTEGER DEFAULT 0,
  -- 错误信息
  error_message   TEXT,
  retry_count     INTEGER NOT NULL DEFAULT 0,
  -- 时间
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (scheduled_for, normalized_keyword, source_type)
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_tasks
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE collection_tasks IS '去重后的共享采集任务；同一关键词同一数据源每天仅创建一条任务，再回关联多个租户关键词';
```

### 8.5 collection_keywords — 采集关键词

```sql
CREATE TABLE collection_keywords (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  -- 关键词信息
  keyword         VARCHAR(200) NOT NULL,
  source_types    JSONB NOT NULL DEFAULT '["waimao_tong"]',  -- 适用的数据源
  -- 配置
  is_active       BOOLEAN NOT NULL DEFAULT true,
  auto_collect    BOOLEAN NOT NULL DEFAULT true,  -- 是否自动定期采集
  collect_frequency_hours INTEGER DEFAULT 168,     -- 采集频率（默认7天）
  -- 统计
  total_companies INTEGER NOT NULL DEFAULT 0,      -- 累计采集公司数
  last_collected_at TIMESTAMPTZ,
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, keyword)  -- 同一租户不重复关键词
);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_keywords
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

COMMENT ON TABLE collection_keywords IS '租户采集关键词（首次登录向导第2步必填）';
COMMENT ON COLUMN collection_keywords.source_types IS '该关键词适用的数据源列表';
```

### 8.6 balance_transactions — 余额变动记录

```sql
CREATE TABLE balance_transactions (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  -- 变动信息
  type            VARCHAR(20) NOT NULL
                  CHECK (type IN ('recharge', 'consumption', 'refund', 'adjustment')),
  amount          NUMERIC(12,4) NOT NULL,  -- 正数=充值，负数=消耗
  balance_before  NUMERIC(12,4) NOT NULL,
  balance_after   NUMERIC(12,4) NOT NULL,
  -- 完整性约束
  CHECK (balance_after = balance_before + amount),
  -- 关联
  reference_type  VARCHAR(50),  -- 'ai_usage_log' / 'manual_recharge' 等
  reference_id    UUID,
  description     TEXT,
  -- 操作人
  operated_by     UUID REFERENCES users(id),  -- 手动充值时为运营人员
  -- 时间
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE balance_transactions IS '租户余额变动流水，充值和消耗的完整记录';
```

#### 并发扣费处理（原子条件更新）

> AI 调用等高频扣费场景存在并发竞态风险。采用**原子条件更新**（也称乐观并发控制），在 `UPDATE` 语句中内联余额校验，避免 TOCTOU 竞态：
> ⚠ 注：此处并非传统 ORM 乐观锁（读取→修改→带版本号写回→冲突重试），而是单条 SQL 原子完成校验+扣减，无需重试循环。

```sql
-- 应用层扣费伪代码（单条 SQL，原子操作）
UPDATE tenants
  SET balance = balance - :amount,
      updated_at = NOW()
WHERE id = :tenant_id
  AND balance >= :amount
RETURNING balance;

-- RETURNING 返回空 → 余额不足，应用层拒绝请求
-- RETURNING 返回新余额 → 扣费成功，随后 INSERT balance_transactions 记录流水
-- 整个流程在同一事务内完成（BEGIN ... COMMIT）
```

> **为什么不用悲观锁（SELECT FOR UPDATE）**：原子条件更新在低冲突场景（租户级别并发通常 < 10 QPS）性能更优，无需持锁等待。若未来出现高并发热点租户，可升级为 `SELECT ... FOR UPDATE SKIP LOCKED` 排队模式。

---

## 9. RLS 策略设计

### 9.1 RLS 总体方案

```sql
-- 1. 创建应用角色（非 superuser）
CREATE ROLE app_user;

-- 2. 设置 session 变量传递 tenant_id
-- 应用层在每次请求时执行：
-- SET LOCAL app.current_tenant_id = '<tenant_uuid>';

-- 3. 辅助函数（fail-closed：未设置 tenant_id 时抛异常，而非返回 NULL）
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
DECLARE
  tid UUID;
BEGIN
  tid := NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
  IF tid IS NULL THEN
    RAISE EXCEPTION 'app.current_tenant_id is not set — RLS 会话变量未初始化';
  END IF;
  RETURN tid;
END;
$$ LANGUAGE plpgsql STABLE SET search_path = pg_catalog;
```

> **Session 变量安全说明**：
> - `SET LOCAL app.current_tenant_id` 仅在当前事务内生效（`SET LOCAL` 在事务结束后自动重置），不会泄漏到其他请求。
> - 应用层连接池（如 SQLAlchemy + pgBouncer）必须确保：**每个请求在获取连接后立即 `SET LOCAL`，事务结束后变量自动失效**。
> - 若使用 pgBouncer transaction mode（推荐），`SET LOCAL` 天然安全；若使用 session mode，须在连接归还前执行 `RESET ALL` 清理变量。
> - **禁止在应用层使用 `SET`（不带 LOCAL）**，否则变量会持续到连接释放，导致连接复用时租户泄漏。

### 9.2 RLS Policy 模板

对每张需要 RLS 的租户业务表，应用以下模式：

```sql
-- 以 tenant_companies 为例
ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_companies FORCE ROW LEVEL SECURITY;

-- 租户只能看到自己的数据
CREATE POLICY tenant_isolation ON tenant_companies
  USING (tenant_id = current_tenant_id());

-- 写入时自动绑定 tenant_id
CREATE POLICY tenant_insert ON tenant_companies
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
```

### 9.3 需要启用 RLS 的表清单

> 决策修订：D1 已确认共享池/计费等"租户敏感"表也必须启用 RLS。原方案"共享池由应用层控制"被弃用，改为：
> - **ai_usage_logs / balance_transactions** 等含 tenant_id 的计费类表 → 启用 RLS。平台跨租户统计走 `BYPASSRLS` 角色或物化视图。
> - **shared_companies / shared_contacts / company_sources** → 原表仅平台角色可读写；租户访问统一走 `v_tenant_visible_companies` 等 SECURITY DEFINER 视图（见 §9.4）。
> - **audit_logs** → 启用 RLS，平台审计员用 `BYPASSRLS` 角色查询。

| 表名 | RLS | 说明 |
|------|-----|------|
| tenant_companies | ✅ | 核心业务表 |
| scoring_templates | ✅ | 租户规则 |
| scoring_template_versions | ✅ | 评分模板历史快照 |
| company_scores | ✅ | 评分数据 |
| contact_rules | ✅ | 租户规则 |
| tenant_contacts | ✅ | 核心业务表 |
| groups | ✅ | 群组 |
| group_members | ✅ | 群组成员 |
| email_templates | ✅ | 租户模板 |
| sending_plans | ✅ | 发送计划 |
| sending_plan_recipients | ✅ | 计划有效收件人（启动快照 + 运行中追加） |
| sequence_steps | ✅ | 序列步骤 |
| sequence_enrollments | ✅ | 序列进度 |
| emails | ✅ | 邮件记录 |
| email_events | ✅ | 邮件事件 |
| intelligence_sources | ❌ | 情报源（平台级资源，`tenant_id` 可为 NULL；Admin API 管理，不适用 RLS） |
| intelligence_article_publications | ✅ | 情报文章租户归属（多对多） |
| intelligence_subscriptions | ✅ | 情报订阅 |
| notifications | ✅ | 站内消息 |
| collection_keywords | ✅ | 采集关键词 |
| collection_tasks | ✅ | 采集任务 |
| domain_warmup_status | ✅ | 域名预热 |
| domain_warmup_history | ✅ | 域名预热历史快照 |
| balance_transactions | ✅ | 余额变动 |
| competitor_companies | ✅ | 竞品排除库 |
| company_blacklist | ✅ | 公司黑名单 |
| **ai_usage_logs** | ✅ **(修订)** | 计费表，含 tenant_id 必须 RLS；平台统计走 BYPASSRLS 或物化视图 |
| **tenants** | ❌ | 平台管理 |
| **users** | ✅ **(修订)** | 含 PII（email/name），启用 RLS；策略 `tenant_id = current_tenant_id()`；平台管理走 BYPASSRLS |
| **user_roles** | ✅ **(修订)** | 随 users 启用 RLS，策略同上 |
| **ai_models** | ❌ | 平台配置 |
| **platform_email_templates** | ❌ | 平台模板（所有租户可见） |
| **data_source_credentials** | ❌ | 平台凭证池，仅运营可见 |
| **intelligence_articles** | ❌ | 文章原表无 tenant_id；归属通过 publications 表。⚠ **app_user 无直接 SELECT 权限**，须通过 `v_tenant_articles` 视图访问（见 §9.4） |
| **shared_companies** | ❌ | 共享池，仅平台角色直查；租户走视图 |
| **company_sources** | ❌ | 共享池辅助 |
| **shared_contacts** | ❌ | 共享池，仅平台角色直查；租户走视图 |
| **audit_logs** | ✅ **(修订)** | 启用 RLS；平台审计员用 BYPASSRLS 角色 |

### 9.4 共享池 SECURITY DEFINER 视图（租户访问代理）

> 共享池原表不开放给应用角色，租户通过以下视图访问，自动按 `tenant_companies` 关联过滤。

```sql
-- 租户可见的共享公司视图（仅返回该租户已入池的公司）
-- ⚠ 最小权限原则：显式列出返回字段，不使用 SELECT *
CREATE OR REPLACE VIEW v_tenant_visible_companies
WITH (security_invoker = false) AS  -- DEFINER 模式
SELECT sc.id, sc.name, sc.domain, sc.website, sc.country, sc.industry,
       sc.employee_count, sc.data_completeness,
       sc.created_at, sc.updated_at
FROM shared_companies sc
JOIN tenant_companies tc ON tc.company_id = sc.id
WHERE tc.tenant_id = current_tenant_id()
  AND tc.deleted_at IS NULL;

-- 租户可见的共享联系人视图
CREATE OR REPLACE VIEW v_tenant_visible_contacts
WITH (security_invoker = false) AS
SELECT sct.id, sct.company_id, sct.name, sct.title, sct.department,
       sct.seniority_level, sct.email, sct.phone,
       sct.created_at, sct.updated_at
FROM shared_contacts sct
JOIN tenant_contacts tcon ON tcon.contact_id = sct.id
WHERE tcon.tenant_id = current_tenant_id()
  AND tcon.deleted_at IS NULL;

-- 视图所有者必须是拥有 shared_* 表权限的角色（如 db_owner）
-- 应用角色 app_user 仅授予视图 SELECT 权限，无法直接 SELECT shared_companies
REVOKE ALL ON shared_companies FROM app_user;
REVOKE ALL ON shared_contacts FROM app_user;
REVOKE ALL ON company_sources FROM app_user;
GRANT SELECT ON v_tenant_visible_companies TO app_user;
GRANT SELECT ON v_tenant_visible_contacts TO app_user;

-- ⚠ Viewer 角色 PII 脱敏说明：
-- v_tenant_visible_contacts 返回 email/phone 等 PII 字段。应用层须按用户角色决定是否脱敏：
--   - admin/operator：完整显示 email、phone
--   - viewer：email 显示为 j***@example.com，phone 显示为 +1***789（或完全隐藏）
-- 如 viewer 访问量大或脱敏逻辑复杂，可考虑创建独立的 v_tenant_contacts_viewer 视图，
-- 在 SQL 层用 regexp_replace() 脱敏，避免应用层遗漏。

-- 租户可见的情报文章视图（通过 publications 归属过滤）
-- intelligence_articles 原表无 tenant_id，app_user 无直接 SELECT 权限
CREATE OR REPLACE VIEW v_tenant_articles
WITH (security_invoker = false) AS
SELECT ia.id, ia.source_id, ia.title, ia.url, ia.author, ia.published_at,
       ia.content_summary, ia.ai_category, ia.ai_tags, ia.ai_relevance_score,
       ia.status AS article_status, ia.created_at,
       -- iap 字段映射：status → 布尔派生列（兼容 UI 层）
       (iap.status IN ('read', 'starred')) AS is_read,
       (iap.status = 'starred') AS is_bookmarked,
       iap.status AS publication_status,
       iap.read_at,
       iap.created_at AS tenant_published_at
FROM intelligence_articles ia
JOIN intelligence_article_publications iap
  ON iap.article_id = ia.id
 AND iap.article_created_at = ia.created_at  -- 分区键条件，避免全分区扫描
WHERE iap.tenant_id = current_tenant_id();

REVOKE ALL ON intelligence_articles FROM app_user;
GRANT SELECT ON v_tenant_articles TO app_user;

-- ⚠ search_path 安全加固（防 CVE-2018-1058 类攻击）：
-- current_tenant_id() 已设置 SET search_path = pg_catalog（见 §9.1）
-- 禁止 app_user 在 public schema 创建对象（防止同名函数/表劫持）
REVOKE CREATE ON SCHEMA public FROM app_user;
```

### 9.5 平台跨租户统计的 BYPASSRLS 角色

```sql
-- 平台运营/统计角色，绕过 RLS
CREATE ROLE platform_admin BYPASSRLS;
-- 安全加固：限制并发连接数 + 强制语句超时（防凭证泄漏后的暴力使用和误操作全表扫描）
ALTER ROLE platform_admin CONNECTION LIMIT 5;
ALTER ROLE platform_admin SET statement_timeout = '30s';
-- 应用层在平台后台请求时切换到该角色（SET ROLE platform_admin）
```

### 9.5 service_* 角色（服务间调用）

```sql
-- 服务间调用角色按职责拆分，避免共享单一高权限身份
CREATE ROLE service_collection BYPASSRLS;
CREATE ROLE service_scoring BYPASSRLS;
CREATE ROLE service_sending BYPASSRLS;
CREATE ROLE service_webhook BYPASSRLS;

-- 安全加固：限制并发连接数 + 强制语句超时
ALTER ROLE service_collection CONNECTION LIMIT 10;
ALTER ROLE service_collection SET statement_timeout = '60s';
ALTER ROLE service_scoring CONNECTION LIMIT 10;
ALTER ROLE service_scoring SET statement_timeout = '60s';
ALTER ROLE service_sending CONNECTION LIMIT 10;
ALTER ROLE service_sending SET statement_timeout = '60s';
ALTER ROLE service_webhook CONNECTION LIMIT 10;
ALTER ROLE service_webhook SET statement_timeout = '60s';

-- 仅分配给对应服务的独立连接池（service_pool 按服务拆分）
```

> **service_* 角色说明**：
> - `service_collection`、`service_scoring`、`service_sending`、`service_webhook` 分别服务于采集、评分、发送、Webhook 处理连接池；禁止再共享单一 `service_user`。
> - 与 `platform_admin` 的区别：`service_*` 面向**自动化服务**（无人值守），`platform_admin` 面向**人工运营后台**（有审计要求）。
> - **最小权限**：仅授予每个 `service_*` 必要表的 INSERT/UPDATE/SELECT 权限（不授予 DROP/TRUNCATE/ALTER），具体授权在 §9.6 中补充。
> - **审计要求**：同 `platform_admin`，所有写操作须通过应用层强制写入 `audit_logs`，建议启用 `log_statement = 'all'`。

> **角色隔离安全说明**：
> - `platform_admin` 角色**仅分配给平台后台管理服务的连接池**（独立的 pgBouncer pool / 独立的 SQLAlchemy engine），面向内部运营后台。
> - **租户 API 连接池使用 `app_user` 角色**，永远无法 `SET ROLE platform_admin`（需要 PostgreSQL `GRANT platform_admin TO app_user` 才行，我们不授予）。
> - 若需要在同一应用进程中同时支持两种角色，须维护两个独立连接池，按请求来源路由。
> - **审计要求**：`platform_admin` 拥有 BYPASSRLS 权限，其操作不受 `audit_logs` RLS 策略限制。所有 `platform_admin` 写操作**必须通过应用层强制写入 `audit_logs`**（不依赖数据库 policy）。建议在 PostgreSQL 配置中为该角色启用 `log_statement = 'all'` 级别审计。

---

## 10. 索引策略

### 10.1 通用原则

- 所有 `tenant_id` 列创建索引（RLS 过滤的基础）
- 外键列自动创建索引
- 高频查询条件创建复合索引
- JSONB 字段按需创建 GIN 索引

### 10.2 核心索引清单

```sql
-- === 平台层 ===
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_tenant ON user_roles(tenant_id);
CREATE INDEX idx_ai_usage_logs_tenant ON ai_usage_logs(tenant_id);
CREATE INDEX idx_ai_usage_logs_created ON ai_usage_logs(created_at);

-- === 共享池 ===
CREATE INDEX idx_shared_companies_domain ON shared_companies(domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_shared_companies_name ON shared_companies(name);
CREATE INDEX idx_shared_companies_industry ON shared_companies(industry);
CREATE INDEX idx_shared_contacts_company ON shared_contacts(company_id);
CREATE INDEX idx_shared_contacts_email ON shared_contacts(email) WHERE email IS NOT NULL;

-- === 租户业务-公司 ===
CREATE INDEX idx_tenant_companies_tenant ON tenant_companies(tenant_id);
CREATE INDEX idx_tenant_companies_status ON tenant_companies(tenant_id, status);
CREATE INDEX idx_tenant_companies_grade ON tenant_companies(tenant_id, grade);
CREATE INDEX idx_tenant_companies_keyword ON tenant_companies(keyword_id);
CREATE INDEX idx_company_scores_tenant_company ON company_scores(tenant_company_id);

-- === 租户业务-联系人 ===
CREATE INDEX idx_tenant_contacts_tenant ON tenant_contacts(tenant_id);
CREATE INDEX idx_tenant_contacts_company ON tenant_contacts(tenant_company_id);
CREATE INDEX idx_tenant_contacts_status ON tenant_contacts(tenant_id, status);
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_contact ON group_members(tenant_contact_id);

-- === 邮件系统 ===
CREATE INDEX idx_sending_plans_tenant ON sending_plans(tenant_id);
CREATE INDEX idx_sending_plans_status ON sending_plans(tenant_id, status);
CREATE INDEX idx_sequence_steps_plan ON sequence_steps(plan_id);
CREATE INDEX idx_sequence_enrollments_plan ON sequence_enrollments(plan_id);
CREATE INDEX idx_sequence_enrollments_status ON sequence_enrollments(tenant_id, status);
CREATE INDEX idx_sequence_enrollments_next_due ON sequence_enrollments(next_step_due_at)
  WHERE status = 'active';  -- 调度器高频查询
CREATE INDEX idx_emails_tenant ON emails(tenant_id);
CREATE INDEX idx_emails_plan ON emails(plan_id);
CREATE INDEX idx_emails_contact ON emails(tenant_contact_id);
CREATE INDEX idx_emails_status ON emails(tenant_id, status);
CREATE INDEX idx_emails_engagelab ON emails(engagelab_message_id) WHERE engagelab_message_id IS NOT NULL;
CREATE INDEX idx_email_events_email ON email_events(email_id);
CREATE INDEX idx_email_events_type ON email_events(tenant_id, event_type);

-- === 情报系统 ===
CREATE INDEX idx_intelligence_sources_tenant ON intelligence_sources(tenant_id) WHERE tenant_id IS NOT NULL;
-- 注：intelligence_articles 无 tenant_id（归属通过 intelligence_article_publications）
CREATE INDEX idx_intelligence_articles_source ON intelligence_articles(source_id);
CREATE INDEX idx_intelligence_articles_status ON intelligence_articles(status);
-- intelligence_article_publications 的索引已在 §7.3 表定义中内联创建

-- === 系统支撑 ===
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_tenant ON notifications(tenant_id);
CREATE INDEX idx_collection_keywords_tenant ON collection_keywords(tenant_id);
CREATE INDEX idx_collection_tasks_tenant ON collection_tasks(tenant_id);
CREATE INDEX idx_collection_tasks_status ON collection_tasks(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_balance_transactions_tenant ON balance_transactions(tenant_id);
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_domain_warmup_status_tenant ON domain_warmup_status(tenant_id);
CREATE INDEX idx_competitor_companies_tenant ON competitor_companies(tenant_id);
```

---

## 11. 分区策略

### 11.1 按月分区表

已确认 D10：以下三张高增长表按 `created_at` 月份分区。

| 表名 | 分区键 | 预估月增量 |
|------|--------|-----------|
| emails | created_at | 数万~数十万行 |
| audit_logs | created_at | 数万行 |
| intelligence_articles | created_at | 数千行 |

### 11.2 分区管理

```sql
-- 自动创建分区的函数（建议用 pg_partman 扩展或 cron job）
-- 示例：手动创建下月分区
CREATE TABLE emails_2026_05 PARTITION OF emails
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE TABLE intelligence_articles_2026_05 PARTITION OF intelligence_articles
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- ⚠ DEFAULT 分区（兜底，防止 cron 创建分区失败时 INSERT 报错导致生产中断）
CREATE TABLE emails_default PARTITION OF emails DEFAULT;
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;
CREATE TABLE intelligence_articles_default PARTITION OF intelligence_articles DEFAULT;
```

### 11.3 数据保留策略

| 表名 | 热数据 | 温数据 | 冷数据 |
|------|--------|--------|--------|
| emails | 近3个月 | 3~12个月 | >12个月可归档 |
| email_events | 近3个月 | 3~12个月（metadata PII 已脱敏） | >12个月可归档 |
| audit_logs | 近1个月 | 1~6个月 | >6个月可归档 |
| intelligence_articles | 近3个月 | 3~12个月 | >12个月可清理 |

### 11.4 分区表注意事项

1. **跨分区查询性能**：跨分区去重/聚合查询（如 emails 按收件人去重统计）会扫描多个分区，建议通过 `created_at` 范围条件限定扫描范围
2. **分区表索引**：每个分区继承父表索引定义，PostgreSQL 会自动在新分区上创建索引；但已有分区的索引需手动或通过 `pg_partman` 管理
3. **UNIQUE 约束局限**：分区表的 UNIQUE 约束仅在单个分区内有效，跨分区唯一性需应用层保证（已在 §6.6 emails 表注释中标注）

---

## 12. 现有表迁移路径

现有系统 12 张表（见 `01_DATA_MODEL.md`）到新表结构的映射：

| 现有表 | 新表 | 迁移策略 |
|--------|------|---------|
| `company_data` | `shared_companies` + `company_sources` + `tenant_companies` | 拆分：基础信息→共享池，租户关系→tenant_companies，数据源→company_sources |
| `contact_data` | `shared_contacts` + `tenant_contacts` | 拆分：基础信息→共享池，租户视图→tenant_contacts |
| `keyword_list` | `collection_keywords` | 1:1 迁移，增加 tenant_id |
| `email_templates` | `email_templates`（新） | 1:1 迁移，增加 tenant_id |
| `email_plans` | `sending_plans`（新）+ `sequence_steps` | 拆分：计划主体迁移，序列部分拆为独立步骤 |
| `email_drafts` | `emails`（分区表）| 迁移到分区表，状态字段映射 |
| `company_analysis` | `company_scores` | 结构重构：从 A/B/X 映射到新评分体系 |
| `flow_runs` | 废弃 | Prefect 自带运行记录，不再自建 |
| `system_config` | `tenants.settings` + `ai_models` | 拆分到对应的新表 |
| `scheduled_tasks` | `collection_tasks` | 概念映射，结构重建 |
| `product_industry_config` | `scoring_templates.rules` (JSONB) | 行业配置内嵌到评分模板规则中，租户级自定义 |
| `draft_rewrite_logs` | `audit_logs` | 草稿修改记录纳入统一审计日志 |
| _(不存在)_ | `users` + `tenants` + `user_roles` | 新建：从 `system_config` 中的单用户认证拆出，创建租户→用户→角色 |

### 迁移注意事项

1. **主键切换**: 现有 SERIAL → UUID v7，需维护旧ID到新UUID的映射表（临时）
2. **数据完整性**: 先创建新表 → 迁移数据 → 验证 → 切换应用指向 → 删除旧表
3. **评分体系**: 现有 A/B/X 三级 → 新 S/A/B/C/D 五级，需定义映射规则
4. **零停机**: 建议双写过渡期（新旧表同时写入），而非大爆炸迁移
5. **ENUM 类型变更**: `ALTER TYPE ... ADD VALUE` 在 PostgreSQL 中不可回滚（无法在事务中执行），需在迁移的第一步单独执行；如需回滚，需 `DROP TYPE` + 重建

### 回滚策略

> 每个迁移步骤必须有对应的回滚方案，在迁移脚本中以 `down()` 函数实现。

| 迁移操作 | 回滚方案 |
|----------|---------|
| CREATE TABLE（新表） | DROP TABLE（无数据损失） |
| 数据迁移（旧表→新表） | 保留旧表直到验证期结束（至少 7 天），旧表不在迁移期间 DROP |
| ALTER TABLE ADD COLUMN | ALTER TABLE DROP COLUMN |
| CREATE INDEX CONCURRENTLY | DROP INDEX |
| ENUM ADD VALUE | 不可回滚，需 DROP TYPE + 重建（见注意事项 5） |
| 应用代码切换到新表 | 回滚应用代码，恢复指向旧表（双写期间两边数据一致） |

**迁移执行顺序**：
1. 创建新表结构（可回滚）
2. 启动双写（新旧表同时写入）
3. 批量迁移历史数据（分批，每批 1000 条，带 checkpoint）
4. 验证数据一致性（行数 + 抽样校验）
5. 切换应用读取到新表
6. 停止双写，旧表标记为只读
7. 观察期（7 天）后 DROP 旧表

---

## 13. ER 关系图

> **简化 ER 图**：以下仅展示核心实体和主要关系（约 22 张表），省略了 `scoring_template_versions`、`contact_rules`、`sending_plan_recipients`、`email_templates`、`platform_email_templates`、`data_source_credentials`、`intelligence_subscriptions`、`intelligence_article_publications`、`ai_models`、`ai_usage_logs`、`company_blacklist` 等辅助表。完整的表关系和 FK 定义见各章节 DDL。

```
                    ┌──────────┐
                    │ tenants  │
                    └────┬─────┘
                         │ 1
          ┌──────────────┼──────────────┬─────────────────┐
          │              │              │                   │
          ▼ N            ▼ N            ▼ N                ▼ N
     ┌─────────┐  ┌───────────┐  ┌──────────────┐  ┌─────────────┐
     │  users  │  │ ai_usage  │  │ balance_txn  │  │ competitor  │
     │         │  │   _logs   │  │              │  │ _companies  │
     └────┬────┘  └───────────┘  └──────────────┘  └─────────────┘
          │ N
     ┌────┴────┐
     │user_roles│
     └─────────┘

  ┌──────────────┐     N     ┌──────────────┐
  │   shared     │◄──────────│   company    │
  │  companies   │           │   sources    │
  └──────┬───────┘           └──────────────┘
         │ 1
         │              ┌─────────────────┐
         ├──────────────►│ shared_contacts │  N
         │              └────────┬────────┘
         │                       │
    ┌────┴──────────┐      ┌────┴──────────┐
    │   tenant      │      │   tenant      │
    │  companies    │      │  contacts     │
    └───────┬───────┘      └───────┬───────┘
            │                      │
    ┌───────┴───────┐      ┌───────┴───────┐
    │ company_scores│      │    groups      │
    └───────────────┘      └───────┬───────┘
                                   │ 1
                           ┌───────┴───────┐
                           │ group_members  │  N
                           └───────────────┘

  ┌──────────────┐    1     ┌──────────────┐    N    ┌──────────────┐
  │   sending    │──────────│  sequence    │────────►│  sequence    │
  │    plans     │          │   steps      │         │ enrollments  │
  └──────┬───────┘          └──────────────┘         └──────────────┘
         │ 1
         │    N
    ┌────┴──────────┐    N    ┌──────────────┐
    │    emails     │────────►│ email_events │
    └───────────────┘         └──────────────┘

  ┌──────────────┐    1     ┌──────────────┐
  │ intelligence │──────────│ intelligence │
  │   sources    │    N     │  articles    │
  └──────────────┘          └──────────────┘

  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  scoring     │  │  contact     │  │  collection  │
  │  templates   │  │   rules      │  │  keywords    │
  └──────────────┘  └──────────────┘  └──────┬───────┘
                                             │
                                      ┌──────┴───────┐
                                      │  collection  │
                                      │    tasks     │
                                      └──────────────┘

  系统支撑:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ audit_logs   │  │notifications │  │domain_warmup │
  │  (分区表)     │  │              │  │   _status    │
  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 14. 附录

### 14.1 评分规则 JSONB 结构示例

```json
{
  "dimensions": [
    {
      "id": "industry_match",
      "name": "行业匹配度",
      "weight": 25,
      "type": "rule",
      "rules": [
        {"condition": "industry_contains", "values": ["PCB", "电路板"], "score": 100},
        {"condition": "industry_contains", "values": ["电子", "半导体"], "score": 70},
        {"condition": "default", "score": 20}
      ]
    },
    {
      "id": "company_scale",
      "name": "公司规模",
      "weight": 20,
      "type": "rule",
      "rules": [
        {"condition": "employee_range", "min": 200, "score": 100},
        {"condition": "employee_range", "min": 50, "max": 199, "score": 70},
        {"condition": "employee_range", "max": 49, "score": 30}
      ]
    },
    {
      "id": "semantic_match",
      "name": "语义匹配度",
      "weight": 15,
      "type": "llm",
      "prompt_template": "评估该公司与{industry}行业的匹配度..."
    },
    {
      "id": "data_completeness",
      "name": "数据完整度",
      "weight": 10,
      "type": "rule",
      "rules": [
        {"condition": "completeness_gte", "value": 0.8, "score": 100},
        {"condition": "completeness_gte", "value": 0.5, "score": 60},
        {"condition": "default", "score": 20}
      ]
    },
    {
      "id": "export_geography",
      "name": "出口地区",
      "weight": 15,
      "type": "rule",
      "rules": [
        {"condition": "export_to", "regions": ["北美", "欧洲"], "score": 100},
        {"condition": "export_to", "regions": ["东南亚", "日韩"], "score": 70},
        {"condition": "default", "score": 30}
      ]
    },
    {
      "id": "contact_quality",
      "name": "联系人质量",
      "weight": 15,
      "type": "rule",
      "rules": [
        {"condition": "has_email_and_decision_maker", "score": 100},
        {"condition": "has_email", "score": 60},
        {"condition": "default", "score": 10}
      ]
    }
  ]
}
```

### 14.2 联系人规则 JSONB 结构示例

```json
{
  "grades": {
    "A": {
      "description": "决策层",
      "conditions": {
        "seniority_level_in": ["c_level", "vp", "director"],
        "title_keywords": ["CEO", "COO", "VP", "Director", "总经理", "副总"],
        "department_keywords": ["采购", "供应链", "Procurement", "Supply Chain"]
      }
    },
    "B": {
      "description": "管理层",
      "conditions": {
        "seniority_level_in": ["manager"],
        "title_keywords": ["Manager", "经理", "主管"],
        "department_keywords": ["采购", "工程", "技术", "Engineering"]
      }
    },
    "C": {
      "description": "执行层",
      "conditions": {
        "seniority_level_in": ["staff"],
        "title_keywords": ["Engineer", "Buyer", "工程师", "采购员"]
      }
    },
    "D": {
      "description": "其他",
      "conditions": {
        "default": true
      }
    }
  },
  "exclude_patterns": {
    "title_keywords": ["intern", "实习", "前台", "reception"]
  }
}
```

### 14.3 表统计总览

| 层级 | 表数量 | 表名 |
|------|--------|------|
| 平台层 (§2) | 7 | tenants, users, user_roles, ai_models, ai_usage_logs, data_source_credentials, platform_email_templates |
| 共享数据池 (§3) | 5 | shared_companies, company_sources, shared_contacts, company_blacklist, competitor_companies |
| 租户-公司评分 (§4) | 4 | tenant_companies, scoring_templates, scoring_template_versions, company_scores |
| 租户-联系人群组 (§5) | 4 | contact_rules, tenant_contacts, groups, group_members |
| 租户-邮件 (§6) | 7 | email_templates, sending_plans, sending_plan_recipients, sequence_steps, sequence_enrollments, emails, email_events |
| 租户-情报 (§7) | 4 | intelligence_sources, intelligence_articles, intelligence_article_publications, intelligence_subscriptions |
| 系统支撑 (§8) | 7 | audit_logs, notifications, domain_warmup_status, domain_warmup_history, collection_tasks, collection_keywords, balance_transactions |
| **合计** | **38** | |

对比现有系统 12 张表 → 新系统 38 张表，增长主要来自：
- 多租户拆分（tenants / user_roles / tenant_companies / tenant_contacts）
- 新功能（情报系统4张、序列邮件3张、群组2张、评分版本快照1张）
- 系统支撑（审计/通知/域名预热+历史/余额流水/数据源凭证）
- 排除/黑名单（company_blacklist + competitor_companies）

---

> **文档结束**
> 下一步：`10_API_DESIGN.md`（API 设计文档），将基于本文档的表结构进行设计。
