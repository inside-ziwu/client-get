# 数据库约定

> 事实来源：`app/db/`、`app/security/dependencies.py`、alembic 迁移链、`backend/03_database/`、`scripts/schema_snapshot.py`，以及历史事故记录（`docs/solutions/`，已冻结为档案）。安全红线（生产默认只读）以 [AGENTS.md](../../../AGENTS.md) §1 为准，本文只写怎么做。

## 访问方式

- 连接来自 `app/db/pools.py`：单 `AsyncEngine`（asyncpg，`pool_pre_ping`），`get_connection()` 用 `engine.begin()` 产出 **一请求一事务** 的 `AsyncConnection`；worker 自己 `async with engine.begin() as conn`。
- SQL 一律 `text("""...""")` + 命名参数 `:name`；取行用 `result.mappings().first() / .all()`，标量用 `conn.scalar()`。无 ORM 实体、alembic `env.py` 的 `target_metadata = None`，不要引入 ORM。
- JSON 列写入：Python 端 `json.dumps(..., ensure_ascii=False)`，SQL 端 `CAST(:value AS jsonb)`；类型转换用 `CAST(:p AS uuid)`，**不要写 `:p::uuid`**（asyncpg 会把 `::` 后面的参数整个跳过，报 `syntax error at or near ":"`）。
- 迁移里直接 `op.get_bind().exec_driver_sql(...)`（psycopg 同步连接，`SYNC_DATABASE_URL`）。

## 隔离过滤（红线的实施细则）

| 表类型 | 例子 | 过滤条件 |
|---|---|---|
| 租户业务表 | `tenant_companies`、`tenant_contacts`、`sending_plans`、`emails`、`groups`、`email_templates` | `WHERE tenant_id = :tenant_id` |
| 平台级表 | `tenants`、`platform_users`、`ai_models`、`ai_scene_defaults` | `WHERE instance_id = :instance_id`（`get_settings().instance_id`） |
| 两类字段兼有 | `ai_usage_logs` 等 | 两个都带 |
| 公池共享层 | `waimaotong_clean_*` | 跨实例共享，读不过滤；与租户的关系通过 `tenant_companies` 按实例隔离 |

- 参照：`tenant_query_service.py` 每个子查询都显式 `WHERE tenant_id = :tenant_id`；`security/dependencies.py` 查 `platform_users` 带 `instance_id`。
- 现状要如实理解：RLS policy 已定义约 20 张表，但 **FORCE ROW LEVEL SECURITY 从未启用**，应用使用单一连接角色；`set_current_tenant()` 写的 `app.current_tenant_id` 只是名义配合。**不得以"有 RLS"为由省略应用层过滤**（#43 是登记的加固项）。
- 改动隔离相关代码必须保留或新增隔离测试：`tests/test_admin_instance_isolation.py`、`test_auth_instance_isolation.py`、`test_worker_instance_isolation.py`、`test_*_no_visibility.py` 是现成样板。
- 租户看不到的资源返回 404（"不存在或无权"），不要 403 泄露存在性。

## 数据模型事实

- `backend/03_database/schema.sql` 是手工蓝图，已知与生产漂移（#61「Schema 主权收复」、#64「空库无法从 Alembic 基线建库」），**不得单独作为实施依据**；事实以 alembic 迁移链 + 生产核对为准。#61 ④ 的 pg_dump 化落地后 schema.sql 转为生成物，届时禁止手改。
- 结构契约：`backend/03_database/schema_snapshot.json` 由 `uv run python scripts/schema_snapshot.py`（默认连开发库；`--prod` 连生产，强制只读）生成，同时产出 `docs/database-schema.md`（人读）与 `.dbml`。**迁移合并后重跑，`git diff` 应恰好等于迁移内容**；多出来的差异 = 有人带外改库。业务语义在 `schema_docs.json` / `schema_notes.md` 人工维护。
- `waimaotong_*` 等外部直写表的 schema 主权不在本仓库：对其结构、数据或关联 FK 的任何变更，先与用户确认。
- 核心表族谱：身份（platform_users / tenants / users / user_roles）→ 外部原始层（waimaotong_ / tendata_ / lixiaoyun_raw_*）→ 外部清洗共享层（waimaotong_clean_* / lixiaoyun_api_clean_*）→ 租户业务层（tenant_companies / tenant_contacts / company_scores / groups）→ 外联层（sending_plans / sequence_enrollments / emails / email_events / email_templates）→ 域名预热（domain_warmup_* / domain_daily_usage / work_rule_sets / countries）→ 支撑（notifications / audit_logs / ai_usage_logs）。逐表说明见 `docs/database-schema.md`。

## 迁移纪律

