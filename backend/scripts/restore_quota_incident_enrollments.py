"""2026-07-02 配额级联事故数据修复：恢复被误杀的 enrollment 并清理 failed 邮件行。

用法（openspec change: restore-quota-incident-enrollments）：
    uv run python scripts/restore_quota_incident_enrollments.py --env prod   # dry-run(只读)
    uv run python scripts/restore_quota_incident_enrollments.py --env prod \
        --execute --confirm RESTORE-20260702                                              # 正式执行

行为：
- 修复集实时反查：事故窗口 [2026-07-02 00:00Z, 2026-07-03 00:00Z) 内 status='failed' 的邮件
  关联 status='failed' 的 enrollment（bounced/active 天然排除）；
- 执行时单事务原子完成：全列备份两张表 → enrollment 恢复(active/attempt=0/due=resume_at)
  → failed 邮件行删除；任一步失败整体回滚；
- 幂等：修复完成后再次运行修复集为空，no-op。

前置（执行前人工确认）：fix-quota-exhaustion-cascade 已部署 A/B 两实例；EngageLab 余额已充值。
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime

import asyncpg
from dotenv import load_dotenv

WINDOW_START = datetime(2026, 7, 2, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 3, 0, 0, tzinfo=UTC)
CONFIRM_TOKEN = "RESTORE-20260702"

REPAIR_SET_SQL = """
    SELECT DISTINCT se.id AS enrollment_id
    FROM emails e
    JOIN sequence_enrollments se ON se.id = e.enrollment_id
    WHERE e.created_at >= $1 AND e.created_at < $2
      AND e.status = 'failed'
      AND se.status = 'failed'
