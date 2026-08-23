# 行业动态 · 技术设计

> 依据 [prd.md](./prd.md)；编码约定遵循 `.trellis/spec/backend` 与 `.trellis/spec/frontend`；术语见 `CONTEXT.md`；结构性决策见 ADR 0001 / 0002。本文只写"怎么做"，需求不再重复。

## 1. 总体结构与数据流

```
仓库种子 app/data/industry_news_sources_pcb.json（14 行：名称/地址/类别/语种/策略/解析规则）
   │  scripts/seed_industry_news_sources.py --instance default      ← 按实例导入/更新属性，不动启停与健康
   ▼
industry_news_sources（instance_id, industry='PCB', …, is_active, last_fetched_at, last_success_at, error_count）
   │  workers/industry_news_fetch.py：每天北京 08:00 一轮（实例级 advisory lock）；管理端「立即抓取」走同一函数
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

一个 alembic revision（`20260824_0001_industry_news`）新建三张表；遗留四表的删除放独立 revision（见 §9 切分）。隔离列按 spec「隔离过滤」表：`industry_news_sources` / `industry_news_items` 是平台级数据带 `instance_id`；`industry_news_reads` 是租户业务数据带 `tenant_id` + `user_id`。

```sql
CREATE TABLE industry_news_sources (
  id uuid PRIMARY KEY,
  instance_id varchar NOT NULL,
  industry varchar(50) NOT NULL,                      -- 规范值，如 'PCB'
  name varchar(100) NOT NULL,
  url text NOT NULL,                                  -- 入口地址（feed 或列表页）
  category varchar(100) NOT NULL,                     -- 客户定的类别
  lang varchar(10) NOT NULL,                          -- en / zh-CN / zh-TW
  strategy varchar(20) NOT NULL CHECK (strategy IN ('rss','html','jsonld')),
  parse_config jsonb NOT NULL DEFAULT '{}',           -- 解析规则，只由种子写
  is_active boolean NOT NULL DEFAULT true,
  last_fetched_at timestamptz,                        -- 上次尝试
  last_success_at timestamptz,                        -- 上次成功（≥1 条）
  error_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (instance_id, url)
);
CREATE INDEX idx_industry_news_sources_instance_industry ON industry_news_sources (instance_id, industry, is_active);

CREATE TABLE industry_news_items (
  id uuid PRIMARY KEY,
  instance_id varchar NOT NULL,
  source_id uuid NOT NULL REFERENCES industry_news_sources(id),
  title varchar(500) NOT NULL,
  url text NOT NULL,                                  -- 原文链接（原样）
  canonical_url text NOT NULL,                        -- 规范化后用于同稿判定
  dedup_key varchar(40) NOT NULL,                     -- sha1(规范化标题)
  published_at timestamptz,                           -- 站点给的发布时间，可空
  fetched_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (instance_id, canonical_url),
  UNIQUE (instance_id, dedup_key)
);
CREATE INDEX idx_industry_news_items_instance_time ON industry_news_items (instance_id, fetched_at DESC);
CREATE INDEX idx_industry_news_items_source ON industry_news_items (source_id);

