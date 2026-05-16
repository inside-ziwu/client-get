# 产品化差距分析与改造建议

> 文档版本：v1.0 | 基于仓库 aoqi-ai/sysdev-ft-marketing | 2026-04-16
> 用途：供 AI Agent 上下文注入 + 人类开发者参考
> 前置阅读：00-05 全部文档

---

## 1. 现状评估

### 1.1 当前系统定位

```
单用户内部工具 → 目标：多租户 SaaS 产品
```

| 维度 | 当前状态 | 产品化目标 |
|------|----------|------------|
| **用户** | 1 个管理员（创始人） | 多团队、多角色 |
| **行业** | PCB 制造（硬编码） | 任意外贸行业 |
| **数据源** | 网易外贸通独占 | 多数据源插件化 |
| **认证** | 单用户 JWT | 多租户 + RBAC |
| **计费** | 无 | 订阅 + 用量计费 |
| **部署** | 单机裸跑（无 Docker） | 容器化 + 可扩展 |
| **安全** | CORS 全开、无审计 | 生产级安全 |

### 1.2 核心优势（产品化可复用）

已验证的价值链路——这些是产品的核心竞争力：

1. **全链路自动化**：关键词→公司→评级→写信→发送，仅 2 次人工介入
2. **AI 评级体系**：多维度打分(相关性/市场匹配/意向度)，A/B/X 三级
3. **时区感知发送**：按目标国家工作时间自动调度
4. **多轮跟进**：`linked_plan_id` + `round_number` 实现自动追邮
5. **域名预热**：20 天从 5 封到 2500 封的科学升温
6. **Prefect 编排**：Flow 状态可观测，失败可重试

---

## 2. 差距分析（按优先级）

### 2.1 P0 — 多租户架构（不做就无法上线）

#### 当前问题

- **零租户隔离**：所有数据共享同一组表，无 `tenant_id` 字段
- **单用户认证**：`users` 表仅 1 条记录，JWT 无租户标识
- **配置全局化**：`system_config` 表存所有密钥，无租户维度
- **Flow 单例**：调度器全局运行，无法区分不同租户的任务

#### 改造方案

**选项 A：行级隔离（Row-Level Security）** — 推荐

```sql
-- 所有核心表增加 tenant_id
ALTER TABLE email_plans ADD COLUMN tenant_id UUID NOT NULL;
ALTER TABLE company_analysis ADD COLUMN tenant_id UUID NOT NULL;
ALTER TABLE contact_data ADD COLUMN tenant_id UUID NOT NULL;
-- ... 所有 12 张表

-- PostgreSQL RLS 策略
CREATE POLICY tenant_isolation ON email_plans
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

优势：改动最小，PostgreSQL 原生支持，不影响现有查询逻辑
劣势：需要所有查询设置 `current_tenant` 上下文

**选项 B：Schema 隔离** — 备选

每个租户独立 schema，通过连接路由隔离。数据完全隔离但运维复杂度高。

#### 需新增的表

```sql
-- 租户表
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- 子域名/标识
    plan_tier VARCHAR(50) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',
    settings JSONB DEFAULT '{}',        -- 行业、Prompt、配置
    created_at TIMESTAMP DEFAULT NOW()
);

-- 租户成员关系
CREATE TABLE tenant_members (
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) NOT NULL,  -- owner/admin/member/viewer
    PRIMARY KEY (tenant_id, user_id)
);

-- 租户级密钥存储
CREATE TABLE tenant_secrets (
    tenant_id UUID REFERENCES tenants(id),
    provider VARCHAR(50) NOT NULL,  -- 'netease'/'engagelab'/'openrouter'
    config JSONB NOT NULL,          -- 加密的认证信息
    PRIMARY KEY (tenant_id, provider)
);
```

#### 影响面分析

| 层级 | 涉及文件 | 改动量 |
|------|----------|--------|
| **数据库** | 12 张表 + 新增 3 张 | 大 |
| **API 中间件** | `deps.py` + 所有路由 | 大（每个查询加 tenant 过滤） |
| **Flow 引擎** | 所有 4 个 Flow + 调度器 | 大（任务按租户分派） |
| **前端** | 登录流程 + 租户切换 | 中 |

---

### 2.2 P0 — 认证与授权（多租户前置条件）

#### 当前问题

- `users` 表仅有 `id/email/hashed_password/is_active/created_at`
- 无角色字段、无权限表
- JWT payload 仅包含 `user_id`，无租户/角色信息
- 密码哈希用 `passlib`（可用但需确认算法）

#### 改造方案

```
认证层升级路径:

