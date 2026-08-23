# 后端交付评审（PR A · A1–A9，worktree `inside-ziwu/industry-news-backend`）

- 评审人：Check Agent（Claude）· 2026-08-23
- 对象：`git -C <worktree> status --short` 列出的全部后端改动（基于 main `dac67d1`）
- 对照：design.md v3 §2 / §3 / §4 / §7、prd.md R2–R4 与 AC、implement.md A1–A9、`research/review-resolution.md` D1–D9 / B1–B7 / C2–C9、`.trellis/spec/backend/*.md`
- 约束遵守：未连接任何数据库、未 git commit、未动当前目录 `/Users/lay/Projects/ClientGet`、未新增 `.env*`、未改 `schema.sql`

## 0. 先说一件事故（已完全恢复）

评审中一条组合命令里的 `git stash pop` 在前序命令失败后仍被执行，把该 worktree 里**早已存在的** `stash@{0}`（"On main: codex: fast-forward main 前保护本地 WIP"，含 README.md / CLAUDE.md / TODO.md 与两份 untracked docs）部分应用进了工作区并产生冲突。处置：`git reset -- <四个冲突路径>` → `git checkout HEAD -- README.md CLAUDE.md` → 删除 `TODO.md`、`CLAUDE.md~Stashed changes`、`docs/EXPERIENCE.md`、`docs/INPROCESS.md`。复核：`git status --short` 与评审开始时完全一致，`git diff HEAD -- README.md CLAUDE.md` 为空；**`stash@{0}` 本体未被消耗，仍在 `git stash list`**。工人的 9 个已跟踪改动文件未受影响（全量测试复跑通过）。教训已记：共享 worktree 里不用 `git stash`。

## ① 发现与处置

### 已修（契约 / spec / SQL 写法层面，直接在 worktree 改）

| # | 问题 | 证据 | 处置 |
|---|---|---|---|
| 1 | `IndustryNewsService.run_once` 默认时钟是 `datetime.now`（naive），不传 `clock` 直接调用会立即 `ValueError`；worker 层恰好总传 clock 所以没暴露 | `backend/app/services/industry_news/service.py:281`（原） | 改为 `datetime.now(UTC)` 并给 `clock` 加 `Callable[[], datetime] \| None` 注解；新增 `test_run_once_default_clock_is_aware` |
| 2 | `_LIST_WHERE` 里 `:lang` 第二次出现裸写 `s.lang = :lang`。asyncpg 把同名参数合并为同一 `$n`，类型只能靠语句解析顺序从第一处 `CAST` 推断，写法脆弱 | `service.py:81`（原） | 两处都 `CAST(:lang AS text)`（已用 asyncpg 方言本地编译确认合并为同一 `$1`）；`test_list_items_sql_has_cast_active_window_and_order` 补断言 |
| 3 | `fetch_source(items: list \| None = None)` 可选参数再 `raise` 的伪可选签名；三处手抄同一 stats 字典；`FetchError` 导入未使用 | `service.py:171-191, 260-270, 316-325`（原） | `items` 改必填 keyword-only；抽 `_empty_stats()`；去掉未用导入 |
| 4 | `_clean_text` 只去 U+200B；design §3.2 / 种子备注要求"去零宽字符"（慕尼黑两站名称），U+200C / 200D / 2060 / FEFF 会留在入库标题里（dedup 侧 `normalize.py` 已处理，展示标题没处理） | `fetchers.py:88-89, 188`（原） | 统一 `_ZERO_WIDTH_RE`，jsonld 分支去掉重复 `replace` |
| 5 | `PCB_INDUSTRY_ALIASES` 是硬编码副本，与 `INDUSTRY_ALIASES` 可能漂移；design §3.5 要求派生 | `backend/app/utils/industry.py:13` | 改为 `[k for k, v in INDUSTRY_ALIASES.items() if v == "PCB"]` |
| 6 | `INDUSTRY_NEWS_FETCH_HOUR_BEIJING` 无范围约束：越界值要到循环首轮 `time(hour=…)` 才抛，且异常在 `try` 之外会让循环任务直接结束 | `backend/app/core/config.py:103-106` | `Field(default=8, ge=0, le=23, …)`，启动期即报错 |
| 7 | 例行循环到点醒来后若墙钟比目标慢几毫秒（`wait_for` 用单调钟，目标用墙钟），`next_beijing_time` 会再次返回同一目标 → 同一时刻连跑两轮（幂等但多一次源请求与 `last_fetched_at` 写） | `backend/app/workers/industry_news_fetch.py:55-58`（原） | 下一目标按 `max(now, 上一目标)` 计算；新增 `test_loop_runs_once_at_target_then_waits_for_next_day`（第二次等待必须 > 86000 秒） |
| 8 | 例行轮的 `run_once` 没登记进 `_background_tasks`，08:00 轮进行中点「立即抓取」会返回 `triggered: true`，后台再被事务锁静默拒绝——单副本场景下 API 在撒谎（design §3.4 "本进程已有未完成任务 → in_progress" 的字面范围应含例行轮） | `industry_news_fetch.py:64, 97-99`（原） | 抽 `_spawn()` 统一登记，循环与手动触发共用；新增 `test_scheduled_round_is_visible_to_trigger_fetch`。外层任务取消会级联取消内层 `await task`，lifespan 四步不受影响 |
| 9 | CLI `--once --dry-run` 会**静默忽略** `--dry-run` 直接写库（design §3.4 写 `--dry-run` 只打印不写库；工人报告第 3 条只说了种子脚本） | `backend/scripts/run_industry_news_fetch.py:99-102`（原） | 连库模式带 `--dry-run` 明确拒绝（exit 2），帮助文案改为"只与 `--from-file` 搭配"；已不连库冒烟两个脚本的守卫 |
| 10 | `ipc.xml` fixture 含 5 处 Drupal 匿名 flag `token="…"`（公开 feed 自带、非凭证，但会触发密钥扫描误报） | `backend/tests/fixtures/industry_news/ipc.xml` | 值脱敏为 `REDACTED`；其余 13 份 fixture 核过无凭证（仅站点公开的新闻联系邮箱），最大 28,259 字节 |
| 11 | 测试覆盖缺口（implement A6 / A7 / A9 列出但未落）：savepoint 隔离单源失败、`mark_read` 成功路径 SQL、0 条记错误、`trigger_fetch` 成功路径、路由默认参数与 `page_size` 上限、`/filters`、admin GET 数组形态、PATCH 422、种子 `--confirm-instance` 守卫与 `_same` | 7 个测试文件 | 共补 13 条用例（479 → 492） |
| 12 | 新文件未过 `ruff format`（仓库非 format-clean，不是门禁，但新文件没理由不齐） | 7 个新文件 | 已 format；`ruff check` 改动文件全绿 |

