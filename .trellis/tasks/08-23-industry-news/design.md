# 行业动态 · 技术设计（v3，按三份核证 + Codex 评审修订）

> 依据 [prd.md](./prd.md)；编码约定遵循 `.trellis/spec/backend` 与 `.trellis/spec/frontend`；术语见 `CONTEXT.md`；结构性决策见 ADR 0001 / 0002。本文只写"怎么做"。修订依据：`research/design-review-{data-model,backend,frontend}.md`（逐条对照仓库与真库核证）与 `research/design-review-codex.md`（产品口径与共库运维的第二视角），修订对照见 `research/review-resolution.md`。

## 1. 总体结构与数据流

```
仓库种子 app/data/industry_news_sources_pcb.json（14 行：名称/地址/类别/语种/策略/解析规则）
   │  scripts/seed_industry_news_sources.py --instance default      ← 按实例导入/更新属性，不动启停与健康
   ▼
industry_news_sources（instance_id, industry='PCB', …, is_active, last_fetched_at, last_success_at, error_count）
   │  workers/industry_news_fetch.py：每天北京 08:00 一轮（单事务 + 实例级事务锁 + 每源 savepoint）；管理端「立即抓取」走同一函数
   ▼
services/industry_news/fetchers.py → rss | html | jsonld 解析出 [(title, url, published_at)]
services/industry_news/normalize.py → canonical_url、dedup_key（规范化标题 sha1）
   ▼
industry_news_items（instance_id, source_id, title, url, canonical_url, dedup_key, published_at, fetched_at）
   │                                            ▲
租户端 GET /industry-news/items ── JOIN sources（本实例 + 租户行业）LEFT JOIN industry_news_reads（当前用户）
管理端 GET /industry-news-sources ── 本实例源列表 + 健康；PATCH 启停；POST fetch 触发一轮
```

一个实例一条抓取循环，两实例各自抓各自的源（Instance B 没有源就是空转）。

## 2. 数据模型

一个 alembic revision `20260824_0001_industry_news`（`down_revision = "20260723_0003"`，当前唯一 head；链有编号倒挂，不按文件名推断）新建三张表；遗留四表的删除放独立 revision `20260824_0002`（`down_revision = "20260824_0001"`）。隔离列按 spec：`industry_news_sources` / `industry_news_items` 是平台级数据带 `instance_id`；`industry_news_reads` 是租户业务数据带 `tenant_id` + `user_id`。

```sql
CREATE TABLE industry_news_sources (
  id uuid PRIMARY KEY,                                -- 应用层 new_uuid() 生成（uuid7），无默认值，与库内 38 张表一致
  instance_id varchar NOT NULL,                       -- 与其他平台表同为无长度 varchar；有意不设 DEFAULT 'default'：seed 显式传、service 用 get_settings().instance_id
  industry varchar(50) NOT NULL,                      -- 规范值，如 'PCB'（租户原值 varchar(100) 经 canonical_industry 归一）
  code varchar(50) NOT NULL,                          -- 稳定代号（pcea / cpca-news …），种子 upsert 键，地址可变
  name varchar(100) NOT NULL,
  url text NOT NULL,                                  -- 入口地址（feed 或列表页）
  category varchar(100) NOT NULL,                     -- 客户定的类别
  lang varchar(10) NOT NULL,                          -- en / zh-CN / zh-TW
  strategy varchar(20) NOT NULL CHECK (strategy IN ('rss','html','jsonld')),
  parse_config jsonb NOT NULL DEFAULT '{}',           -- 解析规则，只由种子写
  is_active boolean NOT NULL DEFAULT true,
  last_fetched_at timestamptz,                        -- 上次尝试
  last_success_at timestamptz,                        -- 上次成功（解析 ≥1 条）
  error_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_industry_news_sources_instance_code UNIQUE (instance_id, code)
);
CREATE INDEX idx_industry_news_sources_instance_industry ON industry_news_sources (instance_id, industry, is_active);
DROP TRIGGER IF EXISTS set_updated_at ON industry_news_sources;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON industry_news_sources
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();   -- 函数已存在（schema.sql:10-16，两库 pg_proc 均有）；写法先例 20260529_0001:44-51

CREATE TABLE industry_news_items (
  id uuid PRIMARY KEY,
  instance_id varchar NOT NULL,
  source_id uuid NOT NULL REFERENCES industry_news_sources(id),
  title varchar(500) NOT NULL,
  url text NOT NULL,                                  -- 原文链接（原样）
  canonical_url text NOT NULL,                        -- 规范化后用于同稿判定
  dedup_key varchar(40) NOT NULL,                     -- sha1(规范化标题)，40 个十六进制字符恰好放下
  published_at timestamptz,                           -- 站点给的发布时间，可空
  fetched_at timestamptz NOT NULL,                    -- 该轮抓取的统一时间戳（run_at），同一轮所有动态相同
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_industry_news_items_instance_canonical_url UNIQUE (instance_id, canonical_url),
  CONSTRAINT uq_industry_news_items_instance_dedup_key UNIQUE (instance_id, dedup_key)
);
CREATE INDEX idx_industry_news_items_instance_fetched ON industry_news_items (instance_id, fetched_at DESC);
CREATE INDEX idx_industry_news_items_source ON industry_news_items (source_id);

CREATE TABLE industry_news_reads (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,     -- 每用户标记，随用户物理删除（先例 user_roles.user_id）；租户不物理删除，tenant_id 不带 CASCADE
  item_id uuid NOT NULL REFERENCES industry_news_items(id) ON DELETE CASCADE,
  read_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, item_id)
);
CREATE INDEX idx_industry_news_reads_tenant_user ON industry_news_reads (tenant_id, user_id);
```