- **每次 schema 变更一个 alembic revision**，文件名 `YYYYMMDD_NNNN_描述.py`，docstring 写 revision / down_revision / 考证与拍板依据（参照 `20260723_0003_drop_service_idempotency_keys.py`）。
- 迁移开头 `SET LOCAL lock_timeout = '5s'` / `SET LOCAL statement_timeout = '30s'`；破坏性 DDL 不带 `IF EXISTS` / `CASCADE` 兜底——缺表或有依赖就报错回滚、人工介入。
- backend 镜像启动会自动执行 `alembic upgrade head`，**迁移失败直接阻断 API 启动**。合并前必须：① 核对存量数据；② 查 FK 依赖图（`SELECT conname, conrelid::regclass, confrelid::regclass, confdeltype FROM pg_constraint WHERE confrelid IS NOT NULL`，`r`=RESTRICT 会阻塞删除）；③ 用带数据的开发库跑一遍——空库通过不等于线上通过。
- 线上有带外加的列时用 `ADD COLUMN IF NOT EXISTS` 追平；FK 列改指向新表而旧值无法映射时，按"删旧 UNIQUE → 删旧 FK → 去 NOT NULL 并 `UPDATE SET NULL` → RENAME → 建新 FK（`ON DELETE SET NULL`）"的顺序做一个原子块。
- 重建表会改变主键类型（曾把 `tenant_companies.id` 从 uuid 重建成 bigserial，导致 `bigint = uuid` 崩溃）——改表结构后 grep 所有 JOIN 该列的 SQL。
- **禁止对生产迁移重复手工 DROP 或 downgrade**（#75 有历史证据）。生产写操作一律走 [../guides/production-operations.md](../guides/production-operations.md)。

## 分区表

- `audit_logs`、`emails` 按 `created_at` 月度 RANGE 分区，各有 DEFAULT 分区兜底；`app/db/partitions.py::ensure_partitions` 在启动时建当月与下月分区；`scripts/maintain_partitions.py` 只维护 `emails` 与 `audit_logs` 两张表的分区。
- 分区表主键必须含分区键（如 `(id, created_at)`），唯一约束同理——跨分区去重只能在应用层做。
- 父表建索引会自动下发到所有分区。

## 时间与时区

- 生产数据库会话时区 UTC；业务锚点（配额熔断恢复、自然日配额）用北京时间：`app/utils/beijing_time.py` 的 `beijing_today` / `beijing_day_bounds`。
- **日期窗口计算放 Python 端传参**（如 `:usage_date`），不在 SQL 端写时区表达式——mock 单测能直接断言参数值。
- 对 `timestamptz` 做范围查询时传带时区的 `datetime` 瞬时，不传裸 `date`（裸 date 会按会话时区 UTC 提升为零点，北京日窗口错位 8 小时）。
- 测试不用 freezegun：worker 注入 `clock` callable，service 显式 `now_utc: datetime | None = None` 参数。

## 一次性脚本（`backend/scripts/`）

- 手写列清单前对照**当前**结构（`schema_snapshot.json` 或开发库 `information_schema.columns`），不凭记忆写列名。
- 默认 dry-run + 环境变量二重确认；幂等（`ON CONFLICT DO NOTHING` / 可重跑）+ 单事务；发布前在开发库全流程预演。
- 分页 `ORDER BY created_at DESC` 必须加 `id DESC` 作 tiebreaker，否则同秒记录翻页重复或遗漏。

## 常见错误（历史事故提炼）

| 现象 | 根因 | 规则 |
|---|---|---|
| `syntax error at or near ":"` | `:param::uuid` 被 asyncpg 跳过 | 用 `CAST(:param AS uuid)` |
| 字段值错但不报错，潜伏数月 | JOIN 里 `p.created_at AS published_at` 与 `a.published_at` 撞名，`.mappings()` 静默取后者 | 别名直接用最终序列化字段名（如 `published_to_tenant_at`）；`created_at / updated_at / status / id` 起别名必须带前缀语义 |
| `operator does not exist: bigint = uuid` | 迁移重建表改了主键类型 | 改表后 grep 所有引用列的 JOIN |
| 启动 crash-loop：`ForeignKeyViolation` | 迁移 DELETE 父表前未清理 RESTRICT 子表 | 按 FK 图逆序预清理；用带数据的库测迁移 |
| Neon 连接报 `unsupported startup parameter in options` | pooler 不透传 startup options | 会话参数走连接属性或连接后 `SET`；只读用 `conn.read_only = True` + `SHOW transaction_read_only` 复核 |
| `pg_restore` 报 `unsupported version` / `type citext does not exist` | 客户端主版本高于生产 PG16；缺扩展 | 备份恢复用同主版本工具；恢复前建扩展、补父表桩与触发器函数 |
| `text[]` 列存了 Python repr | 直接 `str(dict)` 入库 | 结构化数据用 jsonb |
