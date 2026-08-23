# ClientGet

> **本文是仓库总入口**：前半是「🚀 快速开始」（装环境、跑起来），后半（§1–§13）是产品、架构与运维的深度参考（原 HANDBOOK 并入）。基线日期：2026-07-14（全量只读审计），快速开始部分 2026-07-22 核验。
>
> **文档体系**：本文（人看的总入口：快速开始、产品、功能现状、部署、运维）+ [AGENTS.md](AGENTS.md)（项目身份、安全红线、spec 索引）+ [.trellis/spec/](.trellis/spec/)（编码约定、数据库与迁移纪律、行为口径、设计系统、Git 与收尾、运维细则——由 Trellis 在编码前注入）+ GitHub Issues（唯一债务与需求台账，`gh issue list`）。[docs/solutions/](docs/solutions/) 为已冻结的历史事故档案。本文与代码冲突时，以代码与测试为准，并修订本文。

## 🚀 快速开始

### 前置条件

| 工具 | 版本 | 用途 |
|---|---|---|
| Python | 3.11+（当前 .venv 实际为 3.12） | 后端 |
| uv | 最新 | 后端依赖管理 |
| Node.js | 20+ | 前端 |
| pnpm | 10.28.1（钉死于 `packageManager`，建议 `corepack enable` 自动匹配） | 前端 workspace |
| Docker | 近期版本 | 可选：自建本地 PostgreSQL 16 |
| gh CLI | 推荐 | 债务台账（Issues）与 PR 操作 |

### 克隆与安装

```bash
git clone https://github.com/inside-ziwu/client-get.git
cd client-get
```

```bash
cd backend && uv sync
```

```bash
cd frontend && pnpm install
```

### 环境变量

- **后端**：`cp backend/.env.example backend/.env.local`（应用读取的是 `.env.local`，见 `backend/app/core/config.py:23`），逐项填写；变量全集见 §7。
  - 必填：`CLIENTGET_DEV_DATABASE_URL`（开发库连接串，见下节）、`JWT_SECRET`、`ADMIN_EMAIL`、`ADMIN_PASSWORD`（首次启动引导平台管理员）、`DATA_SOURCE_ENCRYPTION_KEY`、`INTERNAL_SERVICE_SECRET`。
  - `ENGAGELAB_*` 四项本地开发可填占位值，只有真实发送/回调链路需要真值。
  - ⚠️ `CLIENTGET_PROD_DATABASE_URL` 仅个别一次性脚本使用，**本地开发禁止填写生产连接串**（红线见 [AGENTS.md](AGENTS.md) §1）。
  - `.env.local` 由开发者手动维护，AI 代理禁止修改。
- **前端**：`cp frontend/.env.example frontend/apps/admin/.env.local`、`cp frontend/.env.example frontend/apps/tenant/.env.local`，默认指向 `http://localhost:8000`，本地开发通常无需改动（生产不走 env 文件，API 地址构建时写死，见 §7）。

### 数据库设置

两条路任选其一：

**A. 团队现行：Neon 云开发库**——向维护者索取 `CLIENTGET_DEV_DATABASE_URL` 连接串填入 `.env.local`，库已就绪，直接执行迁移确认到 head：

```bash
cd backend && uv run alembic -c alembic.ini upgrade head
```

**B. 自足备选：docker compose 本地库**：

```bash
cd backend && docker compose up -d postgres
```

得到 `localhost:5432`，用户/密码 `postgres`/`postgres`，业务库 `clientget`；随后同样执行上面的迁移命令。

> ⚠️ **已知坑（issue #64）**：**全新空库**当前无法从 Alembic 基线跑通（迁移链存在 FK 类型缺陷）——走 B 路建新库会撞上。在 #64 修复前，新库请向维护者索要开发库 dump 导入后再 `upgrade head`；A 路的既有 Neon 库不受影响。

集成测试若需数据库，另建 `clientget_test`：

```bash
docker exec clientget-postgres createdb -U postgres clientget_test
```

### 启动

```bash
cd backend && uv run uvicorn app.main:app --reload
```

```bash
cd frontend && pnpm dev:admin
```

```bash
cd frontend && pnpm dev:tenant
```

