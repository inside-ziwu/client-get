# ClientGet 项目手册（HANDBOOK）

> **本文件是本仓库的唯一事实源入口。** 基线日期：2026-07-14（基于对代码、数据库迁移、部署配置的全量只读审计）。
>
> **文档地位声明**：仓库内有效文档 = 本手册 + [TODO.md](TODO.md)（唯一债务与需求台账），外加两个附属：[docs/solutions/](docs/solutions/)（踩坑知识库）与 [docs/handovers/2026-07-06-b-instance-operations-manual.md](docs/handovers/2026-07-06-b-instance-operations-manual.md)（B 实例运营手册）。**其余历史文档（旧工作流产物、specs、会议资料、原型、openspec/ 等约 370 份）已于 2026-07-11 整体删除**，考古方式：`git show archive/2026-07-pre-handbook:<路径>`。手册内容与代码冲突时，以代码与测试为准，并修订本手册。

---

## 1. 产品是什么

**ClientGet 是一个 B2B 外贸获客与邮件营销 SaaS**：外部境外采购商数据入池 → 分类与租户评分 → 邮件序列触达 → 送达/打开数据回传。当前唯一投产行业是 **PCB（电路板）制造业出海获客**。

- **商业形态**：平台方（我们）运营 admin 后台，为客户企业开通租户；客户的销售/运营团队使用 tenant 自服务后台。
- **双端**：`admin`（平台运营后台，端口 3000）+ `tenant`（租户自服务后台，端口 3001，URL 按 `/t/{slug}` 区分租户）。
- **生产实例**：Instance A（api.xinanpcb.com）与 Instance B（同一套代码与底层库，账户体系按实例隔离），B 实例已有真实客户运营，操作细节见运营手册。

## 2. 核心业务流程

原始设计共 13 个场景 + 4 个后台任务（源自立项文档 V3.2，此处为兑现后的现实版本）：

**平台侧一次性配置（admin）**：
① 配置行业评分模板 → ② 维护行业情报源 → ③ 配置行业邮件模板 → ④ 配置域名预热规则 → ⑤ 配置 AI 模型与定价。客户数据由外部管道写入共享池，本平台不再管理采集任务或数据源凭证。

**开通客户（admin）**：
⑦ 创建租户 + 配发信域名（选预热档位）+ 配置该租户 OpenRouter 密钥 →（可选）添加团队成员 → 交付登录信息（完整分步操作见运营手册）

**租户自服务主链（tenant）**：
⑧ 首次登录与引导 → ⑨ 从共享客户池浏览/筛选公司 → ⑩ 优选客户入群组（联系人自动物化、按职级分类）→ ⑪ 创建/编辑邮件模板（富文本，支持测试发送）→ ⑫ 按筛选条件创建发送计划（预览收件人 → 锁定 → 启动）→ ⑬ 仪表盘监控送达/打开/退信数据

**后台自动任务**：数据血缘修复与行业分发循环（进程内，300 秒/轮）、发送 worker（独立进程，节流+熔断）、邮件状态对账（约 10 分钟/轮，兜底 webhook 丢失）、发送计划自动完成。

> 注意与原始设计的两处已知落差：「AI 大模型」目前无真实推理（启发式桩，T-04）；「情报自动采集」尚未实现、已排期补建（T-08），当前过渡为人工策展。详见功能矩阵与 TODO。

## 3. 功能现状矩阵（2026-07-14 审计基线）

图例：✅ 完成并可用 ｜ 🟡 半成品（外壳在、缺关键环节，缺口必读）

### 平台侧（admin）

| 功能 | 状态 | 说明与关键位置 |
|---|---|---|
| 共享客户池与外部数据浏览 | ✅ | 保留「同行原始/同行清洗/外贸通原始/客户池」四页；只读外部写入的 `lixiaoyun_api_*`、`waimaotong_*` 表。采集任务、数据源凭证与 peer 清洗管线已从运行时及生产物理表退役（T-21 Phase A/B）。 |
| 联系人职位分类体系 | ✅ | 分级关键词已数据化可维护。admin `/contact-classification` |
| 评分模板配置 | ✅ | admin `/scoring-templates` |
| 工作日历（国家/节假日/规则集） | ✅ | 供时区感知发送使用。admin `/work-schedule` |
| 域名与预热管理 | 🟡 | 建域名/选档位可用；**「验证」按钮是假验证，不查 DNS/SPF/DKIM，直接置 verified**（T-05）；**预热不会自动升档，只有手动调整**（T-06）。`admin_config_service.py:1707` 附近 |
| AI 模型配置 | 🟡 | 配置与余额查询可用；**系统没有任何真实 LLM 推理调用**（T-04）。`backend/app/integrations/openrouter.py` |
| 平台邮件模板 | ✅ | 含向租户同步。admin `/email-templates` |
| 情报源管理 | 🟡 | 人工导入/发布可用；**定时自动采集未实现，已排期**（T-08）。`intelligence_service.py` |
| 租户生命周期管理 | ✅ | 创建/暂停/删除、域名、团队、OpenRouter 四块。admin `/tenants`（前端为 984 行单文件，T-18） |

