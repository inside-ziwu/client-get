from unittest.mock import AsyncMock

import httpx
import pytest

from app.integrations.collection import lixiaoyun as lixiaoyun_module
from app.integrations.collection.base import CollectionTask
from app.integrations.collection.lixiaoyun import LixiaoyunCollectionProvider

pytestmark = pytest.mark.asyncio


class FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body
        self.text = str(body)
        self.headers = {}

    def json(self) -> dict:
        return self._body


def make_provider() -> LixiaoyunCollectionProvider:
    provider = LixiaoyunCollectionProvider(
        [{"secret": "test-token", "account_no": "acct-1", "is_active": True}]
    )
    provider._search_headers = lambda _cred: {}
    provider._detail_headers = lambda _cred: {}
    return provider


def make_task(params: dict | None = None) -> CollectionTask:
    return CollectionTask(
        id="task-lixiaoyun",
        keyword="pcb",
        source_types=["lixiaoyun"],
        params=params or {},
    )


def search_response(items: list[dict]) -> FakeResponse:
    return FakeResponse(200, {"data": {"list": items}})


def base_info_response(
    company_id: str,
    ent_name_eng: str | None = "English Co",
    *,
    shape: str = "nested",
) -> FakeResponse:
    gs_info = {
        "entNameEng": ent_name_eng,
        "address": f"{company_id} register address",
        "regCapDisplay": "100万人民币",
        "regccap": "50万人民币",
        "legalperson": f"{company_id} legal",
        "uncid": f"{company_id}-uncid",
    }
    if shape == "direct":
        return FakeResponse(200, {"data": {"GSInfo": gs_info}})
    return FakeResponse(
        200,
        {"data": {"GSInfo": {"gsInfo": gs_info}}},
    )


def development_response(*, shape: str = "nested") -> FakeResponse:
    b2b_info = {"scale": "51-200人"}
    if shape == "b2binfo":
        return FakeResponse(200, {"data": {"B2B": {"B2BInfo": b2b_info}}})
    if shape == "direct":
        return FakeResponse(200, {"data": {"B2B": b2b_info}})
    return FakeResponse(
        200,
        {"data": {"B2B": {"b2b": {"B2BInfo": {"b2bInfo": b2b_info}}}}},
    )


def biz_card_response(company_id: str) -> FakeResponse:
    return FakeResponse(200, {"data": {"contactaddress": f"{company_id} contact address"}})


def contacts_response(contacts: list[dict] | None = None, *, shape: str = "list") -> FakeResponse:
    if shape == "contacts":
        return FakeResponse(200, {"data": {"contacts": contacts or []}})
    return FakeResponse(200, {"data": contacts or []})


async def collect_with_router(
    provider: LixiaoyunCollectionProvider,
    task: CollectionTask,
    search_items: list[dict],
    *,
    ent_name_eng: str | None = "English Co",
    contacts: list[dict] | None = None,
    contacts_shape: str = "list",
    detail_shape: str = "nested",
) -> tuple:
    async def router(_client, method: str, url: str, **kwargs) -> FakeResponse:
        if method == "POST" and url.endswith("/api_skb/v1/search"):
            page = kwargs["json"]["page"]
            return search_response(search_items if page == 1 else [])
        if method == "GET" and url.endswith("/api_skb/v1/companyDetail/sectionInfo"):
            section = kwargs["params"]["section"]
            company_id = kwargs["params"]["id"]
            if section == "BaseInfo":
                return base_info_response(company_id, ent_name_eng, shape=detail_shape)
            if section == "Development":
                return development_response(shape=detail_shape)
        if method == "GET" and url.endswith("/api_skb/v1/companyDetail/bizCard"):
            return biz_card_response(kwargs["params"]["id"])
        if method == "GET" and url.endswith("/api_skb/v1/clue/contacts"):
            return contacts_response(contacts, shape=contacts_shape)
        raise AssertionError(f"unexpected request: {method} {url}")

    provider._request_with_retry = AsyncMock(side_effect=router)
    payload = await provider.collect(task)
    return payload, provider._request_with_retry


async def test_max_competitors_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()
    items = [{"id": str(i), "companyName": f"公司{i}"} for i in range(1, 6)]

    payload, _mock = await collect_with_router(
        provider, make_task({"max_competitors": 2}), items
    )

    assert len(payload.competitors) == 2
    assert [company["source_id"] for company in payload.competitors] == ["1", "2"]


