from types import SimpleNamespace
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.api.admin import collection as collection_api
from app.core.errors import AppError
from app.main import create_app
from app.security.dependencies import get_current_platform_user
from app.security.jwt import create_access_token

RAW_FILTER_DEFAULTS = {
    "keyword_filter": None,
    "found_date_start": None,
    "found_date_end": None,
    "reg_capital": None,
    "employee_scale": None,
    "contacts_filter": None,
    "has_name_en": None,
    "has_domain": None,
    "industry": None,
    "tag": None,
    "size": None,
    "amount_min": None,
    "amount_max": None,
    "count_min": None,
    "count_max": None,
    "pcb": None,
    "contact_min": None,
    "contact_max": None,
    "year_min": None,
    "year_max": None,
    "method": None,
}

CLEAN_FILTER_DEFAULTS = {
    "country": None,
    "industry": None,
    "tag": None,
    "size": None,
    "amount_min": None,
    "amount_max": None,
    "count_min": None,
    "count_max": None,
    "pcb": None,
    "contact_min": None,
    "contact_max": None,
    "year_min": None,
    "year_max": None,
}

V3_CLEAN_FILTER_DEFAULTS = {
    "source_type": None,
    "keyword": None,
    "countries": None,
    "sub_industries": None,
    "product_tags": None,
    "sources": None,
    "employee_count_min": None,
    "employee_count_max": None,
    "trade_amount_min": None,
    "trade_amount_max": None,
    "trade_count_min": None,
    "trade_count_max": None,
    "contact_count_min": None,
    "contact_count_max": None,
    "founded_year_from": None,
    "founded_year_to": None,
    "pcb_supplier_presence": None,
}


def platform_admin_token() -> str:
    return create_access_token(
        {
            "sub": "platform-admin-test",
            "kind": "platform",
            "email": "admin@example.com",
            "name": "Admin",
            "roles": ["platform_admin"],
        }
    )


async def build_admin_client() -> tuple[AsyncClient, object]:
    app = create_app()
    dummy_conn = object()

    async def override_platform_user():
        return SimpleNamespace(
            platform_user_id="platform-admin-test",
            email="admin@example.com",
            name="Admin",
            roles=["platform_admin"],
            connection=dummy_conn,
        )

    app.dependency_overrides[get_current_platform_user] = override_platform_user
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    return client, dummy_conn


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {platform_admin_token()}"}