### 租户侧（tenant）

| 功能 | 状态 | 说明与关键位置 |
|---|---|---|
| 认证体系 | ✅ | 登录、refresh token 静默刷新（并发排队）、强制改密、onboarding。`shared-api/src/client.ts` |
| 仪表盘 | ✅ | 邮件统计趋势、计划概览、配额/AI 余额、漏斗。`tenant/core.py` 5 端点 |
| 公司列表与筛选 | ✅ | 16 项多维条件（含采集类型、已入群）紧凑常驻；筛选控件与表格列使用 shared-ui 统一的 `small/medium/large/{ custom }` 宽度契约，默认 `medium`、例外显式声明；表格按长文本左、短枚举居中、数值与操作右的语义对齐。远程多选支持明确搜索文案、可查看加载态与空态。函数索引优化过查询性能。`tenant_query_service.py` |
| 优选客户（群组） | ✅ | 入群自动物化联系人。tenant `/curated-customers` |
| 评分 | ✅ | **租户评分是确定性规则引擎，不是 AI**；仅依该租户当前模板/版本写入 `company_scores`，平台不对全局客户池打分。`scoring_engine_service.py` |
| 邮件模板 | ✅ | TipTap 富文本、纯文本兜底、测试发送；「AI 生成」当前为启发式桩（T-04）。tenant `/templates` |
| 发送计划全生命周期 | ✅ | 4 步向导、收件人预览/锁定、状态机操作、运行中轮询。tenant `/send-plans/*`，后端 `tenant_messaging_service.py`（3261 行核心文件） |
| 团队管理 | 🟡 | CRUD 可用；**API 层缺最后管理员保护与自操作拦截，可把租户锁死**（T-02）。`tenant_team_service.py` |
| 情报中心（阅读侧） | ✅ | 列表/已读/收藏/归档。tenant `/intelligence` |
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
| 多租户隔离 | 🟡 | 应用层过滤 + 测试锁定可用；**数据库层 RLS 未强制（无 FORCE、单一 owner 连接），属单点防线**（T-01） |
| 前端布局与路由反馈 | ✅ | Admin/Tenant 共用 shared-ui `DashboardShell`；小屏使用左侧抽屉导航，桌面保留折叠侧栏；应用级与 dashboard 级错误边界提供重试/刷新，dashboard 路由提供统一 loading 骨架 |

已废弃：本地一键验证脚本（openspec 时代承诺，30 项任务只完成 4 项，核心脚本从未创建，判定放弃）。

## 4. 系统架构

```
client_get/
├── backend/            FastAPI + PostgreSQL + Alembic + workers（app/ 91 文件 ≈ 20.8k 行）
│   ├── app/api/        路由层：admin(/admin/api/v1) tenant(/t/{slug}/api/v1) internal(/internal/api/v1) webhooks(/webhooks)
│   ├── app/services/   业务逻辑 + SQL（30 文件 ≈ 15.2k 行，占 73%）
│   ├── app/workers/    sending / reconciliation / wmt_lineage_repair
│   ├── app/db/         连接池、RLS 会话变量、事务、分区维护
│   ├── app/security/   JWT（platform / tenant / service 三种 kind）、bcrypt、服务间鉴权
│   ├── alembic/        69 个迁移（2026-04-21 起），仓库与生产 head=20260714_0001；T-21 Phase B 已完成
│   └── scripts/        运维脚本（见 §9）
├── frontend/           pnpm workspace（166 文件 ≈ 18.4k 行）
│   ├── apps/tenant/    Next.js 15 + React 19，纯客户端渲染，端口 3001
│   ├── apps/admin/     Next.js 15 + React 19，SSR 预取壳 + 客户端页，端口 3000
│   └── packages/       shared-ui（Radix 封装 + 设计令牌）/ shared-api（统一 axios 客户端）/ shared-hooks / shared-types
└── 03_database/schema.sql   数据库蓝图（1497 行，含 RLS policy 定义）
```

