# 评审发现 → 处置对照（2026-08-23）

来源：`design-review-data-model.md`、`design-review-backend.md`、`design-review-frontend.md`（三个只读核证子代理，含 Neon / 生产只读实查）。Codex 独立评审另见 `design-review-codex.md`（如有）。

## 必改（已落入 design v2 / implement v2）

| # | 发现 | 处置 |
|---|---|---|
| D1 | "遗留四表生产 0 行"不成立：`intelligence_sources` 2 行 | B1 docstring 记录两行后删；implement §2 核对口径改 0/0/0/2 |
| D2 | `(instance_id, fetched_at DESC)` 不能服务 `COALESCE` 排序 | design §2 改口径：索引管过滤，排序内存 top-N |
| D3 | `schema.sql` 被 0001 迁移直接执行、最近两次删表未同步、#61 ④ 将改生成物 | 不动 `schema.sql`；契约只看 `schema_snapshot.json` |
| D4 | 快照不采集触发器；DDL 未写 `CREATE TRIGGER` | design §2 补触发器 DDL；A1 加 `pg_trigger` 验证 |
| D5 | A1 缺 `down_revision` / docstring / `SET LOCAL` | A1 补齐；`down_revision="20260723_0003"` |
| D6 | downgrade 仅能按快照还原结构（无触发器 / RLS / 分区） | B1 注明并重建 DEFAULT 分区 |
| D7 | `maintain_partitions.py` 无 `intelligence_articles` 条目 | design §6 / B2 纠正；spec `database-guidelines.md:44` 列入 A13 修正 |
| D8 | PR B 后镜像不可回退（旧 `partitions.py` 启动即崩） | design §7 与 implement §2 写明"只能前向修复" |
| D9 | `industry_news_reads.user_id` 无 CASCADE 会阻塞物理删用户 | DDL 加 `ON DELETE CASCADE` |
| B1 | 事务级锁与每源独立事务互斥 | `run_once` 改专用连接会话级锁（AUTOCOMMIT + finally unlock / invalidate）；spec workers.md 列入 A13 修正 |
| B2 | asyncpg 重复命名参数 `AmbiguousParameterError` | SQL 全部 `CAST(:p AS text[] / uuid[] / text)` |
| B3 | `IntegrityError` 视为同稿会让事务 aborted | 改 `INSERT … ON CONFLICT DO NOTHING` + `rowcount` |
| B4 | "JOIN tenants 取行业"与 `:industry` 参数矛盾 | service 开头单独查 `tenants.industry` 再归一 |
| B5 | 清理清单漏 `internal_ops_service.py`（API 启动即崩）、`admin_config_service.py:1463`（dashboard 500）、`seed_demo_data.py`、`test_admin_config.py` 用例、方法行号范围 | design §6 / B2 全部补齐 |
| B6 | 后台任务引用防 GC、`ASGITransport` 无 lifespan | `trigger_fetch` + `_background_tasks`；测试 patch |
| B7 | `paginated_response` 需显式传 `has_more` | route 传 `page*page_size < total` |
| F1 | FilterBar 无布尔 kind | 「只看未读」用 `custom` 渲染 Switch，draft `'' \| '1'` |
| F2 | TableState 空态文案不可定制 | `has_sources=false` 在表外渲染说明块；筛选空态用真实文案 |
| F3 | Pagination 真实签名；需 `keepPreviousData` | design §5.1 按真实 props 重写 |
| F4 | 无 `window.open` 先例 | 标题用 `<a target="_blank" rel="noopener noreferrer">` |
| F5 | 乐观更新与"不手改缓存"冲突 | 页面本地 `clickedIds`；markRead 不 invalidate 列表 |
| F6 | admin 预取 key 只能字面量 | design §5.2 写明；spec quality-guidelines.md:38 列入 A13 修正 |
| F7 | `rg intelligence frontend` 不可能为空（enums 三处） | B3 门禁口径改为排除 `enums.ts` |
| F8 | 列宽 token spec 漂移（实际 64/96/144） | A13 修正 component-guidelines / design-system |
| F9 | PR B 前端与 spec 引用清单 | design §6 行级补全 |

## 未采纳 / 记录

- 数据模型核证建议的 `uq_…` 命名：已采纳（显式 `CONSTRAINT uq_…`）。
- 前端核证提出的「只看未读 + 点击已读」组合：采用"markRead 不 invalidate、行保持可见为已读态，下一次取数自然消失"，待用户确认。
- 表达式索引方案：暂不采用（量级不需要）。

## Codex 独立评审（`design-review-codex.md`）→ 处置

| # | 发现 | 处置 |
|---|---|---|
| C1 | implement 仍是核证前文本 | 已由 v2 解决（Codex 拿到的是 v1 快照） |
| C2 | 首轮把站点历史灌进未读；AC3 与排序键混用 | 入库过滤：`published_at` 早于 90 天不入库；一轮共用 `run_at` 作 `fetched_at`，排序 `fetched_at DESC, COALESCE(...) DESC`，AC3 字面成立；PRD R1/R3/AC3 改写 |
| C3 | 停用源与空态口径打架 | 停用即隐藏：列表与筛选都只看启用源；PRD R1/AC4 改写 |
| C4 | 种子按 URL upsert 改地址会生成新行 | 源加稳定 `code`，UNIQUE `(instance_id, code)`，种子按 code upsert、地址可变；AC4 改为开发库坏 `parse_config` 验证 |
| C5 | 启动补跑补不了"跑失败" | 删除启动补跑；错过的轮次靠「立即抓取」 |
| C6 | 「立即抓取」会撒谎；同步解析卡事件循环 | 返回 `triggered/reason`（in_progress / no_sources）并按 reason 提示；解析放 `asyncio.to_thread`；30 秒后再 invalidate |
| C7 | 真站可达 ≠ Sealos 出口可达 | 真站冒烟改为信息性；合并门槛只看 fixture；上线后在 A 容器内 dry-run |
| C8 | B 管理端空列表像故障；seed 不拦 instance_b | admin 空列表说明块；seed 非 default 需 `--confirm-instance` |
| C9 | 同稿去重后按落选源筛选看不到 | AC2 写明按保留源筛选、不按 14 源条数对账 |
| C10 | 只看未读 + 点击 | 与用户已确认口径一致（行保持可见至下次取数） |
| 简化 | 删补跑 / 锁改单事务 + savepoint（方案 C）/ 管理端 `success_response` / 不上 tenacity / 保留两 UNIQUE + ON CONFLICT / 保留 `/filters` / 不改 FilterBar、TableState | 全部采纳 |
| 不同意 | 会话级锁无先例 → 采纳改方案 C；RSS 自动发现须显式删除 → PRD R3 已明确；A8 真站不作合并门槛 → 采纳；AC3 时间键 → 以 run_at 排序解决 |
