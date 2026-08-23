"""A6 真库三段式断言（Neon DEV）：借外键 → 事务内断言 → ROLLBACK 复核零残留；
run_once 的 savepoint / 锁 断言单独用 dev-assert2 实例，commit 后清理。连接串不打印。
CR2 修复后 tenants 查询带 instance_id，因此阶段 2 在事务内自造 dev-assert 实例的测试租户 + 两个用户
（随 ROLLBACK 消失），并用借来的 default 实例真实租户断言跨实例解析为空。"""
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.db.pools import close_engines, get_engine, initialize_engines
from app.services.industry_news.fetchers import FetchError, RawItem
from app.services.industry_news.service import ADVISORY_LOCK_KEY, IndustryNewsService

INST = "dev-assert"
INST2 = "dev-assert2"
NOW = datetime(2026, 8, 23, 0, 0, tzinfo=UTC)
PASS = []; FAIL = []
def check(cond, label, extra=""):
    (PASS if cond else FAIL).append(label + (f" [{extra}]" if extra else ""))
    print(("  ✓ " if cond else "  ✗ ") + label + (f"  {extra}" if extra else ""))

async def insert_source(conn, *, inst, code, active=True, lang="en", category="类别A"):
    sid = str(new_uuid())
    await conn.execute(text("""
        INSERT INTO industry_news_sources (id, instance_id, industry, code, name, url, category, lang, strategy, parse_config, is_active)
        VALUES (:id, :inst, 'PCB', :code, :name, :url, :category, :lang, 'rss', '{}'::jsonb, :active)"""),
        {"id": sid, "inst": inst, "code": code, "name": f"源-{code}", "url": f"https://example.test/{code}", "category": category, "lang": lang, "active": active})
    return {"id": sid, "instance_id": inst, "industry": "PCB", "code": code, "name": f"源-{code}", "url": f"https://example.test/{code}",
            "category": category, "lang": lang, "strategy": "rss", "parse_config": {}, "is_active": active}