后端 API 在 8000，Admin 前端在 3000，Tenant 前端在 3001。可选：

```bash
cd backend && uv run python scripts/seed_demo_data.py
```

灌入演示数据（demo 租户）。

- 也可 `docker compose up` 整套拉起（backend 容器读 `backend/.env.local`）。注意：compose 的 `command` 覆盖了镜像默认入口，**不会**自动跑迁移；生产镜像（`/start.sh`）才会先 `alembic upgrade head` 再起服务，迁移失败会直接阻断 API 启动。
- 发送 worker 单轮验证：`uv run python scripts/run_sending_worker.py --once`。它会访问配置的数据库与邮件服务能力，**没有隔离环境不要执行**。

### 测试

```bash
cd backend && uv run pytest -q
```

```bash
cd frontend && pnpm type-check
```

后端用例以 mock 为主，无真库也能跑大部分（现状见 §10）。门禁范围、已知失效命令清单（当前：根 `pnpm lint`、tenant `test:contract`）与"SQL 语义 / 时区 / 状态机必须真库验证"的纪律见 [.trellis/spec/backend/quality-guidelines.md](.trellis/spec/backend/quality-guidelines.md) 与 [.trellis/spec/frontend/quality-guidelines.md](.trellis/spec/frontend/quality-guidelines.md)。

### 常见问题排查

| 症状 | 原因与处理 |
|---|---|
| 空库 `alembic upgrade head` 失败 | 已知缺陷 issue #64；向维护者索要开发库 dump 导入 |
| 容器里 API 起不来、日志停在 alembic | 生产镜像先跑迁移再起服务，迁移失败会阻断启动；先修迁移 |
| `pnpm install` 报 pnpm 版本不符 | `corepack enable` 后重试（版本钉在 `packageManager` 字段） |
| admin / tenant 端口冲突 | admin 固定 3000、tenant 固定 3001，检查残留进程 |
| Tenant 前端频繁跳回登录页 | tenant 端无静默续期，令牌过期即登出，属已知缺陷（#76） |
| EngageLab 行为与预期不符 | 端点/配额/错误语义随账号区域不同，勿跨实例复制配置（见 §6–§7） |

仓库目录与架构全景见 §4。

---

## 1. 产品是什么

本项目的核心定义、业务链路与不可削弱的核心价值（租户隔离、发送可靠），见 [AGENTS.md](AGENTS.md) §0「项目身份」。商业形态为平台方运营 admin 后台、客户企业使用 tenant 自服务后台（双端与路由见 §4）；生产实例现状见 §6。

## 2. 核心业务流程

**平台侧一次性配置（admin）**：
① 配置行业评分模板 → ② 维护行业动态源（种子定义，管理端只做监控与启停） → ③ 配置行业邮件模板 → ④ 配置域名预热规则 → ⑤ 配置 AI 模型与定价。客户数据由外部管道写入共享池，本平台不再管理采集任务或数据源凭证。

**开通客户（admin）**：
⑦ 创建租户 + 配发信域名（选预热档位）+ 配置该租户 OpenRouter 密钥 →（可选）添加团队成员 → 交付登录信息

**租户自服务主链（tenant）**：
⑧ 首次登录与引导 → ⑨ 从共享客户池浏览/筛选公司 → ⑩ 优选客户入群组（联系人自动物化、按职级分类）→ ⑪ 创建/编辑邮件模板（富文本，支持测试发送）→ ⑫ 按筛选条件创建发送计划（预览收件人 → 锁定 → 启动）→ ⑬ 仪表盘监控送达/打开/退信数据

**后台自动任务**：数据血缘修复与行业分发循环（进程内，300 秒/轮）、发送 worker（独立进程，节流+熔断）、邮件状态对账（约 10 分钟/轮，兜底 webhook 丢失）、发送计划自动完成。

## 3. 功能现状矩阵（2026-07-14 审计基线）

图例：✅ 完成并可用 ｜ 🟡 半成品（外壳在、缺关键环节，缺口必读）

### 平台侧（admin）