**后端路由组**：admin 侧 config/collection/tenants/work-schedule/contact-classification/auth；tenant 侧 messaging/ops/settings/core/team/intelligence/auth；internal 仅保留发送与情报服务端点；webhooks 接收 EngageLab 事件。采集和数据源凭证端点已退役。

**核心表族谱**：身份（platform_users/tenants/users/user_roles）→ 外部原始层（waimaotong_/tendata_/lixiaoyun_raw_*）→ 外部清洗共享层（waimaotong_clean_*/lixiaoyun_api_clean_*）→ 租户业务层（tenant_companies/tenant_contacts/company_scores/groups）→ 外联层（sending_plans/sequence_enrollments/emails/email_events/email_templates）→ 域名预热（domain_warmup_*/domain_daily_usage/work_rule_sets/countries）→ 支撑（notifications/audit_logs/ai_usage_logs/service_idempotency_keys）。

**认证与隔离**：JWT HS256，三种 kind（platform/tenant/service）；租户 token 校验 slug 与 URL 一致、角色与 DB 实时比对；多实例用 `iid` claim。租户数据隔离现状要如实理解：RLS policy 已定义约 20 张表，但 **FORCE ROW LEVEL SECURITY 从未启用**，应用使用单一连接角色——实际隔离靠 service 层手写 `tenant_id` 过滤 + 9 个隔离专项测试文件锁定（T-01 是登记的加固项）。

**worker 部署形态**：sending worker 为独立进程（`scripts/run_sending_worker.py` 常驻，内含约每 10 分钟一轮的对账）；客户池修复循环在 API 进程 lifespan 内常驻，使用带 `instance_id` 的 advisory lock 防同实例并发。

## 5. 关键行为口径

这些是散落在代码里的重要业务决策，按此为准：

| 口径 | 规则 |
|---|---|
| 发送间隔 | 固定 **3 秒**（worker fallback 与新建计划默认 `[3,3]`；2026-07-08 由 1 秒调整） |
| 收件人选取 | 按联系人等级排序选取，**单公司上限 8 人**；排除 unsubscribed/bounced/invalid |
| 发送窗口 | 按**收件人国家**的工作日历（工作日+节假日+时区）决定；不在窗口内则顺延 |
| 配额熔断 | 同域名连续 3 次配额错误 → 熔断至北京时间次日凌晨；10 分钟窗口内 3 次 429 → 限流熔断 |
| 发送幂等键 | `enrollment_id:step_id` |
| 状态对账 | webhook 为主，对账 worker 约每 10 分钟主动查询兜底 |
| 仪表盘统计 | 邮件统计**排除 failed**；「已评分公司」只计入租户当前活跃模板的最新版本分数 |
| 租户评分 | 确定性规则引擎（非 AI），结果归租户所有；平台模板只是创建租户时的默认种子。「AI 评级/邮件生成/情报摘要」当前为启发式桩 |
| 采集类型 | `manual` 看 `source_id LIKE 'manual-%'`；`keyword` 看精确标签「外贸通关键词采集」；`reverse` 看精确「腾道」标签或非空 `source_competitor`；其余为 `unknown`。优先级 manual > keyword > reverse。 |
| PCB 供应商评分 | 只有显式 `reverse` 才视为「有中国 PCB 供应商」；keyword/manual/unknown 均为否 |
| 域名验证 | **当前为假验证**：点击即置 verified，不做任何 DNS 校验（T-05，勿向客户承诺） |
| 预热升档 | 仅手动调整，无自动升档（T-06） |
| 计划完成 | 全部 enrollment 终态后自动置 completed |
| 客户池修复 | 300 秒/轮，共享全池但排除手工私有行；按实例 + PCB 行业隔离，幂等可重复执行 |
| 公司筛选交互 | 16 项查询条件常驻，并按业务语义合并呈现为 12 个控件：进口额、进口次数、联系人、成立年份各使用一体式起止范围；关键词使用 `medium`，国家、细分行业、产品标签、采集类型、群组状态与两种评级显式使用 `small`，范围组件显式使用 256px 自定义宽度。查询/重置跟随最后一个条件，1920px 主工作区保持两排。未选择统一显示“不限”。远程多选加载时可打开并显示转圈与“正在加载选项…”，接口返回后原位刷新；空数组显示“暂无可选项” |
| 时间基准 | 生产数据库会话时区 UTC；熔断恢复等业务锚点用北京时间 |

## 6. 多实例（Instance A / B）

同一套代码 + 共享底层数据库，按 `CLIENTGET_INSTANCE_ID` 区分实例：

