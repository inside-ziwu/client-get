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

### T-12 · 测试覆盖缺口 — P2
- **来源**：原 TODOS.md #1、#5
- **缺口**：admin 前端零测试基建；tenant 前端仅覆盖 settings/team；后端覆盖不均（多租户 RLS、fan-out 幂等等集成场景待补），426 处裸 SQL 缺回归保障。另注意原记录提及 `data_source_tags`/`product_tags` 列不在 alembic 体系内，需手工对齐核实。
- **验收**：admin 搭起 vitest；tenant 覆盖 auth/路由保护；后端补 RLS 与 worker 幂等集成测试。

### T-13 · 行业分发规则硬编码 — P3（条件触发）
- **来源**：原 TODOS.md #6（有意识的 YAGNI）
- **缺口**：「批次标签→行业」规则与行业别名表硬编码在 `app/workers/wmt_lineage_repair.py` 常量中，当前仅 PCB 一个行业。
- **触发条件**：出现第二个采集行业时，将规则数据化（进库表 + admin 可维护）。

## D. 前端体验

### T-14 · 移动端导航完全不可用（双端同款 bug）— P1
- **来源**：2026-07-11 审计
- **缺口**：两端侧栏 `hidden lg:block`（<1024px 不可见），而 app-shell 的汉堡按钮（`aria-label="打开导航"`）**没有 onClick**——小屏下主导航不可达。`apps/tenant/src/components/layout/app-shell.tsx:46`、admin 同款 :47。
- **验收**：小屏点汉堡出抽屉导航（shared-ui 已有 Sheet 组件可用）；顺手把两端重复的 284/287 行布局壳抽到共享包。

### T-15 · 无错误边界与路由级 loading — P2
- **缺口**：两端零 `error.tsx`；`loading.tsx` 全仓仅 admin 一处。运行时异常无恢复 UI。
- **验收**：两端补路由级 error/loading。
- 备注：原范围中「统一 Skeleton/EmptyState 收编空态」部分已并入 T-23（由 TableState 组件承载），本条只剩路由级错误边界。

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
- **清单**：`shared-api/src/tenant/prospects.ts`（幽灵 API，零 UI 消费）、`shared-ui/components/form.tsx` 若 T-16 决策移除、`shared-hooks/usePermission.ts`（零消费）、`app/workers/fan_out.py` 的 FanOutWorker class（死封装）、`wmt_lineage.py` 与 `wmt_lineage_repair.py` 两份近重复 SQL（合并为单一来源）、admin 本地 `lib/utils.ts` 的 cn() 副本、tenant `test:contract` 死脚本、`components.json`（shadcn 配置与实际组件路径不符）。
- **验收**：逐项删除或合并，grep 零残留。

### T-20 · 租户硬删除工具定位 — P3
- **缺口**：`tenant_hard_delete_service.py` 未挂任何 API，唯一出口是按具体客户命名的一次性脚本（`hard_delete_zhaokui_test_data.py`），无使用文档。
- **验收**：决定定位（参数化运维脚本 / admin API + 二次确认），沉淀使用说明进 HANDBOOK §9。