- 不分区：日均几十行、一年两万行量级。`(instance_id, fetched_at DESC)` 索引服务 90 天窗口过滤并给排序首键；列表排序 `ORDER BY fetched_at DESC, COALESCE(published_at, fetched_at) DESC, id DESC`——一轮内所有动态共用 `run_at` 作 `fetched_at`，因此"最近一轮整体在上、一轮内按发布时间"，AC3 字面成立；余下排序在 2–5k 行结果上走内存 top-N，足够。
- 同稿判定由两个 UNIQUE 兜底，写入用 `INSERT … ON CONFLICT DO NOTHING`（不指定冲突目标即覆盖两条 UNIQUE），`rowcount = 0` 即同稿，**不做预 SELECT、不捕获 IntegrityError**（事务内任一语句出错会让整个事务 aborted）。
- 已知边界：btree 单条索引项 ≤ 2704 字节，超长 `canonical_url` 会报 `ProgramLimitExceeded`——按"该源当轮失败、错误计数 +1"处理，不会误判同稿。
- 入库过滤：带 `published_at` 且早于 90 天前的条目不入库（防首轮把站点历史灌进"未读"）；无发布时间的正常入库。窗口键是 `fetched_at`（我们何时抓到），展示键是 `published_at ?? fetched_at`。
- **不动 `backend/03_database/schema.sql`**：该文件被 `20260421_0001` 迁移直接执行，最近两次删表迁移（0714、0723）均未同步它，#61 ④ 将改为 pg_dump 生成物；结构契约只看 `schema_snapshot.json`。迁移合并后重跑 `scripts/schema_snapshot.py`：PR A 阶段只提交 `schema_snapshot.json`（diff = 三表 + `alembic_version` 一行），`docs/database-schema.md` / `.dbml` 留到发布后 `--prod` 再生；同时在 `schema_docs.json` 新增「行业动态」域与三表说明。
- 迁移文件写法：docstring 记 revision / down_revision / 依据（PRD + ADR）；开头 `SET LOCAL lock_timeout = '5s'` / `SET LOCAL statement_timeout = '30s'`；快照不采集触发器，A1 验证需另查 `pg_trigger`。
- 遗留删除（`20260824_0002`）：顺序 `publications → subscriptions → articles → sources`（四表间唯一 FK 是 `publications.subscription_id → subscriptions`；无外部表引用；分区与 RLS policy 随父表消失；不带 `IF EXISTS` / `CASCADE`）。生产实况：三表 0 行，**`intelligence_sources` 2 行**——按 `20260723_0003` 先例在 docstring 记录这两行（源名 / 地址，非敏感）后再删。downgrade 仅按快照定义还原结构（列 / 约束 / 索引）并重建 `intelligence_articles` 的 DEFAULT 分区，注明不还原触发器与 RLS policy。

## 3. 抓取模块（`backend/app/services/industry_news/`）

### 3.1 解析器（`fetchers.py`）

统一接口 `fetch_items(source: SourceRow, client: httpx.AsyncClient) -> list[RawItem]`，`RawItem(title, url, published_at | None)`。按 `strategy` 分发：

| strategy | 实现 | `parse_config` 键 |
|---|---|---|
| `rss` | `feedparser.parse(response.text)`；`entries[].title / link / published_parsed` | 无 |
| `html` | `selectolax.parser.HTMLParser`；`item_selector` 选出锚点或容器；链接取自身或 `link_selector`；标题取锚文本、`title_selector` 或 `title_from: "parent"`（所在段落全文）；`href_pattern` / `href_exclude` 正则过滤（`href_exclude` 必须锚定到自家域名/路径，不得用裸子串）；相对链接 `urljoin(跟随重定向后的最终响应 URL, href)`——站点 301 改路径后相对链接不会拼到旧路径 | `item_selector`、`link_selector?`、`title_selector?`、`title_from?`、`href_pattern?`、`href_exclude?` |
| `jsonld` | 解析全部 `<script type="application/ld+json">`，遍历 `ItemList.itemListElement[].item | self` 的 `name` / `url`，`href_pattern` 过滤，相对 `url` 则 `urljoin` | `href_pattern` |