1. users 表扩展
   + name, avatar, phone, last_login_at
   + email_verified BOOLEAN

2. JWT Payload 扩展
   {
     "sub": user_id,
     "tid": tenant_id,      # 新增
     "role": "admin",        # 新增
     "exp": timestamp
   }

3. RBAC 权限矩阵
   owner  → 全部权限 + 账单 + 成员管理
   admin  → 全部业务权限
   member → 创建/编辑自己的计划
   viewer → 只读

4. API 中间件
   get_current_user() → get_current_user_with_tenant()
   每个端点声明所需角色 → @require_role("admin")
```

#### 是否引入第三方认证

| 方案 | 优势 | 劣势 |
|------|------|------|
| **自建**（当前+扩展） | 完全可控、无依赖 | 需实现邮箱验证、密码重置、SSO |
| **Supabase Auth** | 内置 RLS、邮箱/社交登录 | 绑定 Supabase 生态 |
| **Clerk** | 最快上线、预制 UI | 成本随用户增长 |
| **Auth0** | 企业级、SSO 支持 | 成本高 |

建议：**团队一人+AI 的情况下，优先自建最小可用认证，后续考虑 Clerk/Supabase**。

---

### 2.3 P0 — 计费与订阅系统

#### 当前问题

- 完全没有计费机制
- 无用量追踪（LLM token、邮件发送量、API 调用次数）
- 无套餐/配额概念

#### 改造方案

```
计费架构设计:

1. 套餐定义
   ┌────────┬──────────┬───────────┬───────────┐
   │  维度  │  免费版   │  专业版    │  企业版   │
   ├────────┼──────────┼───────────┼───────────┤
   │ 邮件/月 │   500   │   5,000   │  50,000   │
   │ AI评级  │   200   │   2,000   │  无限     │
   │ 关键词  │    5    │    50     │   500     │
   │ 成员数  │    1    │     5     │    50     │
   │ 数据源  │ 外贸通   │  +Apollo  │   全部    │
   └────────┴──────────┴───────────┴───────────┘

2. 用量追踪表
   CREATE TABLE usage_records (
       tenant_id UUID,
       metric VARCHAR(50),    -- 'email_sent'/'llm_tokens'/'api_calls'
       value INTEGER,
       recorded_at TIMESTAMP
   );

3. 配额检查中间件
   每次 Flow 执行前 → check_quota(tenant_id, 'email_sent')
   超额 → 暂停任务 + 通知用户

4. 支付集成
   国内: 微信支付 / 支付宝
   海外: Stripe（如果未来面向海外客户）
```

---

### 2.4 P1 — 行业可配置化（去 PCB 硬编码）

#### 当前问题

- Prompt 中硬编码 "XAPCB"（公司名）、"PCB manufacturer" 等
- `config.py` 中 `PCB_SUB_INDUSTRIES` 16 个子行业硬编码
- 邮件模板假设 PCB 制造商身份
- 评级标准绑定 PCB 相关性

#### 改造方案

```python
# 租户配置（存 tenants.settings JSONB）
{
    "industry": {
        "name": "PCB Manufacturing",
        "name_zh": "PCB制造",
        "sub_industries": ["Rigid PCB", "Flex PCB", ...],
        "keywords": ["pcb", "circuit board", ...]
    },
    "company": {
        "name": "XAPCB",
        "description": "Leading PCB manufacturer...",
        "selling_points": ["ISO certified", "20+ years", ...]
    },
    "prompts": {
        "rating_template": "...",      # 可自定义或用默认
        "email_template": "...",
        "rating_dimensions": {
            "relevance": 40,
            "market_fit": 30,
            "intent": 30
        }
    }
}
```

改造步骤：
1. 将所有硬编码值提取为模板变量
2. Prompt 改为 f-string/Jinja2 模板，变量从租户配置注入
3. 提供默认模板（PCB行业版），用户可基于默认修改

---

### 2.5 P1 — 数据源插件化

#### 当前问题

- 仅网易外贸通一个数据源
- `netease_api.py` 与 Flow 01/02 紧耦合
- 无抽象的数据源接口

#### 改造方案

```python
# 数据源抽象接口
class DataSourceProvider(ABC):
    @abstractmethod
    async def search_companies(self, keyword: str, **params) -> list[Company]:
        """按关键词搜索公司"""

    @abstractmethod
    async def get_company_detail(self, company_id: str) -> CompanyDetail:
        """获取公司详情"""

    @abstractmethod
    async def get_contacts(self, company_id: str) -> list[Contact]:
        """获取公司联系人"""

# 已有实现
class NetEaseProvider(DataSourceProvider): ...