| 功能 | 状态 | 说明与关键位置 |
|---|---|---|
| 共享客户池与外部数据浏览 | ✅ | 保留「同行原始/同行清洗/外贸通原始/客户池」四页；只读外部写入的 `lixiaoyun_api_*`、`waimaotong_*` 表；采集任务与数据源凭证功能已退役（#75）。 |
| 联系人职位分类体系 | ✅ | 分级关键词已数据化可维护。admin `/contact-classification` |
| 评分模板配置 | ✅ | 行业筛选在点击「查询」或按 Enter 后生效；列表状态可直接启停。admin `/scoring-templates` |
| 工作日历（国家/节假日/规则集） | ✅ | 供时区感知发送使用。admin `/work-schedule` |
| 域名与预热管理 | 🟡 | 建域名/选档位可用；**「验证」按钮是假验证，不查 DNS/SPF/DKIM，直接置 verified**（#47）；**预热不会自动升档，只有手动调整**（#48）。`admin_config_service.py:1707` 附近 |
| AI 模型配置 | 🟡 | 配置与余额查询可用；**系统没有任何真实 LLM 推理调用**（#46）。`backend/app/integrations/openrouter.py` |
| 平台邮件模板 | ✅ | 含向租户同步；TipTap 编辑器支持加粗、斜体、有序列表、无序列表及变量插入，列表标记与缩进保持可见。admin `/email-templates` |
| 动态源管理 | ✅ | 行业动态的动态源监控页：种子定义的源列表只读展示 + 启停 + 上次成功时间 / 错误计数 + 「立即抓取」；每实例每天北京 08:00 自动抓取（`INDUSTRY_NEWS_FETCH_ENABLED`）。`app/services/industry_news/`、`app/workers/industry_news_fetch.py` |
| 租户生命周期管理 | ✅ | 创建/暂停/删除、域名、团队、OpenRouter 四块。admin `/tenants`（前端为 984 行单文件，拆分随 #59 Phase C 处理） |

### 租户侧（tenant）

| 功能 | 状态 | 说明与关键位置 |
|---|---|---|
| 认证体系 | 🟡 | 登录、强制改密、onboarding 可用；**tenant 不签发 refresh token，前端 401 拦截器硬编码 admin 续期路径，令牌过期即强制登出**（#76）。`shared-api/src/client.ts:82` |
| 仪表盘 | ✅ | 邮件统计趋势、计划概览、配额/AI 余额、漏斗。`tenant/core.py` 5 端点 |
| 公司列表与筛选 | ✅ | 16 项多维条件（含采集类型、已入群）紧凑常驻；交互与列宽契约见 [.trellis/spec/frontend/component-guidelines.md](.trellis/spec/frontend/component-guidelines.md)。函数索引优化过查询性能。`tenant_query_service.py` |
| 优选客户（群组） | ✅ | 入群自动物化联系人。tenant `/curated-customers` |
| 评分 | ✅ | **租户评分是确定性规则引擎，不是 AI**；仅依该租户当前模板/版本写入 `company_scores`，平台不对全局客户池打分。`scoring_engine_service.py` |
| 邮件模板 | 🟡 | 双 Tab 列表、TipTap 富文本、纯文本兜底、测试发送；「AI 生成」当前为启发式桩（#46）；**平台模板“预览”会误调用复制接口，已排期修复**（#65）。tenant `/templates` |
| 发送计划全生命周期 | ✅ | 4 步向导、收件人预览/锁定、状态机操作、运行中轮询；锁定/启动前校验模板变量，含无法替换的 `{{…}}` 时 422 拦截（防字面量事故，2026-07-23）。tenant `/send-plans/*`，后端 `tenant_messaging_service.py`（3334 行核心文件） |
| 团队管理 | 🟡 | CRUD 可用；列表前端隐藏当前账号操作并对行级状态提交提供 pending 保护，但**API 层仍缺最后管理员保护与自操作拦截，可把租户锁死**（#44）。`tenant_team_service.py` |
| 行业动态（阅读侧） | ✅ | 实例内按行业可见的每日动态流：标题 + 原文链接、来源 / 类别 / 语种筛选、「只看未读」、按用户已读、90 天窗口、同稿去重。tenant `/industry-news` |
| 各项设置 | ✅ | 评分模板、AI 供应商、团队。tenant `/settings/*` |

