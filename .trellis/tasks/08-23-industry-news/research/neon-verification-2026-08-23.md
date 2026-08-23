# Neon 开发库验证记录（2026-08-23，协调者执行）

连接：`CLIENTGET_DEV_DATABASE_URL`（Neon，可写）；生产库未触碰。

## A1 迁移 `20260824_0001_industry_news`

- `alembic upgrade head`：`20260723_0003 → 20260824_0001`；三表、`uq_*` 三条唯一约束、四个索引、`reads.user_id/item_id ON DELETE CASCADE`（`tenant_id` 不带）、`set_updated_at` 触发器经 `pg_constraint` / `pg_indexes` / `pg_trigger` 逐项核对与 design §2 一致。
- `downgrade -1` 后 industry_news 表数 0 → `upgrade head` 往返通过。
- 结构快照：用 dev 再生会混入 dev 与生产快照间既有漂移（dev 多 `_tenant_companies_snapshot`、`cleanup_queue`，少 `crawl_progress` 等），因此 PR A 不更新 `schema_snapshot.json`，发布后按 bb0de0d 先例 `--prod` 再生。

## A5 种子脚本（实例 `dev-seed-test`）

- 非 default 实例不带 `--confirm-instance` → 拒绝写入。
- `--dry-run` 14 新增 → 执行后 14 行 → 幂等重跑 `created 0 / updated 0 / unchanged 14`。
- 改 pcea 的 url 与类别后重跑 → `updated 1`，行数仍 14，预置的 `is_active=false / error_count=7` 原样保留；default 实例 0 行未波及。
- 清理：DELETE 14 行，剩余 0。

## A6 三段式断言（脚本 `assert_industry_news.py`，输出如下）

```
industry_news: 源失败 source=源-assert-bad
Traceback (most recent call last):
  File "/Users/lay/Projects/ClientGet/backend/app/services/industry_news/service.py", line 252, in fetch_source_from_network
    items = await self._load_raw_items(source)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lay/Projects/ClientGet/backend/app/services/industry_news/service.py", line 242, in _load_raw_items
    return await self.fetcher.fetch_items(source)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/private/tmp/claude-501/-Users-lay-Projects-ClientGet/8b4530db-1435-4b49-8092-f18f9e32e365/scratchpad/assert_industry_news.py", line 105, in fetch_items
    raise FetchError("模拟站点改版：解析失败")
app.services.industry_news.fetchers.FetchError: 模拟站点改版：解析失败
== 阶段 1：借外键 ==
  租户 赵奎（industry=PCB），两个用户已借到

== 阶段 2：事务内断言（结束 ROLLBACK）==
  ✓ 同稿去重（canonical_url / dedup_key 各一）+ 90 天入库过滤  stats={'fetched': 4, 'inserted': 1, 'duplicate': 2, 'skipped_old': 1, 'ok': True}
  ✓ 成功后 last_success_at=run_at、error_count=0
  ✓ 90 天窗口（89 在 / 91 不在）+ 停用源条目隐藏  total=2 titles=["PCB West Panel to Take On What's Next", '窗口in89']
  ✓ 默认未读
  ✓ 序列化字段 time/source_name  first=PCB West Panel to Take On What's Next
  ✓ CAST 数组参数：None / 命中 / 不命中 / 来源+语种  2,2,0,2
  ✓ 已读只对当前用户生效 + mark_read 幂等
  ✓ 只看未读排除已读条目  total=1
  ✓ 不可见条目 mark_read → 404 NOT_FOUND
  ✓ 停用即隐藏：列表清空、has_sources=false  total=0 has_sources=False
  ✓ 跨实例启停 → 404
  ✓ 阶段 3：ROLLBACK 后 dev-assert 零残留  count=0

== run_once：savepoint 隔离 + 事务锁互斥（dev-assert2，结束清理）==
  ✓ 坏源：savepoint 回滚后 error_count=1、last_fetched_at=run_at、无 last_success_at  bad={'code': 'assert-bad', 'error_count': 1, 'last_success_at': None, 'last_fetched_at': datetime.datetime(2026, 8, 23, 0, 0, tzinfo=datetime.timezone.utc)}
  ✓ 好源不受影响：2 条入库且 fetched_at=run_at  items=2
  ✓ 锁被占时 run_once 返回 skipped/in_progress  res2={'skipped': True, 'reason': 'in_progress'}
  ✓ 清理后 dev-assert2 零残留  count=0

结果：通过 16，失败 0
```