# 未来扩展
class ApolloProvider(DataSourceProvider): ...
class LinkedInProvider(DataSourceProvider): ...
class ZoomInfoProvider(DataSourceProvider): ...
```

#### 优先级排序

| 数据源 | 优先级 | 理由 |
|--------|--------|------|
| 网易外贸通（已有） | — | 已实现 |
| Apollo.io | P1 | 海外 B2B 数据标杆，API 标准 |
| LinkedIn Sales Nav | P2 | 数据量大但 API 限制严格 |
| ZoomInfo | P2 | 企业级，成本高 |
| 自定义导入（CSV/Excel） | P1 | 用户自有数据的入口 |

---

### 2.6 P1 — 安全加固

#### 当前问题

| 问题 | 位置 | 风险 |
|------|------|------|
| **CORS 全开** | `main_api.py` `allow_origins=["*"]` | 任何域名可调用 API |
| **无 API 版本化** | 所有路由 `/api/xxx` | 无法平滑迭代 |
| **无请求限流** | 全局 | API 可被暴力调用 |
| **密钥明文存 DB** | `system_config` | DB 泄漏即全部密钥泄漏 |
| **无审计日志** | 全局 | 无法追溯操作历史 |
| **无 CSRF 保护** | 全局 | POST 请求无令牌校验 |

#### 改造清单

```
安全加固优先级:

P0 (上线前必须):
  ☐ CORS 收紧为具体域名
  ☐ API 版本化 → /api/v1/
  ☐ 请求限流 (slowapi 或自实现)
  ☐ 密钥加密存储 (Fernet/KMS)

P1 (上线后尽快):
  ☐ 审计日志表 (who/what/when/from_where)
  ☐ API Key 认证选项 (给第三方集成用)
  ☐ 输入校验强化 (Pydantic strict mode)
  ☐ SQL 注入检查 (虽然用 psycopg2 参数化，但有 f-string 拼接风险)

P2 (持续改进):
  ☐ CSRF token
  ☐ Content Security Policy
  ☐ 定期依赖漏洞扫描
```

---

### 2.7 P1 — 前端体验升级

#### 当前问题

- 面向技术人员的管理后台风格
- 无引导流程（Onboarding）
- 无状态管理库（纯 `useState`/`useEffect`）
- 无国际化（纯中文 + 少量英文混杂）
- 无移动端适配

#### 改造方向

```
前端改造路线:

Phase 1 — 体验基础
  ☐ 引导流程 (注册 → 配置行业 → 首次采集 → 首封邮件)
  ☐ 全局状态管理 (Zustand 或 Jotai，轻量优先)
  ☐ 错误边界 + 全局 loading 状态
  ☐ 移动端响应式适配

Phase 2 — 产品化 UI
  ☐ 多租户切换 UI
  ☐ 用量仪表盘 (配额可视化)
  ☐ 团队成员管理页面
  ☐ 套餐/账单管理页面

Phase 3 — 高级功能
  ☐ 国际化 (i18next)
  ☐ 暗色模式
  ☐ 邮件模板可视化编辑器
  ☐ 数据源配置向导
```

---

### 2.8 P2 — 基础设施

#### 当前问题

- 无 Docker/容器化
- 单机运行，无水平扩展能力
- 无 CI/CD 管道
- Prefect 调度器是单进程循环
- 无日志聚合 / APM

#### 改造方案

```
基础设施路线:

Phase 1 — 容器化
  ☐ Dockerfile (API + Worker 分离)
  ☐ docker-compose.yml (本地开发)
  ☐ 环境变量 .env.example

Phase 2 — CI/CD
  ☐ GitHub Actions (lint + test + build)
  ☐ 自动部署到测试环境
  ☐ 数据库迁移工具 (Alembic)

Phase 3 — 可观测性
  ☐ 结构化日志 (JSON format)
  ☐ Prometheus metrics (已有基础)
  ☐ Grafana 仪表盘
  ☐ Sentry 错误追踪

Phase 4 — 扩展性
  ☐ Prefect 调度器多实例（或迁移到 Celery/Temporal）
  ☐ 数据库读写分离
  ☐ Redis 缓存层
```

---

## 3. 改造路线图

### Phase 1：最小可售产品（MVP）— 预计 4-6 周

目标：让第二个用户能注册并独立使用系统

```
Week 1-2: 多租户基础
  ├── 数据库迁移（12表加 tenant_id + 3新表）
  ├── RLS 策略
  ├── JWT 扩展（含 tenant_id + role）
  └── API 中间件改造

