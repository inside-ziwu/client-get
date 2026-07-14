# TODO — 唯一债务与需求台账

> **本文件是仓库唯一的技术债与未实现需求登记册**，取代原 `docs/tech-debt.md`（TD-1~TD-4 已并入）与原根目录 `TODOS.md`（6 条已逐条处置，其中 2 条经代码核实已完成、直接销账，见文末）。原两份文件已于 2026-07-11 删除（考古：`git show archive/2026-07-pre-handbook:<路径>`）。
>
> **维护纪律**：
> 1. 只登记「今天仍然想要」的承诺——不想要的进 [HANDBOOK.md](HANDBOOK.md) §12 非目标，或直接不留。
> 2. 每条必须有：来源、缺口（缺什么才能用）、验收（做到什么算完）。一条 3~5 行，不展开成实施方案。
> 3. **任何实施任务收尾时，检查本文件并销账**（移入文末「已销账」并注明证据，或直接删行）。
> 4. 优先级：P0 = 安全/客户信任问题，尽快；P1 = 高价值或已承诺；P2 = 体系建设；P3 = 条件触发/择机。

---

## A. 安全与数据隔离

### T-01 · 数据库层多租户隔离未强制（RLS 无 FORCE）— P0
- **来源**：2026-07-11 全量审计
- **缺口**：RLS policy 已在约 20 张表定义，但 `FORCE ROW LEVEL SECURITY` 从未执行（schema.sql 中仅存注释），且应用使用单一连接角色（疑似表 owner，owner 默认绕过 RLS）。实际隔离完全依赖 service 层手写 `tenant_id` 过滤——漏写一处即跨租户泄露，数据库层无兜底。
- **验收**：创建低权限应用角色 + 对全部租户表启用 FORCE RLS；用现有 no_visibility 测试系列验证；生产连接串切换到新角色。
- **实施路径修正（2026-07-12 生产盘点）**：30 张 RLS 表中 **21 张零 policy**（enabled + 无 policy = 对非 owner 角色全拒）——直接切低权限角色会让这 21 张表查询全挂。必须三步走：① 迁移为 21 张表补齐 policy → ② 建低权限角色并切换 → ③ FORCE。工作量比原估大一档。
- 备注：需先连库核实当前连接角色的实际权限。

### T-02 · 团队管理缺最后管理员保护与自操作拦截 — P0（工作量极小）
- **来源**：原 TODOS.md 附加条 / team-management-crud-completion 工程审查
- **缺口**：`backend/app/services/tenant_team_service.py` 的 `update_user`/`delete_user` 无「不能删/降级最后一个 admin」与「不能操作自己」校验；前端只是藏了按钮，API 可直接绕过，可把租户锁死。
- **验收**：两处校验 + 对应测试；用 API 直接调用验证被拒。

### T-03 · 安全细项打包（三件）— P1
- **来源**：2026-07-11 审计
- **缺口**：① `app/core/errors.py` 未处理异常时把 `str(exc)` 原样返回 500 响应体（内部信息透传）；② `app/api/webhooks/engagelab.py` 签名比对用 `==` 而非 `hmac.compare_digest`；③ 同文件把完整 webhook 原始 body+headers 记入 INFO 日志（收件人邮箱等入日志）。
- **验收**：生产 500 只返回 request_id 级信息；签名恒时比对；webhook 日志降敏。

## B. 产品承诺兑现

### T-04 · AI 无真实推理（原 TD-3）— P0（产品价值最高）
- **来源**：docs/tech-debt.md TD-3
- **缺口**：`app/integrations/openrouter.py` 只有余额查询，无 `chat/completions`。三个消费入口已就绪但全是启发式桩：邮件生成（`heuristic-email-*`）、情报摘要（截前 240 字）、AI 评级。产品名义上的「智能」未兑现。
- **验收**：封装真实模型调用（按租户 OpenRouter 配置计费入 ai_usage_logs）→ 至少一个场景（建议先邮件生成）切换为真实推理并可在 UI 感知差异。
- 备注：先接哪个场景是产品决策，实施前确认。