"""


def resolve_url(env: str) -> str:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    key = "CLIENTGET_PROD_DATABASE_URL" if env == "prod" else "CLIENTGET_DEV_DATABASE_URL"
    url = os.environ.get(key)
    if not url:
        raise SystemExit(f"环境变量 {key} 未配置")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def summarize(conn: asyncpg.Connection) -> dict:
    enrollments = await conn.fetchval(
        f"SELECT count(*) FROM ({REPAIR_SET_SQL}) t", WINDOW_START, WINDOW_END
    )
    emails = await conn.fetchval(
        """
        SELECT count(*) FROM emails e
        WHERE e.created_at >= $1 AND e.created_at < $2 AND e.status = 'failed'
          AND e.enrollment_id IN (SELECT enrollment_id FROM (
              SELECT DISTINCT se.id AS enrollment_id
              FROM emails e2 JOIN sequence_enrollments se ON se.id = e2.enrollment_id
              WHERE e2.created_at >= $1 AND e2.created_at < $2
                AND e2.status = 'failed' AND se.status = 'failed') t)
        """,
        WINDOW_START,
        WINDOW_END,
    )
    by_plan = await conn.fetch(
        f"""
        SELECT sp.name, sp.status AS plan_status, count(*) AS cnt
        FROM ({REPAIR_SET_SQL}) t
        JOIN sequence_enrollments se ON se.id = t.enrollment_id
        JOIN sending_plans sp ON sp.id = se.plan_id
        GROUP BY 1, 2 ORDER BY cnt DESC
        """,
        WINDOW_START,
        WINDOW_END,
    )
    return {"enrollments": enrollments, "emails": emails, "by_plan": by_plan}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=["prod", "dev"], required=True, help="目标库(必须显式)")
    parser.add_argument("--execute", action="store_true", help="执行写操作(默认 dry-run 只读)")
    parser.add_argument("--confirm", default="", help=f"执行确认词: {CONFIRM_TOKEN}")
    parser.add_argument("--resume-at", default="", help="恢复的 next_step_due_at(ISO,默认执行时刻)")
    args = parser.parse_args()

    if args.execute and args.confirm != CONFIRM_TOKEN:
        print(f"拒绝执行：--execute 必须叠加 --confirm {CONFIRM_TOKEN}（当前未提供或不匹配）")
        return 2

    resume_at = (
        datetime.fromisoformat(args.resume_at) if args.resume_at else datetime.now(UTC)
    )
    if resume_at.tzinfo is None:
        raise SystemExit("--resume-at 必须带时区")

    conn = await asyncpg.connect(resolve_url(args.env), statement_cache_size=0)
    try:
        summary = await summarize(conn)
        print(
            f"[{args.env}] 修复集：enrollment={summary['enrollments']} "
            f"封存邮件={summary['emails']}"
        )
        for r in summary["by_plan"]:
            print(f"  计划 {r['name']}({r['plan_status']}): {r['cnt']}")
        print(f"resume_at = {resume_at.isoformat()}")

        if summary["enrollments"] == 0:
            print("修复集为空（已修复或无事故数据），no-op。")
            return 0

        if not args.execute:
            print("dry-run 结束（零写操作）。执行请叠加 --execute --confirm " + CONFIRM_TOKEN)
            return 0

        print("\n前置自查（回车继续，Ctrl+C 中止）：")
        print("  1. fix-quota-exhaustion-cascade 已部署 Instance A 与 B（熔断保护就位）？")
        print("  2. EngageLab 余额已充值到账？")
        input("确认以上两项后回车执行> ")

        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        bk_enroll = f"backup_quota_incident_enrollments_{ts}"
        bk_emails = f"backup_quota_incident_emails_{ts}"

        async with conn.transaction():
            # 备份 enrollment
            await conn.execute(
                f"""
                CREATE TABLE {bk_enroll} AS
                SELECT se.* FROM sequence_enrollments se
                WHERE se.id IN ({REPAIR_SET_SQL})
                """,
                WINDOW_START,
                WINDOW_END,
            )
            n_backup_enroll = await conn.fetchval(f"SELECT count(*) FROM {bk_enroll}")
            # 备份 failed 邮件
            await conn.execute(
                f"""
                CREATE TABLE {bk_emails} AS
                SELECT e.* FROM emails e
                WHERE e.created_at >= $1 AND e.created_at < $2 AND e.status = 'failed'
                  AND e.enrollment_id IN ({REPAIR_SET_SQL})
                """,
                WINDOW_START,
                WINDOW_END,
            )
            n_backup_emails = await conn.fetchval(f"SELECT count(*) FROM {bk_emails}")
            # 恢复 enrollment
            restored = await conn.execute(
                f"""
                UPDATE sequence_enrollments se
                SET status = 'active',
                    send_attempt_count = 0,
                    last_skip_reason = NULL,
                    next_step_due_at = $3,
                    updated_at = now()
                WHERE se.id IN ({REPAIR_SET_SQL})
                """,
                WINDOW_START,
                WINDOW_END,
                resume_at,
            )
            # 删除 failed 邮件行(修复集范围;emails 无入向外键,窗口条件走分区裁剪)
            deleted = await conn.execute(
                f"""
                DELETE FROM emails e
                WHERE e.created_at >= $1 AND e.created_at < $2 AND e.status = 'failed'
                  AND e.enrollment_id IN (SELECT id FROM {bk_enroll})
                """,
                WINDOW_START,
                WINDOW_END,
            )
            n_restored = int(restored.split()[-1])
            n_deleted = int(deleted.split()[-1])
            if n_restored != n_backup_enroll or n_deleted != n_backup_emails:
                raise RuntimeError(
                    f"行数不一致,回滚: 恢复 {n_restored}/{n_backup_enroll}, "
                    f"删除 {n_deleted}/{n_backup_emails}"
                )

        print("\n执行完成（单事务已提交）：")
        print(f"  备份表: {bk_enroll}({n_backup_enroll} 行), {bk_emails}({n_backup_emails} 行)")
        print(f"  恢复 enrollment: {n_restored}")
        print(f"  删除 failed 邮件行: {n_deleted}")

        post = await summarize(conn)
        print(f"  复核: 剩余修复集 enrollment={post['enrollments']}(应为 0)")
        return 0 if post["enrollments"] == 0 else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