HTTP：`httpx.AsyncClient(follow_redirects=True, timeout=20, headers={"User-Agent": 桌面浏览器 UA}, transport=self.transport)`——`transport` 构造注入，单测用 `httpx.MockTransport` 喂 fixture（先例 `integrations/engagelab.py`）；瞬时错误（超时、5xx）手写循环重试 2 次（不引入 `tenacity`：全仓零用法，不值得为此开先例），4xx 不重试。`feedparser` / `selectolax` 是同步解析，放 `asyncio.to_thread` 执行，不卡 API 进程事件循环。不做 RSS 自动发现（PRD R3 已明确删除）。

种子里一行 html 的形态：

```json
{"name": "CPCA 协会动态", "industry": "PCB", "category": "中国 PCB 行业", "lang": "zh-CN",
 "strategy": "html", "url": "https://www.cpca.org.cn/news.html",
 "parse_config": {"item_selector": "li.news-item a.lk", "title_selector": "p.tit"}}
```

### 3.2 规范化（`normalize.py`）

- `canonical_url(url)`：scheme / host 小写；去 `utm_*`、`fbclid`、`ref` 等跟踪参数；去 fragment；去尾部 `/`；保留其余 query。
- `normalize_title(title)`：NFKC → 去零宽字符 → `html.unescape` → 小写 → 去非字母数字（保留 CJK）→ 合并空白；`dedup_key = sha1(normalized)`。
- 标题截断 500；空标题或空链接的条目丢弃。

### 3.3 服务（`service.py`，`IndustryNewsService`）

- `fetch_source(conn, source, *, run_at) -> FetchStats`：调解析器（线程池）→ 规范化 → 丢弃 `published_at` 早于 90 天前的条目 → 逐条 `INSERT … ON CONFLICT DO NOTHING`（id 由 `new_uuid()` 生成，`fetched_at = run_at`），统计 `fetched / inserted / duplicate / skipped_old`。成功（解析 ≥1 条）：`last_fetched_at = last_success_at = run_at, error_count = 0`；失败或 0 条：`last_fetched_at = run_at, error_count = error_count + 1`，异常 `logger.exception` 带源名后继续下一源。
- `run_once(engine, *, instance_id, clock) -> dict`：**整轮一个事务 + 事务级锁 + 每源 savepoint**——`async with engine.begin() as conn`：`SELECT pg_try_advisory_xact_lock(CAST(:key AS bigint) + pg_catalog.hashtext(:instance_id))`，拿不到返回 `{"skipped": True, "reason": "in_progress"}`；`run_at = clock()`；逐源 `async with conn.begin_nested():` 调 `fetch_source`，单源异常回滚到 savepoint 并写错误计数，不影响其他源；事务结束锁自动释放，无 unlock 簿记。与 `wmt_lineage_repair` 第一阶段同构（事务锁 + 事务内完成全部工作）。代价：抓取期间连接处于事务中，单源等待 ≤ 60 秒（远小于 `idle_in_transaction_session_timeout`：Neon 5min / 生产 1h）；进程崩溃则整轮回滚、次日重来。
- 行业归一（§3.5）：租户端 service 方法开头单独 `SELECT industry FROM tenants WHERE id = :tenant_id`（先例 `tenant_messaging_service.py:72-79`），`canonical_industry()` 后作 `:industry` 参数；无法归一 → 直接返回空列表 / `has_sources=false`，不再查表。
- 租户读 `list_items(conn, *, tenant_id, user_id, instance_id, industry, filters, page, page_size) -> (items, total)`：

```sql
SELECT i.id, i.title, i.url, i.published_at, i.fetched_at,
       s.id AS source_id, s.name AS source_name, s.url AS source_url, s.category, s.lang,
       (r.item_id IS NOT NULL) AS is_read
FROM industry_news_items i
JOIN industry_news_sources s ON s.id = i.source_id
LEFT JOIN industry_news_reads r ON r.item_id = i.id AND r.user_id = :user_id AND r.tenant_id = :tenant_id
WHERE i.instance_id = :instance_id AND s.industry = :industry AND s.is_active
  AND i.fetched_at >= :window_start                                              -- Python 端算 now - 90d，带时区 datetime
  AND (CAST(:categories AS text[]) IS NULL OR s.category = ANY(CAST(:categories AS text[])))
  AND (CAST(:source_ids AS uuid[]) IS NULL OR s.id = ANY(CAST(:source_ids AS uuid[])))
  AND (CAST(:lang AS text) IS NULL OR s.lang = :lang)
  AND (NOT :unread_only OR r.item_id IS NULL)
ORDER BY i.fetched_at DESC, COALESCE(i.published_at, i.fetched_at) DESC, i.id DESC
LIMIT :limit OFFSET :offset
```
  重复命名参数必须带 `CAST`，否则 asyncpg 报 `AmbiguousParameterError`（Neon 实测）。另一条同条件 `count(*)` 给 `total`；route 传 `paginated_response(items, total=total, has_more=page * page_size < total)`（先例 `admin/collection.py:83`）。`target_domain = urlparse(url).netloc`，`is_external = target_domain != urlparse(source_url).netloc`。
