from uuid import uuid4

from sqlalchemy import text

from app.core.ids import new_uuid
from app.services.keyword_service import (
    bind_tenant_keyword,
    get_or_create_keyword_master,
    normalize_keyword,
)
from app.services.tenant_settings_service import TenantSettingsService
from tests.helpers import make_engine


def test_normalize_keyword_merges_non_semantic_separators() -> None:
    assert normalize_keyword("P.C.B") == "pcb"
    assert normalize_keyword(" pcb ") == "pcb"
    assert normalize_keyword("PCB ") == "pcb"
    assert normalize_keyword("Ｐ．Ｃ．Ｂ") == "pcb"


def test_normalize_keyword_preserves_semantic_symbols() -> None:
    assert normalize_keyword("FR-4") == "fr-4"
    assert normalize_keyword("FR4") == "fr4"
    assert normalize_keyword("C++") == "c++"
    assert normalize_keyword("C") == "c"
    assert normalize_keyword("线路板") == "线路板"
    assert normalize_keyword("PCB-线路板") == "pcb-线路板"


async def test_bind_tenant_keyword_restores_deleted_row_without_refreshing_created_at() -> None:
    engine = make_engine()
    async with engine.connect() as conn:
        tx = await conn.begin()
        try:
            tenant_id = str(new_uuid())
            user_id = str(new_uuid())
            slug = f"kw-restore-{uuid4().hex[:8]}"
            await conn.execute(
                text(
                    """
                    INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                    VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
                    """
                ),
                {"tenant_id": tenant_id, "slug": slug},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                    VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                    """
                ),
                {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
            )

            keyword_master_id = await get_or_create_keyword_master(
                conn,
                keyword="P.C.B",
                keyword_normalized=normalize_keyword("P.C.B"),
            )
            created = await bind_tenant_keyword(
                conn,
                tenant_id=tenant_id,
                keyword_master_id=keyword_master_id,
                keyword_raw="P.C.B",
                created_by=user_id,
            )
            before = (
                await conn.execute(
                    text(
                        """
                        SELECT id, keyword_raw, created_by, created_at, status
                        FROM tenant_keyword
                        WHERE tenant_id = :tenant_id AND keyword_master_id = :keyword_master_id
                        """
                    ),
                    {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
                )
            ).mappings().one()

            await conn.execute(
                text(
                    """
                    UPDATE tenant_keyword
                    SET status = 'deleted'
                    WHERE tenant_id = :tenant_id AND keyword_master_id = :keyword_master_id
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )

            restored = await bind_tenant_keyword(
                conn,
                tenant_id=tenant_id,
                keyword_master_id=keyword_master_id,
                keyword_raw="PCB ",
                created_by=user_id,
            )
            after = (
                await conn.execute(
                    text(
                        """
                        SELECT id, keyword_raw, created_by, created_at, status
                        FROM tenant_keyword
                        WHERE tenant_id = :tenant_id AND keyword_master_id = :keyword_master_id
                        """
                    ),
                    {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
                )
            ).mappings().one()
        finally:
            await tx.rollback()
            await engine.dispose()

    assert created is True
    assert restored is False
    assert after["id"] == before["id"]
    assert after["created_at"] == before["created_at"]
    assert after["keyword_raw"] == "PCB "
    assert str(after["created_by"]) == user_id
    assert after["status"] == "active"


async def test_create_keyword_triggers_fan_out_for_subscription(monkeypatch) -> None:
    calls = []

    async def fake_fan_out(conn, tenant_id: str, keyword_master_id: str) -> dict:
        calls.append({"tenant_id": tenant_id, "keyword_master_id": keyword_master_id})
        return {"inserted": 1, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    monkeypatch.setattr(
        "app.services.tenant_settings_service.run_fan_out_for_tenant_keyword",
        fake_fan_out,
    )

    engine = make_engine()
    async with engine.connect() as conn:
        tx = await conn.begin()
        try:
            for statement in (
                """
                CREATE TEMP TABLE keyword_master (
                  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                  keyword text NOT NULL,
                  keyword_normalized text NOT NULL UNIQUE,
                  created_at timestamptz NOT NULL DEFAULT now()
                ) ON COMMIT DROP
                """,
                """
                CREATE TEMP TABLE tenant_keyword (
                  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                  tenant_id uuid NOT NULL,
                  keyword_master_id uuid NOT NULL,
                  keyword_raw text NOT NULL,
                  created_by uuid,
                  created_at timestamptz NOT NULL DEFAULT now(),
                  status text NOT NULL DEFAULT 'active',
                  UNIQUE (tenant_id, keyword_master_id)
                ) ON COMMIT DROP
                """,
                """
                CREATE TEMP TABLE collection_keywords (
                  id uuid PRIMARY KEY,
                  tenant_id uuid NOT NULL,
                  keyword text NOT NULL,
                  keyword_normalized text NOT NULL,
                  status text NOT NULL DEFAULT 'active',
                  created_by uuid,
                  keyword_master_id uuid,
                  created_at timestamptz NOT NULL DEFAULT now(),
                  updated_at timestamptz NOT NULL DEFAULT now()
                ) ON COMMIT DROP
                """,
            ):
                await conn.execute(text(statement))

            tenant_id = str(new_uuid())
            user_id = str(new_uuid())

            result = await TenantSettingsService().create_keyword(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={"keyword": "P.C.B"},
            )
        finally:
            await tx.rollback()
            await engine.dispose()

    assert result["keyword_normalized"] == "pcb"
    assert len(calls) == 1
    assert calls[0]["tenant_id"] == tenant_id
    assert calls[0]["keyword_master_id"]
