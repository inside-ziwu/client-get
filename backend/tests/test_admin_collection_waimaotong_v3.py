"""V3 waimaotong 合约测试：list / debug / contacts 端点。

复用 test_admin_collection_extras.py 的 AsyncMock + ASGI 模式。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.api.admin import collection as collection_api
from app.main import create_app
from app.security.dependencies import get_current_platform_user
from app.security.jwt import create_access_token


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


# --- V3 waimaotong list 合约测试 ---


async def test_v3_waimaotong_list_basic(monkeypatch) -> None:
    """验证基本列表返回 19 字段响应格式。"""
    client, conn = await build_admin_client()
    mock_rows = [
        {
            "id": "1",
            "company_name": "Acme Corp",
            "country": "China",
            "domain": "acme.com",
            "industry": "Electronics",
            "employee_size": "50-100",
            "founded_year": 2010,
            "full_address": "Shenzhen, China",
            "source_keyword": "电路",
            "source_competitor": "CompetitorX",
            "source_type": "buyer",
            "contacts_count": 5,
            "email_count": 3,
            "has_detail": True,
            "has_contacts": True,
            "id_verified": True,
            "website": "https://acme.com",
            "api_company_id": "api-123",
            "created_at": "2026-05-01T00:00:00+00:00",
        }
    ]
    mock_list = AsyncMock(return_value=(mock_rows, 1))
    monkeypatch.setattr(
        collection_api.service, "list_v3_raw_companies", mock_list, raising=False
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/raw/waimaotong/companies?page=1&page_size=20",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"][0]["company_name"] == "Acme Corp"
    assert body["data"][0]["country"] == "China"
    assert body["data"][0]["source_keyword"] == "电路"
    assert body["pagination"]["total"] == 1


async def test_v3_waimaotong_list_filters_passthrough(monkeypatch) -> None:
    """验证 source_keyword, source_competitor, has_contacts 参数透传。"""
    client, conn = await build_admin_client()
    mock_list = AsyncMock(return_value=([], 0))
    monkeypatch.setattr(
        collection_api.service, "list_v3_raw_companies", mock_list, raising=False
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/raw/waimaotong/companies"
            "?source_keyword=电路&source_competitor=某公司&has_contacts=true",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["source_keyword"] == "电路"
    assert call_kwargs["source_competitor"] == "某公司"
    assert call_kwargs["has_contacts"] is True


# --- V3 waimaotong debug 合约测试 ---


async def test_v3_waimaotong_debug_dict_response(monkeypatch) -> None:
    """验证 debug 返回 dict(row) 格式，无硬编码 payload 键。"""
    client, conn = await build_admin_client()
    mock_debug = AsyncMock(
        return_value={
            "id": "42",
            "provider": "waimaotong",
            "company_name": "Debug Corp",
            "country": "India",
            "domain": "debug.in",
            "industry": "Software",
            "phone": "+91-123",
            "employee_size": "200+",
            "founded_year": 2005,
            "description": "A test company",
            "full_address": "Mumbai",
            "website": "https://debug.in",
            "products": ["PCB", "LED"],
            "source_tags": ["tag1"],
            "source_keyword": "线路",
            "source_competitor": "Rival Inc",
            "source_type": "buyer",
            "id_verified": True,
            "api_company_id": "debug-api-42",
            "contacts_count": 10,
            "email_count": 7,
            "has_detail": True,
            "has_contacts": True,
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-10T00:00:00+00:00",
        }
    )
    monkeypatch.setattr(
        collection_api.service, "get_v3_raw_company_debug", mock_debug, raising=False
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/raw/waimaotong/companies/42/debug",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    # dict(row) 模式：直接返回字段，无 raw_payload / search_payload 等硬编码键
    assert data["company_name"] == "Debug Corp"
    assert data["country"] == "India"
    assert "raw_payload" not in data
    assert "search_payload" not in data
    assert "detail_payload" not in data
    assert "trade_payload" not in data


# --- V3 waimaotong contacts 合约测试 ---


async def test_v3_waimaotong_contacts_list(monkeypatch) -> None:
    """验证联系人列表返回格式。"""
    client, conn = await build_admin_client()
    mock_contacts = AsyncMock(
        return_value=[
            {
                "id": "1",
                "raw_company_id": "42",
                "source_contact_id": "sc-1",
                "name": "张三",
                "position": "销售经理",
                "department": None,
                "email": "zhang@example.com",
                "email_status": "valid",
                "phone": "+86-123",
                "linkedin": "https://linkedin.com/in/zhang",
                "source": "apollo",
                "confidence": 0.95,
                "created_at": "2026-05-01T00:00:00+00:00",
            }
        ]
    )
    monkeypatch.setattr(
        collection_api.service,
        "list_v3_raw_company_contacts",
        mock_contacts,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/raw/waimaotong/companies/42/contacts",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["data"]) == 1
    contact = body["data"][0]
    assert contact["name"] == "张三"
    assert contact["email"] == "zhang@example.com"
    assert contact["email_status"] == "valid"
    assert contact["linkedin"] == "https://linkedin.com/in/zhang"
    # mobile / whatsapp 不在响应中
    assert "mobile" not in contact or contact.get("mobile") is None
    assert "whatsapp" not in contact


async def test_v3_waimaotong_contacts_empty(monkeypatch) -> None:
    """验证联系人为空时返回空列表。"""
    client, conn = await build_admin_client()
    mock_contacts = AsyncMock(return_value=[])
    monkeypatch.setattr(
        collection_api.service,
        "list_v3_raw_company_contacts",
        mock_contacts,
        raising=False,
    )

    async with client:
        response = await client.get(
            "/admin/api/v1/raw/waimaotong/companies/999/contacts",
            headers=auth_headers(),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0