> **硬性声明：A、B 共用同一个物理 PostgreSQL `clientget` 数据库，不是两套独立数据库。** `instance_id` 只提供逻辑数据边界；repair、评分、发送和所有批量操作仍竞争同一套连接、CPU、I/O 与锁。即使只操作 B，也必须同时审计 A 的在途发送负载，不能把 B 当成无影响的测试库。

- 每实例独立 JWT secret，token 带 `iid` claim；管理员、租户、认证、worker 任务按实例隔离
- `waimaotong_clean_companies`/`waimaotong_clean_contacts` 公池跨实例共享；`tenant_companies` 关系按实例的租户隔离，手工录入行不跨租户分发
- 新实例初始化：`backend/scripts/init_instance.py`（创建实例管理员）
- 前端按构建时注入的 API 地址区分实例，前端代码无实例概念
- B 实例日常运营（开客户、配发信域名、坑速查）见[运营手册](docs/handovers/2026-07-06-b-instance-operations-manual.md)

## 7. 环境与部署

**两套完全隔离的环境，无切换动作**：

| | 开发 | 生产 |
|---|---|---|
| 数据库 | Neon 云 PG（`CLIENTGET_DEV_DATABASE_URL`） | Sealos PG（环境变量由 Sealos 控制台注入） |
| 后端 | 本地 uvicorn | Sealos 容器（镜像启动时 `/start.sh` 自动 `alembic upgrade head`） |
| 前端 | 本地 next dev | Sealos 容器，API 地址**构建时**经 `--build-arg` 写死 |

**发布流程**：push GitHub → Actions 手动触发 `workflow_dispatch`（选 service: admin/tenant/backend）→ amd64 构建推送阿里云 ACR（`crpi-…aliyuncs.com/lay_inside/clientget-{service}`，tag 格式 `YYYY.MM.DD-rN` 自动递增）→ Sealos 控制台手动更新对应服务镜像 tag（backend 镜像同时供 API 与 worker 容器使用）。本地 `push-*.sh` 仅调试用（ARM 交叉编译慢），不作正式发布。

**环境变量**（值由用户手动维护，不得自动修改）：

- `backend/.env`：`CLIENTGET_DEV_DATABASE_URL`、`CLIENTGET_PROD_DATABASE_URL`、`JWT_SECRET`、`ADMIN_EMAIL`、`ADMIN_PASSWORD`（首次启动引导平台管理员）、`DATA_SOURCE_ENCRYPTION_KEY`（历史名，仍用于 OpenRouter Key 等存量密文，不得删除或轮换）、`INTERNAL_SERVICE_SECRET`（worker↔API 鉴权）、`ENGAGELAB_WEBHOOK_SECRET`、`ENGAGELAB_BASE_URL`、`ENGAGELAB_API_USER`、`ENGAGELAB_CREDENTIAL`
- `frontend/apps/tenant/.env`：`NEXT_PUBLIC_API_BASE_URL`；`frontend/apps/admin/.env`：`NEXT_PUBLIC_ADMIN_API_BASE_URL`（本地开发指向 `http://localhost:8000`；生产不走 .env）

## 8. 本地开发

```bash
# 后端（Python ≥3.11，uv 管理，实际 .venv 为 3.12）
cd backend
uv sync
# 配好 backend/.env（开发库为 Neon，见 §7）
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload        # http://localhost:8000
uv run pytest -q                            # 42 个测试文件
uv run python scripts/run_sending_worker.py --once   # 发送 worker 单轮
uv run python scripts/seed_demo_data.py     # 演示数据（demo 租户）

# 前端（pnpm 10.28.1，Node ≥20）
cd frontend
pnpm install
pnpm dev:admin     # http://localhost:3000
pnpm dev:tenant    # http://localhost:3001
pnpm type-check    # 全 workspace tsc
```

已知失效脚本（勿踩）：`frontend` 的 `pnpm lint`（eslint 从未被安装，T-10）、tenant 的 `test:contract`（目标文件不存在，T-19）。

## 9. 运维脚本速查（backend/scripts/）

| 类别 | 脚本 |
|---|---|
| 初始化 | `bootstrap_platform_admin.py`（平台管理员）、`init_instance.py`（新实例管理员）、`seed_demo_data.py`、`generate_country_holidays.py` |
| 常驻/定时 | `run_sending_worker.py`（发送+对账）、`maintain_partitions.py`（分区维护） |
| 修复/回填 | `backfill_email_status.py`、`backfill_email_template_body_text.py` |
| 一次性事故处理 | `restore_quota_incident_enrollments.py`（2026-07-02 配额事故）、`hard_delete_zhaokui_test_data.py`（租户硬删除目前仅此 ad hoc 出口，T-20）、`migrate_legacy.py` |
| 部署辅助 | `push-backend.sh`（仅本地调试） |

