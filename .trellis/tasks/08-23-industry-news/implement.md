# 行业动态 · 执行计划（v3，按三份核证 + Codex 评审修订）

> 依据 [prd.md](./prd.md) 与 [design.md](./design.md)（v3）。两条 PR、两次发布；每步带验证命令与回滚点。Git 流程按 `.trellis/spec/guides/git-workflow.md`，收尾按 `guides/delivery-checklist.md`。

## 0. 前置

- 分支：PR A `feat/industry-news`，PR B `refactor/industry-news-legacy-cleanup`；各自 `git worktree add .claude/worktrees/<名> -b <分支> origin/main`。
- 依赖：`cd backend && uv add feedparser selectolax`（提交 `pyproject.toml` + `uv.lock`；`uv lock` 与 py3.13 安装已实测）。
- 门禁命令（每个阶段末尾都跑）：backend `uv run pytest -q`、`uv run ruff check app tests scripts`；frontend `pnpm type-check`、`pnpm --filter @apps/tenant test`、`pnpm build:admin`。
- 真库：Neon 开发库做迁移与断言（用专用 `instance_id='dev-seed-test'` 造数，事务内断言 ROLLBACK，种子测试后按该 instance 清理）；生产只读，写操作逐次确认。

## 1. PR A · 新功能（`feat/industry-news`，`Fixes #49`）

