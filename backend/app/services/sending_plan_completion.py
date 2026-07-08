from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def complete_running_plan_if_finished(conn: AsyncConnection, *, plan_id: str) -> bool:
    result = await conn.execute(
        text(
            """
            UPDATE sending_plans sp
            SET status = 'completed',
                completed_at = COALESCE(sp.completed_at, now()),
                updated_at = now()
            WHERE sp.id = :plan_id
              AND sp.status = 'running'
              AND EXISTS (
                SELECT 1
                FROM sequence_enrollments se
                WHERE se.plan_id = sp.id
              )
              AND NOT EXISTS (
                SELECT 1
                FROM sequence_enrollments se
                WHERE se.plan_id = sp.id
                  AND se.status IN ('active', 'paused')
              )
            RETURNING sp.id
            """
        ),
        {"plan_id": plan_id},
    )
    return result.mappings().first() is not None