- `list_filter_options(conn, *, instance_id, industry)`：启用源的 `category` 去重列表、`(id, name)` 列表、`lang` 去重列表；三者皆空即 `has_sources=false`。口径：**停用即隐藏**——列表与筛选都只看启用源，全部停用等同于未配置。
- `mark_read(conn, *, tenant_id, user_id, instance_id, industry, item_id)`：先用同一可见集合条件校验，再 `INSERT … ON CONFLICT (user_id, item_id) DO NOTHING`；不可见 → `AppError(NOT_FOUND)`。
- 管理端：`list_sources(conn, instance_id)`（14 行量级，`success_response` 返回数组，不分页）、`set_source_active(conn, instance_id, source_id, is_active)`（`UPDATE … WHERE id = :id AND instance_id = :iid`，0 行即 404）。

### 3.4 调度（`backend/app/workers/industry_news_fetch.py`）

- `run_industry_news_fetch_loop(engine, stop_event, *, clock=None)`：循环计算下一个北京 `FETCH_HOUR:00`（新增 `beijing_time.next_beijing_time(hour: int, now_utc: datetime | None = None) -> datetime`，内部经 `beijing_today` 继承 aware 校验，返回 aware datetime），`asyncio.wait_for(stop_event.wait(), timeout)` 睡到点后调 `run_once`。**不做启动补跑**：错过的一轮由运营点「立即抓取」补（去掉时钟 / 重启风暴一整类边界；按 `last_fetched_at` 判断的补跑也补不了"跑失败"的轮次）。多副本由事务锁互斥。
- `main.py` lifespan：`ensure_partitions` 之后，`INDUSTRY_NEWS_FETCH_ENABLED` 为真时 `asyncio.create_task`，`stop_event` + `cancel` + `suppress(CancelledError)` 四步与 `wmt_lineage_repair` 同构。
- 「立即抓取」：worker 模块提供 `trigger_fetch(engine, *, instance_id) -> dict`，内部 `_background_tasks: set[asyncio.Task]` 持有任务引用（`add_done_callback(discard)`）；本进程已有未完成任务、或在一个短事务里探测 `pg_try_advisory_xact_lock` 失败（另一进程——CLI、滚动发布中的旧 Pod——正持锁）→ `{"triggered": false, "reason": "in_progress"}`；后台任务结束后把 `run_once` 的结果写日志（skipped 记 warning）；本实例没有启用源 → `{"triggered": false, "reason": "no_sources"}`；否则 `{"triggered": true}`。路由 `@router.post("/fetch", status_code=202)`；前端按 `reason` toast「已开始抓取，稍后刷新查看」/「一轮抓取正在进行」/「本实例没有可抓取的源」。一轮 14 源最长可达数分钟，不在请求内等待。后台任务必须用 `get_engine()` 开新连接，不得复用 `context.connection`（一请求一事务）。测试里 `ASGITransport` 不触发 lifespan，`get_engine()` 会抛——用例 patch `trigger_fetch`。
- CLI `scripts/run_industry_news_fetch.py`：两种互斥模式——`--once [--source 名称]`（连库跑一轮，写库）与 `--from-file 路径 [--source 名称]`（不连库，按种子文件抓取并打印，永不写库；验收解析规则用）。照 `run_sending_worker.py` 模式（`initialize_engines` 在协程内调用，`finally close_engines`）。

### 3.5 行业归一（`app/utils/industry.py`）

导出 `INDUSTRY_ALIASES: dict[str, str] = {"pcb": "PCB", "电路板": "PCB"}`、`canonical_industry(value) -> str | None`（`lower(trim)` 后查表）与派生列表 `PCB_INDUSTRY_ALIASES`；`wmt_lineage_repair.py:25` 改为 `from app.utils.industry import PCB_INDUSTRY_ALIASES as _PCB_INDUSTRY_ALIASES`（保留旧名，`test_lineage_repair_industry_fanout.py:47-49` 的断言不用改）。

### 3.6 种子（`app/data/industry_news_sources_pcb.json` + `scripts/seed_industry_news_sources.py`）