### T-05 · 域名「验证」是假验证（原 TD-1）— P1
- **来源**：docs/tech-debt.md TD-1；B 实例运营手册「坑速查」
- **缺口**：`admin_config_service.py:1707` 附近，点验证即无条件置 verified，不做 DNS/SPF/DKIM/DMARC 查询，也不调 EngageLab。
- **验收**：真实 DNS TXT 校验（或对接 EngageLab 域名状态）；未通过时如实展示原因。短期止血：先改按钮文案，避免运营误判。

### T-06 · 预热域名不自动升档（原 TD-2）— P1
- **来源**：docs/tech-debt.md TD-2
- **缺口**：`warmup_rule_levels` 的升档阈值字段（min_stay_days/min_delivery_rate/max_bounce_rate/max_complaint_rate）已就绪，但无任何 worker 读取判断；`domain_warmup_history.change_type` 实际只有 manual_adjust。
- **验收**：一个定时任务按阈值自动升档并写 history（change_type=auto）；对不满足条件的域名不动作。

### T-07 · 数据源命名分裂 tendata/tengdao（原 TD-4）— P1
- **来源**：docs/tech-debt.md TD-4；B 实例排查第一坑
- **缺口**：种子数据用 `tengdao`，前端下拉与采集服务用 `tendata`；`source_type` CHECK 约束已删除，不再拦截不一致写入。
- **验收**：选定统一取值 → 迁移存量行 → 改前端常量与服务常量 → 恢复约束（或白名单校验）；生产核对无残留旧值。

### T-08 · 情报定时采集 worker — P2（2026-07-11 拍板保留）
- **来源**：原始需求「每天定时采集行业信息」；现状为 admin 人工导入/发布，无任何定时抓取
- **缺口**：一个定时 worker：按 admin 配置的情报源周期抓取 → 生成文章 → 发布给订阅租户（发布链路 `intelligence_service.py` 已就绪，缺的是抓取与调度）。摘要质量依赖 T-04（当前为截前 240 字的启发式桩，可先带桩上线）。
- **验收**：配置了情报源的租户无需任何人工操作即可周期性收到新文章；抓取失败有日志与重试。
- 备注：回信监控（原 T-09）已于 2026-07-11 拍板放弃，记录在 HANDBOOK §12 非目标；编号 T-09 保持空缺不复用。

## C. 工程体系

### T-10 · CI 质量门禁缺失 — P0/P1
- **来源**：2026-07-11 审计
- **缺口**：GitHub Actions 只构建镜像，不跑任何测试/lint；后端 42 个测试文件全靠本地自觉；前端 `pnpm lint` 是死脚本（**eslint 从未被安装**，无任何 eslint 依赖与配置文件）。
- **验收**：CI 增加后端 `pytest + ruff` 与前端 `tsc --noEmit` 必过门禁；前端补装 eslint（或明确改用 biome）并使 lint 真实可跑。

### T-11 · 前后端类型契约缺失 — P1
- **来源**：原 TODOS.md #4；2026-07-11 审计发现已有漂移（`SendingPlanStep` 的 step_order/step_number 并存、`status as never` 强转、多个端点返回 `Record<string, unknown>`）
- **缺口**：后端 224 端点中 `response_model` 使用为 0、schemas 层仅 112 行；前端 shared-types 全手写。
- **验收**：后端核心端点补 Pydantic 响应模型 → OpenAPI 质量达标 → 接入 `openapi-typescript` 生成前端类型替换手写 → 删除强转。
- **文档定位（2026-07-12 决策）**：API 文档 = FastAPI 自动生成的 OpenAPI（Swagger UI `/docs` 即人类可读入口），**禁止另行手工维护端点清单**（docs/specs 的死法不再重演）；本条完成后追加「`openapi.json` 快照随 CI 导出入仓」，使 API 变更在 PR diff 中可见。

### T-12 · 测试覆盖缺口 — P2
- **来源**：原 TODOS.md #1、#5
- **缺口**：admin 前端零测试基建；tenant 前端仅覆盖 settings/team；后端覆盖不均（多租户 RLS、fan-out 幂等等集成场景待补），426 处裸 SQL 缺回归保障。另注意原记录提及 `data_source_tags`/`product_tags` 列不在 alembic 体系内，需手工对齐核实。
- **验收**：admin 搭起 vitest；tenant 覆盖 auth/路由保护；后端补 RLS 与 worker 幂等集成测试。

