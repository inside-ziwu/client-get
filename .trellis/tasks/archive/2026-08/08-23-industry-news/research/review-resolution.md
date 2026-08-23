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


## code-review（PR #97，high，8 视角 × 验证）→ 处置

| # | 发现 | 处置 |
|---|---|---|
| CR1 | PCB Update `href_exclude` 裸子串 `pcea` 误杀第三方新闻（fixture 实证 2 条） | 种子改为锚定自家链接；补测试断言 pcdandf `pcea-` 链接保留 |
| CR2 | `tenants` 行业查询缺 `instance_id`（红线） | SQL 加 `AND instance_id = :instance_id`，`resolve_tenant_industry` 增参数，三处调用同步 |
| CR3 | 列表 SQL 隔离谓词无测试（红线） | 新增 `test_list_sql_keeps_isolation_predicates_and_params` |
| CR4 | 非 UUID id → asyncpg DataError 500 | 路由层 `UUID` 类型（路径与 `source_id[]`）→ 422；补测试 |
| CR5 | 立即抓取跨进程持锁时谎报 triggered | 触发前短事务探测事务锁；后台结果写日志；补两条测试 |
| CR6 | markRead 失败静默 | `onError` 回滚 `clickedIds` + toast；补用例 |
| CR7 | 隐藏情报摘要场景后被引用模型删不掉 | 删模型失败 toast 显示后端原因；PR B 删除该场景默认模型行（design §6 / PRD R5 已改） |
| CR8 | 重定向后仍用种子 URL 作 urljoin 基址 | `_get_text` 返回最终 URL 作解析基址；补 301 测试；design §3.1 已改 |
| CR9 | CLI `--dry-run` 无语义 | `--once` / `--from-file` 互斥组，删 `--dry-run`；文档同步 |
| CR10 | 语种码表两份 + 封闭联合与 DB 口径不一致 | `@shared/ui` 统一 `industryNewsLangLabel`，`IndustryNewsLang` 改为开放 `string` |
| 未报 | 其余清理项（转发方法、三处手抄健康参数、`_list_params`、worker 无用参数）及驳回项 | `_get_text` 死代码随 CR8 清理；其余不扩大本 PR |
| 存量 | `tenant_messaging_service.py:73/115` 同类查询缺 `instance_id` | 登记 #98 |

## code-review（PR #101，high，8 视角 × 验证）→ 处置

| # | 发现 | 判定 | 处置 |
|---|---|---|---|
| CR-B1 | `AISceneDefaultUpdate.scene` Literal 仍接受 `intelligence_summary`，PUT 可把迁移刚删的默认行写回 | PLAUSIBLE | Literal 删该值；`tenant_query_service` 能力清单同名项一并删；测试断言该 scene 被 422；design §6 同步 |
| CR-B2 | 前端去掉过滤后发布错位时整份 PUT 回灌 | PLAUSIBLE | 由 CR-B1 的后端拒绝兜底（新后端 ⇒ 迁移已跑 ⇒ 无该行；旧后端接受亦无害），前端不再加过滤 |
| CR-B3 | 迁移测试手抄 47 列清单做 re.search，改坏 NOT NULL/类型照样绿；getsource 断言脆弱 | CONFIRMED | 删列清单，只留结构性断言；`init_instance` 场景清单提为 `AI_SCENE_SEEDS` 常量直接断言；新增本机 PostgreSQL 门控的往返 + 回滚用例（桩父表 + `ai_scene_defaults`，抽查 9 列类型/可空性），Docker `postgres:16` 实跑 11/11 |
| CR-B4 | 测试脚手架与 `test_drop_retired_collection_tables_migration.py` 逐行重复 | CONFIRMED | 抽到 `tests/migration_helpers.py` + conftest `postgres_schema` fixture，两份测试共用 |
| CR-B5 | README / spec / schema_notes 用墓碑句替代删段 | PLAUSIBLE | README:154/:169、domain-rules:20、database-guidelines:44、schema_notes:31 直接删句/括注 |
| CR-B6 | `schema_notes.md:30` 硬编码迁移计数 | PLAUSIBLE | 改为「head 以快照 alembic_version 为准」；README:201 同类过期计数一并改 |
| 驳回 | 两实例发布窗口（dashboard overview 无前端调用方；旧镜像重启即挂是串行换 tag 规则下所有带迁移发布的固有属性，docstring 已写）、快照再生时序（PR 正文与 implement.md 已明示）、docstring 过长（design §2 与 spec 明文要求） | REFUTED | 不改 |
