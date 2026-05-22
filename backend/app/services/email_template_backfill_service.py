from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.utils.email_text import text_from_html

TABLES = ("platform_email_templates", "email_templates")


@dataclass(frozen=True)
class BackfillCandidate:
    id: str
    body_text: str


def build_body_text_backfill_candidates(rows) -> tuple[list[BackfillCandidate], int]:
    candidates: list[BackfillCandidate] = []
    skipped = 0
    for row in rows:
        body_text = text_from_html(row["body_html"])
        if body_text:
            candidates.append(BackfillCandidate(id=str(row["id"]), body_text=body_text))
        else:
            skipped += 1
    return candidates, skipped


async def backfill_email_template_body_text(
    conn: AsyncConnection,
    *,
    dry_run: bool,
) -> dict:
    environment = await _load_environment(conn)
    tables = {}
    for table_name in TABLES:
        table_result = await _backfill_table(conn, table_name, dry_run=dry_run)
        tables[table_name] = table_result
    return {
        "dry_run": dry_run,
        "environment": environment,
        "tables": tables,
    }


async def _load_environment(conn: AsyncConnection) -> dict:
    row = (
        await conn.execute(
            text("SELECT current_database() AS database_name, current_user AS user_name")
        )
    ).mappings().one()
    return {
        "database_name": row["database_name"],
        "user_name": row["user_name"],
    }


async def _backfill_table(conn: AsyncConnection, table_name: str, *, dry_run: bool) -> dict:
    total = (
        await conn.execute(text(f"SELECT count(*) FROM {table_name}"))
    ).scalar_one()
    result = await conn.execute(
        text(
            f"""
            SELECT id, body_html
            FROM {table_name}
            WHERE (body_text IS NULL OR btrim(body_text) = '')
              AND body_html IS NOT NULL
              AND btrim(body_html) <> ''
            ORDER BY id
            """
        )
    )
    rows = result.mappings().all()
    candidates, skipped_without_text = build_body_text_backfill_candidates(rows)

    updated = 0
    if not dry_run:
        for candidate in candidates:
            update_result = await conn.execute(
                text(
                    f"""
                    UPDATE {table_name}
                    SET body_text = :body_text,
                        updated_at = now()
                    WHERE id = :id
                      AND (body_text IS NULL OR btrim(body_text) = '')
                    """
                ),
                {"id": candidate.id, "body_text": candidate.body_text},
            )
            updated += update_result.rowcount or 0

    return {
        "total": total,
        "missing_body_text": len(rows),
        "backfillable": len(candidates),
        "skipped_without_text": skipped_without_text,
        "updated": updated,
    }