客户池 repair 发布门禁：

1. 发布 Phase A 后端前，由用户在目标实例手动设置现有变量 `WMT_LINEAGE_REPAIR_ENABLED=false`；本仓库不修改 `.env`。
2. 仅发布代码并确认 API 健康，此时不会执行全池 fan-out。
3. 激活前做生产只读基数、`EXPLAIN`、关系差异及 **A 实例在途发送负载**快照；再展示准确影响量与写入 SQL，取得针对该操作的明确批准。A/B 共用物理数据库，只按 `instance_id` 逻辑隔离。
4. 每次只激活一个实例，观察至少两个 300 秒周期的 `fan_out/deleted_stale/score_*` 统计；异常时立即关闭开关。
5. T-21 Phase B 已于 2026-07-15 完成：PG16 age 加密备份与隔离恢复演练通过，生产最终只读闸门确认 revision、目标表、旧 SQL、锁、活跃查询与到期邮件均符合预期后，由用户明确批准执行。
6. A/B 共用同一个物理库，因此仅由**唯一一个**一次性 migration runner 执行；生产已从 `20260708_0002` 升至 `20260714_0001` 并回读确认 15 张退役表全部不存在。后续 A、B 后端镜像可按正常顺序滚动，`/start.sh` 只会确认当前 head；禁止重复手工 DROP 或尝试 downgrade。

生产数据库操作纪律：默认只读；任何写操作先展示 SQL 与影响范围、经用户确认；模式见 [docs/solutions/conventions/production-data-operation-safety.md](docs/solutions/conventions/production-data-operation-safety.md)。

## 10. 测试与质量现状

- 后端：45 个测试文件、307 个测试函数；默认全量执行为 306 passed、5 个 PostgreSQL 可选集成测试在未提供本机连接串时 skipped；提供 T-21 本机 PG16 连接串后为 310 passed、1 skipped。重点锁定跨租户不可见性、实例隔离、发送计划生命周期、认证、客户池 repair 与退役表迁移原子回滚；`ruff` 已配置，**无 mypy**
- 前端：tenant Vitest 当前 7 个测试文件、33 项测试；shared-ui 覆盖布局交互与路由反馈；admin 零单元测试，以 type-check 与 production build 为当前门禁
- **CI 现状：GitHub Actions 只构建镜像，不跑任何测试或 lint**——质量门禁缺失是已登记的头部债务（T-10）
- 类型契约：前端 shared-types 为手写，与后端 Pydantic 无自动同步（已发现漂移实例，T-11）

## 11. 已知债务与风险

**全部登记于 [TODO.md](TODO.md)（唯一台账，本手册不重复维护）。** 接手前必读的三条头部风险：T-01（RLS 未强制，隔离是单点防线）、T-04（AI 无真实推理，涉及产品承诺）、T-05（域名假验证，涉及客户信任）。

## 12. 非目标（显式放弃的需求）

| 需求 | 状态 |
|---|---|
| 回信监控（原始需求第 8 条的一部分） | **已放弃**（2026-07-11 拍板）：从未开工，送达商支持存疑；如未来重启，先做供应商回信检测能力调研 |

> 放弃也是决策——记录在此防止未来重复发现、重复讨论。重新启用某项非目标前，先在此删行并登记回 TODO。（情报定时采集曾列为放弃候选，2026-07-11 拍板保留为 T-08。）

## 13. 文档体系与维护规则

1. **真相链**：代码 + 测试 > 本手册 > 其他一切。发现手册与代码不符，改手册。
2. **行为变更**：影响 §3 矩阵或 §5 口径的变更，合并时同步修订本手册对应行。
3. **实施完成**：检查 [TODO.md](TODO.md) 并销账（这是每次收尾的固定动作）。
4. **新踩坑**：沉淀到 `docs/solutions/`（现有 14 篇，分 best-practices/conventions/database-issues/integration-issues/runtime-errors/workflow-issues 六类）。
5. **历史考古**：历史文档删除时将打 tag `archive/2026-07-pre-handbook`；此后用 `git show archive/2026-07-pre-handbook:<路径>` 查阅任何旧文档。另注意：项目 2026-04-17 至 2026-05-16 的更早历史保留在未合并的远程分支 `origin/codex/tenant-nextjs-rewrite`、`origin/codex/admin-server-prefetch` 上（main 是三仓库合并后的重新起点）。