### T-13 · 行业分发规则硬编码 — P3（条件触发）
- **来源**：原 TODOS.md #6（有意识的 YAGNI）
- **缺口**：「批次标签→行业」规则与行业别名表硬编码在 `app/workers/wmt_lineage_repair.py` 常量中，当前仅 PCB 一个行业。
- **触发条件**：出现第二个采集行业时，将规则数据化（进库表 + admin 可维护）。

## D. 前端体验

### T-16 · 表单基建「装了没通电」— P2
- **缺口**：admin 已声明 react-hook-form + zod + resolvers，shared-ui 已导出 Form 封装，但**全仓零消费**；所有表单为 useState + 手写校验。
- **验收**：挑 2~3 个高频表单（租户创建、发送计划向导、登录）迁移到 RHF+zod 立标杆，后续新表单一律走该模式；或明确决策移除这套依赖（二选一，不允许继续「装着不用」）。

### T-17 · 数据层纪律收敛 — P2
- **缺口**：query-keys 工厂 92 处调用仅 5 文件采用（其余手写数组，靠约定碰巧对齐 SSR hydration）；tenant 登录页绕开统一 client 手写 axios；tenant 无服务端路由守卫（admin 有 middleware，tenant 直输 URL 闪白）。
- **验收**：query key 全量走工厂；登录页回归 `tenantApi.auth`；tenant 补 middleware 或明确接受 CSR 守卫并记录原因。
- 备注：原范围中「手写分页 9 处收敛」已并入 T-23（Pagination 组件）。

### T-18 · 拆分 984 行巨型组件 — P2
- **缺口**：`apps/admin/src/app/(dashboard)/tenants/client-page.tsx` 单文件承载列表+创建+四标签详情，且是全仓唯一用 useEffect 把 query data 拷贝进本地 state 的反模式点。
- **验收**：按 Tab 拆子组件、移除本地拷贝 state、行为不变。
- 备注：建议在 T-23 Phase C 迁移 tenants 页时顺手完成。

### T-23 · 列表页设计系统（DESIGN.md + Pattern 五件套）— P1（2026-07-12 方案已确认）
- **来源**：2026-07-12 列表页一致性盘点（20 页 × 8 维度差异矩阵）：列宽 6 种策略并存、`max-w` 出现 11 个随机像素值、手写「上一页/下一页」分页被复制 9 次且两端 disabled 逻辑已分叉、loading 文案 11 种、3 页无加载/空态区分、数字列右对齐 0/20、同一 `is_active` 字段 Badge/Switch 随机二选一。根因：shared-ui 原子层完备、Pattern 层空白（无 DataTable/Pagination/FilterBar/空态组件）。
- **方案两层**：
  ① **DESIGN.md**（仓库根，Google Stitch 格式，结构借鉴 VoltAgent/awesome-design-md：frontmatter token + components 引用 + Do's/Don'ts + Iteration Guide）：现有 shared-ui token 成文化 + 本次 Pattern 规范；AGENTS.md 增加「改 UI 前先读 DESIGN.md」；美学参照**已选定 Cal.com**（2026-07-12 用户从 Linear/Cal.com 效果对比稿中拍板）：白画布 + 黑主按钮（无彩色 CTA）+ 12px 柔和圆角 + `#f8f9fa` 浅灰分层 + 彩色语义标签（emerald/violet/orange），与现有浅色主题迁移平滑；token 来源 `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/cal/DESIGN.md`，实施时按本项目现状裁剪后写入仓库根 DESIGN.md。
  ② **shared-ui Pattern 五件套**：DataTable（列类型驱动展示：text/number/date/status/boolean/actions；列宽 token 四档 col-sm/md/lg/xl，禁止任意 px；sticky 表头默认开；密度统一 px-3 py-2）、FilterBar（声明式 schema，「查询+重置」标准交互，按钮文案统一「查询」）、Pagination（现有 9 份手写原样上移成组件并统一两端逻辑）、TableState（参数化「正在加载{实体}…/暂无{实体}」）、ListPage 骨架（清除 3 处 space-y 叠加）。
