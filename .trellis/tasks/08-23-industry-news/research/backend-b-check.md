# PR B 后端复审（B1 迁移 + B2 删除）

- **对象**：分支 `refactor/industry-news-legacy-cleanup` 工作区的 `backend/` 改动（未提交；`git diff -- backend` 16 文件 + 新增迁移），实现者报告 `backend-b-report.md`
- **依据**：design.md §2 / §6、implement.md §2 B1 / B2、spec `backend/{database,quality,api}-guidelines.md`
- **日期**：2026-08-23
- **约束遵守**：未 commit / stash / checkout；未动 `.env*`；只连 Neon 开发库（`load_db_url("CLIENTGET_DEV_DATABASE_URL")`，主机 `…neon.tech`，脚本内 `assert "neon.tech" in host`），`CLIENTGET_PROD_DATABASE_URL` 从未读取

## 1. 迁移 `20260824_0002_drop_intelligence_tables.py`

| 核对项 | 结论 |
|---|---|
| 与 `20260723_0003` 先例写法一致 | **通过**。docstring 同样写 revision / down_revision / 考证；`conn = op.get_bind()` + 两句 `SET LOCAL` 开头；`DROP TABLE public.<t>` 不带 `IF EXISTS` / `CASCADE`，注释同句；downgrade 注明"定义取自快照"。多出的部分：upgrade 先 `DELETE FROM ai_scene_defaults WHERE scene='intelligence_summary'`（design §6 / PRD R5 明确要求）；downgrade 也带 `SET LOCAL`（先例没有，无害） |
| `down_revision` | **通过**。`"20260824_0001"`；`alembic heads` 单 head = `20260824_0002` |
| upgrade 顺序与 FK 方向 | **通过**。`publications → subscriptions → articles → sources`；快照 `pg_constraint` 核对：四表间唯一 FK `publications.subscription_id → subscriptions`，无外部表 FK 指向四表，也无表 FK 指向 `ai_scene_defaults`；无视图引用 |
| downgrade 四表定义 vs `schema_snapshot.json` | **通过（逐项相等）**。在 Neon 开发库独立执行 `alembic downgrade -1`，用 `scripts/schema_snapshot.py::export_structure` 只读导出，按 kind / partition_key / columns（名、类型、默认值、NOT NULL、顺序）/ constraints（名、类型、定义）/ indexes（名、定义）与已提交快照逐项比较：四表 **全部 EQUAL**（CHECK 仅 `ARRAY[('a'::varchar)::text]` 与 `(ARRAY['a'::varchar])::text[]` 的等价写法差异，已归一后比较）。约束名由 PG 默认规则生成，与快照一致（`<t>_<col>_check` / `_fkey` / `_pkey` / `<t>_tenant_id_article_id_key`）；`intelligence_articles` 为 `PARTITION BY RANGE (created_at)` 且重建了 `intelligence_articles_default`；downgrade 后 triggers / policies 为空（与 docstring 约定一致）。随后 `alembic upgrade head` 回到 `20260824_0002`，开发库终态 59 表、无 `intelligence*` / `articles_p*` 关系、`ai_scene_defaults` 无 `intelligence_summary` 行 |
| `SET LOCAL` 在 alembic 事务内是否有效 | **有效**。`alembic/env.py` 在线模式 `connectable.connect()` → `context.begin_transaction()` → `run_migrations()`；PostgreSQL impl `transactional_ddl=True`（日志 `Will assume transactional DDL`），整次 `upgrade` 在一个事务内，`SET LOCAL` 作用到事务末尾；与 `20260723_0003`、`20260824_0001` 同一路径 |
| 枚举与 CHECK 不动 | **通过**。迁移不触碰 `ai_scene_defaults_scene_check`、`ai_usage_logs_usage_type_check`、`notifications_category_check`（开发库迁移后三者仍在） |

## 2. 删除彻底且不过度

| 核对项 | 结论 |
|---|---|
| `rg -n -i "intelligence" backend/app backend/scripts backend/tests --glob '!**/fixtures/**'` | 只剩 `schemas/admin_config.py:111`（scene Literal）与 `tenant_query_service.py:1068`（能力清单项）——与约定保留项一致 |
| `rg -n "total_articles\|publish_article\|ensure_intelligence\|IntelligenceSource"`（全仓，排除 node_modules / alembic 历史 / docs / 快照） | 为空 |
| `app/db/partitions.py::_MANAGED` | 只剩 `audit_logs` / `emails`（docstring 同步） |
| `scripts/init_instance.py` | scenes = `["scoring", "email_generation", "data_analysis"]`；`tests/test_init_instance.py` 不受影响 |
| dashboard overview | `admin_config_service.get_platform_dashboard` 删掉 `total_articles` 子查询与输出键后 SQL 语法正确：在 Neon 开发库（已无 `intelligence_articles`）直接执行同文本 SQL 返回 4 列；`tests/test_admin_instance_isolation.py::TestPlatformDashboardInstanceId` 两处 mock 同步去键，通过。前端无消费方（`rg total_articles frontend` 为空；`dashboard/overview` 仅租户端另一个端点） |
| 其他配置 / 文档残留 | `backend/.env.example`、`Dockerfile`、`pyproject.toml`、`app/data/` 无 `intelligence`；`app/security/internal.py` 无 `intelligence:publish` scope 硬编码；`notifications` 表在 app / scripts 中已无 INSERT 写入方（`schema_docs.json` 改成"当前无写入路径"属实） |
| `test_admin_config.py` docstring 计数 | 32 = `config.router` 实际路由数 = `SMOKE_CASES` 条数（守护用例 `test_smoke_cases_cover_all_config_routes` 通过）；main 上的 38 本就与实际 37 不符，改为真实值合理 |

