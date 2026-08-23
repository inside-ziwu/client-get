# 行业动态 · 执行计划

> 依据 [prd.md](./prd.md) 与 [design.md](./design.md)。两条 PR、两次发布；每步都带验证命令与回滚点。Git 流程按 `.trellis/spec/guides/git-workflow.md`（worktree 隔离、白名单提交），收尾按 `guides/delivery-checklist.md`。

## 0. 前置

- 分支：PR A `feat/industry-news`，PR B `refactor/industry-news-legacy-cleanup`；各自 `git worktree add .claude/worktrees/<名> -b <分支> origin/main`。
- 依赖：`cd backend && uv add feedparser selectolax`（提交 `pyproject.toml` + `uv.lock`）。
- 门禁命令（每个阶段末尾都跑）：
  - backend：`uv run pytest -q`、`uv run ruff check app tests scripts`
  - frontend：`pnpm type-check`、`pnpm --filter @apps/tenant test`、`pnpm build:admin`
- 真库：Neon 开发库（`CLIENTGET_DEV_DATABASE_URL`）做迁移与断言；生产只读，写操作逐次确认。

## 1. PR A · 新功能（`feat/industry-news`，`Fixes #49`）

| # | 步骤 | 产出 | 验证 | 回滚点 |
|---|---|---|---|---|
| A1 | 迁移 `20260824_0001_industry_news`：三表、索引、`updated_at` 触发器；`schema.sql` 同步 | `alembic/versions/…`、`03_database/schema.sql` | Neon：`uv run alembic upgrade head` → `uv run python scripts/schema_snapshot.py` 的 diff 恰好只含三表；`alembic downgrade -1` 再 `upgrade head` 可往返 | downgrade 删三表，无数据 |
| A2 | `app/utils/industry.py`（`canonical_industry` + 别名常量），`wmt_lineage_repair` 改为导入该常量 | 1 个新文件、1 行改动 | `uv run pytest -q tests/test_lineage_repair_*.py` 全绿 | 还原导入 |
| A3 | `services/industry_news/normalize.py` | `canonical_url`、`normalize_title`、`dedup_key` | 单测：跟踪参数剥离、尾斜杠、大小写、零宽字符、CJK 保留、500 截断 | — |
| A4 | `services/industry_news/fetchers.py` + fixtures | 三策略解析器；`tests/fixtures/industry_news/` 放裁剪后的真实 RSS / HTML / JSON-LD 样本（14 个源各一份，去掉无关内容） | 单测：每个 fixture 解析条数 ≥1、标题链接非空、相对链接已 join、`href_pattern` / `href_exclude` 生效、`title_from: parent` 取段落 | — |
| A5 | 种子 `app/data/industry_news_sources_pcb.json` + `scripts/seed_industry_news_sources.py` | 14 行；`--instance` `--file` `--dry-run` | Neon：`--dry-run` 输出 14 新增 → 执行 → `SELECT count(*)` = 14 → 再执行一次输出 0 新增 14 不变（幂等）→ 改一行类别再执行输出 1 更新且 `is_active` 未变 | Neon 上 `DELETE WHERE instance_id='dev-seed-test'` 清理（用专用实例 id 做断言） |
| A6 | `services/industry_news/service.py` | `fetch_source` / `run_once` / `list_items` / `list_filter_options` / `mark_read` / 管理端两方法 | mock 单测断言 SQL 片段与参数（`window_start`、`industry`、数组筛选、`unread_only`、`LIMIT/OFFSET`）；Neon 三段式断言：同稿（同 canonical_url / 同 dedup_key 各插一次只留一条）、90 天边界（89/91 天各一条）、已读只对当前用户生效、`mark_read` 不可见条目 404、停用源不被 `run_once` 处理；全部 ROLLBACK 后计数归零 | — |
| A7 | 调度：`workers/industry_news_fetch.py`、`utils/beijing_time.next_beijing_time`、Settings 两项、`main.py` lifespan | 循环 + 启动补跑 + 锁 | 单测（注入 clock）：下一个 08:00 计算跨日 / 跨月；启动时 `now ≥ 08:00 且 max(last_fetched_at) < 今日 08:00` 触发补跑、否则不触发；锁被占返回 `skipped`；`stop_event` 能退出 | 开关默认 false，合入即安全 |
| A8 | CLI `scripts/run_industry_news_fetch.py`（`--once` / `--source` / `--dry-run` / `--from-file`） | 手工与 Agent 入口 | 真站冒烟：`--from-file app/data/industry_news_sources_pcb.json --dry-run`，14 行每行 ≥1 条，样本标题存到 `research/live-fetch-<日期>.md`；据样本定稿 PCB Update 标题规则并回填种子与 fixture | — |
| A9 | 后端 API：`schemas/industry_news.py`、`api/tenant/industry_news.py`、`api/admin/industry_news_sources.py`（`/fetch` 静态路由在 `/{id}` 前）、router 挂载 | 租户 3 + 管理端 3 端点 | 单测：鉴权 kind 校验、分页 `total`、筛选参数、`read` 幂等与 404、`fetch` 返回 202、`PATCH` 非本实例 404 | — |
| A10 | `shared-types`（`IndustryNewsItem` / `IndustryNewsSource` / `IndustryNewsFilters`）、`shared-api`（tenant / admin 两文件）、`queryKeys.industryNews` | 只新增，不删旧 | `pnpm type-check` | — |
| A11 | 租户页 `industry-news/page.tsx` + 导航替换 + Vitest | 五件套页面 | Vitest：未读 / 已读样式类名、点击调用 `window.open` 与 `markRead` 并乐观置已读、`has_sources=false` 空态文案、筛选参数透传；`pnpm type-check` | 导航可一行还原 |
| A12 | 管理端 `industry-news-sources/page.tsx` + `client-page.tsx` + 导航改名 + AI 配置页隐藏 `intelligence_summary` | 监控页 | `pnpm type-check`、`pnpm build:admin`；本地起 admin 手工点启停与立即抓取（对接本地后端） | — |
| A13 | 文档：README 功能矩阵「情报源管理 / 情报中心」两行改为行业动态并标 ✅；`backend/.env.example` 补两个变量说明（`.env.local` 不动）；`.trellis/spec/backend/workers.md` 补一行新 worker | — | 链接可达 | — |
| A14 | 全量门禁 + 收尾清单 + PR A | PR 描述带验证证据与 `Fixes #49` | 见 §0 门禁 | — |