- **已确认默认值**：数字列右对齐+等宽数字；宽表操作列右侧固定；删除确认统一内联 AlertDialogTrigger；布尔状态可交互用 Switch、只读用 Badge；loading 用文字提示、骨架屏不强制。
- **实施顺序**：T-21 完成后启动（少迁 collection-tasks/data-sources 两页）；Phase A 组件+token（纯新增零风险）→ Phase B 打样 2 页验证 API（tenant companies + 一个 admin 简单页）→ Phase C 存量约 16 页分批迁移（每页迁移为净删代码）。
- **吸收关系**：T-15 的空态/骨架部分、T-17 的分页收敛部分已并入本条；T-18 随 Phase C 顺手完成。
- **验收**：DESIGN.md 通过 `npx @google/design.md lint`；五件套上线且打样 2 页通过用户走查；全量迁移后 grep 无手写 `<table>`、无手写分页、无 space-y 叠加容器。

## E. 清理与定位

### T-19 · 死代码与失效配置清理 — P3
- **清单**：`shared-api/src/tenant/prospects.ts`（幽灵 API，零 UI 消费）、`shared-ui/components/form.tsx` 若 T-16 决策移除、`shared-hooks/usePermission.ts`（零消费）、admin 本地 `lib/utils.ts` 的 cn() 副本、tenant `test:contract` 死脚本、`components.json`（shadcn 配置与实际组件路径不符）。`fan_out.py` 与重复 `wmt_lineage.py` 已由 T-21 Phase A 删除。
- **验收**：逐项删除或合并，grep 零残留。

### T-20 · 租户硬删除工具定位 — P3
- **缺口**：`tenant_hard_delete_service.py` 未挂任何 API，唯一出口是按具体客户命名的一次性脚本（`hard_delete_zhaokui_test_data.py`），无使用文档。
- **验收**：决定定位（参数化运维脚本 / admin API + 二次确认），沉淀使用说明进 HANDBOOK §9。

