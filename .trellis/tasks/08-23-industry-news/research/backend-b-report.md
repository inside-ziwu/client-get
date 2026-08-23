# 后端 PR B 报告（B1 迁移 + B2 删除）

> 分支 `refactor/industry-news-legacy-cleanup`，主检出。只改 `backend/`；未 commit / stash / checkout；未触碰 `.env*`；全程只连 Neon 开发库（`get_settings()` 默认解析 `CLIENTGET_DEV_DATABASE_URL`，主机 `ep-bitter-lab-ap0zolyn-pooler.c-7.us-east-1.aws.neon.tech`，`CLIENTGET_PROD_DATABASE_URL` 从未读取）。

## 1. 改动文件

| 类型 | 文件 | 内容 |
|---|---|---|
| 新增 | `backend/alembic/versions/20260824_0002_drop_intelligence_tables.py` | B1 迁移：`down_revision="20260824_0001"`；upgrade `SET LOCAL` 两个超时 → `DELETE FROM ai_scene_defaults WHERE scene='intelligence_summary'` → 按 `publications → subscriptions → articles → sources` `DROP TABLE`（无 IF EXISTS / CASCADE）；downgrade 按快照重建四表结构 + `intelligence_articles_default` DEFAULT 分区；docstring 记生产实况、回退事实与 downgrade 不还原项 |
| 删除 | `backend/app/services/intelligence_service.py` | 整文件（394 行） |
| 删除 | `backend/app/api/tenant/intelligence.py` | 租户 `intelligence` 路由 |
| 删除 | `backend/tests/test_intelligence_article_serialization.py` | 序列化回归测试 |
| 修改 | `backend/app/api/tenant/router.py` | 去掉 `intelligence_router` 导入与挂载 |
| 修改 | `backend/app/api/admin/config.py` | 去掉三个情报源模型导入与五个 `/intelligence-sources*` 端点 |
| 修改 | `backend/app/services/admin_config_service.py` | 删六个情报源方法、`_serialize_intelligence_source`、dashboard overview 的 `total_articles` 子查询与输出键（-171 行） |
| 修改 | `backend/app/services/internal_ops_service.py` | 去掉 `IntelligenceService` 导入 / 属性与 `publish_article` |
| 修改 | `backend/app/api/internal/ops.py` | 去掉 `POST /intelligence/articles/publish` 端点 |
| 修改 | `backend/app/schemas/admin_config.py` | 删 `IntelligenceSourceCreate / BatchImport / Update` 三个模型；**保留** `AISceneDefaultUpdate.scene` Literal 里的 `intelligence_summary` |
| 修改 | `backend/app/db/partitions.py` | docstring 与 `_MANAGED` 去掉 `intelligence_articles → articles_p` |
| 修改 | `backend/scripts/seed_demo_data.py` | 去掉导入、`intelligence_service` 实例、`ensure_intelligence` 函数及其调用 |
| 修改 | `backend/scripts/init_instance.py` | `ai_scene_defaults` 种子场景列表去掉 `intelligence_summary` |
| 修改 | `backend/tests/test_admin_config.py` | 删 5 条 SMOKE_CASES、2 条必填字段用例、2 条第三批非法 payload 用例、1 条局部更新用例、`test_batch_import_passes_validated_items_to_service`；docstring 端点计数改为 **32**（main 上写 38，实际 SMOKE_CASES 为 37，本就漂移；现以 `router.routes` 实数为准，守护用例 `test_smoke_cases_cover_all_config_routes` 通过） |
| 修改 | `backend/tests/test_admin_instance_isolation.py` | 两处 dashboard mock 去掉 `total_articles` 键 |

未改：`backend/03_database/schema_snapshot.json`（已提交版本是生产 `--prod` 发布后同步，与开发库本就有大量无关差异；按 design §7 在发布 B 后 `--prod` 再生）。`backend/03_database/schema_docs.json` / `schema_notes.md` 工作区有改动，但那是 B4 工人的，不是我。

## 2. 验证输出

### 2.1 迁移往返（Neon 开发库）

迁移前只读核对：`alembic_version = 20260824_0001`；四表存在；行数 `intelligence_sources=2`、其余三表 0；`ai_scene_defaults` 有 `('default','intelligence_summary')` 1 行（开发库只有一个实例）；`intelligence_articles` 分区 `articles_p_2026_04..08` + `intelligence_articles_default`；三表各有 `set_updated_at` 触发器；`intelligence_sources` 有 2 条 RLS policy；四表之间唯一 FK `publications.subscription_id → subscriptions`，无外部表引用；无表 FK 引用 `ai_scene_defaults`。

**① `uv run python -m alembic upgrade head`**

```
Running upgrade 20260824_0001 -> 20260824_0002
alembic_version: ['20260824_0002']
information_schema.tables LIKE 'intelligence%': []
pg_class (r/p) LIKE 'intelligence%' OR 'articles_p%': []          ← 父表 + 5 个月分区 + DEFAULT 分区全部消失
ai_scene_defaults scenes: [('default','data_analysis'), ('default','email_generation'), ('default','scoring')]
```

结构快照对比（复用 `scripts/schema_snapshot.py::export_structure` 只读导出到 scratchpad，不写 docs）：迁移前 63 表 → 迁移后 59 表；`removed = [intelligence_article_publications, intelligence_articles, intelligence_sources, intelligence_subscriptions]`，`added = []`，`changed = []`，views / backup_tables 相等，`alembic_version` 0001 → 0002。**diff 恰好 = 四表 + alembic_version。**