Week 3: 认证与权限
  ├── 注册/登录流程
  ├── 租户创建向导
  ├── RBAC 基础（owner/member）
  └── CORS + API 版本化

Week 4: 行业可配置化
  ├── Prompt 模板化
  ├── 租户 settings 配置页面
  ├── 去 PCB 硬编码
  └── 默认模板库

Week 5-6: 基础计费 + 打磨
  ├── 用量追踪
  ├── 配额检查中间件
  ├── 引导流程
  ├── Docker 化
  └── 测试 + Bug 修复
```

### Phase 2：产品完善 — 预计 4-6 周

```
  ├── 完整计费系统（支付集成）
  ├── 团队管理 UI
  ├── 数据源插件架构（+CSV 导入）
  ├── 域名预热动态管理
  ├── 安全加固（审计日志、密钥加密）
  └── CI/CD 管道
```

### Phase 3：增长功能 — 持续迭代

```
  ├── Apollo/LinkedIn 数据源集成
  ├── 邮件模板可视化编辑器
  ├── A/B 测试（邮件主题/内容）
  ├── 高级分析仪表盘
  ├── API 开放（给第三方集成）
  └── 国际化
```

---

## 4. 技术决策建议

### 4.1 需要决策的关键问题

| # | 决策项 | 选项 | 建议 | 理由 |
|---|--------|------|------|------|
| 1 | 多租户隔离策略 | RLS vs Schema | **RLS** | 改动最小，PostgreSQL 原生 |
| 2 | 认证方案 | 自建 vs Clerk vs Supabase | **自建（最小）→ 后续评估** | 一人团队控制成本 |
| 3 | 数据库迁移工具 | Alembic vs 手动 SQL | **Alembic** | 版本管理 + 自动化 |
| 4 | 状态管理 | Zustand vs Jotai vs Redux | **Zustand** | 最简单，迁移成本低 |
| 5 | 支付集成 | Stripe vs 微信/支付宝 | **取决于目标市场** | 国内客户→微信，海外→Stripe |
| 6 | 调度器方案 | Prefect 优化 vs Celery vs Temporal | **先优化 Prefect** | 已在用且满足当前规模 |
| 7 | 部署平台 | 自有服务器 vs 云服务 | **取决于预算和规模** | 初期 VPS 即可 |

### 4.2 不建议做的事

| 不做 | 理由 |
|------|------|
| **重写前端（Next.js/Vue）** | 现有 React+Antd 完全够用，重写纯消耗 |
| **微服务拆分** | 当前体量无需，单体+模块化足够 |
| **换数据库** | PostgreSQL 足以支撑百万级数据 |
| **过早做国际化** | 先验证国内市场 |
| **自建邮件基础设施** | EngageLab 送达率已验证，无需自建 SMTP |

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 网易外贸通 API 变更/封禁 | 中 | 高 | 数据源抽象层 + CSV 导入兜底 |
| OpenRouter 服务中断 | 低 | 高 | 已有 fallback 模型机制 |
| 邮件送达率下降 | 中 | 高 | 监控告警 + 多通道备选 |
| 一人团队精力瓶颈 | 高 | 高 | MVP 最小化 + AI 辅助开发 |
| 数据迁移出错（加 tenant_id） | 中 | 高 | 迁移脚本 + 回滚计划 + 测试环境验证 |
| 多租户性能下降 | 低 | 中 | RLS + 索引优化，按需分库 |

---

## 6. AI Agent 快速参考

```yaml
# 产品化改造的技术要点摘要（供 Agent 上下文注入）

current_state:
  architecture: monolithic_single_tenant
  database: postgresql_12_tables_no_rls
  auth: single_user_jwt_no_rbac
  billing: none
  industry: hardcoded_pcb
  deployment: bare_metal_no_docker
  security: cors_open_no_rate_limit

target_state:
  architecture: monolithic_multi_tenant_rls
  database: postgresql_15_tables_with_rls
  auth: multi_user_jwt_with_rbac
  billing: subscription_plus_usage
  industry: configurable_per_tenant
  deployment: docker_compose
  security: cors_restricted_rate_limited_audit_logged

migration_strategy:
  approach: incremental_not_rewrite
  phase_1_weeks: 4-6
  phase_1_scope: [multi_tenant, auth, industry_config, basic_billing]
  key_tables_to_add: [tenants, tenant_members, tenant_secrets, usage_records]
  key_columns_to_add: tenant_id_on_all_12_tables

critical_decisions_needed:
  - target_market: domestic_or_international
  - payment_provider: stripe_or_wechat_alipay
  - auth_approach: self_built_or_third_party
```