**发布 A 与上线操作（均由用户触发）**：`/release` 发 backend 与 A / B 两实例前端 → A 实例 backend 容器内 `seed --instance default --dry-run` 展示 14 行 → 用户确认 → 执行 → `SELECT count(*)` 回读 14 → 用户在 A 实例环境设 `INDUSTRY_NEWS_FETCH_ENABLED=true` 并重启 → 观察启动补跑日志或点「立即抓取」→ 按 AC1–AC5 逐条记录验收（含 B 实例租户空态）。

## 2. PR B · 遗留清理（`refactor/industry-news-legacy-cleanup`，在 A 上线并跑过一轮真实抓取后）

| # | 步骤 | 验证 | 回滚点 |
|---|---|---|---|
| B1 | 迁移 `20260824_0002_drop_intelligence_tables`：`SET LOCAL` 超时；按依赖序 `DROP TABLE intelligence_article_publications, intelligence_subscriptions, intelligence_articles, intelligence_sources`（不带 CASCADE）；docstring 记生产 0 行证据；`downgrade` 用快照里的定义重建 | Neon：upgrade / downgrade 往返；`schema_snapshot.py` diff 恰好少四表 | downgrade 重建 |
| B2 | 后端删除：`intelligence_service.py`、租户 `intelligence.py` 与挂载、admin 五端点与 service 方法、`IntelligenceSource*` 模型、internal `publish` 端点、`partitions.py` / `maintain_partitions.py` 条目、旧测试 | `uv run pytest -q`、`ruff`；`rg -n "intelligence" backend/app` 只剩枚举值 | — |
| B3 | 前端删除：tenant `intelligence/` 页与测试、admin `intelligence-sources/`、shared-api / shared-types 旧文件与类型、`queryKeys.intelligence` | `pnpm type-check`、tenant test、`build:admin`；`rg -n "intelligence" frontend --glob '!node_modules'` 为空 | — |
| B4 | 文档：spec `database-guidelines.md` 分区表清单去掉 `intelligence_articles`、`directory-structure.md` 路由组描述；README 路由组与矩阵；`schema.sql` 删四表 | 链接可达 | — |
| B5 | 门禁 + PR B | 同 §0 | — |

**发布 B**：启动自动执行删表迁移；发布后 `scripts/schema_snapshot.py --prod` 再生 `docs/database-schema.md` 并提交（只读连接）。

## 3. 风险处置

- PR A 上线后抓取异常：关闭 `INDUSTRY_NEWS_FETCH_ENABLED` 即停，数据无害；页面异常回退前端镜像 tag。
- 种子导入错误行：`UPDATE … SET is_active=false` 或按 `url` 删除，均为生产写，逐次确认。
- PR B 迁移在生产失败会阻断 API 启动：先在 Neon 往返验证；生产执行前用 `--prod` 只读核对四表行数为 0。

## 4. 收尾清单映射（`guides/delivery-checklist.md`）

- 证据：pytest / ruff / type-check / vitest / build 输出；Neon 断言记录（A5、A6、B1）；真站冒烟样本（A8）；生产验收记录（AC1–AC6）。
- Issues：PR A `Fixes #49`；新发现的问题 `gh issue create` 打 P 级。
- 文档与 spec：README 矩阵、spec 分区清单与 worker 清单、`domain-rules.md` 若口径有变；新教训写进 spec「常见错误」。
- Trellis：两条 PR 都合并后 `/trellis:finish-work` 归档任务。

## 5. 任务结构

保持单任务、两阶段（PR A / PR B），不拆子任务：同一人顺序执行，B 严格依赖 A 上线，拆分只会多一套 PRD 副本。