**② `uv run python -m alembic downgrade -1`**

```
Running downgrade 20260824_0002 -> 20260824_0001
alembic_version: ['20260824_0001']
intelligence_sources:              columns=13 rows=0
intelligence_articles:             columns=15 rows=0   relkind='p'  RANGE (created_at)
intelligence_subscriptions:        columns=8  rows=0
intelligence_article_publications: columns=11 rows=0
partitions: [('intelligence_articles_default', 'DEFAULT')]
triggers: []   policies: []                                          ← 按 docstring 约定不还原
```

四表 downgrade 后的定义（列 / 主键 / 唯一 / 外键 / CHECK / 索引 / 分区键）与已提交的 `schema_snapshot.json`（生产）**逐字相等**；与开发库迁移前导出的唯一差异是 CHECK 表达式的文本写法（`ARRAY[('rss'::character varying)::text, …]` vs `(ARRAY['rss'::character varying, …])::text[]`），语义相同，源于开发库旧表的建表路径不同，与本迁移无关。

**③ `uv run python -m alembic upgrade head`**（再次）

```
Running upgrade 20260824_0001 -> 20260824_0002
alembic_version: ['20260824_0002']；intelligence* / articles_p* 关系：[]；ai_scene_defaults 无 intelligence_summary
```

开发库最终停在 `20260824_0002`。

### 2.2 测试与静态检查

- `uv run python -m pytest -q -p no:cacheprovider`：**478 passed, 5 skipped, 11 warnings**（全绿；用例数较 main 净减 21 条 = 删除的序列化测试 2 条 + `test_admin_config.py` 收集数 118 → 99 的 19 条参数化用例，`test_admin_instance_isolation.py` 收集数 19 不变）。
- ruff：新迁移文件 `ruff check` / `ruff format --check` 均干净；`schemas/admin_config.py`、`db/partitions.py`、`api/tenant/router.py`、`scripts/init_instance.py` 同样干净（`router.py` 在 main 上的 1 条 I001 随删除消失）。其余改动文件逐个与 `git show main:` 版本对比：**告警集合无新增**（config.py 49→42、admin_config_service.py 73→66、internal_ops_service.py 2→1、ops.py 17→13、seed_demo_data.py 30→27、test_admin_config.py 38→32、test_admin_instance_isolation.py 0→0），`ruff format --check` 不通过的文件在 main 上同样不通过（既有格式债，未整文件重排以免制造无关 diff）。
- `uv run python -c "import app.main"` → `import app.main OK`。

### 2.3 残留扫描

```
$ rg -n -i "intelligence" backend/app backend/scripts backend/tests --glob '!**/fixtures/**'
backend/app/services/tenant_query_service.py:1068:                    "feature": "intelligence_summary",
backend/app/schemas/admin_config.py:111:        "intelligence_summary",
```

恰好是约定保留的两处。`backend/tests/fixtures/industry_news/*.{xml,html}` 里另有 "Artificial Intelligence" / "market intelligence" 等第三方 feed 正文，非代码引用。`backend/alembic/` 下历史迁移（0421_0001/0002、0501_0010/0013）里的 `intelligence` 属迁移链历史，不动。

## 3. 保留项与理由

| 保留 | 理由 |
|---|---|
| `schemas/admin_config.py` `AISceneDefaultUpdate.scene` Literal 含 `intelligence_summary` | 任务书明确保留；与数据库 `ai_scene_defaults.scene` / `ai_usage_logs.usage_type` CHECK 枚举一致，枚举不动 |
| `tenant_query_service.py:1068` 能力清单项 `intelligence_summary` | 任务书明确保留 |
| 通知分类枚举 `intelligence`、各 CHECK 枚举 | 设计 §6 保留 |
| `scripts/maintain_partitions.py` | 本就没有 `intelligence_articles` 条目 |
| 历史迁移文件中的 `intelligence` 引用 | 迁移链历史，不可改 |

## 4. 疑点 / 留给协调者

1. **生产执行前**：按 implement.md B1 用 `--prod` 只读核对四表行数（预期 0 / 0 / 0 / 2）与 `ai_scene_defaults` 的 `intelligence_summary` 行数（预期 2，两实例各一）；docstring 已按任务书记录 Hermes / vzkoo 两行。
2. **滚动发布窗口**：删表迁移在新 Pod 启动时执行；旧 Pod 的 `GET /admin/api/v1/dashboard/overview` 仍查 `intelligence_articles`，在新旧 Pod 并存的几十秒内旧 Pod 该端点会 500，新 Pod 接管后恢复。`lock_timeout=5s` 下若旧 Pod 恰有查询持 ACCESS SHARE 锁，迁移会失败并阻断启动——count(*) 零行表瞬时完成，概率极低，但若发生重启一次即可。
3. **不可回退**：落地后旧镜像（含旧 `partitions.py`）启动即崩，已写入迁移 docstring；合并 B 前确认 A 稳定。
4. `schema_snapshot.json` 未更新（见 §1 说明），发布后 `scripts/schema_snapshot.py --prod` 再生并连同 docs 提交。
5. `test_admin_config.py` docstring 的端点计数从 main 的 38（实为 37）改为真实值 32，顺手修正了既有漂移；若希望保持"只减不改"可改回 33（38-5）。
