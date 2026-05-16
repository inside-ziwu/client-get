"""同行公司清洗服务测试。

覆盖 tasks.md 6.1 规划的 15 个核心路径 test cases:
- normalize_website_host (4 case)
- derive_identity (3 case)
- _build_display_set_clause D1 最新覆盖 (2 case)
- source_id 双向复用 D2 (2 case)
- _upsert_peer_contact 三级去重 + 升级场景 D3 (5 case)
- refresh_peer_contact_count (1 case)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.peer_company_cleaning_service import (
    PeerCompanyCleaningService,
    PeerIdentity,
    _build_display_set_clause,
    normalize_website_host,
)


# ── normalize_website_host (4 case) ──────────────────────


class TestNormalizeWebsiteHost:
    def test_strips_protocol_and_www(self):
        assert normalize_website_host("https://www.example.com/path") == "example.com"

    def test_handles_bare_domain(self):
        assert normalize_website_host("example.com") == "example.com"

    def test_lowercases_and_strips(self):
        assert normalize_website_host("  WWW.Example.COM.  ") == "example.com"

    def test_returns_none_for_empty(self):
        assert normalize_website_host(None) is None
        assert normalize_website_host("") is None
        assert normalize_website_host("   ") is None


# ── derive_identity (3 case) ──────────────────────


class TestDeriveIdentity:
    def setup_method(self):
        self.svc = PeerCompanyCleaningService()

    def test_website_host_identity(self):
        identity = self.svc.derive_identity({"domain": "https://www.example.com"})
        assert identity == PeerIdentity(
            identity_type="website_host",
            identity_value="example.com",
            identity_source="website_host",
            identity_confidence=1.0,
        )

    def test_source_id_fallback(self):
        identity = self.svc.derive_identity({"source_id": "lx_123"})
        assert identity == PeerIdentity(
            identity_type="source_id",
            identity_value="lx_123",
            identity_source="lixiaoyun_source_id",
            identity_confidence=0.8,
        )

    def test_none_when_no_identity(self):
        identity = self.svc.derive_identity({})
        assert identity is None


# ── _build_display_set_clause D1 最新覆盖 (2 case) ──────────────────────


class TestBuildDisplaySetClause:
    def test_generates_correct_sql_for_text_fields(self):
        clause = _build_display_set_clause("peer_companies")
        # D1: 新值非空覆盖旧值 — COALESCE(NULLIF(new, ''), existing)
        assert "COALESCE(NULLIF(:name, ''), peer_companies.name)" in clause
        assert "COALESCE(NULLIF(:english_name, ''), peer_companies.english_name)" in clause

    def test_generates_correct_sql_for_date_fields(self):
        clause = _build_display_set_clause("peer_companies")
        # date 字段不做 NULLIF 空字符串处理
        assert "COALESCE(:esdate, peer_companies.esdate)" in clause


# ── source_id 双向复用 D2 (2 case) ──────────────────────


class TestSourceIdBidirectionalReuse:
    """D2: 任何带 source_id 的 raw 都先查 peer_company_sources 同 source_id 已有映射。"""

    def setup_method(self):
        self.svc = PeerCompanyCleaningService()

    @pytest.mark.asyncio
    async def test_reuse_peer_via_source_id_when_no_domain(self):
        """正向：raw 无 domain → identity=source_id → 同 source_id 已有 peer → 复用。"""
        conn = AsyncMock()
        existing_peer_id = "peer-aaa"

        # 第一次查询（raw_company_id 查 existing）→ 无
        # 第二次查询（source_id 查 existing）→ 有
        first_result = MagicMock()
        first_result.mappings.return_value.first.return_value = None

        second_result = MagicMock()
        second_result.mappings.return_value.first.return_value = {"peer_company_id": existing_peer_id}

        # _update_existing_peer_display, _upsert_peer_keywords, _upsert_peer_source, refresh_peer_contact_count
        subsequent_results = [MagicMock() for _ in range(4)]

        conn.execute = AsyncMock(side_effect=[first_result, second_result, *subsequent_results])

        result = await self.svc.clean_raw_company(
            conn,
            raw_company_id=999,
            row={"source_id": "lx_123", "name": "公司A"},
            upsert_contacts=False,
        )
        assert result == existing_peer_id

    @pytest.mark.asyncio
    async def test_reuse_peer_via_source_id_when_has_domain(self):
        """反向：raw 有 domain → identity=website_host → 但同 source_id 已有 peer → 也复用。"""
        conn = AsyncMock()
        existing_peer_id = "peer-bbb"

        # 第一次查询（raw_company_id）→ 无
        # 第二次查询（source_id）→ 有
        first_result = MagicMock()
        first_result.mappings.return_value.first.return_value = None

        second_result = MagicMock()
        second_result.mappings.return_value.first.return_value = {"peer_company_id": existing_peer_id}

        subsequent_results = [MagicMock() for _ in range(4)]
        conn.execute = AsyncMock(side_effect=[first_result, second_result, *subsequent_results])

        result = await self.svc.clean_raw_company(
            conn,
            raw_company_id=1000,
            row={"domain": "example.com", "source_id": "lx_123", "name": "公司B"},
            upsert_contacts=False,
        )
        assert result == existing_peer_id


# ── _upsert_peer_contact 三级去重 + 升级 D3 (5 case) ──────────────────────


class TestUpsertPeerContact:
    def setup_method(self):
        self.svc = PeerCompanyCleaningService()

    @pytest.mark.asyncio
    async def test_skip_contact_without_name_and_email(self):
        """无 name 且无 email 的联系人跳过。"""
        conn = AsyncMock()
        await self.svc._upsert_peer_contact(
            conn,
            peer_company_id="peer-1",
            raw_company_id=1,
            contact={"phone": "1234"},
        )
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_normalization(self):
        """D11: email 做 lower(trim()) 规范化。"""
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock())

        await self.svc._upsert_peer_contact(
            conn,
            peer_company_id="peer-1",
            raw_company_id=1,
            contact={"name": "张三", "email": "  Zhang@Example.COM  "},
        )
        # 检查传给 SQL 的 email 参数已规范化
        call_args = conn.execute.call_args_list[-1]
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("parameters", {})
        assert params["email"] == "zhang@example.com"

    @pytest.mark.asyncio
    async def test_insert_contact_with_email(self):
        """有 email 的联系人正常插入。"""
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock())

        await self.svc._upsert_peer_contact(
            conn,
            peer_company_id="peer-1",
            raw_company_id=1,
            contact={"name": "张三", "email": "zhang@example.com", "position": "经理"},
        )
        # 应该调用了 INSERT (无 source_contact_id → 跳过第一步查询)
        assert conn.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_upgrade_contact_with_email_via_source_contact_id(self):
        """D3 升级场景：已有 source_contact_id 行无 email → 新数据补上 email → UPDATE。"""
        conn = AsyncMock()

        # 第一步查询：按 source_contact_id 找到已有行，且无 email
        existing_result = MagicMock()
        existing_result.mappings.return_value.first.return_value = {"id": 42, "email": None}

        # UPDATE 结果
        update_result = MagicMock()

        conn.execute = AsyncMock(side_effect=[existing_result, update_result])

        await self.svc._upsert_peer_contact(
            conn,
            peer_company_id="peer-1",
            raw_company_id=2,
            contact={
                "name": "李四",
                "email": "li@example.com",
                "source_contact_id": "ct_789",
            },
        )
        # 应该是 SELECT + UPDATE（2 次调用），不是 INSERT
        assert conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_insert_contact_with_source_contact_id_no_email(self):
        """source_contact_id 去重：无 email 时按 source_contact_id 去重插入。"""
        conn = AsyncMock()

        # 第一步查询：按 source_contact_id 未找到已有行
        existing_result = MagicMock()
        existing_result.mappings.return_value.first.return_value = None

        # INSERT 结果
        insert_result = MagicMock()

        conn.execute = AsyncMock(side_effect=[existing_result, insert_result])

        await self.svc._upsert_peer_contact(
            conn,
            peer_company_id="peer-1",
            raw_company_id=3,
            contact={"name": "王五", "source_contact_id": "ct_999"},
        )
        # SELECT（无结果）+ INSERT
        assert conn.execute.call_count == 2


# ── refresh_peer_contact_count (1 case) ──────────────────────


class TestRefreshPeerContactCount:
    @pytest.mark.asyncio
    async def test_updates_count_from_contacts_table(self):
        """D3: 直接从 peer_company_contacts 计数。"""
        svc = PeerCompanyCleaningService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock())

        await svc.refresh_peer_contact_count(conn, peer_id="peer-1")
        # 确认执行了 UPDATE 语句
        conn.execute.assert_called_once()
        sql_text = str(conn.execute.call_args[0][0].text)
        assert "peer_company_contacts" in sql_text
        assert "COUNT(*)" in sql_text