## 3. 逐 hunk 核对是否误删

16 个文件的每个 hunk 均只涉及情报模块：`config.py`（3 个 import + 5 端点）、`ops.py`（1 端点）、`tenant/router.py`（1 import + 1 include）、`partitions.py`（docstring + `_MANAGED` 条目）、`schemas/admin_config.py`（3 模型，`AISceneDefaultUpdate.scene` Literal 保留）、`admin_config_service.py`（6 方法 + `_serialize_intelligence_source` + dashboard 子查询 / 输出键）、`internal_ops_service.py`（import / 属性 / `publish_article`，`AppError` 仍在用）、`init_instance.py`（场景列表 1 项）、`seed_demo_data.py`（import / 实例 / 函数 / 调用）、两个测试文件（只删情报用例与 `total_articles` 键）、删除 3 个文件。`schema_docs.json` 删「行业情报」域与四表说明、`schema_notes.md` 删四处注记并改写 partitions 行，JSON 仍合法（domains 9 个、tables 61 张 = 发布 B 后生产预期表数）。通知分类枚举、`ai_usage_logs.usage_type` 枚举、各 CHECK 约束、`tenant_query_service` 能力项均未动。

## 4. 门禁

| 命令 | 结果 |
|---|---|
| `uv run python -m pytest -q -p no:cacheprovider` | **481 passed, 5 skipped**（实现者报告 478 + 本次新增 3 条） |
| `uv run python -m ruff check <改动文件>` | 逐文件与 `git show main:` 版本比对告警码多重集：**无新增**（`ops.py` 16→13、`config.py` 48→42、`tenant/router.py` 1→0、`admin_config_service.py` 72→66、`internal_ops_service.py` 2→1、`seed_demo_data.py` 30→27、`test_admin_config.py` 37→32，其余 0→0 / 8→8）；新迁移文件与新测试文件 `ruff check` + `ruff format --check` 干净 |
| `uv run python -c "import app.main"` | OK |
| `uv run python -m py_compile scripts/seed_demo_data.py scripts/init_instance.py` + `import scripts.seed_demo_data` | OK |
| `alembic heads` | 单 head `20260824_0002` |

## 5. 复审修正（本次直接改）

1. **新增 `backend/tests/test_drop_intelligence_tables_migration.py`**（3 条，纯 mock 不连库）：spec `quality-guidelines.md`「迁移测试：对破坏性迁移写原子回滚用例」在本 PR 没有落地，补上与 `test_drop_retired_collection_tables_migration.py` 同手法的契约锁定——① upgrade 语句序列：`SET LOCAL` ×2 → `DELETE ai_scene_defaults` → 四表严格顺序 `DROP TABLE`，全程无 `IF EXISTS` / `CASCADE`；② downgrade 建表顺序（`sources → articles → DEFAULT 分区 → subscriptions → publications`）、每表列名与 FK 目标（固化自 2026-08-23 快照，**不读 `schema_snapshot.json`**，避免发布 B 后快照再生删掉四表时用例 KeyError）、分区键、UNIQUE、索引，且不含 TRIGGER / POLICY；③ 运行时退役锁定：`partitions._MANAGED == [audit_logs, emails]`、`init_instance.main` 源码不含 `intelligence_summary`。
2. **`backend/03_database/schema_notes.md:30`**：`alembic/versions/` 计数 "70 个迁移" 改为 "74 个迁移，截至 20260824_0002"（main 上已漂移，B4 恰好改了同一行，顺手对齐实况：`ls alembic/versions/*.py` 去 `__init__` = 74）。

## 6. 未修 / 留给协调者

1. **`schema_snapshot.json` 不随 PR B 更新**：已提交快照是 PR A 发布后 `--prod` 再生（65 表、`20260824_0001`），开发库与之本有无关差异；按 design §7 与 f2ac2f9 先例，发布 B 后 `schema_snapshot.py --prod` 再生并连同 `docs/database-schema.md` / `.dbml` 提交。需协调者确认沿用该顺序。
2. **生产执行前的只读核对**（implement B1）：四表行数预期 0 / 0 / 0 / 2，`ai_scene_defaults` 的 `intelligence_summary` 预期 2 行（两实例各一）——docstring 的"生产实况"段据此写成，本次复审按约束未连生产库复核，请在发布前走 `/db-verify` 只读确认。
3. **滚动发布窗口**：新 Pod 启动跑迁移删表期间，旧 Pod 的 `GET /admin/api/v1/dashboard/overview` 会 500 几十秒；`lock_timeout=5s` 下若旧 Pod 恰好持有 `intelligence_articles` 的 ACCESS SHARE 锁，迁移失败会阻断新 Pod 启动（重启即可）。概率极低，知情即可。
4. **不可回退**：B 落地后旧镜像（含旧 `partitions.py`）启动即崩，只能前向修复——已写入迁移 docstring 与 design §7，发布前确认 A 已稳定。
5. `test_admin_config.py` docstring 计数改为 32（而非 38−5=33）：以实际路由数为准更准确，若协调者坚持"只减不改"可改回。