async def make_tenant_with_users(conn, *, inst):
    tenant_id = str(new_uuid())
    await conn.execute(text("""
        INSERT INTO tenants (id, instance_id, name, slug, industry) VALUES (:id, :inst, :name, :slug, 'PCB')"""),
        {"id": tenant_id, "inst": inst, "name": f"断言租户-{inst}", "slug": f"assert-{tenant_id[:8]}"})
    users = []
    for i in (1, 2):
        uid = str(new_uuid()); users.append(uid)
        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, email, password_hash, name) VALUES (:id, :t, :email, 'x', :name)"""),
            {"id": uid, "t": tenant_id, "email": f"assert-{uid}@example.test", "name": f"断言用户{i}"})
    return tenant_id, users[0], users[1]

async def phase_transactional(engine, svc, foreign_tenant_id, foreign_u1):
    print("\n== 阶段 2：事务内断言（结束 ROLLBACK）==")
    async with engine.connect() as conn:
        tx = await conn.begin()
        try:
            tenant_id, u1, u2 = await make_tenant_with_users(conn, inst=INST)
            s1 = await insert_source(conn, inst=INST, code="assert-a")
            s2 = await insert_source(conn, inst=INST, code="assert-b", active=False, category="类别B")
            items = [
                RawItem(title="PCB West Panel to Take On What's Next", url="https://pcea.net/2026/08/18/pcb-west-panel/", published_at=NOW - timedelta(days=5)),
                RawItem(title="PCB West Panel to Take On What's Next (copy)", url="https://pcea.net/2026/08/18/pcb-west-panel/?utm_source=x", published_at=NOW - timedelta(days=5)),  # 同 canonical_url
                RawItem(title="pcb west panel to take on what's next", url="https://pcbwest.com/2026/08/18/pcb-west-panel/", published_at=NOW - timedelta(days=5)),  # 同规范化标题
                RawItem(title="Very old story", url="https://pcea.net/2026/01/01/old/", published_at=NOW - timedelta(days=100)),  # 早于 90 天
            ]
            stats = await svc.fetch_source(conn, s1, run_at=NOW, items=items)
            check(stats["fetched"] == 4 and stats["inserted"] == 1 and stats["duplicate"] == 2 and stats["skipped_old"] == 1 and stats["ok"],
                  "同稿去重（canonical_url / dedup_key 各一）+ 90 天入库过滤", f"stats={ {k:stats[k] for k in ('fetched','inserted','duplicate','skipped_old','ok')} }")
            row = (await conn.execute(text("SELECT last_success_at, error_count FROM industry_news_sources WHERE id=:id"), {"id": s1["id"]})).mappings().first()
            check(row["last_success_at"] == NOW and row["error_count"] == 0, "成功后 last_success_at=run_at、error_count=0")
            # 窗口边界：手工插 89 天与 91 天的条目
            for days, code in ((89, "in89"), (91, "out91")):
                await conn.execute(text("""INSERT INTO industry_news_items (id, instance_id, source_id, title, url, canonical_url, dedup_key, published_at, fetched_at)
                    VALUES (:id, :inst, :sid, :t, :u, :u, :dk, NULL, :fa)"""),
                    {"id": str(new_uuid()), "inst": INST, "sid": s1["id"], "t": f"窗口{code}", "u": f"https://example.test/{code}", "dk": code.ljust(40, "0"), "fa": NOW - timedelta(days=days)})
            # 停用源下的条目
            await conn.execute(text("""INSERT INTO industry_news_items (id, instance_id, source_id, title, url, canonical_url, dedup_key, published_at, fetched_at)
                VALUES (:id, :inst, :sid, '停用源条目', 'https://example.test/hidden', 'https://example.test/hidden', :dk, NULL, :fa)"""),
                {"id": str(new_uuid()), "inst": INST, "sid": s2["id"], "dk": "hidden".ljust(40, "0"), "fa": NOW})
            hidden_id = (await conn.execute(text("SELECT id FROM industry_news_items WHERE source_id=:sid"), {"sid": s2["id"]})).scalar()

            items1, total = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, now_utc=NOW)
            titles = [i["title"] for i in items1]
            check(total == 2 and "窗口in89" in titles and "窗口out91" not in titles and "停用源条目" not in titles,
                  "90 天窗口（89 在 / 91 不在）+ 停用源条目隐藏", f"total={total} titles={titles}")
            check(all(i["is_read"] is False for i in items1), "默认未读")
            check(items1[0]["title"].startswith("PCB West") and items1[0]["time"] is not None and items1[0]["source_name"] == "源-assert-a", "序列化字段 time/source_name", f"first={items1[0]['title']}")
            # CAST 数组参数：None 与 list
            _, t_none = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, categories=None, source_ids=None, lang=None, now_utc=NOW)
            _, t_cat = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, categories=["类别A"], now_utc=NOW)
            _, t_nope = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, categories=["不存在"], now_utc=NOW)
            _, t_src = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, source_ids=[s1["id"]], lang="en", now_utc=NOW)
            check(t_none == 2 and t_cat == 2 and t_nope == 0 and t_src == 2, "CAST 数组参数：None / 命中 / 不命中 / 来源+语种", f"{t_none},{t_cat},{t_nope},{t_src}")
            # 已读按用户
            target = items1[0]["id"]
            r = await svc.mark_read(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, item_id=target, now_utc=NOW)
            r2 = await svc.mark_read(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, item_id=target, now_utc=NOW)  # 幂等
            a1, _ = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, now_utc=NOW)
            a2, _ = await svc.list_items(conn, tenant_id=tenant_id, user_id=u2, instance_id=INST, now_utc=NOW)
            read1 = {i["id"]: i["is_read"] for i in a1}; read2 = {i["id"]: i["is_read"] for i in a2}
            check(r["is_read"] is True and r2["is_read"] is True and read1[target] is True and read2[target] is False, "已读只对当前用户生效 + mark_read 幂等")
            unread1, t_unread = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, unread_only=True, now_utc=NOW)
            check(t_unread == 1 and all(i["id"] != target for i in unread1), "只看未读排除已读条目", f"total={t_unread}")
            try:
                await svc.mark_read(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, item_id=str(hidden_id), now_utc=NOW); check(False, "不可见条目 mark_read 应 404")
            except AppError as e:
                check(e.status_code == 404 and e.code == "NOT_FOUND", "不可见条目 mark_read → 404 NOT_FOUND")
            # 停用即隐藏
            await svc.set_source_active(conn, instance_id=INST, source_id=s1["id"], is_active=False)
            _, t_after = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, now_utc=NOW)
            opts = await svc.list_filter_options(conn, tenant_id=tenant_id, instance_id=INST)
            check(t_after == 0 and opts["has_sources"] is False, "停用即隐藏：列表清空、has_sources=false", f"total={t_after} has_sources={opts['has_sources']}")
            # CR2：default 实例的真实租户 id 在 dev-assert 实例下查不到 tenants 行 → 三个入口统一 404 租户不存在
            await svc.set_source_active(conn, instance_id=INST, source_id=s1["id"], is_active=True)
            codes = []
            for call in (
                lambda: svc.list_items(conn, tenant_id=foreign_tenant_id, user_id=foreign_u1, instance_id=INST, now_utc=NOW),
                lambda: svc.list_filter_options(conn, tenant_id=foreign_tenant_id, instance_id=INST),
                lambda: svc.mark_read(conn, tenant_id=foreign_tenant_id, user_id=foreign_u1, instance_id=INST, item_id=target, now_utc=NOW),
            ):
                try:
                    await call(); codes.append("ok")
                except AppError as e:
                    codes.append(e.status_code)
            check(codes == [404, 404, 404], "跨实例租户 id：tenants 查询带 instance_id → list/filters/mark_read 均 404", f"codes={codes}")
            same_items, same_total = await svc.list_items(conn, tenant_id=tenant_id, user_id=u1, instance_id=INST, now_utc=NOW)
            check(same_total == 2, "同实例租户重新启用源后仍可见（对照组）", f"total={same_total}")
            try:
                await svc.set_source_active(conn, instance_id="other-inst", source_id=s1["id"], is_active=True); check(False, "跨实例启停应 404")
            except AppError as e:
                check(e.status_code == 404, "跨实例启停 → 404")
        finally:
            await tx.rollback()
    async with engine.connect() as conn:
        n = await conn.scalar(text("SELECT (SELECT count(*) FROM industry_news_sources WHERE instance_id=:i) + (SELECT count(*) FROM industry_news_items WHERE instance_id=:i) + (SELECT count(*) FROM industry_news_reads r JOIN industry_news_items i ON i.id=r.item_id WHERE i.instance_id=:i) + (SELECT count(*) FROM tenants WHERE instance_id=:i) + (SELECT count(*) FROM users WHERE tenant_id IN (SELECT id FROM tenants WHERE instance_id=:i))"), {"i": INST})
        check(n == 0, "阶段 3：ROLLBACK 后 dev-assert 零残留", f"count={n}")

class FakeFetcher:
    async def fetch_items(self, source):
        if source["code"] == "assert-bad":
            raise FetchError("模拟站点改版：解析失败")
        return [RawItem(title=f"好源条目 {i}", url=f"https://example.test/good/{i}", published_at=NOW - timedelta(days=i)) for i in (1, 2)]

async def phase_run_once(engine):
    print("\n== run_once：savepoint 隔离 + 事务锁互斥（dev-assert2，结束清理）==")
    svc = IndustryNewsService(fetcher=FakeFetcher())
    async with engine.begin() as conn:
        await insert_source(conn, inst=INST2, code="assert-good")
        await insert_source(conn, inst=INST2, code="assert-bad")
    try:
        res = await svc.run_once(engine, instance_id=INST2, clock=lambda: NOW)
        async with engine.connect() as conn:
            rows = (await conn.execute(text("SELECT code, error_count, last_success_at, last_fetched_at FROM industry_news_sources WHERE instance_id=:i ORDER BY code"), {"i": INST2})).mappings().all()
            by = {r["code"]: r for r in rows}
            n_items = await conn.scalar(text("SELECT count(*) FROM industry_news_items WHERE instance_id=:i AND fetched_at=:fa"), {"i": INST2, "fa": NOW})
        check(not res.get("skipped") and by["assert-bad"]["error_count"] == 1 and by["assert-bad"]["last_success_at"] is None and by["assert-bad"]["last_fetched_at"] == NOW,
              "坏源：savepoint 回滚后 error_count=1、last_fetched_at=run_at、无 last_success_at", f"bad={dict(by['assert-bad'])}")
        check(by["assert-good"]["error_count"] == 0 and by["assert-good"]["last_success_at"] == NOW and n_items == 2,
              "好源不受影响：2 条入库且 fetched_at=run_at", f"items={n_items}")
        # 锁互斥：另一连接持事务锁
        async with engine.connect() as holder:
            htx = await holder.begin()
            got = await holder.scalar(text("SELECT pg_try_advisory_xact_lock(CAST(:k AS bigint) + pg_catalog.hashtext(:i))"), {"k": ADVISORY_LOCK_KEY, "i": INST2})
            res2 = await svc.run_once(engine, instance_id=INST2, clock=lambda: NOW + timedelta(minutes=1))
            await htx.rollback()
        check(got is True and res2.get("skipped") is True and res2.get("reason") == "in_progress", "锁被占时 run_once 返回 skipped/in_progress", f"res2={res2}")
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM industry_news_reads WHERE item_id IN (SELECT id FROM industry_news_items WHERE instance_id=:i)"), {"i": INST2})
            await conn.execute(text("DELETE FROM industry_news_items WHERE instance_id=:i"), {"i": INST2})
            await conn.execute(text("DELETE FROM industry_news_sources WHERE instance_id=:i"), {"i": INST2})
        async with engine.connect() as conn:
            n = await conn.scalar(text("SELECT (SELECT count(*) FROM industry_news_sources WHERE instance_id=:i) + (SELECT count(*) FROM industry_news_items WHERE instance_id=:i)"), {"i": INST2})
        check(n == 0, "清理后 dev-assert2 零残留", f"count={n}")

async def main():
    initialize_engines(get_settings()); engine = get_engine()
    try:
        print("== 阶段 1：借外键 ==")
        async with engine.connect() as conn:
            t = (await conn.execute(text("SELECT id, name, industry, instance_id FROM tenants WHERE industry='PCB' AND status='active' AND instance_id='default' AND id IN (SELECT tenant_id FROM users WHERE status='active') LIMIT 1"))).mappings().first()
            users = (await conn.execute(text("SELECT id FROM users WHERE tenant_id=:t AND status='active' ORDER BY created_at LIMIT 1"), {"t": t["id"]})).scalars().all()
        foreign_tenant_id, foreign_u1 = str(t["id"]), str(users[0])
        print(f"  借到 {t['instance_id']} 实例租户 {t['name']}（industry={t['industry']}）作跨实例对照；断言租户与用户在事务内自造")
        svc = IndustryNewsService()
        await phase_transactional(engine, svc, foreign_tenant_id, foreign_u1)
        await phase_run_once(engine)
    finally:
        await close_engines()
    print(f"\n结果：通过 {len(PASS)}，失败 {len(FAIL)}")
    for f in FAIL: print("  FAIL:", f)
    raise SystemExit(1 if FAIL else 0)

asyncio.run(main())
