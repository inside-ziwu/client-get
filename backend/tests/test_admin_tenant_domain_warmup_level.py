from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.admin_config_service import AdminConfigService
from tests.helpers import make_engine


async def _seed_tenant_domain_context(conn, *, levels: list[tuple[int, int]]) -> tuple[str, str, str]:
    tenant_id = str(new_uuid())
    platform_user_id = str(new_uuid())
    rule_id = str(new_uuid())
    slug = f"domain-warmup-{uuid4().hex[:8]}"

    await conn.execute(text("UPDATE warmup_rules SET is_active = false WHERE is_active = true"))
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:id, :name, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"id": tenant_id, "name": slug, "slug": slug},
    )
    await conn.execute(
        text(
            """
            INSERT INTO platform_users (id, email, password_hash, name, status)
            VALUES (:id, :email, 'hash', '测试平台用户', 'active')
            """
        ),
        {"id": platform_user_id, "email": f"{slug}@example.com"},
    )
    await conn.execute(
        text(
            """
            INSERT INTO warmup_rules (id, name, is_active, min_observation_emails, bounce_alert_rate, config)
            VALUES (:id, '测试预热规则', true, 20, 0.05, '{}'::jsonb)
            """
        ),
        {"id": rule_id},
    )
    for level, daily_limit in levels:
        await conn.execute(
            text(
                """
                INSERT INTO warmup_rule_levels (id, rule_id, level, daily_limit)
                VALUES (:id, :rule_id, :level, :daily_limit)
                """
            ),
            {
                "id": str(new_uuid()),
                "rule_id": rule_id,
                "level": level,
                "daily_limit": daily_limit,
            },
        )
    return tenant_id, platform_user_id, rule_id


async def test_create_tenant_domain_derives_daily_limit_for_status_and_history() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            nested = await conn.begin_nested()
            try:
                tenant_id, platform_user_id, rule_id = await _seed_tenant_domain_context(
                    conn,
                    levels=[(1, 50), (3, 180)],
                )

                domain = await AdminConfigService().create_tenant_domain(
                    conn,
                    tenant_id=tenant_id,
                    payload={
                        "domain": "Mail.Example.COM",
                        "warmup_rule_id": rule_id,
                        "warmup_level": 3,
                        "daily_limit": 999,
                    },
                    platform_user_id=platform_user_id,
                )

                assert domain["domain"] == "mail.example.com"
                assert domain["warmup_rule_id"] == rule_id
                assert domain["warmup_level"] == 3
                assert domain["daily_limit"] == 180

                history = (
                    await conn.execute(
                        text(
                            """
                            SELECT warmup_level, daily_limit
                            FROM domain_warmup_history
                            WHERE warmup_status_id = :domain_id
                            """
                        ),
                        {"domain_id": domain["id"]},
                    )
                ).mappings().one()
                assert history["warmup_level"] == 3
                assert history["daily_limit"] == 180
            finally:
                await nested.rollback()
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("rule_active", "submitted_level", "expected_message"),
    [
        (False, 2, "刷新"),
        (True, 6, "刷新"),
    ],
)
async def test_create_tenant_domain_rejects_stale_rule_or_missing_level(
    rule_active: bool,
    submitted_level: int,
    expected_message: str,
) -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            nested = await conn.begin_nested()
            try:
                tenant_id, platform_user_id, rule_id = await _seed_tenant_domain_context(
                    conn,
                    levels=[(2, 120)],
                )
                if not rule_active:
                    await conn.execute(
                        text("UPDATE warmup_rules SET is_active = false WHERE id = :rule_id"),
                        {"rule_id": rule_id},
                    )

                with pytest.raises(AppError) as exc_info:
                    await AdminConfigService().create_tenant_domain(
                        conn,
                        tenant_id=tenant_id,
                        payload={
                            "domain": f"invalid-{uuid4().hex[:8]}.example.com",
                            "warmup_rule_id": rule_id,
                            "warmup_level": submitted_level,
                        },
                        platform_user_id=platform_user_id,
                    )

                assert exc_info.value.code == "VALIDATION_ERROR"
                assert exc_info.value.status_code == 422
                assert expected_message in exc_info.value.message
            finally:
                await nested.rollback()
    finally:
        await engine.dispose()


async def test_create_tenant_domain_uses_latest_server_side_daily_limit() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            nested = await conn.begin_nested()
            try:
                tenant_id, platform_user_id, rule_id = await _seed_tenant_domain_context(
                    conn,
                    levels=[(4, 200)],
                )
                await conn.execute(
                    text(
                        """
                        UPDATE warmup_rule_levels
                        SET daily_limit = 260
                        WHERE rule_id = :rule_id AND level = 4
                        """
                    ),
                    {"rule_id": rule_id},
                )

                domain = await AdminConfigService().create_tenant_domain(
                    conn,
                    tenant_id=tenant_id,
                    payload={
                        "domain": f"latest-{uuid4().hex[:8]}.example.com",
                        "warmup_rule_id": rule_id,
                        "warmup_level": 4,
                        "daily_limit": 200,
                    },
                    platform_user_id=platform_user_id,
                )

                assert domain["warmup_level"] == 4
                assert domain["daily_limit"] == 260
            finally:
                await nested.rollback()
    finally:
        await engine.dispose()


async def test_create_tenant_domain_accepts_active_rule_level_above_six() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            nested = await conn.begin_nested()
            try:
                tenant_id, platform_user_id, rule_id = await _seed_tenant_domain_context(
                    conn,
                    levels=[(7, 120)],
                )

                domain = await AdminConfigService().create_tenant_domain(
                    conn,
                    tenant_id=tenant_id,
                    payload={
                        "domain": f"level-7-{uuid4().hex[:8]}.example.com",
                        "warmup_rule_id": rule_id,
                        "warmup_level": 7,
                    },
                    platform_user_id=platform_user_id,
                )

                assert domain["warmup_level"] == 7
                assert domain["daily_limit"] == 120
            finally:
                await nested.rollback()
    finally:
        await engine.dispose()