| # | 步骤 | 产出 | 验证 | 回滚点 |
|---|---|---|---|---|
| A1 | 迁移 `20260824_0001_industry_news`：`down_revision="20260723_0003"`；docstring（revision / down_revision / 依据 PRD + ADR）；开头 `SET LOCAL lock_timeout='5s'` / `statement_timeout='30s'`；三表 + 命名约束 + 索引 + `set_updated_at` 触发器；**不动 `schema.sql`**；`schema_docs.json` 新增「行业动态」域与三表说明 | revision、`schema_docs.json` | Neon：`uv run alembic upgrade head` → `uv run python scripts/schema_snapshot.py` 的 `schema_snapshot.json` diff 恰好 = 三表 + `alembic_version` 一行（**只提交 JSON**，MD / DBML 不提交）→ `SELECT tgname FROM pg_trigger WHERE tgrelid='industry_news_sources'::regclass` 含 `set_updated_at` → `alembic downgrade -1` 再 `upgrade head` 往返 | downgrade 删三表，无数据 |
| A2 | `app/utils/industry.py`（`INDUSTRY_ALIASES`、`canonical_industry`、`PCB_INDUSTRY_ALIASES`），`wmt_lineage_repair.py:25` 改为导入并保留 `_PCB_INDUSTRY_ALIASES` 名 | 1 新文件、1 行改动 | `uv run pytest -q tests/test_lineage_repair_*.py tests/test_worker_instance_isolation.py` 全绿 | 还原导入 |
| A3 | `services/industry_news/normalize.py` | `canonical_url`、`normalize_title`、`dedup_key` | 单测：跟踪参数、尾斜杠、大小写、零宽字符、CJK 保留、500 截断、空标题 / 空链接丢弃 | — |
| A4 | `services/industry_news/fetchers.py` + `tests/fixtures/industry_news/`（14 个源各一份裁剪样本） | 三策略解析器，`transport` 注入 | 单测经 `httpx.MockTransport` 喂 fixture：每源 ≥1 条、标题链接非空、相对链接已 join、`href_pattern` / `href_exclude` 生效、`title_from: parent` 取段落、4xx 不重试 / 5xx 重试 2 次 | — |
| A5 | 种子 `app/data/industry_news_sources_pcb.json`（每行含稳定 `code`）+ `scripts/seed_industry_news_sources.py`（按 `(instance_id, code)` upsert，地址可变；id 由 `new_uuid()` 生成；`--instance` `--file` `--dry-run`；非 `default` 实例需 `--confirm-instance`；单事务） | 14 行 | Neon（`--instance dev-seed-test --confirm-instance dev-seed-test`）：`--dry-run` 输出 14 新增 → 执行 → `count(*)=14` → 再执行 0 新增 14 不变（幂等）→ 改一行 `url` 与类别再执行 1 更新、行数仍 14 且 `is_active` 未变 → 不带 `--confirm-instance` 时拒绝写入 → `DELETE … WHERE instance_id='dev-seed-test'` 清理 | 清理语句即回滚 |
| A6 | `services/industry_news/service.py`：`fetch_source(conn, source, run_at)`（解析放 `asyncio.to_thread`；丢弃发布时间早于 90 天的条目；`ON CONFLICT DO NOTHING` + `rowcount`；`fetched_at = run_at`）、`run_once`（整轮单事务 + `pg_try_advisory_xact_lock` + 每源 `begin_nested()` savepoint）、`list_items -> (items, total)`（只看启用源；数组参数 `CAST(:p AS text[] / uuid[])`；排序 `fetched_at DESC, COALESCE(published_at, fetched_at) DESC, id DESC`）、`list_filter_options`、`mark_read`、管理端两方法；租户 service 开头单独查 `tenants.industry` 并 `canonical_industry()` | service | mock 单测断言 SQL 片段与参数（`CAST`、`window_start` 为 aware datetime、`industry`、`s.is_active`、`unread_only`、排序键、`LIMIT/OFFSET`）与 90 天入库过滤；Neon 三段式：同稿（同 canonical_url / 同 dedup_key 各插一次 `rowcount` 0）、`CAST` 数组参数传 `None` 与 list 均可执行、90 天窗口边界（89 / 91 天）、已读只对当前用户生效、`mark_read` 不可见 404、停用源的动态不再出现且不被抓取、savepoint 隔离单源失败（坏 `parse_config` 的源计数 +1、其余源正常入库）、两连接事务锁互斥；全部 ROLLBACK 后计数归零 | — |
| A7 | 调度：`workers/industry_news_fetch.py`（`run_industry_news_fetch_loop` 不做启动补跑；`trigger_fetch` + `_background_tasks`，返回 `in_progress` / `no_sources` / `triggered`）、`beijing_time.next_beijing_time`、Settings 两项、`main.py` lifespan 四步 | worker | 单测（注入 clock）：下一个 08:00 跨日 / 跨月；锁被占 `run_once` 返回 `in_progress`；`trigger_fetch` 已有任务 / 无启用源的两种返回；`stop_event` 能退出 | 开关默认 false，合入即安全 |
| A8 | CLI `scripts/run_industry_news_fetch.py`（`--once` 与 `--from-file` 互斥；`--source` 可选，照 `run_sending_worker.py` 模式） | CLI | 真站冒烟（信息性，不是合并门槛）：`--from-file app/data/industry_news_sources_pcb.json`，记录每源条数与样本到 `research/live-fetch-<日期>.md`；据样本定稿 PCB Update 规则并回填种子与 fixture；个别源当日 0 条记为环境事项，不阻塞 | — |
| A9 | 后端 API：`schemas/industry_news.py`；`api/tenant/industry_news.py`（`Query(alias="category[]")` 收数组；route 传 `has_more = page*page_size < total`）；`api/admin/industry_news_sources.py`（`APIRouter(prefix=…)`；`GET` 用 `success_response` 数组；`POST /fetch status_code=202` 返回 `{triggered, reason?}`，定义在 `PATCH /{source_id}` 之前）；两个 router 挂载 | 租户 3 + 管理端 3 端点 | 单测：`noauth_client` 401（先例 `test_admin_config.py:133-141`）；`dependency_overrides` 下分页 `total / has_more`、筛选参数、`read` 幂等与 404、`fetch` 202 的三种返回（patch `trigger_fetch`，`ASGITransport` 无 lifespan）、`PATCH` 非本实例 404 | — |
| A10 | `shared-types`（`IndustryNewsItem` / `IndustryNewsSource` / `IndustryNewsFilterOptions` / `IndustryNewsFilters`）、`shared-api`（tenant / admin 两文件 + 两个 index 注册 + 根 index 再导出）、`queryKeys.industryNews` | 只新增，不删旧 | `pnpm type-check` | — |
| A11 | 租户页 `industry-news/page.tsx`（FilterBar：两 multiSelect + select + custom Switch；`placeholderData: keepPreviousData`；`Pagination mode="total"`；标题 `<a target="_blank">` + `clickedIds`；`has_sources=false` 说明块）+ 导航 `:30` 替换 + Vitest `test/industry-news/industry-news-page.test.tsx` | 页面 + 测试 | Vitest 四条用例（见 design §9）；`pnpm type-check` | 导航一行还原 |
| A12 | 管理端 `industry-news-sources/{page,client-page}.tsx`（字面量 key、`ApiResponse<IndustryNewsSource[]>`、`primaryAction` 立即抓取按 `reason` 提示、`boolean interactive` 启停列、「从未」时间列、错误计数标红、空列表说明块）+ 导航 `:33` 改名 + `ai-config/client-page.tsx:65` 过滤 `intelligence_summary` | 监控页 | `pnpm type-check`、`pnpm build:admin`；本地起 admin 手工点启停与立即抓取（含进行中提示与空列表说明） | — |
| A13 | 文档与 spec：README 矩阵 `:154` `:169` 两行改为行业动态 ✅；`backend/.env.example` 补两个变量；spec 修正（design §8：列宽 token、workers.md 会话锁与新 worker、database-guidelines.md:44、quality-guidelines.md:38） | — | 链接可达；`grep -rn "224px\|96/144/224" .trellis/spec` 为空 | — |
| A14 | 全量门禁 + 收尾清单 + PR A（描述带验证证据与 `Fixes #49`） | PR | §0 门禁 | — |

