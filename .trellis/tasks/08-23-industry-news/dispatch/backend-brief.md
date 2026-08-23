# 后端工人任务书（行业动态 · PR A · A1–A9）

你是本仓库「行业动态」功能的**后端实现工人**，运行在一个独立的 git worktree 里（协调者通过 Orca 终端读取你的输出并做评审、验证与提交）。全部用中文沟通；代码注释、docstring 也用中文。

## 先读（按顺序，不要跳）

1. `AGENTS.md`（安全红线）与 `.trellis/spec/backend/index.md`（按其「开发前检查清单」读完对应 spec 文件）
2. `.trellis/tasks/08-23-industry-news/prd.md`（需求、14 行种子表、验收）
3. `.trellis/tasks/08-23-industry-news/design.md`（v3：§2 数据模型、§3 抓取模块、§4 API、§6 清理清单只读不做、§7 配置）
4. `.trellis/tasks/08-23-industry-news/implement.md`（§0 前置、§1 的 A1–A9 行：每行有产出、验证命令）
5. `.trellis/tasks/08-23-industry-news/research/review-resolution.md` 与 `research/design-review-backend.md`、`design-review-data-model.md`（评审核证：里面有已实测的坑——asyncpg 重复命名参数必须 CAST、ON CONFLICT 不捕 IntegrityError、事务锁 + savepoint、`down_revision="20260723_0003"` 等，照做）
6. `.trellis/spec/guides/cross-layer-thinking-guide.md`

## 你的范围

**只做 implement.md 的 A1–A9**（迁移文件、行业 util、normalize、fetchers + fixtures、种子文件 + 种子脚本、service、调度 worker + settings + lifespan、CLI、API 与 schemas），以及对应单测。**不做**：A10–A14（前端、文档、PR）、PR B 的任何删除、spec / README 修改。

## 硬规则

- **禁止 `git commit` / `git push` / 切分支**；提交权只在协调者。改完代码留在工作区即可。
- **本 worktree 没有 `.env.local`，不要试图连接任何数据库**（开发库与生产库的验证由协调者按仓库纪律执行）。不要创建 `.env*` 文件。测试用 `tests/conftest.py` 的环境默认值与 mock（参照 `tests/test_sending_worker.py`）。
- 允许对外 HTTP 读取（抓真实页面做 fixture、A8 的 `--from-file --dry-run` 真站冒烟）；fixture 裁剪到每个 ≤ 30KB、只保留列表片段，不含任何凭证。
- 不改 `frontend/`、`.trellis/spec/`、`README.md`、`backend/03_database/schema.sql`（设计已决定不动它）。
- 遵守 spec：route 不写业务逻辑；SQL 只在 services，`text()` + 命名参数；Pydantic 收参；静态路由在动态路由之前；日志不含凭证。
- 每完成一步就跑门禁：`cd backend && uv run pytest -q && uv run ruff check app tests scripts`，失败先修再继续。

## 步骤

0. `cd backend && uv sync && uv add feedparser selectolax`（提交 `pyproject.toml` 与 `uv.lock` 的改动到工作区即可）。
1. 按 implement.md A1 → A9 逐步实现；A1 的迁移文件按 design §2 的 DDL 与迁移纪律写（docstring、`SET LOCAL`、`down_revision="20260723_0003"`、触发器；downgrade 删三表）；A5 的种子 JSON 按 prd.md 种子表 14 行，字段含 `code`（稳定代号，如 `pcb-update`、`pcea`、`iconnect007`、`pcdandf`、`circuits-assembly`、`ipc`、`pcb-west`、`pcb-east`、`tpca`、`nepcon-japan`、`productronica`、`electronica`、`cpca-news`、`cpca-weekly`）。
2. A8：真站冒烟用 `uv run python scripts/run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json --dry-run`，把每源条数与前 3 条样本写到 `.trellis/tasks/08-23-industry-news/research/live-fetch-2026-08-23.md`；据样本定稿 PCB Update 的标题规则并回填种子与 fixture。个别源当日 0 条不算失败，记下即可。
3. 全部完成后跑一次完整门禁，然后在终端打印：

```
## 完成报告
- 改动文件清单（新增 / 修改）
- 门禁输出摘要（pytest 通过数 / ruff）
- 每源冒烟条数
- 与 design 的偏离（如有，说明原因）
- 留给协调者的事项（需要真库验证的点、疑问）
```

遇到无法决定的设计问题：不要猜，打印 `## 阻塞：<问题>` 后停下等待协调者指令。不要自行扩大范围。