- 读取先例 `generate_country_holidays.py`（`Path(__file__).resolve().parents[1] / "app" / "data"`）；参数 `--instance <id>`（必填）`--file`（默认 PCB 种子）`--dry-run`；按 `(instance_id, code)` upsert：新行插入（id 由 `new_uuid()` 生成）；已存在则更新 `name / url / industry / category / lang / strategy / parse_config`（地址可变），**不改** `is_active / last_* / error_count`。单事务；输出新增 / 更新 / 不变计数。防误：`--instance` 不是 `default` 时必须同时带 `--confirm-instance <同值>` 才执行写入（共库上误导入会破坏"B 不配源"）。
- 生产执行属写操作：先 `--dry-run` 展示 14 行与计数，确认后执行，执行后 `SELECT count(*)` 回读。

## 4. API 契约（全部 Pydantic 收参，`success_response` / `paginated_response` 包装）

### 租户端 `/t/{slug}/api/v1`（`api/tenant/industry_news.py`，`get_current_tenant_user`，所有角色含 viewer）

| 方法 | 路径 | 请求 | 响应 `data` |
|---|---|---|---|
| GET | `/industry-news/items` | Query：`category[]?`、`source_id[]?`（`Query(alias="category[]")` 收数组，与 `ops.py:41-46` 一致）、`lang?`、`unread_only?=false`、`page=1`、`page_size=50`（≤100） | `[{id, title, url, source_id, source_name, category, lang, time, is_read, target_domain, is_external}]` + `pagination.total`、`has_more` |
| GET | `/industry-news/filters` | — | `{categories: [str], sources: [{id, name}], langs: [str], has_sources: bool}` |
| POST | `/industry-news/items/{item_id}/read` | — | `{item_id, is_read: true}`（幂等；不可见 404） |

`time` = `published_at ?? fetched_at`（ISO 字符串）。

### 管理端 `/admin/api/v1`（`api/admin/industry_news_sources.py`：`APIRouter(prefix="/industry-news-sources")`，在 `admin/router.py` 用 `include_router` 挂入；`get_current_platform_user`）

| 方法 | 路径 | 请求 | 响应 `data` |
|---|---|---|---|
| GET | `/industry-news-sources` | — | `[{id, code, name, url, industry, category, lang, strategy, is_active, last_fetched_at, last_success_at, error_count}]`（仅本实例，`success_response` 数组，不分页） |
| POST | `/industry-news-sources/fetch` | — | `{"triggered": bool, "reason"?: "in_progress" \| "no_sources"}`，`status_code=202`；**定义在 `/{source_id}` 之前** |
| PATCH | `/industry-news-sources/{source_id}` | `IndustryNewsSourceToggle {is_active: bool}` | 更新后的源 |

Pydantic 模型放 `app/schemas/industry_news.py`。

## 5. 前端

### 5.1 租户端 `apps/tenant/src/app/(dashboard)/industry-news/page.tsx`（`'use client'`）

- 取数：`useQuery({ queryKey: queryKeys.industryNews.filters(), queryFn: async () => (await tenantApi.industryNews.filters()).data.data })`；列表 `useQuery({ queryKey: queryKeys.industryNews.list({ ...applied, page, pageSize }), queryFn, placeholderData: keepPreviousData })`——没有 `keepPreviousData` 翻页 / 筛选换 key 时旧行会消失。`queryKeys.industryNews`（tenant 区，带 `tenantScope()`）：`all()`、`list(filters)`、`filters()`。
- 布局：`ListPage`（`title="行业动态"`，无 `primaryAction`）→ `FilterBar`（`layout` 默认 grid，4 个字段一行）→ `DataTable`（`entityName="动态"`）→ `Pagination`（`mode="total" total={total} value={{page, pageSize}} onChange isDisabled={listQuery.isLoading}`，每页 50）。
- FilterBar schema（draft 值只能是 `string | string[]`）：类别 `kind: 'multiSelect'`（`categories: string[]`）、来源 `kind: 'multiSelect'`（`sources: string[]`，value=id，label=name）、语种 `kind: 'select'`（`lang: string`，内置「不限」）、「只看未读」`kind: 'custom'` 渲染共享 `Switch`（draft `unread_only: '' | '1'`，`aria-label="只看未读"`，className 照 `data-table.tsx:189` 的 `data-[state=checked]:bg-ui-primary`）。`onSubmit` 设 applied + `setPage(1)`；`onReset` 自己清 draft / applied / page（先例 `companies/page.tsx:76-87`）。选项来自 `/industry-news/filters`，传 `optionState`。
- 列：标题（`large`，`type: 'text'`，`render`）、来源（`medium`）、类别（`small`，`<Badge tone="neutral">`）、语种（`small`，`en→英文 / zh-CN→简体中文 / zh-TW→繁体中文`）、时间（`medium`，`type: 'date'`，`format: (value) => formatDateTime(value as string | undefined, 'YYYY-MM-DD')`）。
- 标题单元格：`<a href={row.url} target="_blank" rel="noopener noreferrer" onClick={() => markRead.mutate(row.id)}>`（先例 `admin/collection/customers/client-page.tsx:563-571`；无 `onRowClick`、无行级 className 钩子，已读 / 未读只能在单元格内区分）。未读 `truncate text-ui-body-strong text-ui-foreground`，已读 `truncate text-ui-muted-foreground`；`is_external` 时标题后 `text-ui-caption text-ui-muted-foreground` 灰字 `target_domain`。
- 已读反馈：页面本地 `clickedIds: Set<string>`（`useState`，手法同 `updatingIds`），渲染 `row.is_read || clickedIds.has(row.id)`；**`markRead` 成功后不 invalidate 列表**——点过的行保持可见并显示为已读态，直到用户翻页 / 改筛选 / 重进页面（符合 spec「不手改缓存」；开着「只看未读」时行不会在点击瞬间消失，下一次取数后自然不再出现）。
- 状态：`filters.has_sources === false` → 不渲染 DataTable，在 `ListPage` children 位置渲染说明块（容器样式同 `companies/page.tsx:175`）文案「本实例尚未配置动态源」；有源无结果 → `TableState` 空态，`entityName="动态"` 自动得「暂无动态」/「没有符合当前条件的动态」，传 `filtered: appliedCount > 0, onResetFilters`；`isLoading` / `isError`（`description: '请检查网络后重试', onRetry: refetch`）/ `isRefreshing={isFetching && !isLoading}` 按五件套传参。