### 发送与可靠性（worker）

| 功能 | 状态 | 说明 |
|---|---|---|
| 发送 worker | ✅ | 全仓工程质量最高模块：域名级配额熔断、限流探测、错误四分类、重试退避、stale lock 恢复、幂等。`app/workers/sending.py` |
| 时区感知发送窗口 | ✅ | 按收件人国家的工作日历与时区决定可发时间 |
| 邮件状态对账 | ✅ | 主动查 EngageLab 补齐 webhook 丢失的状态。`app/workers/reconciliation.py` |
| Webhook 事件入库 | ✅ | 幂等去重、超长 provider_event_id 兼容。`app/api/webhooks/engagelab.py` |
| 客户池关系修复与补评循环 | ✅ | 当前实例的活跃 PCB 租户共享全池，排除 `source_id LIKE 'manual-%'` 的私有行；按实例清理 stale 关系。关系事务提交后再用租户当前模板有界补评，单条失败不回滚关系修复。`app/workers/wmt_lineage_repair.py` |
| 发送计划自动完成 | ✅ | `sending_plan_completion.py` |

### 基础设施

| 功能 | 状态 | 说明 |
|---|---|---|
| 多实例部署 | ✅ | 详见 §6，已生产运行 |
| 多租户隔离 | 🟡 | 应用层过滤 + 测试锁定可用；**数据库层 RLS 未强制（无 FORCE、单一 owner 连接），属单点防线**（#43） |
| 前端布局与路由反馈 | ✅ | Admin/Tenant 共用 shared-ui `DashboardShell`；小屏使用左侧抽屉导航，桌面保留折叠侧栏；应用级与 dashboard 级错误边界提供重试/刷新，dashboard 路由提供统一 loading 骨架 |

## 4. 系统架构

```
client_get/
├── backend/            FastAPI + PostgreSQL + Alembic + workers（app/ 91 文件 ≈ 20.8k 行）
│   ├── app/api/        路由层：admin(/admin/api/v1) tenant(/t/{slug}/api/v1) internal(/internal/api/v1) webhooks(/webhooks)
│   ├── app/services/   业务逻辑 + SQL（30 文件 ≈ 15.2k 行，占 73%）
│   ├── app/workers/    sending / reconciliation / wmt_lineage_repair
│   ├── app/db/         连接池、RLS 会话变量、事务、分区维护
│   ├── app/security/   JWT（platform / tenant / service 三种 kind）、bcrypt、服务间鉴权
│   ├── alembic/        迁移链（head 以 03_database/schema_snapshot.json 的 alembic_version 为准）
│   └── scripts/        运维脚本（见 §9）
├── frontend/           pnpm workspace（166 文件 ≈ 18.4k 行）
│   ├── apps/tenant/    Next.js 15 + React 19，纯客户端渲染，端口 3001
│   ├── apps/admin/     Next.js 15 + React 19，SSR 预取壳 + 客户端页，端口 3000
│   └── packages/       shared-ui（Radix 封装 + 设计令牌）/ shared-api（统一 axios 客户端）/ shared-hooks / shared-types
└── 03_database/schema.sql   数据库蓝图（1497 行，含 RLS policy 定义；已知与生产漂移，见 #61，勿单独作为实施依据）
```

路由组与鉴权上下文、核心表族谱、认证与隔离现状、worker 部署形态等编码事实已迁入 [.trellis/spec/backend/directory-structure.md](.trellis/spec/backend/directory-structure.md) 与 [database-guidelines.md](.trellis/spec/backend/database-guidelines.md)；前端结构见 [.trellis/spec/frontend/directory-structure.md](.trellis/spec/frontend/directory-structure.md)。逐表结构见 [docs/database-schema.md](docs/database-schema.md)（生产快照自动生成）。

## 5. 关键行为口径

发送间隔、收件人选取、发送窗口、配额熔断、统计口径、评分、采集类型、域名验证等全部行为口径已迁入 [.trellis/spec/backend/domain-rules.md](.trellis/spec/backend/domain-rules.md)（唯一出处，行为变更时同步修订）。列表页与筛选的 UI 交互口径见 [.trellis/spec/frontend/component-guidelines.md](.trellis/spec/frontend/component-guidelines.md)。