async def test_skip_source_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()
    items = [
        {"id": "id-1", "companyName": "公司1"},
        {"id": "id-2", "companyName": "公司2"},
        {"id": "id-3", "companyName": "公司3"},
    ]

    payload, _mock = await collect_with_router(
        provider, make_task({"skip_source_ids": ["id-1", "id-3"]}), items
    )

    assert len(payload.competitors) == 1
    assert payload.competitors[0]["source_id"] == "id-2"


@pytest.mark.parametrize("ent_name_eng", ["", None])
async def test_english_name_empty_no_fallback(
    monkeypatch: pytest.MonkeyPatch,
    ent_name_eng: str | None,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        ent_name_eng=ent_name_eng,
    )

    company = payload.competitors[0]
    assert company["company_name_en"] == ""
    assert company["company_name_en"] != company["name"]


async def test_contacts_not_in_payload_contacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()
    contacts = [
        {"name": "张三", "mobile": "13800000001", "position": "销售"},
        {"contactName": "李四", "phone": "13800000002", "title": "经理"},
    ]

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        contacts=contacts,
    )

    assert payload.contacts == []
    assert payload.competitors[0]["raw_payload"]["lx_contacts"] == [
        {"name": "张三", "phone": "13800000001", "position": "销售", "email": None},
        {"name": "李四", "phone": "13800000002", "position": "经理", "email": None},
    ]


async def test_detail_fields_parse_when_lixiaoyun_returns_direct_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        detail_shape="direct",
    )

    company = payload.competitors[0]
    assert company["company_name_en"] == "English Co"
    assert company["reg_capital"] == "100万人民币"
    assert company["employee_scale"] == "51-200人"
    assert company["reg_address"] == "id-1 register address"
    assert company["raw_payload"]["legalperson"] == "id-1 legal"


async def test_employee_scale_parse_when_lixiaoyun_returns_b2binfo_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        detail_shape="b2binfo",
    )

    company = payload.competitors[0]
    assert company["employee_scale"] == "51-200人"
    assert company["raw_payload"]["employee_scale"] == "51-200人"


async def test_contact_aliases_from_lixiaoyun_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        contacts=[
            {
                "contact_person": "王五",
                "mobilePhone": "13900000001",
                "positionName": "销售总监",
                "emailAddress": "wang@example.com",
            }
        ],
    )

    assert payload.competitors[0]["raw_payload"]["lx_contacts"] == [
        {
            "name": "王五",
            "phone": "13900000001",
            "position": "销售总监",
            "email": "wang@example.com",
        }
    ]


async def test_contacts_parse_lixiaoyun_contacts_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
        contacts_shape="contacts",
        contacts=[
            {
                "contact": "龚先生",
                "content": "18268883010",
                "positionContent": "高管",
            }
        ],
    )

    assert payload.competitors[0]["raw_payload"]["lx_contacts"] == [
        {
            "name": "龚先生",
            "phone": "18268883010",
            "position": "高管",
            "email": None,
        }
    ]


async def test_request_with_retry_retries_read_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_RETRY_BASE", 0)
    provider = make_provider()
    client = AsyncMock()
    client.request = AsyncMock(
        side_effect=[
            httpx.ReadTimeout("slow upstream"),
            search_response([{"id": "id-1", "companyName": "深圳样例公司"}]),
        ]
    )

    response = await provider._request_with_retry(client, "POST", "https://example.test/search")

    assert response.status_code == 200
    assert client.request.await_count == 2


async def test_request_page_size_defaults_to_10_and_caps_at_100(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()
    observed_per_page: list[int] = []

    async def router(_client, method: str, url: str, **kwargs) -> FakeResponse:
        if method == "POST" and url.endswith("/api_skb/v1/search"):
            observed_per_page.append(kwargs["json"]["per_page"])
            return search_response([])
        raise AssertionError(f"unexpected request: {method} {url}")

    provider._request_with_retry = AsyncMock(side_effect=router)

    await provider.collect(make_task())
    await provider.collect(make_task({"page_size": 250}))

    assert observed_per_page == [10, 100]


async def test_target_table_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
    )

    assert payload.competitors[0]["target_table"] == "lixiaoyun_raw_companies"


async def test_existing_tests_still_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lixiaoyun_module, "_CONTACTS_DELAY", 0)
    provider = make_provider()

    payload, _mock = await collect_with_router(
        provider,
        make_task(),
        [{"id": "id-1", "companyName": "深圳样例公司"}],
    )

    company = payload.competitors[0]
    assert payload.companies == []
    assert payload.contacts == []
    assert company["source_id"] == "id-1"
    assert company["name"] == "深圳样例公司"
    assert company["source_type"] == "lixiaoyun"
    assert company["raw_payload"]["employee_scale"] == "51-200人"