### 逐项核对通过（无需改）

- **迁移** `20260824_0001`：三表列 / 类型 / 默认值、`uq_industry_news_sources_instance_code`、两条 items UNIQUE 命名、四个索引名与列序、`reads.user_id … ON DELETE CASCADE`、`item_id … ON DELETE CASCADE`、`tenant_id` 不带 CASCADE、`PRIMARY KEY (user_id, item_id)`、`DROP TRIGGER IF EXISTS; CREATE TRIGGER set_updated_at … trigger_set_updated_at()`（与 `20260529_0001:44-51` 同式）、docstring 含 revision / down_revision / 依据、开头两句 `SET LOCAL`、`down_revision = "20260723_0003"`、downgrade 顺序 reads → items → sources、不动 `schema.sql`——与 design §2 逐行一致。
- **SQL**：`CAST(:categories AS text[])` / `CAST(:source_ids AS uuid[])`、`s.is_active`、`:window_start` 为 Python 端 aware datetime（`now - 90d`）、排序 `i.fetched_at DESC, COALESCE(i.published_at, i.fetched_at) DESC, i.id DESC`、`LIMIT :limit OFFSET :offset`、count 同 WHERE、`(NOT :unread_only OR r.item_id IS NULL)`、`mark_read` 先查可见集合（instance + industry + is_active + 窗口）再 `ON CONFLICT (user_id, item_id) DO NOTHING`、管理端 `UPDATE … WHERE id AND instance_id … RETURNING` 0 行 404、租户方法开头单独 `SELECT industry FROM tenants` + `canonical_industry()`（先例 `tenant_messaging_service.py:72-79`，同样不带 instance 过滤）；`text()` 多余参数（count 语句收到 `limit/offset`）已本地验证被 SQLAlchemy 忽略。
- **run_once**：整轮一个 `engine.begin()`、`pg_try_advisory_xact_lock(CAST(:key AS bigint) + pg_catalog.hashtext(:instance_id))`（key `2_026_082_401`，与 lineage repair 不同）、锁忙返回 `{"skipped": True, "reason": "in_progress"}`、`run_at` 统一时间戳、每源 `begin_nested()`、savepoint 内异常 → `logger.exception` → 另开 savepoint 写 `error_count + 1` 并继续；`INSERT … ON CONFLICT DO NOTHING` + `rowcount`，不捕 IntegrityError；成功 `last_fetched_at = last_success_at = run_at, error_count = 0`，失败 / 0 条只动 `last_fetched_at` 与计数；不做启动补跑。
- **解析器**：rss / html / jsonld 三策略与 `item_selector` / `link_selector` / `title_selector` / `title_from: parent` / `href_pattern` / `href_exclude` 键齐全；相对链接 `urljoin`；`asyncio.to_thread` 跑同步解析；`transport` 构造注入；手写循环重试 2 次（超时 / 传输错误 / 5xx），4xx 不重试；不用 tenacity；发布时间早于 90 天不入库（service 侧）；标题截断 500；空标题 / 空链接丢弃。
- **API**：Pydantic 收参（`IndustryNewsSourceToggle`），`Annotated[…, Query(default_factory=list, alias="category[]")]` 语义与 `ops.py:41-46` 一致（已用路由测试证明 `category[]=A&category[]=B` → `["A","B"]`、缺省 → `None`）；租户 `paginated_response(items, total=total, has_more=page*page_size < total)`；管理端 GET `success_response` 数组；`POST /fetch status_code=202` 定义在 `PATCH /{source_id}` 之前；鉴权 `get_current_tenant_user`（不限角色）/ `get_current_platform_user`；响应字段 `id, title, url, source_id, source_name, category, lang, time, is_read, target_domain, is_external`、`{categories, sources[{id,name}], langs, has_sources}`、`{item_id, is_read: true}`、`{triggered, reason?}`、源 12 字段——与 design §4 逐字一致。
- **种子**：14 行 `code` 唯一（`pcb-update / pcea / iconnect007 / pcdandf / circuits-assembly / ipc / pcb-west / pcb-east / tpca / nepcon-japan / productronica / electronica / cpca-news / cpca-weekly`），类别 / 语种 / 策略 / 地址 / `parse_config` 与 prd 种子表 14 行逐项一致；脚本按 `(instance_id, code)` upsert、只更新 7 个属性、不动 `is_active / last_* / error_count`、id 用 `new_uuid()`、单事务、`--dry-run`、非 `default` 须 `--confirm-instance <同值>`。
- **隔离与安全**：所有 SQL 的 `instance_id`（sources / items / 健康更新 / 启停 / 计数）、`tenant_id + user_id`（reads 的 JOIN 与 INSERT）显式存在；日志只含源名 / 实例 id；无新增 `.env*`；`schema.sql` 未动；`schema_docs.json` 新增「行业动态」域与三表说明。
- **配置与 lifespan**：`INDUSTRY_NEWS_FETCH_ENABLED` 默认 false、`INDUSTRY_NEWS_FETCH_HOUR_BEIJING` 默认 8；`main.py` 在 `ensure_partitions` 之后四步（event → create_task → set → cancel + suppress），与 `wmt_lineage_repair` 同构。
- **依赖**：`feedparser>=6.0.14`、`selectolax>=0.4.11` 写入 `pyproject.toml`（镜像 `uv pip install --system .` 读的是它）；`uv.lock` 的 1000+ 行 diff 是 uv 0.11 把 lock 格式 revision 2 → 3（`upload_time` → `upload-time`），**未升级任何既有包版本**，只新增 feedparser / feedparser-sgmllib / selectolax 三项。
- **wmt_lineage_repair.py** 一行导入保留 `_PCB_INDUSTRY_ALIASES` 名，`test_lineage_repair_industry_fanout.py` 与 `test_worker_instance_isolation.py` 通过。