## 6. 多实例（Instance A / B）

同一套代码 + **共享同一个物理 PostgreSQL 数据库**，按 `CLIENTGET_INSTANCE_ID` 区分实例。硬性声明、隔离边界与新实例初始化见 [.trellis/spec/backend/domain-rules.md](.trellis/spec/backend/domain-rules.md)「多实例」。各实例当前的运营状态与负责人尚未确认（#66）。

## 7. 环境与部署

**两套完全隔离的环境，无切换动作**：

| | 开发 | 生产 |
|---|---|---|
| 数据库 | Neon 云 PG（`CLIENTGET_DEV_DATABASE_URL`） | Sealos PG（环境变量由 Sealos 控制台注入） |
| 后端 | 本地 uvicorn | Sealos 容器（镜像启动时 `/start.sh` 自动 `alembic upgrade head`） |
| 前端 | 本地 next dev | Sealos 容器，API 地址**构建时**经 `--build-arg` 写死 |

**发布流程**：push GitHub → Actions 手动触发 `workflow_dispatch`（选 service: admin/tenant/backend）→ amd64 构建推送阿里云 ACR（`crpi-…aliyuncs.com/lay_inside/clientget-{service}`，tag 格式 `YYYY.MM.DD-rN` 自动递增）→ Sealos 控制台手动更新对应服务镜像 tag（backend 镜像同时供 API 与 worker 容器使用）。本地 `push-*.sh` 仅调试用（ARM 交叉编译慢），不作正式发布。

**⚠️ 全量发布 = 5 个构建**（两实例共库共 backend 镜像，前端因 API 地址构建时写死须按实例各构建一套；2026-07-23 曾漏发 B 实例，特此记录）：

| # | service | 实例 | 构建参数（`workflow_dispatch` inputs） | 建议 tag 惯例 |
|---|---|---|---|---|
| 1 | backend | A+B 共用 | 无需实例参数 | `YYYY.MM.DD-rN`（自动） |
| 2 | admin | A | 全部留空（`api_url` 默认 `https://api.xinanpcb.com`，portal 空值由前端 fallback 到 `https://tenant.xinanpcb.com`） | 同上 |
| 3 | tenant | A | 留空 | 同上 |
| 4 | admin | B | `api_url=https://sfxteoewmcow.sealosbja.site`、`tenant_portal_url=https://ihvjdybutzgy.sealosbja.site` | 显式 `YYYY.MM.DD-b-rN` |
| 5 | tenant | B | `api_url=https://sfxteoewmcow.sealosbja.site` | 显式 `YYYY.MM.DD-b-rN` |

仅动 backend 时可只发 #1；动了前端则 A/B 四个前端镜像都要发。Sealos 更新时按实例对号入座（镜像名不区分实例，认 tag）。

**环境变量**（值由用户手动维护，不得自动修改）：

- `backend/.env.local`：`CLIENTGET_DEV_DATABASE_URL`、`CLIENTGET_PROD_DATABASE_URL`、`JWT_SECRET`、`ADMIN_EMAIL`、`ADMIN_PASSWORD`（首次启动引导平台管理员）、`DATA_SOURCE_ENCRYPTION_KEY`（历史名，仍用于 OpenRouter Key 等存量密文，不得删除或轮换）、`INTERNAL_SERVICE_SECRET`（worker↔API 鉴权）、`ENGAGELAB_WEBHOOK_SECRET`、`ENGAGELAB_BASE_URL`、`ENGAGELAB_API_USER`、`ENGAGELAB_CREDENTIAL`
- `frontend/apps/tenant/.env.local`：`NEXT_PUBLIC_API_BASE_URL`；`frontend/apps/admin/.env.local`：`NEXT_PUBLIC_ADMIN_API_BASE_URL`（本地开发指向 `http://localhost:8000`；生产不走 env 文件）

## 8. 本地开发

