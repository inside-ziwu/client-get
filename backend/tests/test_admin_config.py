"""admin/config 路由冒烟测试

覆盖 app/api/admin/config.py 全部 38 个端点的路由层最小可用性，三类断言：
1. 冒烟：认证通过后路由可达，service 被调用，响应信封符合
   {"data": ...} / paginated / 204 约定；
2. 认证：不带 token 一律 401（验证每个端点都挂了平台认证依赖）；
3. 校验契约：缺 body → 422；空 payload {} 缺必填字段 → 期望 422。
   存量 `payload: dict` 裸收参端点缺字段会落到 service 层 KeyError → 500；
   已完成的端点由 Pydantic 在路由层返回 422。

service 层用 AsyncMock 替换（与 test_sending_plan_routes.py 同模式），不触库；
SQL 语义与数据断言走 /db-verify 开发库验证，不在本文件范围。

已知命名陷阱：PATCH/DELETE /ai-config/models/{model_id} 的路径参数是行 UUID
（ai_models.id），而 POST body 里的 "model_id" 是模型代码（存入 model_code 列），
两者不是一个东西，改造时勿混淆。
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.admin.config as config_module
import app.api.admin.tenants as tenants_module
from app.db.pools import get_connection
from app.main import create_app
from app.security.dependencies import PlatformAuthContext, get_current_platform_user

PREFIX = "/admin/api/v1"
ROW = {"id": "obj-001", "name": "冒烟"}
TENANT_ROW = {
    "id": "t-001",
    "name": "冒烟租户",
    "slug": "smoke-tenant",
    "industry": "PCB",
    "status": "active",
    "needs_onboarding": False,
}
NOBODY = object()  # 区分"不发 body"与"发空 body"

# (method, 路由模板, 实际请求 path, service 方法名, service 返回值, 期望状态码, 信封类型, 请求 body)
# 信封类型：success → {"data": ...}；paginated → {"data": [...], "pagination": ...}；
#           deleted → {"data": {"deleted": True}}；none → 204 空响应
SMOKE_CASES = [
    ("GET", "/dashboard/overview", "/dashboard/overview", "get_platform_dashboard", ROW, 200, "success", NOBODY),
    ("GET", "/scoring-templates", "/scoring-templates", "list_platform_scoring_templates", [ROW], 200, "paginated", NOBODY),
    # 已 Pydantic 化端点：body 须为最小合法 payload（校验先于 service 执行）
    ("POST", "/scoring-templates", "/scoring-templates", "create_platform_scoring_template", ROW, 200, "success",
     {"industry": "pcb", "name": "冒烟模板", "dimensions": []}),
    ("GET", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "get_platform_scoring_template", ROW, 200, "success", NOBODY),
    ("PUT", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "update_platform_scoring_template", ROW, 200, "success",
     {"name": "更新后评分模板"}),
    ("DELETE", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "delete_platform_scoring_template", None, 200, "deleted", NOBODY),
    ("GET", "/scoring-templates/{template_id}/versions", "/scoring-templates/tmpl-001/versions", "list_platform_scoring_template_versions", [ROW], 200, "paginated", NOBODY),
    ("GET", "/intelligence-sources", "/intelligence-sources", "list_intelligence_sources", [ROW], 200, "paginated", NOBODY),
    ("POST", "/intelligence-sources", "/intelligence-sources", "create_intelligence_source", ROW, 200, "success",
     {"name": "行业动态 RSS", "source_type": "rss"}),
    ("POST", "/intelligence-sources/batch-import", "/intelligence-sources/batch-import", "batch_import_intelligence_sources", [ROW], 200, "paginated", {"items": []}),
    ("PATCH", "/intelligence-sources/{source_id}", "/intelligence-sources/src-001", "patch_intelligence_source", ROW, 200, "success",
     {"name": "更新后情报源"}),
    ("DELETE", "/intelligence-sources/{source_id}", "/intelligence-sources/src-001", "delete_intelligence_source", None, 200, "deleted", NOBODY),
    ("GET", "/email-templates", "/email-templates", "list_platform_email_templates", [ROW], 200, "paginated", NOBODY),
    ("POST", "/email-templates", "/email-templates", "create_platform_email_template", ROW, 200, "success",
     {"industry": "pcb", "name": "冒烟邮件模板", "subject": "冒烟主题", "body_html": ""}),
    ("GET", "/email-templates/{template_id}", "/email-templates/et-001", "get_platform_email_template", ROW, 200, "success", NOBODY),
    ("PUT", "/email-templates/{template_id}", "/email-templates/et-001", "update_platform_email_template", ROW, 200, "success",
     {"name": "更新后邮件模板"}),
    ("DELETE", "/email-templates/{template_id}", "/email-templates/et-001", "delete_platform_email_template", None, 200, "deleted", NOBODY),
    ("GET", "/email-templates/{template_id}/preview", "/email-templates/et-001/preview", "get_platform_email_template_preview", ROW, 200, "success", NOBODY),
    ("GET", "/warmup-rules", "/warmup-rules", "list_warmup_rules", [ROW], 200, "paginated", NOBODY),
    ("PUT", "/warmup-rules", "/warmup-rules", "put_warmup_rules", ROW, 200, "success",
     {"name": "默认预热规则"}),
    ("GET", "/ai-config/models", "/ai-config/models", "list_ai_models", [ROW], 200, "paginated", NOBODY),
    ("POST", "/ai-config/models", "/ai-config/models", "create_ai_model", ROW, 200, "success",
     {"model_id": "openai/gpt-4.1-mini", "display_name": "GPT-4.1 Mini"}),
    ("PATCH", "/ai-config/models/{model_id}", "/ai-config/models/m-001", "patch_ai_model", ROW, 200, "success",
     {"display_name": "更新后模型"}),
    ("DELETE", "/ai-config/models/{model_id}", "/ai-config/models/m-001", "delete_ai_model", None, 200, "deleted", NOBODY),
    ("GET", "/ai-config/scene-defaults", "/ai-config/scene-defaults", "list_ai_scene_defaults", [ROW], 200, "paginated", NOBODY),
    ("PUT", "/ai-config/scene-defaults", "/ai-config/scene-defaults", "put_ai_scene_defaults", [ROW], 200, "success",
     [{"scene": "scoring", "model_id": "m-001"}]),
    ("GET", "/ai-config/pricing", "/ai-config/pricing", "get_ai_pricing", ROW, 200, "success", NOBODY),
    ("GET", "/tenants/{tenant_id}/users", "/tenants/t-001/users", "list_tenant_users", [ROW], 200, "paginated", NOBODY),
    ("POST", "/tenants/{tenant_id}/users", "/tenants/t-001/users", "create_tenant_user", ROW, 200, "success",
     {"email": "user@example.com", "name": "冒烟用户"}),
    ("PATCH", "/tenants/{tenant_id}/users/{user_id}", "/tenants/t-001/users/u-001", "update_tenant_user", ROW, 200, "success",
     {"name": "更新后用户"}),
    ("DELETE", "/tenants/{tenant_id}/users/{user_id}", "/tenants/t-001/users/u-001", "delete_tenant_user", None, 200, "deleted", NOBODY),
    ("GET", "/tenants/{tenant_id}/domains", "/tenants/t-001/domains", "list_tenant_domains", [ROW], 200, "paginated", NOBODY),
    ("POST", "/tenants/{tenant_id}/domains", "/tenants/t-001/domains", "create_tenant_domain", ROW, 200, "success",
     {"domain": "mail.example.com", "warmup_rule_id": "1a2b3c4d-0000-4000-8000-000000000001", "warmup_level": 1}),
    ("POST", "/tenants/{tenant_id}/domains/{domain_id}/verify", "/tenants/t-001/domains/d-001/verify", "verify_tenant_domain", ROW, 200, "success", NOBODY),
    ("GET", "/tenants/{tenant_id}/domains/{domain_id}", "/tenants/t-001/domains/d-001", "get_tenant_domain", ROW, 200, "success", NOBODY),
    ("PATCH", "/tenants/{tenant_id}/domains/{domain_id}", "/tenants/t-001/domains/d-001", "update_tenant_domain", ROW, 200, "success", {}),
    ("DELETE", "/tenants/{tenant_id}/domains/{domain_id}", "/tenants/t-001/domains/d-001", "delete_tenant_domain", None, 204, "none", NOBODY),
]

_IDS = [f"{c[0]}:{c[1]}" for c in SMOKE_CASES]


def _fake_platform_context() -> PlatformAuthContext:
    return PlatformAuthContext(
        platform_user_id="pu-001",
        email="admin@test.com",
        name="Admin",
        roles=["super_admin"],
        connection=AsyncMock(),
    )


async def _fake_connection():
    yield AsyncMock()


@pytest.fixture
def app():
    application = create_app()
    application.dependency_overrides[get_current_platform_user] = _fake_platform_context
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    # raise_app_exceptions=False：让 service 层未捕获异常走全局 500 handler，
    # 而不是在测试里直接抛出 —— 校验契约测试需要观察真实状态码
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def noauth_client():
    """不覆盖认证依赖的 client，用于 401 测试；仅替换 get_connection 避免触真实连接池"""
    application = create_app()
    application.dependency_overrides[get_connection] = _fake_connection
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    application.dependency_overrides.clear()


async def _request(client, method: str, url: str, body):
    if body is NOBODY:
        return await client.request(method, url)
    return await client.request(method, url, json=body)


# ── 1. 冒烟：路由可达 + 信封格式 ────────────────────────────────────────────


@pytest.mark.parametrize(
    "method,template,path,service_attr,service_return,status,envelope,body",
    SMOKE_CASES,
    ids=_IDS,
)
async def test_endpoint_smoke(
    client, monkeypatch, method, template, path, service_attr, service_return, status, envelope, body
):
    mock = AsyncMock(return_value=service_return)
    monkeypatch.setattr(config_module.service, service_attr, mock)

    resp = await _request(client, method, PREFIX + path, body)

    assert resp.status_code == status, resp.text
    mock.assert_awaited_once()

    if envelope == "success":
        assert resp.json() == {"data": service_return}
    elif envelope == "paginated":
        payload = resp.json()
        assert payload["data"] == service_return
        assert payload["pagination"]["total"] == len(service_return)
    elif envelope == "deleted":
        assert resp.json() == {"data": {"deleted": True}}
    elif envelope == "none":
        assert not resp.content


def test_smoke_cases_cover_all_config_routes():
    """守护：SMOKE_CASES 与 config router 实际路由一一对应，新增端点漏写用例会红"""
    actual = {
        (method, route.path)
        for route in config_module.router.routes
        for method in route.methods
        if method != "HEAD"
    }
    covered = {(c[0], c[1]) for c in SMOKE_CASES}
    assert covered == actual, (
        f"用例表与路由不一致；缺用例: {sorted(actual - covered)}；多余用例: {sorted(covered - actual)}"
    )


# ── 2. 认证：每个端点无 token 都必须 401 ────────────────────────────────────


@pytest.mark.parametrize(
    "method,template,path,service_attr,service_return,status,envelope,body",
    SMOKE_CASES,
    ids=_IDS,
)
async def test_endpoint_requires_auth(
    noauth_client, method, template, path, service_attr, service_return, status, envelope, body
):
    resp = await _request(noauth_client, method, PREFIX + path, body)

    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# ── 3. 校验契约 ─────────────────────────────────────────────────────────────

_BODY_CASES = [c for c in SMOKE_CASES if c[7] is not NOBODY]
_BODY_IDS = [f"{c[0]}:{c[1]}" for c in _BODY_CASES]


@pytest.mark.parametrize(
    "method,template,path,service_attr,service_return,status,envelope,body",
    _BODY_CASES,
    ids=_BODY_IDS,
)
async def test_missing_body_returns_422(
    client, method, template, path, service_attr, service_return, status, envelope, body
):
    """body 必填的端点：完全不发 body 必须 422（FastAPI 层校验，现状即应通过）"""
    resp = await client.request(method, PREFIX + path)
    assert resp.status_code == 422, resp.text


# 空 payload {} 应被参数校验拦下（422）。此处列出 service 层存在必填字段的端点。
_REQUIRED_FIELD_CASES = [
    pytest.param("POST", "/scoring-templates", "industry/name/dimensions",
                 id="POST:/scoring-templates"),
    pytest.param("POST", "/email-templates", "industry/name/subject/body_html",
                 id="POST:/email-templates"),
    pytest.param("POST", "/intelligence-sources", "name/source_type",
                 id="POST:/intelligence-sources"),
    pytest.param("PUT", "/warmup-rules", "name",
                 id="PUT:/warmup-rules"),
    pytest.param("POST", "/ai-config/models", "model_id/display_name",
                 id="POST:/ai-config/models"),
    pytest.param("POST", "/tenants/t-001/users", "email/name",
                 id="POST:/tenants/users"),
    pytest.param("POST", "/intelligence-sources/batch-import", "items",
                 id="POST:/intelligence-sources/batch-import"),
    pytest.param("POST", "/tenants/t-001/domains", "domain/warmup_rule_id/warmup_level",
                 id="POST:/tenants/domains"),
]


@pytest.mark.parametrize("method,path,required_fields", _REQUIRED_FIELD_CASES)
async def test_empty_payload_returns_422_not_500(client, method, path, required_fields):
    """缺必填字段应 422 而非 500 —— 裸 dict 收参改造完成后本组应转绿"""
    resp = await client.request(method, PREFIX + path, json={})
    assert resp.status_code == 422, (
        f"缺必填字段({required_fields})期望 422，实际 {resp.status_code}: {resp.text[:200]}"
    )


_SECOND_BATCH_INVALID_CASES = [
    pytest.param(
        "PATCH",
        "/ai-config/models/m-001",
        "patch_ai_model",
        {"provider": "x" * 51},
        id="PATCH:/ai-config/models",
    ),
    pytest.param(
        "PUT",
        "/ai-config/scene-defaults",
        "put_ai_scene_defaults",
        [{"scene": "unknown", "model_id": "m-001"}],
        id="PUT:/ai-config/scene-defaults",
    ),
    pytest.param(
        "PUT",
        "/scoring-templates/tmpl-001",
        "update_platform_scoring_template",
        {"industry": "x" * 101},
        id="PUT:/scoring-templates",
    ),
    pytest.param(
        "PUT",
        "/email-templates/et-001",
        "update_platform_email_template",
        {"category": "x" * 51},
        id="PUT:/email-templates",
    ),
]


@pytest.mark.parametrize(
    "method,path,service_attr,body",
    _SECOND_BATCH_INVALID_CASES,
)
async def test_second_batch_invalid_payload_returns_422(
    client, monkeypatch, method, path, service_attr, body
):
    """第二批端点应在路由边界拒绝违反数据库约束或请求契约的字段"""
    mock = AsyncMock(return_value=ROW)
    monkeypatch.setattr(config_module.service, service_attr, mock)

    resp = await client.request(method, PREFIX + path, json=body)

    assert resp.status_code == 422, resp.text
    mock.assert_not_awaited()


_SECOND_BATCH_PARTIAL_UPDATE_CASES = [
    pytest.param(
        "PATCH",
        "/ai-config/models/m-001",
        "patch_ai_model",
        {"display_name": "仅更新名称"},
        id="PATCH:/ai-config/models",
    ),
    pytest.param(
        "PUT",
        "/scoring-templates/tmpl-001",
        "update_platform_scoring_template",
        {"name": "仅更新名称"},
        id="PUT:/scoring-templates",
    ),
    pytest.param(
        "PUT",
        "/email-templates/et-001",
        "update_platform_email_template",
        {"name": "仅更新名称"},
        id="PUT:/email-templates",
    ),
]


@pytest.mark.parametrize(
    "method,path,service_attr,body",
    _SECOND_BATCH_PARTIAL_UPDATE_CASES,
)
async def test_second_batch_partial_update_only_passes_provided_fields(
    client, monkeypatch, method, path, service_attr, body
):
    """更新模型不得向 service 注入未提供的 None，以免破坏原有局部更新语义"""
    mock = AsyncMock(return_value=ROW)
    monkeypatch.setattr(config_module.service, service_attr, mock)

    resp = await client.request(method, PREFIX + path, json=body)

    assert resp.status_code == 200, resp.text
    assert mock.await_args.kwargs["payload"] == body


_THIRD_BATCH_INVALID_CASES = [
    pytest.param(
        config_module,
        "PATCH",
        "/tenants/t-001/users/u-001",
        "update_tenant_user",
        {"email": "not-an-email"},
        id="PATCH:/tenants/users",
    ),
    pytest.param(
        tenants_module,
        "PATCH",
        "/tenants/t-001",
        "update_tenant",
        {"contact_email": "not-an-email"},
        id="PATCH:/tenants",
    ),
    pytest.param(
        config_module,
        "POST",
        "/intelligence-sources/batch-import",
        "batch_import_intelligence_sources",
        {"items": [{"name": "非法情报源", "source_type": "unknown"}]},
        id="POST:/intelligence-sources/batch-import",
    ),
    pytest.param(
        config_module,
        "PATCH",
        "/intelligence-sources/src-001",
        "patch_intelligence_source",
        {"source_type": "unknown"},
        id="PATCH:/intelligence-sources",
    ),
    pytest.param(
        config_module,
        "POST",
        "/tenants/t-001/domains",
        "create_tenant_domain",
        {
            "domain": "x" * 256,
            "warmup_rule_id": "1a2b3c4d-0000-4000-8000-000000000001",
            "warmup_level": 1,
        },
        id="POST:/tenants/domains",
    ),
]


@pytest.mark.parametrize(
    "route_module,method,path,service_attr,body",
    _THIRD_BATCH_INVALID_CASES,
)
async def test_third_batch_invalid_payload_returns_422(
    client, monkeypatch, route_module, method, path, service_attr, body
):
    """第三批端点应在路由边界拒绝违反数据库约束或请求契约的字段"""
    service_return = TENANT_ROW if route_module is tenants_module else ROW
    mock = AsyncMock(return_value=service_return)
    monkeypatch.setattr(route_module.service, service_attr, mock)

    resp = await client.request(method, PREFIX + path, json=body)

    assert resp.status_code == 422, resp.text
    mock.assert_not_awaited()


_THIRD_BATCH_PARTIAL_UPDATE_CASES = [
    pytest.param(
        config_module,
        "/tenants/t-001/users/u-001",
        "update_tenant_user",
        {"name": "仅更新用户名称"},
        id="PATCH:/tenants/users",
    ),
    pytest.param(
        tenants_module,
        "/tenants/t-001",
        "update_tenant",
        {"name": "仅更新租户名称"},
        id="PATCH:/tenants",
    ),
    pytest.param(
        config_module,
        "/intelligence-sources/src-001",
        "patch_intelligence_source",
        {"name": "仅更新情报源名称"},
        id="PATCH:/intelligence-sources",
    ),
]


@pytest.mark.parametrize(
    "route_module,path,service_attr,body",
    _THIRD_BATCH_PARTIAL_UPDATE_CASES,
)
async def test_third_batch_partial_update_only_passes_provided_fields(
    client, monkeypatch, route_module, path, service_attr, body
):
    """第三批 PATCH 模型不得向 service 注入未提供的 None"""
    service_return = TENANT_ROW if route_module is tenants_module else ROW
    mock = AsyncMock(return_value=service_return)
    monkeypatch.setattr(route_module.service, service_attr, mock)

    resp = await client.patch(PREFIX + path, json=body)

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == service_return["id"]
    assert mock.await_args.kwargs["payload"] == body


async def test_tenant_update_missing_body_returns_422(client):
    """admin/tenants 的 PATCH 请求体保持必填"""
    resp = await client.patch(PREFIX + "/tenants/t-001")
    assert resp.status_code == 422, resp.text


async def test_batch_import_passes_validated_items_to_service(
    client, monkeypatch
):
    """batch-import 应将包装对象中的情报源列表传给 service"""
    mock = AsyncMock(return_value=[])
    monkeypatch.setattr(
        config_module.service,
        "batch_import_intelligence_sources",
        mock,
    )

    resp = await client.post(
        PREFIX + "/intelligence-sources/batch-import",
        json={"items": [{"name": "RSS 情报源", "source_type": "rss"}]},
    )

    assert resp.status_code == 200, resp.text
    assert mock.await_args.kwargs["items"] == [
        {"name": "RSS 情报源", "source_type": "rss"}
    ]


async def test_tenant_domain_update_rejects_out_of_range_warmup_level(
    client, monkeypatch
):
    """预热档位下限对齐 DB CHECK (warmup_level >= 1)；上限不设，由 service
    对预热规则表的 JOIN 校验兜底（规则可定义任意档位数）"""
    mock = AsyncMock(return_value=ROW)
    monkeypatch.setattr(config_module.service, "update_tenant_domain", mock)

    resp = await client.patch(
        PREFIX + "/tenants/t-001/domains/d-001",
        json={"warmup_level": 0},
    )

    assert resp.status_code == 422, resp.text
    mock.assert_not_awaited()


async def test_tenant_domain_update_only_passes_provided_fields(
    client, monkeypatch
):
    """租户域名 PATCH 不得向 service 注入未提供的 None"""
    mock = AsyncMock(return_value=ROW)
    monkeypatch.setattr(config_module.service, "update_tenant_domain", mock)
    body = {"sender_email": "sender@example.com"}

    resp = await client.patch(
        PREFIX + "/tenants/t-001/domains/d-001",
        json=body,
    )

    assert resp.status_code == 200, resp.text
    assert mock.await_args.kwargs["payload"] == body


async def test_tenant_domain_update_explicit_null_clears_sender_email(
    client, monkeypatch
):
    """显式传 sender_email: null 必须原样到达 service（键存在性=清空列），
    不得被 exclude_unset 丢弃——这是全模块唯一显式 null 有业务含义的字段"""
    mock = AsyncMock(return_value=ROW)
    monkeypatch.setattr(config_module.service, "update_tenant_domain", mock)

    resp = await client.patch(
        PREFIX + "/tenants/t-001/domains/d-001",
        json={"sender_email": None},
    )

    assert resp.status_code == 200, resp.text
    assert mock.await_args.kwargs["payload"] == {"sender_email": None}