### 待协调者决定（产品口径 / 设计取舍，未改）

| # | 事项 | 说明 |
|---|---|---|
| A | 管理端是否展示解析规则 | prd R2 写"只读展示 名称、地址、类别、语种、**解析规则**"，design §4 响应与 §5.2 列都只有 `strategy`、没有 `parse_config`。实现按 design。若要展示，后端加一个字段即可，但 A10 / A12 前端契约要同步。 |
| B | `is_external` 按 netloc 严格比较 | `www.` 有无之差会被当外链，只影响标题后灰字域名；design 原文即此写法。建议验收时看 IPC / TPCA 等 `www.` 站点的实际表现再定。 |
| C | 非法 UUID 的 `source_id[]` / `item_id` 返回 500 而非 422 / 404 | 与仓库现有 str id + `CAST(... AS uuid)` 先例一致（`messaging.py`、`scoring_engine_service.py`），非本 PR 引入；若要收紧属全仓约定变更。 |
| D | `fetch_source` 拆成 `fetch_source_from_network`（网络）+ `fetch_source`（入库）两层 | 与 design §3.3 单函数写法形态不同、语义一致（便于 mock 单测），我接受。 |
| E | `uv.lock` revision 3 | 本地开发需要能读 revision 3 的 uv（当前机器 0.11.15 可读）；镜像不受影响。 |

