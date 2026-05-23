"""收件人选取逻辑测试 — 分类排序 + 每公司8人上限 + 邮箱去重 + 预览 API"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.core.errors import AppError
from app.services.tenant_messaging_service import TenantMessagingService

TENANT_ID = "t-001"
GROUP_ID = "g-001"


def _contact_row(
    *,
    company_id: str = "comp-1",
    contact_id: str,
    email: str,
    company_name: str = "Ilumac",
    company_domain: str = "ilumac.com",
    contact_name: str = "Test",
    contact_status: str = "available",
    is_sendable: bool = True,
    data_status: str = "ready",
    level_display_name: str | None = None,
):
    """构造 _recipients_from_group 返回的行 dict"""
    return {
        "tenant_company_id": company_id,
        "tenant_contact_id": contact_id,
        "source_ref": GROUP_ID,
        "company_name": company_name,
        "company_domain": company_domain,
        "contact_name": contact_name,
        "contact_email": email,
        "contact_status": contact_status,
        "is_sendable": is_sendable,
        "data_status": data_status,
        "is_valid_email": True,
        "level_display_name": level_display_name,
    }


# ── U2: _build_recipient_candidates 等级排序和限数 ──────────────────


class TestRecipientSelectionByLevel:
    """U2: 验证 _build_recipient_candidates 按等级排序+限8人的合约"""

    @pytest.mark.asyncio
    async def test_mixed_levels_returns_8_sorted(self):
        """AE1: 3A + 4B + 2X(is_sendable=false) + 3未分类 → 3A+4B+1未分类=8人，X排除"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        # 模拟 _recipients_from_group 返回新格式（已排序、已限数、已排除X级）
        rows = [
            # 3 个 A 级
            _contact_row(contact_id="c1", email="a1@ilumac.com", level_display_name="A级（决策层）"),
            _contact_row(contact_id="c2", email="a2@ilumac.com", level_display_name="A级（决策层）"),
            _contact_row(contact_id="c3", email="a3@ilumac.com", level_display_name="A级（决策层）"),
            # 4 个 B 级
            _contact_row(contact_id="c4", email="b1@ilumac.com", level_display_name="B级（管理层）"),
            _contact_row(contact_id="c5", email="b2@ilumac.com", level_display_name="B级（管理层）"),
            _contact_row(contact_id="c6", email="b3@ilumac.com", level_display_name="B级（管理层）"),
            _contact_row(contact_id="c7", email="b4@ilumac.com", level_display_name="B级（管理层）"),
            # 1 个未分类（SQL 层已限8人，X级已排除）
            _contact_row(contact_id="c10", email="u1@ilumac.com", level_display_name=None),
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        # 共 8 人，无排除
        valid = [c for c in candidates if c["excluded_reason"] is None]
        assert len(valid) == 8
        assert len(candidates) == 8

    @pytest.mark.asyncio
    async def test_fewer_than_8_all_selected(self):
        """AE2: 5个B级全部入选"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        rows = [
            _contact_row(contact_id=f"c{i}", email=f"b{i}@test.com", level_display_name="B级（管理层）")
            for i in range(5)
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        valid = [c for c in candidates if c["excluded_reason"] is None]
        assert len(valid) == 5

    @pytest.mark.asyncio
    async def test_all_unclassified_takes_first_8(self):
        """全部未分类，10人取前8"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        # SQL 层已限8人
        rows = [
            _contact_row(contact_id=f"c{i}", email=f"u{i}@test.com", level_display_name=None)
            for i in range(8)
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        valid = [c for c in candidates if c["excluded_reason"] is None]
        assert len(valid) == 8

    @pytest.mark.asyncio
    async def test_all_not_sendable_returns_zero(self):
        """全部 is_sendable=false（X级），SQL 层已排除，返回0人"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        # SQL 层已排除 is_sendable=false，返回空
        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=[]):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        assert len(candidates) == 0


# ── U4: 邮箱去重 ──────────────────────────────────────────────


class TestEmailDedup:
    """U4: 同一公司同一邮箱去重，保留等级最高记录"""

    @pytest.mark.asyncio
    async def test_same_company_same_email_deduped(self):
        """同一公司2条记录同一邮箱（A级 + B级），去重后保留A级"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        # SQL 层已去重，只返回A级那条
        rows = [
            _contact_row(contact_id="c1", email="shared@ilumac.com", level_display_name="A级（决策层）"),
            _contact_row(contact_id="c3", email="other@ilumac.com", level_display_name="B级（管理层）"),
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        emails = [c["contact_email"] for c in candidates if c["excluded_reason"] is None]
        assert len(emails) == 2
        # 确认没有重复邮箱
        assert len(set(emails)) == len(emails)

    @pytest.mark.asyncio
    async def test_different_companies_same_email_not_deduped(self):
        """不同公司同一邮箱不去重"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        rows = [
            _contact_row(company_id="comp-1", contact_id="c1", email="shared@test.com",
                         company_name="CompA", level_display_name="A级（决策层）"),
            _contact_row(company_id="comp-2", contact_id="c2", email="shared@test.com",
                         company_name="CompB", level_display_name="B级（管理层）"),
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        valid = [c for c in candidates if c["excluded_reason"] is None]
        assert len(valid) == 2


# ── U5: _build_recipient_candidates 新字段适配 ────────────────────


class TestBuildCandidatesNewFormat:
    """U5: _build_recipient_candidates 处理新格式行"""

    @pytest.mark.asyncio
    async def test_new_format_row_no_key_error(self):
        """新格式行（含 level_display_name）传入不报错"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        rows = [
            _contact_row(contact_id="c1", email="a@test.com", level_display_name="A级（决策层）"),
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        assert len(candidates) == 1
        c = candidates[0]
        assert c["contact_email"] == "a@test.com"
        assert c["company_name"] == "Ilumac"
        assert c["excluded_reason"] is None

    @pytest.mark.asyncio
    async def test_blacklisted_company_excluded(self):
        """黑名单公司的行标记为 excluded_reason=blacklisted"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        rows = [
            _contact_row(contact_id="c1", email="a@evil.com", company_domain="evil.com"),
        ]
        blacklist = [{"shared_company_id": None, "match_domain": "evil.com", "match_name_pattern": None}]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=blacklist):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        assert candidates[0]["excluded_reason"] == "blacklisted"

    @pytest.mark.asyncio
    async def test_is_sendable_false_excluded(self):
        """is_sendable=false 的行标记为 not_sendable（SQL 层已排除，但 Python 层兜底）"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        rows = [
            _contact_row(contact_id="c1", email="x@test.com", is_sendable=False, level_display_name="X级"),
        ]

        with patch.object(svc, "_recipients_from_group", new_callable=AsyncMock, return_value=rows):
            with patch.object(svc, "_load_blacklist", new_callable=AsyncMock, return_value=[]):
                candidates = await svc._build_recipient_candidates(
                    conn, tenant_id=TENANT_ID, recipient_source="group",
                    recipient_config={"group_id": GROUP_ID},
                )

        assert candidates[0]["excluded_reason"] == "not_sendable"


# ── U6: preview_recipients_for_group ─────────────────────────────


class TestPreviewRecipientsForGroup:
    """U6: 按公司分组返回 + summary 统计"""

    @pytest.mark.asyncio
    async def test_groups_by_company_with_summary(self):
        """3家公司共10条候选人，按公司分组后 summary 正确"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        mock_candidates = [
            {"tenant_company_id": "comp-1", "company_name": "CompA", "contact_name": "A1",
             "contact_email": "a1@a.com", "excluded_reason": None, "level_display_name": "A级",
             "tenant_contact_id": "c1", "company_domain": "a.com", "contact_status": "available",
             "data_status": "ready", "source_type": "group", "source_ref": GROUP_ID},
            {"tenant_company_id": "comp-1", "company_name": "CompA", "contact_name": "A2",
             "contact_email": "a2@a.com", "excluded_reason": None, "level_display_name": "B级",
             "tenant_contact_id": "c2", "company_domain": "a.com", "contact_status": "available",
             "data_status": "ready", "source_type": "group", "source_ref": GROUP_ID},
            {"tenant_company_id": "comp-2", "company_name": "CompB", "contact_name": "B1",
             "contact_email": "b1@b.com", "excluded_reason": None, "level_display_name": "A级",
             "tenant_contact_id": "c3", "company_domain": "b.com", "contact_status": "available",
             "data_status": "ready", "source_type": "group", "source_ref": GROUP_ID},
            {"tenant_company_id": "comp-3", "company_name": "CompC", "contact_name": "C1",
             "contact_email": "c1@c.com", "excluded_reason": "blacklisted", "level_display_name": None,
             "tenant_contact_id": "c4", "company_domain": "c.com", "contact_status": "available",
             "data_status": "ready", "source_type": "group", "source_ref": GROUP_ID},
        ]

        with patch.object(svc, "_validate_group_ownership", new_callable=AsyncMock):
            with patch.object(svc, "_build_recipient_candidates", new_callable=AsyncMock, return_value=mock_candidates):
                result = await svc.preview_recipients_for_group(conn, TENANT_ID, GROUP_ID)

        assert result["summary"]["company_count"] == 3
        # comp-1: 2, comp-2: 1, comp-3: 0 (blacklisted) = 3 有效收件人
        assert result["summary"]["recipient_count"] == 3
        assert len(result["companies"]) == 3

        comp_a = next(c for c in result["companies"] if c["company_name"] == "CompA")
        assert comp_a["recipient_count"] == 2
        assert len(comp_a["recipients"]) == 2

    @pytest.mark.asyncio
    async def test_all_excluded_company_shows_zero(self):
        """某公司全部被排除，recipient_count=0 但仍在列表中"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        mock_candidates = [
            {"tenant_company_id": "comp-1", "company_name": "CompA", "contact_name": "A1",
             "contact_email": "a1@a.com", "excluded_reason": "blacklisted", "level_display_name": None,
             "tenant_contact_id": "c1", "company_domain": "a.com", "contact_status": "available",
             "data_status": "ready", "source_type": "group", "source_ref": GROUP_ID},
        ]

        with patch.object(svc, "_validate_group_ownership", new_callable=AsyncMock):
            with patch.object(svc, "_build_recipient_candidates", new_callable=AsyncMock, return_value=mock_candidates):
                result = await svc.preview_recipients_for_group(conn, TENANT_ID, GROUP_ID)

        assert result["summary"]["company_count"] == 1
        assert result["summary"]["recipient_count"] == 0
        assert len(result["companies"]) == 1
        assert result["companies"][0]["recipient_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_group_returns_empty(self):
        """空群组返回空"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "_validate_group_ownership", new_callable=AsyncMock):
            with patch.object(svc, "_build_recipient_candidates", new_callable=AsyncMock, return_value=[]):
                result = await svc.preview_recipients_for_group(conn, TENANT_ID, GROUP_ID)

        assert result["summary"]["company_count"] == 0
        assert result["summary"]["recipient_count"] == 0
        assert result["companies"] == []


# ── U7: 群组校验 ────────────────────────────────────────────────


class TestPreviewGroupValidation:
    """U7: 无效 group_id 返回 422"""

    @pytest.mark.asyncio
    async def test_invalid_group_raises_422(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(
            svc, "_validate_group_ownership", new_callable=AsyncMock,
            side_effect=AppError(code="VALIDATION_ERROR", message="收件人分组不存在或不属于当前租户", status_code=422),
        ):
            with pytest.raises(AppError) as exc_info:
                await svc.preview_recipients_for_group(conn, TENANT_ID, "invalid-id")
            assert exc_info.value.status_code == 422


# ── U8: 路由层测试 ───────────────────────────────────────────────


class TestPreviewRecipientsRoute:
    """U8: GET /sending-plans/preview-recipients 路由"""

    @pytest.fixture
    def app(self):
        from app.main import create_app
        from app.security.dependencies import TenantAuthContext, get_current_tenant_user

        application = create_app()
        ctx = TenantAuthContext(
            tenant_id=TENANT_ID,
            tenant_slug="test-tenant",
            user_id="u-001",
            email="test@test.com",
            name="Test",
            roles=["admin"],
            must_change_pwd=False,
            connection=AsyncMock(),
        )
        application.dependency_overrides[get_current_tenant_user] = lambda: ctx
        yield application
        application.dependency_overrides.clear()

    @pytest.fixture
    async def client(self, app):
        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_preview_recipients_returns_200(self, client):
        mock_result = {
            "companies": [{"tenant_company_id": "c1", "company_name": "Test", "recipient_count": 2, "recipients": []}],
            "summary": {"company_count": 1, "recipient_count": 2},
        }
        with patch(
            "app.api.tenant.messaging.service.preview_recipients_for_group",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.get(
                "/t/test-tenant/api/v1/sending-plans/preview-recipients",
                params={"group_id": GROUP_ID},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "companies" in body["data"]
        assert body["data"]["summary"]["company_count"] == 1

    @pytest.mark.asyncio
    async def test_missing_group_id_returns_422(self, client):
        resp = await client.get("/t/test-tenant/api/v1/sending-plans/preview-recipients")
        assert resp.status_code == 422