### 5.2 管理端 `apps/admin/src/app/(dashboard)/industry-news-sources/`

- `page.tsx`：`createPrefetchPage<ApiResponse<IndustryNewsSource[]>>({ queryKey: ['admin', 'industry-news-sources'], fetchFn: (token) => serverApi.get('/api/v1/industry-news-sources', { token }), Component })`；`client-page.tsx` 用同一**字面量** key（`create-prefetch-page` 是 server-only，`query-keys.ts` 依赖 `@shared/hooks` 的 zustand，现有 8 个预取页全用字面量；spec 评审清单的"工厂"要求对 admin 预取页不适用，见 §8 spec 修订）；客户端 `queryFn` 返回 axios `.data`（响应体），与预取返回形状一致。
- `ListPage` `title="动态源管理"`，`primaryAction={<Button variant="outline">立即抓取</Button>}`（非新增语义不用 `CreateButton`；点击 → `POST …/fetch` → 按 `reason` toast，30 秒后 invalidate 列表一次并提示「稍后刷新查看」）。列表为空（Instance B）时不渲染 DataTable，渲染说明块「本实例尚未配置动态源（由开发随种子导入）」。
- `DataTable` 列：名称、地址（`type: 'text'` 不给 render，自动截断 + Tooltip）、类别、语种、策略、启用（`type: 'boolean', booleanMode: 'interactive'` + `updatingIds`，先例 `admin/intelligence-sources/client-page.tsx:232-242`）、上次成功时间（空显示「从未」，先例 `:244-249`）、错误计数（`render`，>0 套 `text-ui-danger-foreground`）。无新增 / 编辑 / 删除。

### 5.3 共享包、导航、AI 配置页

- `shared-types/models.ts`：`IndustryNewsItem`、`IndustryNewsSource`、`IndustryNewsFilterOptions`；`api.ts`：`IndustryNewsFilters { 'category[]'?: string[]; 'source_id[]'?: string[]; lang?: string; unread_only?: boolean; page?: number; page_size?: number }`（数组键名与 `tenant/companies.ts:63-68` 一致）。PR A 不删旧 `Intelligence*`。
- `shared-api`：`tenant/industry-news.ts`（`list(filters)` → `client.get<PaginatedResponse<IndustryNewsItem>>`、`filters()` → `client.get<ApiResponse<IndustryNewsFilterOptions>>`、`markRead(id)` → `client.post<ApiResponse<{item_id: string; is_read: true}>>`）注册到 `tenant/index.ts`；`admin/industry-news-sources.ts`（`list()`、`fetch()`、`toggle(id, is_active)`）注册到 `admin/index.ts`；类型再导出在 `shared-api/src/index.ts`；`query-keys.ts` tenant 区新增 `industryNews`。
- 导航：tenant `navigation.ts:30` 改为 `{ label: '行业动态', items: [{ href: '/industry-news', label: '行业动态', icon: Newspaper }] }`；admin `navigation.ts:33` 改为 `{ href: '/industry-news-sources', label: '动态源管理', icon: Globe2 }`。
- AI 配置页：`admin/ai-config/client-page.tsx:65` 在灌入 state 时 `filter((item) => item.scene !== 'intelligence_summary')`——既不渲染也不再随整份 PUT 提交该场景；`:34` 的标签在 PR B 删。「删除模型」失败时 toast 显示后端原因（如被场景默认配置引用）。