### T-21 · 采集子系统摘除（Phase A 本地完成、待发布门禁；Phase B 未开始）— P1
- **来源**：2026-07-12 采集子系统调研（代码双线调研 + 生产库只读核查）+ 2026-07-14 完整 autoplan 审查。用户已拍板 G-A（平台不做全局评分，Tenant 按自己的当前模板评分）与 P-R（manual > keyword > reverse > unknown）；PCB 活跃租户共享全池但排除手工私有行。背景：采集执行管线 2026-05-19 已删且从未重建，采集数据全部由外部流程直接写库。
- **执行分期**：Phase A 只做运行时摘除、全池关系 repair、Tenant 评分、前端正名与文档同步，不迁移数据库、不部署、不写生产；Phase B 才做被退役表的 dump、恢复演练与 DROP，需单独方案和明确审批。
- **Phase A 本地证据（2026-07-14）**：后端 309 passed/1 skipped，真实 PostgreSQL 回滚集成测试 1 passed；Tenant 33 tests；全 workspace type-check、Admin/Tenant production build、改动文件 Ruff F/I 与 `git diff --check` 全绿。尚未部署，未执行生产写入。
- **范围 A（死壳）**：Phase A 删除 admin `/collection-tasks`、shared-api 死方法、后端假数据与孤儿端点、`backfill_tendata_raw_contacts.py`、重复 `wmt_lineage.py`、`get_data_source_credential_secret`；Phase B 才 DROP 4 张冻结旧表 `clean_companies`/`clean_contacts`/`clean_company_sources`/`clean_company_keywords`（生产数据均止于 2026-05-14）。
- **范围 B（凭证体系）**：Phase A 摘除 admin `/data-sources` 页面、路由与 internal 凭证端点（`GET /internal/api/v1/collection/credentials/{source_type}`），admin 首页改指向用户管理；Phase B 再清理残余 service CRUD 并 DROP `data_sources` + `data_source_credentials`（生产仅 6+2 行，credentials 止于 5-07）。`DATA_SOURCE_ENCRYPTION_KEY` **不得退役或轮换**：名称虽旧，仍用于 Tenant OpenRouter Key 与存量密文。Phase B 完成后 T-07 随之销账；运营手册「02 配数据源采集账号」已改为「确认共享客户池」。
- **范围 C（peer 死代码与表）**：Phase A 删除 `peer_company_cleaning_service.py`、`peer_company_backfill_service.py`、`scripts/peer_backfill_runner.py`，并退役 peer-companies API 与前端契约。2026-07-12 三方独立验证结论一致：约 12 万行数据在 2026-05-14 一次性生成后遗弃，今日零活路径且无 DB 外部依赖。Phase B 经 dump 与恢复演练后再按 contacts/sources/keywords → peer_companies 顺序 DROP 4 表，不改历史迁移 `20260514_0040`。
- **范围 D（正名）**：admin 导航「采集」组改名（4 个数据浏览页保留）；HANDBOOK 功能矩阵、口径表与 §2 业务主链同步改写（「⑨ 订阅关键词」环节移除，改为「公司数据按租户行业全量下发，当前仅 PCB」）。
- **范围 E（关键词订阅摘除与分发通道收敛，2026-07-12 深查后定稿）**：背景——订阅链路结构性死亡（血缘桥 2026-05-15 迁移后冻结，新词永远零匹配）、175 个关键词 98.9% 为零匹配孤儿、生产仅 3 条订阅且两个月无人使用；**但 reverse（精准反推）公司 4,103 家仅靠订阅通道分发**（曾造成租户间 3~4 千家供给差异：订两个词的租户比订一个词的多看约 1,100 家）。用户拍板（2026-07-12）：reverse 数据可向全部 PCB 租户全量下发。
  - 摘除：tenant `/settings/keywords` 页 + keywords API（4 路由）+ `tenant_settings_service` 关键词四方法 + `keyword_service.py` + `fan_out.py` 整文件 + `wmt_lineage_repair.py` 内关键词 fan-out 与血缘回填 SQL（normalize/clean_path/raw_fallback 三段）+ `scripts/repair_wmt_lineage.py` + `scripts/rebuild_tenant_companies.py` + seed 的 `ensure_keywords` + dashboard `plan_overview.keyword_count` 改写 + 对应测试（test_fan_out_no_visibility、test_settings_no_hide 等，详见 2026-07-12 精查报告连带清单）。
  - 修改：单一 `_SQL_FAN_OUT_FULL_POOL` 向当前实例的活跃 PCB 租户下发全池，去掉关键词标签限定，保留状态刷新，并用 `(wc.source_id IS NULL OR wc.source_id NOT LIKE 'manual-%')` 排除手工私有行；`recovered-` 仍视为共享历史资产。onboarding 改为「筛选目标公司」。
  - Phase B DROP：`tenant_keyword`（3 行，dump 留档）；`keyword_master`（175 行）继续保留（外部表历史列仍引用）。
  - 300 秒循环终态：行业全池下发（排除私有行）+ 失效清理 + 补打分三件事。
  - 预期效果：4 个租户供给对齐**全池共享部分**（约 40,464 家减去租户私有 manual 行，补齐零订阅租户约 4,100 家 reverse 缺口）；反推链未来重启后新公司自动分发，无断供；私有录入公司仍仅录入者可见。
- **安全边界**：Phase A 对外部写入表结构与数据零接触，也不执行任何生产写入；repair 默认沿用现有开关，部署前先关闭。Phase B 的任何 DROP 都必须先逐表 dump、验证恢复并再次审批。
- **Phase A 验收**：退役页面/API 不再出现在运行时；保留 4 个只读数据浏览契约；P-R 分类、PCB 全池、manual 排除、实例边界、幂等与 Tenant 当前模板补评分均有测试；发送计划、公司列表、双端 build、pytest、type-check 全绿。部署与生产首轮对齐另走门禁，不因本地代码完成自动执行。

