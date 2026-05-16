import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.cleanup_service import CleanupService
from app.services.collection_service import CollectionService


@pytest.mark.asyncio
async def test_waimaotong_direct_search_e2e():
    service = CollectionService()
    conn = MagicMock()
    company = json.loads(
        json.dumps(
            {
                "target_table": "waimaotong_raw_companies",
                "source_id": "co-001",
                "name": "Test Corp",
                "country_iso3": "IND",
            }
        )
    )
    service._upsert_waimaotong_raw = AsyncMock(return_value="42")  # str repr of bigint RETURNING id
    service._enqueue_cleanup = AsyncMock()

    summary = await service._route_and_enqueue(conn, task_id="task-1", rows=[company])

    service._upsert_waimaotong_raw.assert_awaited_once_with(conn, "task-1", company)
    service._enqueue_cleanup.assert_has_awaits(
        [call(conn, "waimaotong_raw_companies", 42)]  # int() cast applied before enqueue
    )
    assert summary == {"inserted": 1, "updated": 0, "enqueued": 1}


@pytest.mark.asyncio
async def test_lixiaoyun_tendata_reverse_e2e():
    service = CollectionService()
    conn = MagicMock()
    lixiaoyun = {
        "target_table": "lixiaoyun_raw_companies",
        "source_id": "lx-001",
        "company_name_en": "Test PCB Co",
    }
    tendata = {
        "target_table": "tendata_raw_companies",
        "tid": "IND123",
    }
    service._upsert_lixiaoyun_raw = AsyncMock()
    service._upsert_tendata_raw = AsyncMock(return_value="123")
    service._enqueue_cleanup = AsyncMock()

    summary = await service._route_and_enqueue(conn, task_id="task-2", rows=[lixiaoyun, tendata])

    service._upsert_lixiaoyun_raw.assert_awaited_once_with(
        conn, {**lixiaoyun, "task_id": "task-2"}
    )
    service._upsert_tendata_raw.assert_awaited_once_with(conn, "task-2", tendata)
    service._enqueue_cleanup.assert_awaited_once_with(conn, "tendata_raw_companies", 123)
    assert summary == {"inserted": 2, "updated": 0, "enqueued": 1}


@pytest.mark.asyncio
async def test_target_table_missing_ignored():
    service = CollectionService()
    conn = MagicMock()
    row = {"source_id": "co-ignored", "name": "Ignored Corp", "target_table": None}
    service._upsert_waimaotong_raw = AsyncMock()
    service._upsert_tendata_raw = AsyncMock()
    service._upsert_lixiaoyun_raw = AsyncMock()

    summary = await service._route_and_enqueue(conn, task_id="task-3", rows=[row])

    service._upsert_waimaotong_raw.assert_not_awaited()
    service._upsert_tendata_raw.assert_not_awaited()
    service._upsert_lixiaoyun_raw.assert_not_awaited()
    assert summary == {"inserted": 0, "updated": 0, "enqueued": 0}


@pytest.mark.asyncio
async def test_lixiaoyun_raw_not_enqueued():
    service = CollectionService()
    conn = MagicMock()
    competitors = [
        {
            "target_table": "lixiaoyun_raw_companies",
            "source_id": "lx-001",
            "company_name_en": "Test PCB Co",
        }
    ]
    service._upsert_lixiaoyun_raw = AsyncMock()
    service._enqueue_cleanup = AsyncMock()

    summary = await service._route_and_enqueue(conn, task_id="task-4", rows=competitors)

    service._upsert_lixiaoyun_raw.assert_awaited_once_with(
        conn, {**competitors[0], "task_id": "task-4"}
    )
    service._enqueue_cleanup.assert_not_awaited()
    assert summary == {"inserted": 1, "updated": 0, "enqueued": 0}


@pytest.mark.asyncio
async def test_cleanup_service_batch():
    service = CleanupService()
    conn = MagicMock()
    conn.execute = AsyncMock()
    queue_row = {
        "id": "queue-1",
        "raw_table": "waimaotong_raw_companies",
        "raw_row_id": "1",
        "attempts": 0,
    }
    raw_row = {
        "id": "1",
        "name": "Test Corp",
        "country_iso3": "IND",
        "website": "https://test.example",
        "keyword_master_id": "019e1108-0000-7000-8000-000000000001",
    }
    service._claim_batch = AsyncMock(return_value=[queue_row])
    service._load_raw_row = AsyncMock(return_value=raw_row)
    service._upsert_clean_company = AsyncMock(return_value="1")
    service._upsert_clean_company_keyword = AsyncMock()
    service._materialize_tenant_companies_for_keyword = AsyncMock()

    processed = await service.process_one_batch(conn)

    assert processed == 1
    service._upsert_clean_company.assert_awaited_once()
    service._upsert_clean_company_keyword.assert_awaited_once_with(
        conn, clean_id="1", keyword_master_id="019e1108-0000-7000-8000-000000000001"
    )
    service._materialize_tenant_companies_for_keyword.assert_awaited_once_with(
        conn, clean_id="1", keyword_master_id="019e1108-0000-7000-8000-000000000001"
    )
    assert any("status='done'" in str(args.args[0]) for args in conn.execute.await_args_list)


@pytest.mark.asyncio
async def test_cleanup_attempts_increment():
    service = CleanupService()
    conn = MagicMock()
    conn.execute = AsyncMock()
    row = {
        "id": "queue-2",
        "raw_table": "waimaotong_raw_companies",
        "raw_row_id": "row-2",
        "attempts": 1,
    }
    service._clean_and_link = AsyncMock(side_effect=Exception("DB error"))

    await service._process_one(conn, row)

    sql_texts = [str(args.args[0]) for args in conn.execute.await_args_list]
    assert any("attempts = attempts + 1" in sql for sql in sql_texts)
    assert any("last_error" in sql for sql in sql_texts)


@pytest.mark.asyncio
async def test_cleanup_skip_lixiaoyun():
    service = CleanupService()
    conn = MagicMock()
    conn.execute = AsyncMock()
    service._claim_batch = AsyncMock(
        return_value=[
            {
                "id": "queue-3",
                "raw_table": "lixiaoyun_raw_companies",
                "raw_row_id": "row-3",
                "attempts": 0,
            }
        ]
    )
    service._clean_and_link = AsyncMock()

    processed = await service.process_one_batch(conn)

    assert processed == 1
    service._clean_and_link.assert_not_awaited()
    assert any("status='done'" in str(args.args[0]) for args in conn.execute.await_args_list)


def test_worker_collection_task_no_countries():
    with patch("builtins.open", open):
        with open("app/workers/collection.py", encoding="utf-8") as f:
            source = f.read()

    collection_task_block = source.split("CollectionTask(", 1)[1].split(")", 1)[0]
    assert "countries=" not in collection_task_block