## 6. 遗留清理清单（PR B）

| 层 | 删除 / 修改 |
|---|---|
| 数据库 | revision `20260824_0002` 删四表（§2） |
| 后端 | `services/intelligence_service.py`；`api/tenant/intelligence.py` 及 `tenant/router.py` 挂载；`api/admin/config.py` 五个 `intelligence-sources` 端点；`admin_config_service.py:445-597` 六个方法 + `:1554-1569` `_serialize_intelligence_source` + **`:1463` dashboard 子查询 `total_articles` 与 `:1474` 输出键**（否则删表后 `GET /admin/api/v1/dashboard/overview` 500）；**`internal_ops_service.py:4, 11, 36-37`** 导入与 `publish_article`（否则 API 启动即崩）+ `api/internal/ops.py:50-56` 端点；`schemas/admin_config.py:45-56, 189-192, 195-206` 三个模型；`db/partitions.py:12`（docstring）与 `:26`（`_MANAGED` 条目）；**`scripts/seed_demo_data.py:11, 68, 466-487, 515`**（`ensure_intelligence`）；`tests/test_intelligence_article_serialization.py`；`tests/test_admin_config.py:56-62, 237-238, 245-246, 369-384, 433-438, 468-486` 与 `:3` docstring 计数；`tests/test_admin_instance_isolation.py:594, 619` mock 里的 `total_articles` 键。**`scripts/maintain_partitions.py` 没有 `intelligence_articles` 条目，无需改。** 同一 revision 内 `DELETE FROM ai_scene_defaults WHERE scene = 'intelligence_summary'`（隐藏后无人能改它指向的模型，留着会让被引用模型永远删不掉）并清 `init_instance.py:209` 的种下逻辑。保留：各 CHECK 枚举、`schemas/admin_config.py:121-127` Literal、`tenant_query_service.py:1068` 的能力清单项 |
| 前端 | 删文件：tenant `intelligence/page.tsx`、`test/intelligence/`、admin `intelligence-sources/{page,client-page}.tsx`、`shared-api/src/tenant/intelligence.ts`、`shared-api/src/admin/intelligence-sources.ts`；行级：`shared-api/src/tenant/index.ts:10, 28`、`admin/index.ts:6, 19`、`shared-api/src/index.ts:7, 43`、`query-keys.ts:35-39, 80-84`、`shared-types/src/models.ts:17-19, 355-406`、`enums.ts:30-33`、`api.ts:64-69`（`IntelFilters`）与 `:321-329`（`ImportResult`，孤儿可删）、`admin/ai-config/client-page.tsx:34`。**保留 `enums.ts:39, 40, 43`** 三处枚举成员 |
| 文档 / spec | `schema_docs.json` 删「行业情报」域与四表说明、`schema_notes.md:31, 58, 78, 96, 104`；`docs/database-schema.md` / `.dbml` 随 `--prod` 快照再生；README `:21`（seed 命令说明）`:129`（「维护行业情报源」→「维护行业动态源」）`:154` `:169`（矩阵两行，PR A 已改为行业动态）；spec：`backend/api-guidelines.md:3, 8, 21`、`error-handling.md:3, 18`、`database-guidelines.md:44`、`domain-rules.md:20`（去掉「情报摘要」）、`frontend/directory-structure.md:23`、`state-management.md:3, 17`、`component-guidelines.md:327, 329`、`type-safety.md:16`、`quality-guidelines.md:14, 16`——示例改指向行业动态的新文件；`PROGRESS-2026-Q3.md` 与 `docs/solutions/` 为历史记录不动 |

验收门禁口径：`rg -n -i "intelligence" backend/app backend/scripts backend/tests` 只剩 `schemas/admin_config.py`（场景 Literal）与 `tenant_query_service.py:1068`；`rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!**/enums.ts'` 为空。

## 7. 配置与部署

- 新依赖：`feedparser>=6.0`（纯 Python）、`selectolax>=0.4`（cp313 manylinux wheel）；`uv lock` 与 Python 3.13 安装已实测通过。
- 新 Settings：`industry_news_fetch_enabled: bool = Field(default=False, alias="INDUSTRY_NEWS_FETCH_ENABLED")`、`industry_news_fetch_hour_beijing: int = Field(default=8, alias="INDUSTRY_NEWS_FETCH_HOUR_BEIJING")`。Instance A 的环境打开，B 保持关闭。
- 上线顺序：合并 PR A → 发布共用 backend（启动自动迁移建表）+ A / B **四套**前端镜像（B 曾漏发，导航已替换必须发）→ 开关保持关 → A 实例 backend 容器内 `seed --instance default --dry-run` → 确认 → 执行 → `SELECT count(*)=14` 回读 → **在 A 容器内** `run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json` 核出口可达（国内云出网，IPC / I-Connect007 / 慕尼黑两站可能偶发 403 或 0 条；允许当日个别源 0 条，靠错误计数跟）→ 设 `INDUSTRY_NEWS_FETCH_ENABLED=true` 重启 → 点「立即抓取」跑首轮 → AC1–AC5 验收（含 B 租户与 B 管理端空态）→ 观察一轮 08:00 → 合并 PR B → 发布 → `schema_snapshot.py --prod` 再生文档并提交。
- **回退事实**：PR B 的删表迁移落地后，任何仍含旧 `partitions.py` 的镜像（B 之前的 tag）启动即在 `ensure_partitions` 崩溃，且 spec 禁止生产 downgrade——B 发布后只能前向修复，不能回退镜像。PR A 发布后的回退不受影响（新表无害）。

