# 后端完成报告（行业动态 · PR A · A1–A9）

> 工人：Grok 4.6（Codex）  
> 日期：2026-08-23  
> 范围：implement.md A1–A9。未做 A10–A14、PR B、spec / README。未 git commit / push。本 worktree 未连接任何数据库。

## 改动文件清单

### 新增

- `backend/alembic/versions/20260824_0001_industry_news.py`（`down_revision="20260723_0003"`，三表 + 命名约束 + 索引 + `set_updated_at` 触发器；downgrade 按 reads → items → sources 删表）
- `backend/app/utils/industry.py`（`INDUSTRY_ALIASES` / `canonical_industry` / `PCB_INDUSTRY_ALIASES`）
- `backend/app/services/industry_news/__init__.py`
- `backend/app/services/industry_news/normalize.py`
- `backend/app/services/industry_news/fetchers.py`
- `backend/app/services/industry_news/service.py`
- `backend/app/data/industry_news_sources_pcb.json`（14 行，稳定 `code`：pcb-update / pcea / iconnect007 / pcdandf / circuits-assembly / ipc / pcb-west / pcb-east / tpca / nepcon-japan / productronica / electronica / cpca-news / cpca-weekly）
- `backend/scripts/seed_industry_news_sources.py`
- `backend/scripts/run_industry_news_fetch.py`
- `backend/app/workers/industry_news_fetch.py`
- `backend/app/schemas/industry_news.py`
- `backend/app/api/tenant/industry_news.py`
- `backend/app/api/admin/industry_news_sources.py`
- `backend/tests/fixtures/industry_news/`（14 份裁剪样本，均 ≤ 30KB）
- `backend/tests/test_industry.py`
- `backend/tests/test_industry_news_normalize.py`
- `backend/tests/test_industry_news_fetchers.py`
- `backend/tests/test_industry_news_service.py`
- `backend/tests/test_industry_news_worker.py`
- `backend/tests/test_industry_news_routes.py`
- `backend/tests/test_industry_news_seed.py`
- `.trellis/tasks/08-23-industry-news/research/live-fetch-2026-08-23.md`

### 修改

- `backend/pyproject.toml`、`backend/uv.lock`（`feedparser>=6.0.14`、`selectolax>=0.4.11`）
- `backend/03_database/schema_docs.json`（新增「行业动态」域与三表说明）
- `backend/app/core/config.py`（`INDUSTRY_NEWS_FETCH_ENABLED` 默认 false、`INDUSTRY_NEWS_FETCH_HOUR_BEIJING` 默认 8）
- `backend/app/main.py`（lifespan 四步挂载抓取循环）
- `backend/app/utils/beijing_time.py`（`next_beijing_time`）
- `backend/app/workers/wmt_lineage_repair.py`（行业别名改为从 `app.utils.industry` 导入，保留 `_PCB_INDUSTRY_ALIASES` 名）
- `backend/app/api/tenant/router.py`、`backend/app/api/admin/router.py`（挂载新路由）

### 明确未改

- `frontend/`、`.trellis/spec/`、`README.md`、`backend/03_database/schema.sql`
- 未创建 `.env*`，未连接开发库 / 生产库

## 门禁输出摘要

在 `backend/`：

```
uv run pytest -q
479 passed, 5 skipped, 11 warnings in 12.27s
```

新增与本次改动文件的 `ruff check`：**通过**。

全仓 `uv run ruff check app tests scripts` 在 **main 上即有约 916 条存量告警**（以 FastAPI `Depends` / `Query` 的 B008、以及历史 E501 为主）。本次增量未往新文件引入告警；全仓对比约 916 → 917 的那条是 `admin/router.py` 的 import 排序，已用 ruff --fix 收回。

## 每源冒烟条数

命令（不连库）：

```
uv run python scripts/run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json --dry-run
```

出口：开发机本地网络，非 Sealos 生产出口。详细样本见 `research/live-fetch-2026-08-23.md`。

| 代号 | 名称 | 条数 |
|---|---|---:|
| pcb-update | PCB Update | 23 |
| pcea | PCEA | 10 |
| iconnect007 | I-Connect007 | 46 |
| pcdandf | PCD&F | 12 |
| circuits-assembly | Circuits Assembly | 12 |
| ipc | IPC | 10 |
| pcb-west | PCB West | 10 |
| pcb-east | PCB East | 8 |
| tpca | TPCA | 8 |
| nepcon-japan | NEPCON JAPAN | 5 |
| productronica | Productronica | 9 |
| electronica | electronica | 8 |
| cpca-news | CPCA 协会动态 | 6 |
| cpca-weekly | CPCA 每周资讯 | 6 |

14 源全部解析出 ≥1 条，无当日 0 条。

PCB Update 标题按段落全文定稿（含导语，不是锚文本），种子保持 `title_from: parent` + `href_exclude: pcbupdate\.com|pcea|mediakit`。

## 与 design 的偏离

1. **路由收参写法**：租户 / 管理端用 `Annotated[..., Depends/Query]`，避开 ruff B008；语义与 design 的 `Query(alias="category[]")`、静态 `/fetch` 在 `/{source_id}` 之前一致。
2. **`trigger_fetch` 签名**：`trigger_fetch(engine=None, *, instance_id)`。路由不在请求里调用 `get_engine()`（ASGITransport 无 lifespan 会炸），后台任务内部仍用 `get_engine()` 开新连接，不复用 `context.connection`。
3. **种子 `--dry-run`**：仍会连库做 created / updated / unchanged 分类，但不写入行（空事务提交）。工人环境无 `.env.local`，未在此执行。
4. **未跑 Neon**：A1 迁移往返、`schema_snapshot.py`、A5 种子幂等、A6 去重 / 窗口 / 锁 / savepoint 的真库断言，均留给协调者（任务书禁止本 worktree 连库）。
5. **未改 `schema.sql`**：按 design §2 / 评审核证，结构契约只看 `schema_snapshot.json`（快照本身也留给协调者在 Neon upgrade 后生成）。

## 留给协调者的事项

1. **Neon 迁移**：`uv run alembic upgrade head` → `SELECT tgname FROM pg_trigger WHERE tgrelid='industry_news_sources'::regclass` 含 `set_updated_at` → `uv run python scripts/schema_snapshot.py`（**只提交 JSON**，diff = 三表 + `alembic_version` 一行）→ `alembic downgrade -1` 再 `upgrade head` 往返。
2. **种子幂等**（`--instance dev-seed-test --confirm-instance dev-seed-test`）：dry-run 14 新增 → 执行 count=14 → 再执行 0 新增 14 不变 → 改一行 url/类别再执行 1 更新且 `is_active` 不变 → 不带 `--confirm-instance` 拒绝写入 → `DELETE … WHERE instance_id='dev-seed-test'` 清理。
3. **A6 真库三段式**（事务内断言后 ROLLBACK）：同稿（canonical_url / dedup_key 各插一次 `rowcount` 0）、`CAST` 数组参数传 None 与 list、90 天窗口 89/91 天、已读只对当前用户生效、`mark_read` 不可见 404、停用源动态不再出现且不被抓取、坏 `parse_config` savepoint 隔离（计数 +1、其余源入库）、两连接事务锁互斥。
4. **发布侧**：生产种子导入与 `INDUSTRY_NEWS_FETCH_ENABLED=true` 仍按 implement 发布清单，需用户逐次确认；上线后在 A 容器内再跑一次 `--from-file … --dry-run` 核出口可达。
5. **全仓 ruff 存量告警**（约 916 条 B008/E501）是否另开任务清理——本次未动。