### T-21 · 采集子系统摘除（方案已定稿 2026-07-12）— P1
- **来源**：2026-07-12 采集子系统调研（代码双线调研 + 生产库只读核查）+ 用户三项拍板：凭证链已废（外部流程自管凭证，不回调系统）、外部清洗产物确认为 `lixiaoyun_api_clean_companies`、peer_* 表处置待定。背景：采集执行管线 2026-05-19 已删且从未重建，采集数据全部由外部流程直接写库。
- **范围 A（死壳）**：admin `/collection-tasks` 整页（触发/历史按钮对应后端路由不存在，状态/进度字段为硬编码假数据）；`shared-api/collection.ts` 12 个死方法；后端假数据与孤儿端点（`/collection-keywords`、`/collection/dashboard`、`/collection/cleanup-health`、`/clean/companies`、`master-check`、peer 3 个无消费浏览 API）；死脚本 `backfill_tendata_raw_contacts.py`（import 已删模块必报错）；死文件 `app/workers/wmt_lineage.py`；死方法 `get_data_source_credential_secret`；DROP 4 张冻结旧表 `clean_companies`/`clean_contacts`/`clean_company_sources`/`clean_company_keywords`（生产数据均止于 2026-05-14）并同步修改 `admin_collection_service`/`keyword_service` 中的引用。
- **范围 B（凭证体系）**：admin `/data-sources` 整页（admin 首页 `redirect('/data-sources')` 需改指向）；后端 data_sources/credentials CRUD 与 internal 凭证端点（`GET /internal/api/v1/collection/credentials/{source_type}`）；DROP `data_sources` + `data_source_credentials`（生产仅 6+2 行，credentials 止于 5-07）；`DATA_SOURCE_ENCRYPTION_KEY` 从必填配置退役。**完成后 T-07 随之销账**；运营手册「02 配数据源采集账号」整节同步作废（需知会运营）。
- **范围 C（peer 死代码）**：`peer_company_cleaning_service.py`、`peer_company_backfill_service.py`、`scripts/peer_backfill_runner.py`（产物无任何消费者，数据止于 5-14）。**peer_* 4 张表保留不 DROP**（约 12 万行，处置待定——用户 2026-07-12 拍板）。
- **范围 D（正名）**：admin 导航「采集」组改名（4 个数据浏览页保留）；tenant 关键词页文案去掉「采集」；HANDBOOK 功能矩阵与口径表同步改写。
- **安全边界**：10 张外部写入表（raw 6 张 + waimaotong_clean_* 2 张 + lixiaoyun_api_* 2 张）及其全部消费者（发送、评分、公司列表、fan-out、血缘修复）零接触；DROP 前对被删表 dump 留档。
- **验收**：全仓 grep 被删符号零残留；4 个数据浏览页、发送计划、评分、公司列表回归正常；pytest 全绿 + type-check 通过。

### T-22 · 外部写入契约文档化与数据新鲜度监控 — P1
- **来源**：同上调研。系统核心数据由外部流程直写 10 张表，其中 clean 层 4 张（`waimaotong_clean_companies` 86 列 / `waimaotong_clean_contacts` 20 列 / `lixiaoyun_api_companies` 49 列 / `lixiaoyun_api_clean_companies` 53 列）连表结构都在本系统 alembic/schema 管理之外；`wmt_lineage_repair.py` 头注释自述「外部流程可能重建表」。外部断供时下游不报错，只会静默消费越来越旧的数据。
- **缺口**：① 契约入 HANDBOOK：10 张表清单、4 张脱管表的结构快照（2026-07-12 已从生产取得）、「系统仅回写 system_grade/system_score/keyword_master_ids 等少数列」的边界声明；② 新鲜度监控：两条管道的 max(created_at) 停滞告警——外贸通线（活跃，7-12 仍在写）、同行/反推线（止于 5-26，停滞原因未确认），阈值宽松起步。
- **验收**：契约章节入 HANDBOOK；告警可触达；反推线停滞原因经外部流程侧确认后收紧阈值。
- **备注**：反推链停滞 1.5 个月（励销云 5-26 / 腾道 raw 6-09）是否计划内，需用户向外部流程维护方确认（2026-07-12 状态：不确定）。

---

## 已销账（本次核对确认，留档防止重复登记）

| 原条目 | 结论与证据 |
|---|---|
| TODOS.md #2「收件人筛选 NOT IN 应含 invalid」 | **已修复**：`tenant_messaging_service.py` 收件人筛选已排除 invalid（2026-07-11 代码核实），原台账未销账属文档滞后 |
| TODOS.md #3「Webhook 回填定时任务候补」 | **已被实现覆盖**：对账 worker（`app/workers/reconciliation.py`）已常态化兜底 webhook 丢失，比原设想的每日回填更实时 |
| T-19 部分项「openspec 系列 skill/command 定义」 | **已删除**（2026-07-11 用户授权）：`.claude/commands/opsx/`、`.claude/skills/openspec-*`、`.codex/skills/openspec-*` 共 15 个 tracked 文件，另清理 `.agents/skills/source-command-opsx-*` 5 个 untracked 镜像；`settings.local.json` 内 3 行 openspec CLI 权限白名单属用户本地设置，未动 |