CREATE TABLE industry_news_reads (
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id),
  item_id uuid NOT NULL REFERENCES industry_news_items(id) ON DELETE CASCADE,
  read_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, item_id)
);
CREATE INDEX idx_industry_news_reads_tenant_user ON industry_news_reads (tenant_id, user_id);
```

- 不分区：日均几十行，一年两万行量级；90 天窗口靠 `(instance_id, fetched_at DESC)` 索引即可。
- 同稿判定由两个 UNIQUE 兜底，应用层先 `SELECT` 再 `INSERT`（单进程持锁，无并发竞争）；命中唯一冲突视为同稿跳过。
- `updated_at` 沿用 `trigger_set_updated_at()`。
- `schema.sql` 同步追加；合并后重跑 `scripts/schema_snapshot.py` 提交快照。

## 3. 抓取模块（`backend/app/services/industry_news/`）

### 3.1 解析器（`fetchers.py`）

统一接口 `fetch_items(source: SourceRow, client: httpx.AsyncClient) -> list[RawItem]`，`RawItem(title, url, published_at | None)`。按 `strategy` 分发：

| strategy | 实现 | `parse_config` 键 |
|---|---|---|
| `rss` | `feedparser.parse(response.text)`；`entries[].title/link/published_parsed` | 无 |
| `html` | `selectolax.parser.HTMLParser`；`item_selector` 选出锚点或容器；链接取自身或 `link_selector`；标题取锚文本、`title_selector` 或 `title_from: "parent"`（所在段落全文）；`href_pattern` / `href_exclude` 正则过滤；相对链接用 `urljoin(source.url, href)` | `item_selector`、`link_selector?`、`title_selector?`、`title_from?`、`href_pattern?`、`href_exclude?` |
| `jsonld` | 解析全部 `<script type="application/ld+json">`，遍历 `ItemList.itemListElement[].item|self` 的 `name` / `url`，`href_pattern` 过滤，`url` 相对则 `urljoin` | `href_pattern` |

HTTP：`httpx.AsyncClient(follow_redirects=True, timeout=20, headers={"User-Agent": 桌面浏览器 UA})`；瞬时错误（超时、5xx）用 `tenacity` 重试 2 次；4xx 不重试。不做 RSS 自动发现（种子已标明策略；自动发现只在将来允许运营添加源时才有意义）。

种子里一行 html 的形态：

```json
{"name": "CPCA 协会动态", "industry": "PCB", "category": "中国 PCB 行业", "lang": "zh-CN",
 "strategy": "html", "url": "https://www.cpca.org.cn/news.html",
 "parse_config": {"item_selector": "li.news-item a.lk", "title_selector": "p.tit"}}
```

### 3.2 规范化（`normalize.py`）

- `canonical_url(url)`：scheme/host 小写；去 `utm_*`、`fbclid`、`ref` 等跟踪参数；去 fragment；去尾部 `/`；保留其余 query（PCD&F / CA 的 `?format=…` 不在文章链接上，不受影响）。
- `normalize_title(title)`：NFKC → 去零宽字符（`​‌‍﻿`）→ `html.unescape` → 小写 → 去非字母数字（保留 CJK）→ 合并空白；`dedup_key = sha1(normalized)`。
- 标题截断 500；空标题或空链接的条目丢弃。

### 3.3 服务（`service.py`，`IndustryNewsService`）

- `fetch_source(conn, source) -> FetchStats`：调解析器 → 规范化 → 对每条 `SELECT 1 FROM industry_news_items WHERE instance_id=:iid AND (canonical_url=:cu OR dedup_key=:dk)`，未命中则 INSERT（`IntegrityError` 视为同稿）。统计 `fetched / inserted / duplicate`。成功（解析 ≥1 条）：`last_fetched_at = last_success_at = now(), error_count = 0`；失败或 0 条：`last_fetched_at = now(), error_count = error_count + 1`，异常 `logger.exception` 带源名后继续下一源。**每源一个事务**。
- `run_once(engine, *, instance_id) -> dict`：`engine.begin()` 内 `pg_try_advisory_xact_lock(CAST(:key AS bigint) + hashtext(:instance_id))`，拿不到返回 `{"skipped": True}`；逐源调用 `fetch_source`（每源单独 `engine.begin()`，锁事务只做互斥）。返回各源统计，供 CLI 与日志。
- 租户读：`list_items(conn, *, tenant_id, user_id, instance_id, filters, page, page_size)`：

```sql
SELECT i.id, i.title, i.url, i.published_at, i.fetched_at,
       s.id AS source_id, s.name AS source_name, s.category, s.lang,
       (r.item_id IS NOT NULL) AS is_read
FROM industry_news_items i
JOIN industry_news_sources s ON s.id = i.source_id
LEFT JOIN industry_news_reads r ON r.item_id = i.id AND r.user_id = :user_id AND r.tenant_id = :tenant_id
WHERE i.instance_id = :instance_id AND s.industry = :industry
  AND i.fetched_at >= :window_start                       -- Python 端算 now - 90d
  AND (:categories IS NULL OR s.category = ANY(:categories))
  AND (:source_ids IS NULL OR s.id = ANY(:source_ids))
  AND (:lang IS NULL OR s.lang = :lang)
  AND (NOT :unread_only OR r.item_id IS NULL)