async def test_stop_collection_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    stop_keyword = AsyncMock(
        return_value={
            "keyword_normalized": "pcb",
            "subscription_status": "not_started",
            "cancelled_tasks": 2,
        }
    )
    monkeypatch.setattr(collection_api.service, "stop_keyword", stop_keyword, raising=False)

    async with client:
        response = await client.post(
            "/admin/api/v1/collection-keywords/pcb/stop",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["subscription_status"] == "not_started"
    assert response.json()["data"]["cancelled_tasks"] == 2
    stop_keyword.assert_awaited_once_with(conn, keyword_normalized="pcb")


async def test_reset_collection_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    reset_keyword = AsyncMock(
        return_value={"keyword_normalized": "pcb", "subscription_status": "not_started"}
    )
    monkeypatch.setattr(collection_api.service, "reset_keyword", reset_keyword, raising=False)

    async with client:
        response = await client.post(
            "/admin/api/v1/collection-keywords/pcb/reset",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "keyword_normalized": "pcb",
        "subscription_status": "not_started",
    }
    reset_keyword.assert_awaited_once_with(conn, keyword_normalized="pcb")


async def test_retry_collection_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    retry_keyword = AsyncMock(
        return_value={"keyword_normalized": "pcb", "subscription_status": "pending"}
    )
    monkeypatch.setattr(collection_api.service, "retry_keyword", retry_keyword, raising=False)

    async with client:
        response = await client.post(
            "/admin/api/v1/collection-keywords/pcb/retry",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["subscription_status"] == "pending"
    retry_keyword.assert_awaited_once_with(conn, keyword_normalized="pcb")


async def test_get_collection_dashboard_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    get_dashboard = AsyncMock(
        return_value={
            "today_companies": 3,
            "today_contacts": 8,
            "running_count": 1,
            "paused_count": 2,
            "error_count": 1,
            "keywords": [{"keyword_normalized": "pcb"}],
        }
    )
    monkeypatch.setattr(collection_api.service, "get_dashboard", get_dashboard, raising=False)

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/dashboard",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["today_companies"] == 3
    assert payload["keywords"] == [{"keyword_normalized": "pcb"}]
    get_dashboard.assert_awaited_once_with(conn)


async def test_trigger_collection_rejects_direct_channel(monkeypatch) -> None:
    client, conn = await build_admin_client()
    trigger_collection = AsyncMock(
        side_effect=AppError(
            code="CHANNEL_NOT_AVAILABLE",
            message="外贸通直采已推迟至 V3.1+，当前仅支持 lixiaoyun 渠道",
            status_code=400,
        )
    )
    monkeypatch.setattr(collection_api.service, "trigger_collection", trigger_collection, raising=False)

    async with client:
        response = await client.post(
            "/admin/api/v1/collection-keywords/trigger",
            headers=auth_headers(),
            json={"keyword_normalized": "pcb", "channel": "waimao_tong"},
        )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "CHANNEL_NOT_AVAILABLE"
    trigger_collection.assert_awaited_once_with(
        conn,
        keyword_normalized="pcb",
        channel="waimao_tong",
    )


async def test_list_collection_raw_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    rows = [
        {
            "id": "raw-1",
            "name": "PCB Corp",
            "country": "IND",
            "domain": "pcb.example",
            "task_id": "task-1",
            "created_at": "2026-04-30T12:00:00+00:00",
            "source_id": "src-1",
        }
    ]
    list_raw_companies = AsyncMock(return_value=(rows, 12))
    monkeypatch.setattr(
        collection_api.service,
        "list_raw_companies",
        list_raw_companies,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/raw/waimaotong",
            headers=auth_headers(),
            params={"page": 2, "page_size": 5, "keyword": "PCB", "country": "IND"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"] == rows
    assert payload["pagination"] == {"cursor": None, "has_more": True, "total": 12}
    list_raw_companies.assert_awaited_once_with(
        conn,
        table="waimaotong",
        page=2,
        page_size=5,
        include_payload=False,
        keyword="PCB",
        country="IND",
        **RAW_FILTER_DEFAULTS,
    )


async def test_list_collection_raw_debug_payload_opt_in(monkeypatch) -> None:
    client, conn = await build_admin_client()
    rows = [
        {
            "id": "raw-1",
            "name": "PCB Corp",
            "country": "IND",
            "domain": "pcb.example",
            "task_id": None,
            "created_at": "2026-04-30T12:00:00+00:00",
            "raw_payload": {"source": "waimaotong"},
            "source_id": "src-1",
        }
    ]
    list_raw_companies = AsyncMock(return_value=(rows, 1))
    monkeypatch.setattr(
        collection_api.service,
        "list_raw_companies",
        list_raw_companies,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/raw/waimaotong",
            headers=auth_headers(),
            params={"include_payload": True},
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"][0]["raw_payload"] == {"source": "waimaotong"}
    list_raw_companies.assert_awaited_once_with(
        conn,
        table="waimaotong",
        page=1,
        page_size=20,
        include_payload=True,
        keyword=None,
        country=None,
        **RAW_FILTER_DEFAULTS,
    )


async def test_list_collection_clean_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    rows = [
        {
            "id": "clean-1",
            "name_normalized": "PCB CORP",
            "name_display": "PCB Corp",
            "country_iso3": "IND",
            "domain": "pcb.example",
            "sources": ["waimaotong_raw_companies"],
            "created_at": "2026-04-30T12:00:00+00:00",
        }
    ]
    list_clean_companies = AsyncMock(return_value=(rows, 7))
    monkeypatch.setattr(
        collection_api.service,
        "list_clean_companies",
        list_clean_companies,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/clean-companies",
            headers=auth_headers(),
            params={"page": 3, "page_size": 2, "keyword": "PCB"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"] == rows
    assert payload["pagination"] == {"cursor": None, "has_more": True, "total": 7}
    list_clean_companies.assert_awaited_once_with(
        conn,
        page=3,
        page_size=2,
        keyword="PCB",
        **CLEAN_FILTER_DEFAULTS,
    )


async def test_list_v3_clean_companies_accepts_shared_filter_contract(monkeypatch) -> None:
    client, conn = await build_admin_client()
    rows = [
        {
            "id": "clean-1",
            "name_normalized": "PCB CORP",
            "name": "PCB Corp",
            "country_iso3": "USA",
            "created_at": "2026-04-30T12:00:00+00:00",
        }
    ]
    list_v3_clean_companies = AsyncMock(return_value=(rows, 1))
    monkeypatch.setattr(
        collection_api.service,
        "list_v3_clean_companies",
        list_v3_clean_companies,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/clean/companies",
            headers=auth_headers(),
            params=[
                ("page", "2"),
                ("page_size", "10"),
                ("keyword", "PCB"),
                ("countries[]", "USA"),
                ("countries[]", "DEU"),
                ("sub_industries[]", "EMS"),
                ("product_tags[]", "rigid"),
                ("product_tags[]", "flex"),
                ("sources[]", "tendata"),
                ("employee_count_min", "100"),
                ("employee_count_max", "150"),
                ("trade_amount_min", "1000"),
                ("trade_amount_max", "9000"),
                ("trade_count_min", "2"),
                ("trade_count_max", "8"),
                ("contact_count_min", "4"),
                ("contact_count_max", "10"),
                ("founded_year_from", "2010"),
                ("founded_year_to", "2020"),
                ("pcb_supplier_presence", "has"),
            ],
        )

    assert response.status_code == 200, response.text
    list_v3_clean_companies.assert_awaited_once_with(
        conn,
        page=2,
        page_size=10,
        keyword="PCB",
        countries=["USA", "DEU"],
        sub_industries=["EMS"],
        product_tags=["rigid", "flex"],
        sources=["tendata"],
        employee_count_min=100,
        employee_count_max=150,
        trade_amount_min=1000.0,
        trade_amount_max=9000.0,
        trade_count_min=2,
        trade_count_max=8,
        contact_count_min=4,
        contact_count_max=10,
        founded_year_from=2010,
        founded_year_to=2020,
        pcb_supplier_presence="has",
        source_type=None,
    )


async def test_get_collection_cleanup_health_endpoint(monkeypatch) -> None:
    client, conn = await build_admin_client()
    get_cleanup_health = AsyncMock(
        return_value={
            "pending_count": 4,
            "oldest_pending_seconds": 90,
            "failed_exhausted_count": 1,
            "processed_per_minute": 6,
            "reconcile_a": [{"id": "1"}],
            "reconcile_b": [],
            "reconcile_c": [{"id": "2"}],
        }
    )
    monkeypatch.setattr(
        collection_api.service,
        "get_cleanup_health",
        get_cleanup_health,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/cleanup-health",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["pending_count"] == 4
    assert payload["reconcile_b"] == []
    get_cleanup_health.assert_awaited_once_with(conn)


async def test_collection_keyword_control_missing_keyword_returns_404(monkeypatch) -> None:
    missing_error = AppError(code="NOT_FOUND", message="关键词不存在", status_code=404)
    stop_keyword = AsyncMock(side_effect=missing_error)
    reset_keyword = AsyncMock(side_effect=missing_error)
    retry_keyword = AsyncMock(side_effect=missing_error)
    monkeypatch.setattr(collection_api.service, "stop_keyword", stop_keyword, raising=False)
    monkeypatch.setattr(collection_api.service, "reset_keyword", reset_keyword, raising=False)
    monkeypatch.setattr(collection_api.service, "retry_keyword", retry_keyword, raising=False)

    for action in ("stop", "reset", "retry"):
        client, _conn = await build_admin_client()
        async with client:
            response = await client.post(
                f"/admin/api/v1/collection-keywords/missing/{action}",
                headers=auth_headers(),
            )

        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_list_collection_raw_invalid_table_returns_422(monkeypatch) -> None:
    client, conn = await build_admin_client()
    list_raw_companies = AsyncMock(
        side_effect=AppError(
            code="VALIDATION_ERROR",
            message="table 必须是 waimaotong、tendata 或 lixiaoyun",
            status_code=422,
        )
    )
    monkeypatch.setattr(
        collection_api.service,
        "list_raw_companies",
        list_raw_companies,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/collection/raw/invalid",
            headers=auth_headers(),
        )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    list_raw_companies.assert_awaited_once_with(
        conn,
        table="invalid",
        page=1,
        page_size=20,
        include_payload=False,
        keyword=None,
        country=None,
        **RAW_FILTER_DEFAULTS,
    )


async def test_retry_collection_invalid_state_returns_422(monkeypatch) -> None:
    client, conn = await build_admin_client()
    retry_keyword = AsyncMock(
        side_effect=AppError(
            code="VALIDATION_ERROR",
            message="只允许在 error/paused 状态下重试",
            status_code=422,
        )
    )
    monkeypatch.setattr(collection_api.service, "retry_keyword", retry_keyword, raising=False)

    async with client:
        response = await client.post(
            "/admin/api/v1/collection-keywords/running/retry",
            headers=auth_headers(),
        )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"] == "只允许在 error/paused 状态下重试"
    retry_keyword.assert_awaited_once_with(conn, keyword_normalized="running")
