"""事故窗口内「本地 failed 且没有 provider id」的只读汇总。

默认 dry-run。本地失败次数不能换成服务商接单次数。没有一一对应的回执时
结论固定为 needs_verification，不调用 mark_email_sent，不写库。

生产写入不在本脚本能力内。连接环境变量名包含 PROD 时直接退出。
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime

import psycopg

from app.services.accepted_send_repair import (
    candidate_sql,
    correlate_receipts,
    summarize_candidates,
)

DEFAULT_START = "2026-10-23T00:00:00+00:00"
DEFAULT_END = "2026-10-28T00:00:00+00:00"


def load_rows(
    database_url: str,
    *,
    start: datetime,
    end: datetime,
    instance_id: str | None,
) -> list[dict]:
    with psycopg.connect(database_url, autocommit=False) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            flag = cur.fetchone()[0]
            if flag != "on":
                raise RuntimeError("数据库连接不是只读")
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'email_send_locks'
                  AND column_name = 'provider_message_id'
                """
            )
            has_columns = cur.fetchone() is not None
            cur.execute(
                candidate_sql(has_columns),
                (start, end, instance_id, instance_id),
            )
            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run summary of unpersisted accepted sends")
    parser.add_argument("--database-url-env", default="CLIENTGET_DEV_DATABASE_URL")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--receipt-file", default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if "PROD" in args.database_url_env.upper():
        raise SystemExit("拒绝使用名称中含 PROD 的数据库环境变量")
    if args.apply:
        raise SystemExit("此工具只做 dry-run。修复写入必须单独展示 SQL，并取得该次确认")

    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        raise SystemExit(f"未设置 {args.database_url_env}")

    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    rows = load_rows(database_url, start=start, end=end, instance_id=args.instance_id)
    summary = summarize_candidates(rows)
    if args.receipt_file:
        with open(args.receipt_file, encoding="utf-8") as handle:
            receipts = json.load(handle)
        if not isinstance(receipts, list):
            raise SystemExit("回执文件必须是 JSON 数组")
        summary = correlate_receipts(summary, receipts)
    summary["mode"] = "dry-run"
    summary["start"] = start.isoformat()
    summary["end"] = end.isoformat()
    summary["row_count"] = len(rows)
    summary["note"] = "local_failed_count 不是服务商接单次数；无对应回执不得补 sent"
    json.dump(summary, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