ORDER BY COALESCE(i.published_at, i.fetched_at) DESC, i.id DESC
LIMIT :limit OFFSET :offset
```
  另一条同条件的 `count(*)` 给分页 `total`。`industry` 由租户行业规范化得到（§3.5）。`target_domain` 在序列化时用 `urlparse(url).netloc` 计算，`is_external = target_domain != urlparse(source.url).netloc`。
- `list_filter_options(conn, *, instance_id, industry)`：本实例该行业启用源的 `category` 去重列表、`(id, name)` 列表、`lang` 去重列表；三者皆空即"本实例尚未配置动态源"。
- `mark_read(conn, *, tenant_id, user_id, instance_id, industry, item_id)`：先校验该条属于可见集合（同一 JOIN 条件），再 `INSERT ... ON CONFLICT (user_id, item_id) DO NOTHING`。
- 管理端：`list_sources(conn, instance_id)`、`set_source_active(conn, instance_id, source_id, is_active)`（`UPDATE … WHERE id=:id AND instance_id=:iid`，0 行即 404）。

### 3.4 调度（`backend/app/workers/industry_news_fetch.py`）

- `run_industry_news_fetch_loop(engine, stop_event, *, clock=None)`：循环计算下一个北京 `FETCH_HOUR:00`（`app/utils/beijing_time.py`，新增 `next_beijing_time(hour, now_utc)`），`asyncio.wait_for(stop_event.wait(), timeout)` 睡到点后调 `run_once`。**启动补跑**：若 `now ≥ 今日 08:00` 且 `max(last_fetched_at)` 早于今日 08:00（或为空），立即跑一轮——覆盖发布重启错过的情况；两个 API 副本由锁互斥。
- `main.py` lifespan：`INDUSTRY_NEWS_FETCH_ENABLED`（默认 false）为真时 `asyncio.create_task`；`stop_event` 优雅退出，与 `wmt_lineage_repair` 同一写法。
- 「立即抓取」：admin 端点用 `asyncio.create_task(run_once(engine, instance_id=...))` 异步触发并返回 202；进行中的一轮由锁保证不重叠。
- 新增 CLI `scripts/run_industry_news_fetch.py --once [--source 名称] [--dry-run]`：`--dry-run` 只打印解析结果不写库，用于验收选择器；`--from-file app/data/industry_news_sources_pcb.json` 不连库直接抓全部种子。

### 3.5 行业规范化（`app/utils/industry.py`）

`canonical_industry(value: str | None) -> str | None`：别名表 `{"pcb": "PCB", "电路板": "PCB"}`（常量从 `wmt_lineage_repair._PCB_INDUSTRY_ALIASES` 迁入此处并由其导入，避免两份）。租户行业取自 `tenants.industry`，在租户端点的 service 查询里 JOIN `tenants` 取得后规范化；无法规范化的行业视为无源（空态）。

### 3.6 种子（`app/data/industry_news_sources_pcb.json` + `scripts/seed_industry_news_sources.py`）

- 脚本参数 `--instance <id>`（必填）`--file`（默认 PCB 种子）`--dry-run`；按 `(instance_id, url)` upsert：新行插入；已存在则更新 `name / industry / category / lang / strategy / parse_config`，**不改** `is_active / last_* / error_count`。输出新增 / 更新 / 不变计数。
- 生产执行属写操作：先 `--dry-run` 展示 14 行与计数，取得确认后再执行，执行后 `SELECT count(*)` 回读。

## 4. API 契约（全部 Pydantic 收参，`success_response` / `paginated_response` 包装）

### 租户端 `/t/{slug}/api/v1`（`api/tenant/industry_news.py`，`get_current_tenant_user`，所有角色）

| 方法 | 路径 | 请求 | 响应 `data` |
|---|---|---|---|
| GET | `/industry-news/items` | Query：`category[]?`、`source_id[]?`、`lang?`、`unread_only?=false`、`page=1`、`page_size=50`（≤100） | `[{id, title, url, source_id, source_name, category, lang, time, is_read, target_domain, is_external}]` + `pagination.total` |
| GET | `/industry-news/filters` | — | `{categories: [str], sources: [{id, name}], langs: [str], has_sources: bool}` |
| POST | `/industry-news/items/{item_id}/read` | — | `{item_id, is_read: true}`（幂等；不可见条目 404） |

`time` = `published_at ?? fetched_at`（ISO 字符串）。

### 管理端 `/admin/api/v1`（`api/admin/industry_news_sources.py`，挂入 admin router；`get_current_platform_user`）

| 方法 | 路径 | 请求 | 响应 `data` |
|---|---|---|---|
| GET | `/industry-news-sources` | — | `[{id, name, url, industry, category, lang, strategy, is_active, last_fetched_at, last_success_at, error_count}]`（仅本实例） |
| POST | `/industry-news-sources/fetch` | — | `{"triggered": true}`，HTTP 202（静态路由放在 `/{id}` 之前） |
| PATCH | `/industry-news-sources/{source_id}` | `IndustryNewsSourceToggle {is_active: bool}` | 更新后的源 |

Pydantic 模型放 `app/schemas/industry_news.py`。

## 5. 前端

### 5.1 租户端 `apps/tenant/src/app/(dashboard)/industry-news/page.tsx`（`'use client'`）

- 取数：`useQuery(queryKeys.industryNews.filters())`、`useQuery(queryKeys.industryNews.list({...applied, page, pageSize}))`（新增 `queryKeys.industryNews`，带 tenant scope）；`tenantApi.industryNews.list / filters / markRead`。
- 布局：`ListPage`（标题「行业动态」，无主操作按钮）→ `FilterBar`（schema：类别多选、来源多选、语种单选、「只看未读」开关；draft → applied 按 FilterBar 契约）→ `DataTable` → `Pagination`。
- 列：标题（`large`，`render`：未读 `text-ui-foreground text-ui-body-strong`，已读 `text-ui-muted-foreground`；`is_external` 时标题后 `text-ui-caption text-ui-muted-foreground` 灰字 `target_domain`）、来源（`medium`）、类别（`small`，`Badge` neutral）、语种（`small`，映射 `en→英文 / zh-CN→简体中文 / zh-TW→繁体中文`）、时间（`medium`，`type: 'date'`，`formatDateTime(..., 'YYYY-MM-DD')`）。
- 点击标题：`window.open(url, '_blank', 'noopener,noreferrer')`，同时 `markRead` mutation；`onMutate` 乐观把该行 `is_read` 置 true，`onSettled` invalidate `queryKeys.industryNews.all()`。
- 状态：`filters.has_sources === false` → `TableState` 空态文案「本实例尚未配置动态源」；有源但无结果 → 「暂无动态」/「没有符合筛选的动态」；加载 / 刷新 / 错误按五件套默认。
- 每页 50；refetch 期间保留旧行（五件套契约）。

### 5.2 管理端 `apps/admin/src/app/(dashboard)/industry-news-sources/`

- `page.tsx`：`createPrefetchPage({ queryKey: ['admin', 'industry-news-sources'], fetchFn: token => serverApi.get('/api/v1/industry-news-sources', { token }), Component })`；`client-page.tsx` 用同一 key。
- `ListPage` 标题「动态源管理」，头部一个 `Button`「立即抓取」（点击 → `POST …/fetch` → toast「已触发本轮抓取」，3 秒后 invalidate 列表）。
- `DataTable` 列：名称、地址（截断 + Tooltip）、类别、语种、策略、启用（`Switch`，提交期间禁用当前行）、上次成功时间、错误计数（>0 用 `text-ui-danger-foreground`）。无新增 / 编辑 / 删除。

### 5.3 共享包与导航

- `shared-types/models.ts`：`IndustryNewsItem`、`IndustryNewsSource`；`api.ts`：`IndustryNewsFilters`；删除 `Intelligence*`。
- `shared-api`：新增 `tenant/industry-news.ts`、`admin/industry-news-sources.ts`；`query-keys.ts` 新增 `industryNews`，删除 `intelligence`；删除 `tenant/intelligence.ts`、`admin/intelligence-sources.ts`。
- 导航：tenant `navigation.ts` 的「情报 → 情报中心」改为「行业动态 → 行业动态」（`/industry-news`，图标 `Newspaper`）；admin「情报源管理」改「动态源管理」（`/industry-news-sources`）。
- 管理端「AI 配置」页的场景选项列表移除 `intelligence_summary`（后端 `schemas/admin_config.py` 的校验集合不动）。

## 6. 遗留清理清单

| 层 | 删除 |
|---|---|
| 数据库 | `intelligence_article_publications`、`intelligence_subscriptions`、`intelligence_articles`（含分区）、`intelligence_sources`（独立 revision，见 §9） |
| 后端 | `services/intelligence_service.py`、`api/tenant/intelligence.py` 及 router 挂载、`admin/config.py` 五个 `intelligence-sources` 端点与 `admin_config_service` 对应方法、`schemas/admin_config.py` 的 `IntelligenceSource*` 模型、`api/internal/ops.py` 的 `/intelligence/articles/publish`、`db/partitions.py` 与 `scripts/maintain_partitions.py` 中的 `intelligence_articles` 条目、`tests/test_intelligence_article_serialization.py`；`ai_scene_defaults` 行与各 CHECK 枚举保留 |
| 前端 | tenant `intelligence/` 页与 `test/intelligence/`、admin `intelligence-sources/` 两文件、shared-api / shared-types 对应文件与类型、`queryKeys.intelligence` |
| 文档 | README 功能矩阵「情报源管理」「情报中心」两行改为行业动态；`.trellis/spec/backend/database-guidelines.md` 分区表清单去掉 `intelligence_articles`；`docs/database-schema.md` 随快照再生 |

## 7. 配置与部署

- 新依赖：`feedparser>=6.0`、`selectolax>=0.4`（均有 cp313 / 纯 Python wheel，镜像无需编译）。
- 新 Settings：`INDUSTRY_NEWS_FETCH_ENABLED`（默认 false）、`INDUSTRY_NEWS_FETCH_HOUR_BEIJING`（默认 8）。Instance A 的环境打开，B 保持关闭（B 无源即便打开也只是空转）。
- 上线顺序：合并 → 发布 backend（启动自动迁移建表）→ 在 A 实例容器内 `seed --instance default --dry-run` → 确认 → 执行 → 打开开关并重启（或等次日 08:00；也可用「立即抓取」）→ 发布两端前端镜像（A 实例必发；B 实例前端也要发，因为导航与页面已替换）。

## 8. 测试与验证

- 单测（`backend/tests/test_industry_news_*.py`）：三种解析器用 `tests/fixtures/industry_news/` 下裁剪的真实页面与 feed（不联网）；`normalize` 的规范化 URL / 标题 / 零宽字符 / 截断；service 用替身 conn 断言 SQL 片段与参数（窗口起点、行业、筛选数组、`unread_only`）；worker 的下次 08:00 计算与启动补跑（注入 clock）。
- Neon 开发库断言（`/db-verify` 三段式）：两条 UNIQUE 的同稿语义、90 天窗口边界、已读 LEFT JOIN 只对当前用户生效、`mark_read` 对不可见条目 404、启停后不抓取。
- 真站冒烟：`run_industry_news_fetch.py --from-file … --dry-run`，14 行每行 ≥1 条，PCB Update 标题规则按样本定稿。
- 前端 Vitest（tenant）：未读 / 已读样式、点击后乐观置已读并调用 `markRead`、空态两种文案、筛选参数透传。admin：type-check + build。
- 验收映射：AC1 → 租户页冒烟 + 已读测试；AC2 → 筛选与窗口断言；AC3 → 08:00 后观察 + 去重断言；AC4 → 管理端冒烟（改错地址、立即抓取、停用）；AC5 → B 实例租户空态；AC6 → 清理 revision + 门禁输出。

## 9. 实施切分（供 implement.md 展开）

两条 PR、两次发布，避免"删表与删代码不同步"：

1. **PR A · 新功能**：revision `20260824_0001` 建三表 + 抓取模块 + 调度 + CLI + 种子 + 两端 API 与页面 + 导航替换 + 新依赖 + 测试。遗留端点与页面此时保留但不再有导航入口。
2. **PR B · 遗留清理**：revision `20260824_0002` 删四表 + §6 全部代码与文档清理 + 重跑快照。

PR A 发布并完成种子导入与一次真实抓取后再合并 PR B。

## 10. 风险与未决

- PCB Update 的"段落全文作标题"可能把导语也带进来，dry-run 时如需改为"锚文本 + 同段落补全"，只动解析规则不动模型。
- electronica / productronica 的 JSON-LD 是 TYPO3 生成，改版风险高于 RSS；失败只体现在错误计数。
- 两个 UNIQUE 会把"标题完全相同的两条不同动态"判成同稿（如周期性同名公告）；已接受。
- 租户行业为空或不在别名表的租户看到空态；当前 4 个租户均可规范化为 PCB。