见开头[「🚀 快速开始」](#-快速开始)（本节编号保留以维持既有 §8 引用不断链）。

## 9. 运维脚本速查（backend/scripts/）

| 类别 | 脚本 |
|---|---|
| 初始化 | `bootstrap_platform_admin.py`（平台管理员）、`init_instance.py`（新实例管理员）、`seed_demo_data.py`、`generate_country_holidays.py` |
| 常驻/定时 | `run_sending_worker.py`（发送+对账）、`maintain_partitions.py`（分区维护） |
| 修复/回填 | `backfill_email_status.py`、`backfill_email_template_body_text.py` |
| 一次性事故处理 | `restore_quota_incident_enrollments.py`（2026-07-02 配额事故）、`hard_delete_zhaokui_test_data.py`（租户硬删除目前仅此 ad hoc 出口，#57）、`migrate_legacy.py` |
| 部署辅助 | `push-backend.sh`（仅本地调试） |

生产数据库操作纪律见 [AGENTS.md](AGENTS.md) §1 与 [.trellis/spec/guides/production-operations.md](.trellis/spec/guides/production-operations.md)。客户池 repair（`WMT_LINEAGE_REPAIR_ENABLED`）是高危批量写路径：激活或参数变更需按该纪律逐项审批，禁止对生产迁移重复手工 DROP 或 downgrade（历史发布过程与证据见 #75）。

## 10. 测试与质量现状

- 后端：45 个测试文件、307 个测试函数；默认全量执行为 306 passed、5 个 PostgreSQL 可选集成测试在未提供本机连接串时 skipped；提供本机 PG16 连接串后为 310 passed、1 skipped。重点锁定跨租户不可见性、实例隔离、发送计划生命周期、认证、客户池 repair 与退役表迁移原子回滚；`ruff` 已配置，**无 mypy**
- 前端：tenant Vitest 当前 7 个测试文件、33 项测试；shared-ui 覆盖布局交互与路由反馈；admin 零单元测试，以 type-check 与 production build 为当前门禁
- **CI 现状：GitHub Actions 只构建镜像，不跑任何测试或 lint**——质量门禁缺失是已登记的头部债务（#50）
- 类型契约：前端 shared-types 为手写，与后端 Pydantic 无自动同步（已发现漂移实例，#51）

## 11. 已知债务与风险

**全部登记于 GitHub Issues（唯一台账，本文不重复维护，`gh issue list` 查看）。** 接手前必读的三条头部风险：#43（RLS 未强制，隔离是单点防线）、#46（AI 无真实推理，涉及产品承诺）、#47（域名假验证，涉及客户信任）。

## 12. 非目标

显式放弃的需求以负面清单记录在 [AGENTS.md](AGENTS.md) §0「明确不做」（当前：回信监控）。重启某项非目标前，先经用户拍板并从该清单移除。

## 13. 文档体系与维护规则

1. **真相链**：代码 + 测试 > `.trellis/spec/` 与本文 > 其他一切。发现文档与代码不符，改文档。
2. **分工**：本文只保留人看的入口与事实（快速开始、产品、功能现状矩阵、部署、运维脚本、债务、非目标）；编码约定、数据库与迁移纪律、行为口径、设计系统、Git 与收尾流程、运维细则**只写在 `.trellis/spec/`**，本文只链接不复制。
3. **行为变更**：影响 §3 矩阵的变更合并时同步修订对应行；影响行为口径的变更修订 `.trellis/spec/backend/domain-rules.md`。
4. **实施完成**：销账对应 issue——修复 PR 描述带 `Fixes #NN` 随合并自动关闭，无 PR 的用 `gh issue close` 附证据（收尾清单见 [.trellis/spec/guides/delivery-checklist.md](.trellis/spec/guides/delivery-checklist.md)）。
5. **新教训**：写进 spec 对应的「常见错误」或规则节；`docs/solutions/` 已于 2026-08-23 冻结为历史档案，不再新增。
6. **历史考古**：旧文档 `git show archive/2026-07-pre-handbook:<路径>`；原 TODO.md 台账 `git show e35335d^:TODO.md`；原 `DESIGN.md` 与 `docs/solutions/conventions/` 见 2026-08-23 迁移提交之前的历史；2026-05-16 前的更早历史在远程分支 `origin/codex/tenant-nextjs-rewrite`、`origin/codex/admin-server-prefetch`。