**发布 A 与上线操作（均由用户触发）**：`/release` 发共用 backend + A / B 四套前端镜像（开关保持关）→ A 实例 backend 容器内 `seed --instance default --dry-run` 展示 14 行 → 用户确认 → 执行 → `SELECT count(*)` 回读 14 → 在 A 容器内 `run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json` 核生产出口可达（允许个别源 0 条）→ 用户在 A 实例环境设 `INDUSTRY_NEWS_FETCH_ENABLED=true` 并重启 → 点「立即抓取」跑首轮（不依赖补跑）→ 按 AC1–AC5 逐条记录验收（含 B 租户空态与 B 管理端空列表说明）→ 观察一轮 08:00 后再进入 PR B。

## 2. PR B · 遗留清理（`refactor/industry-news-legacy-cleanup`，在 A 上线并跑过一轮真实抓取后）

| # | 步骤 | 验证 | 回滚点 |
|---|---|---|---|
| B1 | 迁移 `20260824_0002_drop_intelligence_tables`（`down_revision="20260824_0001"`）：`SET LOCAL` 超时；按 `publications → subscriptions → articles → sources` `DROP TABLE`（不带 `IF EXISTS` / `CASCADE`）；docstring 记生产实况（三表 0 行、`intelligence_sources` 2 行的源名 / 地址）；`downgrade` 按快照重建结构 + `intelligence_articles` DEFAULT 分区，注明不还原触发器 / RLS | Neon：upgrade / downgrade 往返；`schema_snapshot.py` diff 恰好少四表 + `alembic_version`；生产执行前 `--prod` 只读核对四表行数（0 / 0 / 0 / 2） | downgrade 重建结构 |
| B2 | 后端删除（design §6 后端行，含 `internal_ops_service.py`、`admin_config_service.py:1463/1474` 与 `:445-597/1554-1569`、`seed_demo_data.py`、`partitions.py:12,26`、`schemas`、tests 用例与 mock 键） | `uv run pytest -q`、`ruff`；`rg -n -i "intelligence" backend/app backend/scripts backend/tests` 只剩 `schemas/admin_config.py` Literal 与 `tenant_query_service.py:1068` | — |
| B3 | 前端删除（design §6 前端行，文件 + 行级）+ `ai-config/client-page.tsx:34` 标签 | `pnpm type-check`、tenant test、`build:admin`；`rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!**/enums.ts'` 为空 | — |
| B4 | 文档与 spec（design §6 文档行：`schema_docs.json`、`schema_notes.md`、README `:21` `:129`、spec 十余处示例改指向新文件） | 链接可达；`rg -n "intelligence" .trellis/spec README.md` 只剩历史说明 | — |
| B5 | 门禁 + PR B | §0 门禁 | — |

**发布 B**：启动自动执行删表迁移；发布后 `scripts/schema_snapshot.py --prod` 再生 `schema_snapshot.json` + `docs/database-schema.md` + `.dbml` 并提交。**发布 B 之后不能回退到 B 之前的镜像 tag**（旧 `partitions.py` 启动即崩，且禁止生产 downgrade），只能前向修复——合并 B 前确认 A 已稳定运行。

## 3. 风险处置

- PR A 上线后抓取异常：关闭 `INDUSTRY_NEWS_FETCH_ENABLED` 即停，数据无害；页面异常回退前端镜像 tag。整轮在单事务内，进程崩溃整轮回滚、次日重来或手动再点。
- 种子导入错误行：`UPDATE … SET is_active=false` 或按 `url` 删除，均为生产写，逐次确认。
- PR B 迁移在生产失败会阻断 API 启动：先在 Neon 往返验证；生产执行前只读核对行数；失败按 database-guidelines 前向修复。

## 4. 收尾清单映射（`guides/delivery-checklist.md`）

- 证据：pytest / ruff / type-check / vitest / build 输出；Neon 断言记录（A1、A5、A6、B1）；真站冒烟样本（A8）；生产验收记录（AC1–AC6）。
- Issues：PR A `Fixes #49`；新发现的问题 `gh issue create` 打 P 级（候选：`tenacity` 声明未用可移除、`schema.sql` 与迁移脱节属 #61）。
- 文档与 spec：A13 与 B4；`domain-rules.md` 若口径有变；新教训写进 spec「常见错误」（候选：asyncpg 重复命名参数需 CAST、事务级锁与多事务不兼容）。
- Trellis：两条 PR 都合并后 `/trellis:finish-work` 归档任务。

## 5. 任务结构

保持单任务、两阶段（PR A / PR B），不拆子任务：同一人顺序执行，B 严格依赖 A 上线。
