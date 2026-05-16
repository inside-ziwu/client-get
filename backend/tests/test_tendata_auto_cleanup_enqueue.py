from uuid import uuid4

from sqlalchemy import text

from app.services.keyword_service import get_or_create_keyword_master, normalize_keyword
from tests.helpers import make_engine


async def _keyword_master(conn, keyword: str) -> str:
    return str(
        await get_or_create_keyword_master(
            conn,
            keyword=keyword,
            keyword_normalized=normalize_keyword(keyword),
        )
    )


async def _insert_tendata_raw(conn, *, source_id: str | None = None) -> int:
    keyword_master_id = await _keyword_master(conn, f"auto enqueue {uuid4().hex}")
    result = await conn.execute(
        text(
            """
            INSERT INTO tendata_raw_companies
              (keyword_master_id, source_id, collection_type, name, country_iso3)
            VALUES
              (:keyword_master_id, :source_id, 'reverse_lookup', 'Auto Enqueue Buyer', 'USA')
            RETURNING id
            """
        ),
        {"keyword_master_id": keyword_master_id, "source_id": source_id or f"td-{uuid4().hex}"},
    )
    return result.scalar_one()


async def _cleanup_queue_rows(conn, raw_id: int) -> list[dict]:
    result = await conn.execute(
        text(
            """
            SELECT raw_table, raw_row_id, status
            FROM cleanup_queue
            WHERE raw_table = 'tendata_raw_companies'
              AND raw_row_id = :raw_id
            ORDER BY id
            """
        ),
        {"raw_id": raw_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def test_direct_tendata_raw_insert_enqueues_pending_cleanup_work() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            raw_id = await _insert_tendata_raw(conn)

            rows = await _cleanup_queue_rows(conn, raw_id)

        assert rows == [
            {
                "raw_table": "tendata_raw_companies",
                "raw_row_id": raw_id,
                "status": "pending",
            }
        ]
    finally:
        await engine.dispose()


async def test_tendata_trigger_and_service_enqueue_keep_one_queue_row() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            raw_id = await _insert_tendata_raw(conn)
            await conn.execute(
                text(
                    """
                    INSERT INTO cleanup_queue (raw_table, raw_row_id, status)
                    VALUES ('tendata_raw_companies', :raw_id, 'pending')
                    ON CONFLICT (raw_table, raw_row_id) DO NOTHING
                    """
                ),
                {"raw_id": raw_id},
            )

            rows = await _cleanup_queue_rows(conn, raw_id)

        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
    finally:
        await engine.dispose()


async def test_tendata_raw_update_does_not_requeue_cleanup_work() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            raw_id = await _insert_tendata_raw(conn)
            await conn.execute(
                text(
                    """
                    UPDATE cleanup_queue
                    SET status = 'done', processed_at = now()
                    WHERE raw_table = 'tendata_raw_companies'
                      AND raw_row_id = :raw_id
                    """
                ),
                {"raw_id": raw_id},
            )
            await conn.execute(
                text(
                    """
                    UPDATE tendata_raw_companies
                    SET website = 'https://buyer.example'
                    WHERE id = :raw_id
                    """
                ),
                {"raw_id": raw_id},
            )

            rows = await _cleanup_queue_rows(conn, raw_id)

        assert len(rows) == 1
        assert rows[0]["status"] == "done"
    finally:
        await engine.dispose()
