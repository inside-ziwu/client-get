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
- **验收**：两端补路由级 error/loading；统一 `<Skeleton>`/`<EmptyState>` 组件收编 13 处手写 pulse 与 34 处硬编码空文案。

### T-16 · 表单基建「装了没通电」— P2
- **缺口**：admin 已声明 react-hook-form + zod + resolvers，shared-ui 已导出 Form 封装，但**全仓零消费**；所有表单为 useState + 手写校验。
- **验收**：挑 2~3 个高频表单（租户创建、发送计划向导、登录）迁移到 RHF+zod 立标杆，后续新表单一律走该模式；或明确决策移除这套依赖（二选一，不允许继续「装着不用」）。

### T-17 · 数据层纪律收敛 — P2
- **缺口**：query-keys 工厂 92 处调用仅 5 文件采用（其余手写数组，靠约定碰巧对齐 SSR hydration）；`useCursorPagination` 零消费、8 个文件复制同一套手写分页；tenant 登录页绕开统一 client 手写 axios；tenant 无服务端路由守卫（admin 有 middleware，tenant 直输 URL 闪白）。
- **验收**：query key 全量走工厂；分页收敛到共享 hook；登录页回归 `tenantApi.auth`；tenant 补 middleware 或明确接受 CSR 守卫并记录原因。

### T-18 · 拆分 984 行巨型组件 — P2
- **缺口**：`apps/admin/src/app/(dashboard)/tenants/client-page.tsx` 单文件承载列表+创建+四标签详情，且是全仓唯一用 useEffect 把 query data 拷贝进本地 state 的反模式点。
- **验收**：按 Tab 拆子组件、移除本地拷贝 state、行为不变。

## E. 清理与定位

### T-19 · 死代码与失效配置清理 — P3
- **清单**：`shared-api/src/tenant/prospects.ts`（幽灵 API，零 UI 消费）、`shared-ui/components/form.tsx` 若 T-16 决策移除、`shared-hooks/usePermission.ts`（零消费）、`app/workers/fan_out.py` 的 FanOutWorker class（死封装）、`wmt_lineage.py` 与 `wmt_lineage_repair.py` 两份近重复 SQL（合并为单一来源）、admin 本地 `lib/utils.ts` 的 cn() 副本、tenant `test:contract` 死脚本、`components.json`（shadcn 配置与实际组件路径不符）、`.claude/` 与 `.codex/` 下的 openspec 系列 skill/command 定义（openspec-propose/explore/archive/verify/apply 与 opsx 命令，指向已删除的 openspec/ 目录，工作流已退役——2026-07-11 文档清理时发现，属清单外遗留，处置前需用户确认）。
- **验收**：逐项删除或合并，grep 零残留。

### T-20 · 租户硬删除工具定位 — P3
- **缺口**：`tenant_hard_delete_service.py` 未挂任何 API，唯一出口是按具体客户命名的一次性脚本（`hard_delete_zhaokui_test_data.py`），无使用文档。
- **验收**：决定定位（参数化运维脚本 / admin API + 二次确认），沉淀使用说明进 HANDBOOK §9。

---

## 已销账（本次核对确认，留档防止重复登记）

| 原条目 | 结论与证据 |
|---|---|
| TODOS.md #2「收件人筛选 NOT IN 应含 invalid」 | **已修复**：`tenant_messaging_service.py` 收件人筛选已排除 invalid（2026-07-11 代码核实），原台账未销账属文档滞后 |
| TODOS.md #3「Webhook 回填定时任务候补」 | **已被实现覆盖**：对账 worker（`app/workers/reconciliation.py`）已常态化兜底 webhook 丢失，比原设想的每日回填更实时 |