## ② 门禁最终输出

```
$ cd backend && uv run pytest -q
492 passed, 5 skipped, 11 warnings in 13.29s

$ uv run ruff check <本次全部改动 / 新增文件>
All checks passed!

$ uv run ruff check app tests scripts
Found 916 errors.            # 与 main 基线一致（工人报告 ~916），全部在未触碰文件 / 行
（改动文件集内仅 config.py:64 E501 与 wmt_lineage_repair.py:181 SIM117 两条，均为 HEAD 原有行）

$ uv run ruff format --check <新文件>
18 files already formatted

$ uv run python scripts/run_industry_news_fetch.py --once --dry-run      # exit 2，拒绝
$ uv run python scripts/seed_industry_news_sources.py --instance instance_b --dry-run   # exit 2，拒绝
```

## ③ 留给协调者的真库验证清单（Neon 开发库，`/db-verify` 三段式，ROLLBACK 零残留）

1. **A1 迁移**：`uv run alembic upgrade head` → `SELECT tgname FROM pg_trigger WHERE tgrelid='industry_news_sources'::regclass` 含 `set_updated_at` → `scripts/schema_snapshot.py` 的 `schema_snapshot.json` diff 恰好 = 三表 + `alembic_version` 一行（只提交 JSON）→ `alembic downgrade -1` / `upgrade head` 往返。
2. **A5 种子**：`--instance dev-seed-test --confirm-instance dev-seed-test`：dry-run 14 created → 执行 count=14 → 再执行 0 created / 14 unchanged → 改一行 url 与类别再执行 1 updated、行数仍 14、`is_active` 未变 → `DELETE … WHERE instance_id='dev-seed-test'` 清理。
3. **A6 SQL 语义**（事务内断言）：
   - `_SQL_LIST_ITEMS` / `_SQL_LIST_COUNT` 以 `categories=None / ['x']`、`source_ids=None / [uuid]`、`lang=None / 'en'`、`unread_only=True / False` 八种组合在 asyncpg 下可执行（重点：`CAST(:lang AS text)` 两处合并为同一 `$n`）；
   - 同稿：同 `canonical_url` 与同 `dedup_key` 各插一次 `rowcount == 0`，且同一事务内跨源也命中（mock 只证明了 SQL 文本）；
   - 90 天边界：`fetched_at` 89 / 91 天的行在列表里的有无；`published_at` 为 NULL 的 INSERT 经 asyncpg 类型推断成功；
   - 已读只对当前用户生效、`unread_only` 时 count 与 list 一致；`mark_read` 不可见（停用源 / 窗口外 / 他实例）→ 404；
   - 停用源：其动态从列表与 `/filters` 消失、`run_once` 不再抓它；
   - savepoint 隔离：用改坏 `parse_config` 的源验证 `error_count + 1`、其余源正常入库；再用超过 2704 字节的 `canonical_url` 触发 `ProgramLimitExceeded`，确认走 `run_once` 的 `except Exception` 分支后其余源仍入库（mock 用 RuntimeError 模拟了这条路径）；
   - 两连接 `pg_try_advisory_xact_lock` 互斥：第二连接返回 `in_progress`。
4. **jsonb 反序列化**：对种子行跑一次 `run_once`（或 `SELECT parse_config`），确认 SQLAlchemy asyncpg 方言把 `parse_config` 返回为 `dict`（代码按 dict 使用；方言源码 `setup_asyncpg_jsonb_codec` 已核，属确认项）。
5. **上线后**（生产、信息性）：在 A 容器内 `--from-file … --dry-run` 核出口可达，允许个别源 0 条。

## ④ 结论

**可合并（后端 A1–A9 范围）**，无需返工：迁移、SQL 写法、锁 / savepoint、解析器、API 契约、种子、隔离过滤均与 design v3 及评审处置（D1–D9 / B1–B7 / C2–C9）逐项一致；本次发现的 12 处问题全部为实现细节与覆盖缺口，已就地修复并复跑门禁（492 passed）。合并前提：协调者完成 ③ 的 Neon 真库断言（尤其第 3 项的 SQL 语义与锁互斥），并就 ①「待决定」A 项（管理端是否展示 `parse_config`）给前端契约一个口径。