### T-22 · 外部写入契约文档化与数据新鲜度监控 — P1
- **来源**：同上调研 + 2026-07-12 schema 全景盘点。系统核心数据由外部流程直写的表实测为 **14 张**（原知 10 张 + 盘点新发现 4 张隐形区域：`waimaotong_keyword_raw_companies`/`_contacts`（389 万行 / 6.7GB，全库最大，代码零引用）、`waimaotong_clean_source_links`、`crawl_progress`（曾被迁移 0054 DROP、外部又重建，22,674 行））；clean 层 4 张连表结构都在本系统 alembic/schema 管理之外；`wmt_lineage_repair.py` 头注释自述「外部流程可能重建表」。外部断供时下游不报错，只会静默消费越来越旧的数据。
- **缺口**：① 契约入 HANDBOOK：**14 张表清单**、4 张脱管 clean 表的结构快照（2026-07-12 已从生产取得）、「平台不再回写全局评分或关键词血缘，Tenant 评分写入自有 `company_scores`」的边界声明、**「schema 变更双方知会」条款**（外部曾重建被系统删除的表、曾新建系统不知情的巨表——单方面变更已实际发生）、各管道数据状态口径（外贸通线持续更新 / 同行反推线为已完成的静态存量）、**资料卡瘦身声明**（wc 86 列中 10 列恒空、15 列填充率 <5%，声明系统不消费这些列）、**租户私有行寄生风险**——租户手动新增的公司（`source_id LIKE 'manual-%'`，现 2 家）及其手填联系人寄生在外部管理的 `waimaotong_clean_companies`/`waimaotong_clean_contacts` 中，外部流程若全量重建这两张表将无声丢失租户数据，需在契约中与外部约定保留，或长期迁移至自有表；② 新鲜度监控：**仅对外贸通线**（唯一活管道）设 max(created_at) 停滞告警。
- **验收**：契约章节入 HANDBOOK；外贸通线告警可触达。
- **备注**：反推链停滞原因已确认为**计划内**（2026-07-12 外部答复：同行数据已采集完毕，励销云止于 5-26 / 腾道 raw 止于 6-09 均为正常收尾）；该线不设告警，如未来重启同行采集需同步启用监控。

## F. 数据隔离

### T-24 · 手动新增公司的联系人跨租户外溢 — P2
- **来源**：2026-07-12 手动新增公司隔离精查（`tenant_ops_service.create_company` 逐段核对）
- **缺口**：租户手动新增公司时若 domain/名称命中池中已有行（含其他租户先前手动建的行），手填联系人会写入共享 `sys_company_id` 下的 `waimaotong_clean_contacts`——此后任何关联该公司的租户都会经 `ensure_contacts_from_wmt`（按 sys_company_id 物化）拿到这条「别的租户手填的联系人」。联系人属商业敏感数据；此外溢面为既有行为，与 T-21 无关，现状因 manual 行仅 2 家且无共享而未实际发生。
- **验收**：手填联系人与外部采集联系人隔离（方案待定：私有联系人表 / 租户归属标记），或明确决策接受共享并把口径写入 HANDBOOK。

## G. Schema 治理（2026-07-12 全景盘点立项）

### T-25 · Schema 主权收复（仓库大扫除）— P2（2026-07-12 拍板：做，清单先给外部）
- **来源**：2026-07-12 schema 全景盘点（生产 information_schema 全量 × alembic 68 迁移考古双线）
- **范围**：① **23 张备份表清理**——第一步：清单已生成、待用户转交外部确认（其中 7-09 的 `waimaotong_clean_companies_ai_label_backup` 为外部程序所建，必须确认）→ 确认后逐张 dump 留档 → DROP；② `tenant_companies.score_adjustment` **幽灵列转正**（生产存在、代码在用、不在任何迁移——0034 重建时抹掉后被带外加回；补一条对齐迁移，同批核实 `score_adjusted_at/by/reason` 三列的代码引用是否报错，`tenant_ops_service.py:428` 附近）；③ `shared_contacts`/`competitor_companies`/`competitor_contacts` 残留清理（三表已被带外删除，蓝图与代码引用需同步移除，注意 `internal_ops_service.batch_upsert_competitors` 若引用已消失的表则该端点必炸）；④ **schema.sql 蓝图重建并机制化**（2026-07-12 决策：schema 文档一律生成、禁止手工维护）：一次性从生产 `pg_dump --schema-only` 重新生成 + 人工标注外部表段落（修复 8 处图有实无、9+ 处实有图无、6 处 FK 列类型标错、1 处视图定义过时）；随后落一个重生成脚本——每次迁移合并后重跑并与上版 diff，**diff 即带外变更探测器**（外部新建/重建表会自动现形，衔接 T-22 契约监督）；同时从 information_schema 自动生成按业务域分组的 ER 图（mermaid/DBML，供业务视角查阅）；⑤ 活表零使用索引清理（`idx_wmt_clean_name`、`idx_tenant_companies_tags` 等）；⑥ 移除代码对恒空列 `email_priority` 的读取。
- **验收**：备份表清零（dump 档可查）；照新蓝图建库结构与生产一致；grep 无三张已删表的残留引用。

