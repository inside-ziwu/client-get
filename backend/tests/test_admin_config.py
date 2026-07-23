"""admin/config 路由冒烟测试

覆盖 app/api/admin/config.py 全部 38 个端点的路由层最小可用性，三类断言：
1. 冒烟：认证通过后路由可达，service 被调用，响应信封符合
   {"data": ...} / paginated / 204 约定；
2. 认证：不带 token 一律 401（验证每个端点都挂了平台认证依赖）；
3. 校验契约：缺 body → 422；空 payload {} 缺必填字段 → 期望 422。
   现状全部端点为 `payload: dict` 裸收参，缺字段会落到 service 层
   KeyError → 500，已用 xfail 记录，Pydantic 化改造后应转绿。

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
from app.db.pools import get_connection
from app.main import create_app
from app.security.dependencies import PlatformAuthContext, get_current_platform_user

PREFIX = "/admin/api/v1"
ROW = {"id": "obj-001", "name": "冒烟"}
NOBODY = object()  # 区分"不发 body"与"发空 body"

# (method, 路由模板, 实际请求 path, service 方法名, service 返回值, 期望状态码, 信封类型, 请求 body)
# 信封类型：success → {"data": ...}；paginated → {"data": [...], "pagination": ...}；
#           deleted → {"data": {"deleted": True}}；none → 204 空响应
SMOKE_CASES = [
    ("GET", "/dashboard/overview", "/dashboard/overview", "get_platform_dashboard", ROW, 200, "success", NOBODY),
    ("GET", "/scoring-templates", "/scoring-templates", "list_platform_scoring_templates", [ROW], 200, "paginated", NOBODY),
    ("POST", "/scoring-templates", "/scoring-templates", "create_platform_scoring_template", ROW, 200, "success", {}),
    ("GET", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "get_platform_scoring_template", ROW, 200, "success", NOBODY),
    ("PUT", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "update_platform_scoring_template", ROW, 200, "success", {}),
    ("DELETE", "/scoring-templates/{template_id}", "/scoring-templates/tmpl-001", "delete_platform_scoring_template", None, 200, "deleted", NOBODY),
    ("GET", "/scoring-templates/{template_id}/versions", "/scoring-templates/tmpl-001/versions", "list_platform_scoring_template_versions", [ROW], 200, "paginated", NOBODY),
    ("GET", "/intelligence-sources", "/intelligence-sources", "list_intelligence_sources", [ROW], 200, "paginated", NOBODY),
    ("POST", "/intelligence-sources", "/intelligence-sources", "create_intelligence_source", ROW, 200, "success", {}),
    ("POST", "/intelligence-sources/batch-import", "/intelligence-sources/batch-import", "batch_import_intelligence_sources", [ROW], 200, "paginated", {"items": []}),
    ("PATCH", "/intelligence-sources/{source_id}", "/intelligence-sources/src-001", "patch_intelligence_source", ROW, 200, "success", {}),
    ("DELETE", "/intelligence-sources/{source_id}", "/intelligence-sources/src-001", "delete_intelligence_source", None, 200, "deleted", NOBODY),
    ("GET", "/email-templates", "/email-templates", "list_platform_email_templates", [ROW], 200, "paginated", NOBODY),
    ("POST", "/email-templates", "/email-templates", "create_platform_email_template", ROW, 200, "success", {}),
    ("GET", "/email-templates/{template_id}", "/email-templates/et-001", "get_platform_email_template", ROW, 200, "success", NOBODY),
    ("PUT", "/email-templates/{template_id}", "/email-templates/et-001", "update_platform_email_template", ROW, 200, "success", {}),
    ("DELETE", "/email-templates/{template_id}", "/email-templates/et-001", "delete_platform_email_template", None, 200, "deleted", NOBODY),
    ("GET", "/email-templates/{template_id}/preview", "/email-templates/et-001/preview", "get_platform_email_template_preview", ROW, 200, "success", NOBODY),
    ("GET", "/warmup-rules", "/warmup-rules", "list_warmup_rules", [ROW], 200, "paginated", NOBODY),
    ("PUT", "/warmup-rules", "/warmup-rules", "put_warmup_rules", ROW, 200, "success", {}),
    ("GET", "/ai-config/models", "/ai-config/models", "list_ai_models", [ROW], 200, "paginated", NOBODY),
    ("POST", "/ai-config/models", "/ai-config/models", "create_ai_model", ROW, 200, "success", {}),
    ("PATCH", "/ai-config/models/{model_id}", "/ai-config/models/m-001", "patch_ai_model", ROW, 200, "success", {}),
    ("DELETE", "/ai-config/models/{model_id}", "/ai-config/models/m-001", "delete_ai_model", None, 200, "deleted", NOBODY),
    ("GET", "/ai-config/scene-defaults", "/ai-config/scene-defaults", "list_ai_scene_defaults", [ROW], 200, "paginated", NOBODY),
    ("PUT", "/ai-config/scene-defaults", "/ai-config/scene-defaults", "put_ai_scene_defaults", [ROW], 200, "success", []),
    ("GET", "/ai-config/pricing", "/ai-config/pricing", "get_ai_pricing", ROW, 200, "success", NOBODY),
    ("PUT", "/ai-config/pricing", "/ai-config/pricing", "put_ai_pricing", ROW, 200, "success", {}),
    ("GET", "/tenants/{tenant_id}/users", "/tenants/t-001/users", "list_tenant_users", [ROW], 200, "paginated", NOBODY),
    ("POST", "/tenants/{tenant_id}/users", "/tenants/t-001/users", "create_tenant_user", ROW, 200, "success", {}),
    ("PATCH", "/tenants/{tenant_id}/users/{user_id}", "/tenants/t-001/users/u-001", "update_tenant_user", ROW, 200, "success", {}),
    ("DELETE", "/tenants/{tenant_id}/users/{user_id}", "/tenants/t-001/users/u-001", "delete_tenant_user", None, 200, "deleted", NOBODY),
    ("GET", "/tenants/{tenant_id}/domains", "/tenants/t-001/domains", "list_tenant_domains", [ROW], 200, "paginated", NOBODY),
    ("POST", "/tenants/{tenant_id}/domains", "/tenants/t-001/domains", "create_tenant_domain", ROW, 200, "success", {}),
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


# 空 payload {} 应被参数校验拦下（422）；现状裸 dict 收参会穿透到 service 层
# 抛 KeyError → 500。此处只列 service 层用 payload["字段"] 硬取值的端点。
# 2026-07-23 实测：除 /tenants/{id}/domains（service 里有手写 AppError 422 校验）外
# 全部返回 500，已标 xfail 记录现状 —— 该端点 Pydantic 化改造后移除对应标记即转绿。
_XFAIL_BARE_DICT = pytest.mark.xfail(
    reason="裸 dict 收参：缺必填字段现返 500（service 层 KeyError），Pydantic 化后应 422",
    strict=False,
)
_REQUIRED_FIELD_CASES = [
    pytest.param("POST", "/scoring-templates", "industry/name/dimensions",
                 marks=_XFAIL_BARE_DICT, id="POST:/scoring-templates"),
    pytest.param("POST", "/email-templates", "industry/name",
                 marks=_XFAIL_BARE_DICT, id="POST:/email-templates"),
    pytest.param("POST", "/intelligence-sources", "name/source_type",
                 marks=_XFAIL_BARE_DICT, id="POST:/intelligence-sources"),
    pytest.param("PUT", "/warmup-rules", "name",
                 marks=_XFAIL_BARE_DICT, id="PUT:/warmup-rules"),
    pytest.param("POST", "/ai-config/models", "model_id/display_name",
                 marks=_XFAIL_BARE_DICT, id="POST:/ai-config/models"),
    pytest.param("POST", "/tenants/t-001/users", "email/name",
                 marks=_XFAIL_BARE_DICT, id="POST:/tenants/users"),
    pytest.param("POST", "/tenants/t-001/domains", "warmup_rule_id/warmup_level",
                 id="POST:/tenants/domains"),
]


@pytest.mark.parametrize("method,path,required_fields", _REQUIRED_FIELD_CASES)
async def test_empty_payload_returns_422_not_500(client, method, path, required_fields):
    """缺必填字段应 422 而非 500 —— 裸 dict 收参改造完成后本组应转绿"""
    resp = await client.request(method, PREFIX + path, json={})
    assert resp.status_code == 422, (
        f"缺必填字段({required_fields})期望 422，实际 {resp.status_code}: {resp.text[:200]}"
    )
