# 上线前验证记录（2026-10-28）

结论：先前确认的非末步 asyncpg 阻塞已经修复，并用真实隔离库复核通过。**上线仍未授权。** 生产迁移、停旧 worker、卡住邮件核对都还没有做。第四封的上游配额错误码仍然未知，这次修复不消除配额限制。

## 修复

`mark_email_sent` 的非末步更新把同一个 `:send_at` 同时用于 `timestamptz` 列和 `make_interval` 加法。asyncpg 0.31.0 无法确定参数类型。

修复只给这两处加上 `CAST(:send_at AS timestamptz)`。发送事实仍是 `provider_accepted_at`，下一步间隔仍从该时刻计算，`tenant_id` 条件和 CAS 幂等没有改。末步分支、迁移和 worker 领取没有改。

## 修复前

同一条服务 SQL、真实 asyncpg、可销毁本地库 `prelaunch_f36204c45b83`（`127.0.0.1/32`，端口 55432）。

```bash
cd backend
env -u CLIENTGET_DEV_DATABASE_URL -u CLIENTGET_PROD_DATABASE_URL \
    -u DATABASE_URL -u SYNC_DATABASE_URL \
    CLIENTGET_PRELAUNCH_LOCAL_PG=1 \
    uv run --extra dev pytest -q tests/test_send_recovery_prelaunch_postgres.py
```

`1 failed in 2.96s`。非末步 `mark_email_sent` 抛出 `AmbiguousParameterError`，锁保持 `accepted_pending`，`sent_count` 为 0。当时测试在记录该失败后删掉第二步，才继续跑末步、领取、租约和降级。完整输出在 `research/prelaunch-verification-before-fix.json`。该库和数据目录已删除。

更早一次发现是库 `prelaunch_43a0e56f1363`，同一错误，同样已清理。

## 修复后

同一命令，库 `prelaunch_0a77777d2315`。`1 passed in 2.88s`。

| 项 | 结果 |
|---|---|
| PostgreSQL | 16.15，`aarch64-apple-darwin24.6.0`，二进制 `aqua:theseus-rs/postgresql-binaries@16.15.1` |
| Python / Alembic / SQLAlchemy / psycopg / asyncpg | 3.13.13 / 1.18.4 / 2.0.49 / 3.3.3 / 0.31.0 |
| 升级 | `20260824_0002` → `20261028_0001`；父表和 8 月、10 月分区都是 `text` |
| 107 字符回执 | 完整相等，落在 `emails_p_2026_10` |
| 非末步 | 第二步仍在，`delay_days` 为 3。两连接并发结果 `[false, true]`，再执行一次仍是 duplicate。`current_step` 为 2，`sent_count` 为 1，`completed_at` 为空 |
| 跨日时间 | 接单 `2026-10-26T15:30:00Z`，恢复时钟 `2026-10-27T02:00:00Z`。`sent_at` 和 `last_step_sent_at` 等于接单时刻，`next_step_due_at` 为 `2026-10-29T15:30:00Z` |
| 两个 worker | 前 20 条失败并写入 60 秒 `finalize_not_before`，第 21 条成功。`send_email` 调用数为 0。第 21 条 `current_step` 为 2，到期为接单时间加 20 秒再加 3 天。计划发送数为 2 |
| 末步 | 单独的一步计划，并发结果同样一次成功一次 duplicate，`completed_at` 等于接单时刻，`next_step_due_at` 为空，没有发信调用 |
| 领取 | 21 条分成 20 和 1，互斥且覆盖全部；单独一条是最晚的第 21 条 |
| 租约 | 持有期间另一连接看到 0 条；连接关闭、时钟超过 15 秒后同一条重新可见 |
| 额度 | 只回收 default 实例确认未外发的 1 条，占用日 2026-10-23 预留从 4 变为 3；另一实例保持 4；旧锁、`dispatching`、`uncertain` 不变 |
| 降级 | 有 107 字符回执时拒绝，revision 仍是 `20261028_0001`，回执保留。清掉新事实后降到 `20260824_0002`，三张表回到 `varchar(100)`，短回执保留。再升级成功。写入 `uncertain` 后再降级，拒绝且行保留 |

JSON 里的 `08:30:00-07:00` 就是 `15:30:00Z`。Alembic 每条 INFO 出现两次，是日志传播；版本表按阶段只有一个 revision。

## 全量测试、lint、diff

```bash
cd backend
env -u CLIENTGET_DEV_DATABASE_URL -u CLIENTGET_PROD_DATABASE_URL \
    -u DATABASE_URL -u SYNC_DATABASE_URL \
    uv run --extra dev pytest -q
uv run --extra dev ruff check \
    tests/test_send_recovery_prelaunch_postgres.py \
    tests/test_send_recovery_scheduler.py
git diff --check
```

全量：`514 passed, 9 skipped, 11 warnings in 12.39s`。9 条跳过都是未设置可选数据库环境变量，不是失败：

- `CLIENTGET_PRELAUNCH_LOCAL_PG`：本记录中的隔离库测试；带该变量时已单独通过
- `CLIENTGET_DEV_DATABASE_URL`：`test_send_recovery_devdb.py`，本次不连接共享开发库
- `TEST_DATABASE_URL`：`test_lineage_repair_postgres.py`
- `T21_MIGRATION_TEST_DATABASE_URL`：`test_drop_retired_collection_tables_migration.py` 4 条，`test_drop_intelligence_tables_migration.py` 2 条

两个测试文件 ruff 通过。非末步 SQL 新行不超过 100 字符。`tenant_messaging_service.py` 里原有的超长行没有在这次改动中新增。`git diff --check` 无输出。

## 清理

修复前库 `prelaunch_f36204c45b83` 和修复后库 `prelaunch_0a77777d2315` 都已 `DROP DATABASE`，`pg_ctl stop` 退出码 0，数据目录已删除。复核时 `/tmp/clientget-prelaunch-20261028-*` 不存在，55432 无监听。没有修改 `.env`，没有写生产库或共享开发库，没有真实发信。

## 上线边界

代码上的这条阻塞已清零。下面仍要另一次明确授权后才能做：

1. 停掉所有还会领取发送锁的旧 worker，再迁移，再只启动包含这次修复的 worker。
2. 单独展示迁移 SQL 和锁范围，取得该次生产写入确认后执行 `alembic upgrade 20261028_0001`。
3. 已卡住邮件只核对。不自动重发，不截断回执，不把前三次标为无效。第四次配额暂停单独看。
4. 没有超长回执、新状态或新列事实时，可以降回 `20260824_0002`。一旦出现这些事实，降级会拒绝并保留数据；保持 `text`，不要用旧 worker 处理这些行。