### T-26 · 公司列表↔公司池的对账机制 — P2【方向待拍板】
- **来源**：同上盘点。`tenant_companies.clean_company_id`、`tenant_contacts.clean_contact_id/clean_company_id` 三条核心 FK 于迁移 0045 **故意删除**（避免阻碍外部整表重建 wc），现由 `wmt_lineage_repair` 每 300 秒 `DELETE ... WHERE NOT EXISTS` 模拟级联清理——应用层轮询替代数据库约束，轮询窗口内存在悬空引用（公司详情打不开）风险，且无监控无测试。
- **选项**：A 维持轮询 + 加监控（每轮删除行数指标与异常暴增告警），待外部答复「是否还会整表重建公司池」后再决定是否升级；B 恢复三条 FK 自动对账（前提：外部承诺不再整表重建）。
- **状态**：2026-07-12 用户未拍板；「是否还会整表重建」已并入待问外部清单（与 T-25 备份清单同一次转发）。

### T-27 · 空库无法从 Alembic 基线建库 — P1
- **来源**：2026-07-14 T-21 Phase A PostgreSQL 实库集成测试准备；在全新 `clientget_test` 数据库执行 `alembic upgrade head` 首次发现。
- **缺口**：首个迁移创建 `company_scores.tenant_company_id uuid`，但被引用的 `tenant_companies.id` 为 `bigint`，PostgreSQL 拒绝创建外键，导致仓库迁移无法从空库建立当前 schema。既有环境因历史带外演进未暴露该问题。
- **验收**：在全新 PostgreSQL 数据库执行 `alembic upgrade head` 全绿；生成 schema 与当前受支持结构一致；补 CI 空库迁移测试，防止再次漂移。

---

## 已销账（本次核对确认，留档防止重复登记）

| 原条目 | 结论与证据 |
|---|---|
| TODOS.md #2「收件人筛选 NOT IN 应含 invalid」 | **已修复**：`tenant_messaging_service.py` 收件人筛选已排除 invalid（2026-07-11 代码核实），原台账未销账属文档滞后 |
| TODOS.md #3「Webhook 回填定时任务候补」 | **已被实现覆盖**：对账 worker（`app/workers/reconciliation.py`）已常态化兜底 webhook 丢失，比原设想的每日回填更实时 |
| T-14「移动端导航完全不可用」 | **已修复**：双端接入 shared-ui `DashboardShell`；375px 实测抽屉打开、链接/Escape 关闭，1440px 桌面侧栏与折叠状态正常；shared-ui 交互测试 + 双端 build 通过 |
| T-15「无错误边界与路由级 loading」 | **已修复**：双端应用级与 dashboard 级 `error.tsx`、dashboard `loading.tsx` 已接入；临时故障注入验证两级恢复 UI 与流式加载骨架；shared-ui 状态测试 + 双端 build 通过 |
| T-19 部分项「openspec 系列 skill/command 定义」 | **已删除**（2026-07-11 用户授权）：`.claude/commands/opsx/`、`.claude/skills/openspec-*`、`.codex/skills/openspec-*` 共 15 个 tracked 文件，另清理 `.agents/skills/source-command-opsx-*` 5 个 untracked 镜像；`settings.local.json` 内 3 行 openspec CLI 权限白名单属用户本地设置，未动 |
