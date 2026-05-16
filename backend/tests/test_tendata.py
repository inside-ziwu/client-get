from unittest.mock import AsyncMock

import pytest

from app.core.errors import CredentialExpiredError
from app.integrations.collection.base import CollectionTask
from app.integrations.collection.tendata import TendataCollectionProvider


class FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body
        self.text = str(body)
        self.headers = {}

    def json(self) -> dict:
        return self._body


def make_provider() -> TendataCollectionProvider:
    return TendataCollectionProvider(
        [
            {
                "token": "8f0b3f3d-6664-4d20-a72d-30ffddfbcddd",
                "userId": "123456",
                "jsessionid": "B6D58F2D552132E905B8",
                "is_active": True,
            }
        ]
    )


def make_task(competitor_names: list[str] | None = None) -> CollectionTask:
    return CollectionTask(
        id="task-tendata",
        keyword="pcb",
        source_types=["tendata"],
        competitor_names=(
            ["Shenzhen PCB Supplier"] if competitor_names is None else competitor_names
        ),
        params={"max_buyers": 10},
    )


def t1_response(importer: str = "INDIGO PRINT SMART PRIVATE LIMITED") -> FakeResponse:
    return FakeResponse(
        200,
        {
            "total": 1,
            "size": 20,
            "page": 1,
            "items": [
                {
                    "importer": importer,
                    "exporter": "Shenzhen PCB Supplier",
                    "country": "India",
                    "productTag": "Printed circuit boards",
                    "sumOfUSD": 32000,
                    "database": "india",
                }
            ],
        },
    )


def brief_response(name: str = "INDIGO PRINT SMART PRIVATE LIMITED") -> FakeResponse:
    return FakeResponse(
        200,
        {
            "tid": "INDI6d2d38e51b0338f13b702e9613d9d44e",
            "globizId": "globiz-indi",
            "name": name,
            "country": "India",
            "website": "https://indigoprint.example",
            "taxNo": "AAFCI1234A",
            "aliases": ["INDIGO PRINT"],
            "moreInfo": {"source": "brief"},
        },
    )


def t3_response() -> FakeResponse:
    return FakeResponse(
        200,
        {
            "incorporationDate": "2018-07-12",
            "employeeNum": "51-200",
            "industryDesc": "Packaging and printing",
            "websites": ["https://indigoprint.example"],
        },
    )


def vot_response() -> FakeResponse:
    return FakeResponse(
        200,
        {"stats": {"total_sumOfMoney_sum": 19041400.37, "total_trades_sum": 1488}},
    )


def stats_response() -> FakeResponse:
    return FakeResponse(
        200,
        {
            "stats": {"sample": True},
            "exporter": {"results": [{"__gk": "Shenzhen PCB Supplier"}]},
            "top_items": [{"productTag": "PCB assembly"}],
        },
    )


def empty_contacts_response() -> FakeResponse:
    return FakeResponse(200, {"content": []})


async def default_router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
    if method == "POST" and url.endswith("/api/tradec1/v2/search"):
        return t1_response()
    if method == "GET" and url.endswith("/api/corp/v2/companies/brief/0"):
        return brief_response()
    if method == "GET" and "/api/corp/v2/companies/0/" in url:
        return t3_response()
    if method == "POST" and url.endswith("/volume_of_trade"):
        return vot_response()
    if method == "POST" and url.endswith("/reports/0/stats"):
        return stats_response()
    if method == "GET" and "/api/contactx/" in url:
        return empty_contacts_response()
    raise AssertionError(f"unexpected request: {method} {url}")


async def test_collect_basic() -> None:
    provider = make_provider()
    provider._request_with_retry = AsyncMock(side_effect=default_router)

    payload = await provider.collect(make_task())

    assert len(payload.companies) == 1
    company = payload.companies[0]
    assert company["tid"] == "INDI6d2d38e51b0338f13b702e9613d9d44e"
    assert company["target_table"] == "tendata_raw_companies"
    assert company["trade_amount_3y_usd"] == 19041400.37
    assert company["trade_count"] == 1488


async def test_contacts_dedup() -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "GET" and url.endswith("/api/contactx/v3/contacts/linkedin"):
            return FakeResponse(
                200,
                {
                    "content": [
                        {
                            "uniqueKey": "li-1",
                            "name": "Kunal Shah",
                            "position": "Director",
                            "personalEmail1": {"email": "kunal@posiflow.in^ESD"},
                            "emailVerify": True,
                        }
                    ]
                },
            )
        if method == "GET" and url.endswith("/api/contactx/v3/contacts/internet"):
            return FakeResponse(
                200,
                {
                    "content": [
                        {
                            "uniqueKey": "net-1",
                            "name": "Posiflow",
                            "email": "posiflow.in@gmail.com",
                            "important": "high",
                            "description": "Public company inbox",
                        }
                    ]
                },
            )
        if method == "GET" and url.endswith("/api/contactx/v2/contacts/more"):
            return FakeResponse(
                200,
                {
                    "content": [
                        {
                            "id": "more-1",
                            "name": "Kunal",
                            "position": "CEO",
                            "email": "kunal@posiflow.in",
                            "status": "verified",
                        }
                    ]
                },
            )
        return await default_router(_client, method, url, **_kwargs)

    provider._request_with_retry = AsyncMock(side_effect=router)

    payload = await provider.collect(make_task(["Posiflow PCB"]))

    contacts = payload.companies[0]["contacts"]
    emails = sorted(contact["email"] for contact in contacts)
    assert len(contacts) == 2
    assert emails == ["kunal@posiflow.in", "posiflow.in@gmail.com"]


async def test_brief_failure_skips_company() -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "GET" and url.endswith("/api/corp/v2/companies/brief/0"):
            return FakeResponse(404, {"message": "not found"})
        return await default_router(_client, method, url, **_kwargs)

    provider._request_with_retry = AsyncMock(side_effect=router)

    payload = await provider.collect(make_task())

    assert payload.companies == []


async def test_401_raises_credential_expired() -> None:
    provider = make_provider()
    provider._request_with_retry = AsyncMock(
        return_value=FakeResponse(401, {"message": "Unauthorized"})
    )

    with pytest.raises(CredentialExpiredError):
        await provider.collect(make_task())


async def test_401_in_response_body() -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "GET" and url.endswith("/api/corp/v2/companies/brief/0"):
            return FakeResponse(200, {"code": 401, "message": "未登录"})
        return await default_router(_client, method, url, **_kwargs)

    provider._request_with_retry = AsyncMock(side_effect=router)

    with pytest.raises(CredentialExpiredError):
        await provider.collect(make_task())


async def test_empty_competitor_names() -> None:
    provider = make_provider()
    provider._request_with_retry = AsyncMock(side_effect=AssertionError("should not request"))

    payload = await provider.collect(make_task([]))

    assert payload.companies == []
    assert payload.contacts == []
    assert payload.competitors == []