## 8. 顺带修正的 spec 漂移（随 PR A 提交）

- `frontend/component-guidelines.md:217` 与 `design-system.md:178-183`：列宽 token 实际为 small=64px / medium=96px / large=144px（`globals.css:62-64`，commit 7ffc926），spec 仍写 96/144/224。
- `backend/workers.md` 必备模式 2：补"事务级锁只覆盖持锁事务；要整轮互斥就把整轮放进同一事务并用 savepoint 隔离单条失败（现役 `wmt_lineage_repair` 第一阶段即此模式）"，并登记新 worker。
- `backend/database-guidelines.md:44`：`maintain_partitions.py` 只维护 `emails` / `audit_logs`。
- `frontend/quality-guidelines.md:38`：admin 预取页的 key 为字面量是既定做法，"工厂"要求限于客户端页面。

## 9. 测试与验证

- 单测：三种解析器用 `tests/fixtures/industry_news/` 裁剪的真实页面与 feed，经 `httpx.MockTransport` 喂入；`normalize`；90 天入库过滤；service 用替身 conn 断言 SQL 片段与参数（`CAST(... AS text[])`、`window_start`、`industry`、`s.is_active`、`unread_only`、`LIMIT/OFFSET`、排序键）；worker 的 `next_beijing_time`、`in_progress` / `no_sources` 返回、`trigger_fetch` 去重（注入 clock）。
- Neon 断言（`/db-verify` 三段式）：两条 UNIQUE 的同稿语义与 `ON CONFLICT DO NOTHING` 的 `rowcount`、`CAST` 数组参数在 asyncpg 下可执行、90 天边界、已读只对当前用户生效、`mark_read` 不可见 404、停用源的动态不再出现且不被抓取、savepoint 隔离单源失败、两连接事务锁互斥。
- 真站冒烟（**信息性，不是合并门槛**——站点偶发与出口环境不算代码错误）：开发侧 `--from-file … --dry-run` 定稿 PCB Update 规则；上线后在 A 容器内再跑一次。合并门槛只看 fixture 单测。
- 前端 Vitest（tenant，模板 `test/intelligence/intelligence-page.test.tsx`）：未读 / 已读类名、`<a>` 的 href / target / rel 与点击后 `markRead` 被调用且行变已读态、`has_sources=false` 说明块、筛选参数透传（`toHaveBeenCalledWith(expect.objectContaining({ 'category[]': [...], unread_only: true, page: 1, page_size: 50 }))`）；mock `list` 返回 `{ data: { data: rows, pagination: { total } } }`。admin：type-check + build。
- 验收映射：AC1 → 租户页冒烟 + 已读测试；AC2 → 筛选与窗口断言（来源筛选按保留源）；AC3 → 首轮「立即抓取」后观察置顶 + 去重与 90 天入库过滤断言；AC4 → 管理端冒烟（停用、立即抓取进行中提示）+ 开发库坏 `parse_config` 计数断言；AC5 → B 租户与 B 管理端空态；AC6 → 清理 revision + 门禁口径（§6）。

## 10. 实施切分

两条 PR、两次发布：PR A 新功能（建表 revision + 全部功能 + §8 spec 修正；旧页面保留但无入口），PR B 遗留清理（删表 revision + §6 清单）。A 发布、种子导入、首轮「立即抓取」并观察过一轮 08:00 后再合 B（B 删表后不可回退）。

## 11. 风险与未决

- PCB Update 的"段落全文作标题"可能把导语带进来，dry-run 时按样本定稿；electronica / productronica 的 JSON-LD 改版风险高于 RSS。
- 两个 UNIQUE 会把标题完全相同的两条不同动态判成同稿（周期性同名公告）；已接受。
- 超长 URL 边界（§2）；生产出口对个别站点的可达性（§7）；首轮无发布时间的 HTML 条目全部按当轮入库（I-Connect007 约 46 条），首日列表偏多，可接受。
- 租户行业为空或不在别名表的租户看到空态。
