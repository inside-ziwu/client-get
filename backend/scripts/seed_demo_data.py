import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.config import get_settings
from app.security.passwords import hash_password
from app.services.admin_config_service import AdminConfigService
from app.services.tenant_messaging_service import TenantMessagingService
from app.services.tenant_ops_service import TenantOpsService
from app.services.tenant_query_service import TenantQueryService
from app.services.tenant_service import TenantService
from app.services.tenant_settings_service import TenantSettingsService
from app.services.webhook_service import WebhookService


@dataclass(frozen=True)
class DemoTenantConfig:
    name: str
    slug: str
    industry: str
    admin_email: str
    admin_name: str
    admin_password: str
    contact_name: str
    contact_phone: str
    completed: bool


ADMIN_PASSWORD = "change-me-now"
TENANT_PASSWORD = "ChangeMe123!"

TENANTS = [
    DemoTenantConfig(
        name="Acme PCB Trading",
        slug="acme-pcb",
        industry="PCB",
        admin_email="owner@acme.example.com",
        admin_name="Acme Owner",
        admin_password=TENANT_PASSWORD,
        contact_name="Acme Owner",
        contact_phone="13800000001",
        completed=False,
    ),
    DemoTenantConfig(
        name="Globex Circuits",
        slug="globex-pcb",
        industry="PCB",
        admin_email="owner@globex.example.com",
        admin_name="Globex Owner",
        admin_password=TENANT_PASSWORD,
        contact_name="Globex Owner",
        contact_phone="13800000002",
        completed=True,
    ),
]


tenant_service = TenantService()
admin_config_service = AdminConfigService()
tenant_ops_service = TenantOpsService()
tenant_query_service = TenantQueryService()
tenant_settings_service = TenantSettingsService()
tenant_messaging_service = TenantMessagingService()
webhook_service = WebhookService()


async def get_platform_admin_id(conn: AsyncConnection) -> str:
    settings = get_settings()
    result = await conn.execute(
        text(
            """
            SELECT id
            FROM platform_users
            WHERE lower(email) = lower(:email)
            LIMIT 1
            """
        ),
        {"email": settings.admin_email},
    )
    platform_user_id = result.scalar_one_or_none()
    if platform_user_id is None:
        raise RuntimeError(
            f"未找到平台管理员 {settings.admin_email}，请先执行 migrations 或 bootstrap_platform_admin.py"
        )
    return str(platform_user_id)


async def ensure_tenant(conn: AsyncConnection, platform_user_id: str, cfg: DemoTenantConfig) -> dict:
    result = await conn.execute(
        text(
            """
            SELECT id
            FROM tenants
            WHERE slug = :slug
            LIMIT 1
            """
        ),
        {"slug": cfg.slug},
    )
    tenant_id = result.scalar_one_or_none()
    if tenant_id is None:
        tenant = await tenant_service.create_tenant(
            conn,
            platform_user_id=platform_user_id,
            payload={
                "name": cfg.name,
                "slug": cfg.slug,
                "industry": cfg.industry,
                "contact_name": cfg.contact_name,
                "contact_phone": cfg.contact_phone,
                "admin_email": cfg.admin_email,
                "admin_name": cfg.admin_name,
                "admin_password": cfg.admin_password,
            },
        )
        return tenant
    return await tenant_service.get_tenant(conn, str(tenant_id))


async def get_tenant_admin_user_id(conn: AsyncConnection, tenant_id: str, email: str, name: str) -> str:
    result = await conn.execute(
        text(
            """
            SELECT u.id, u.email
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id AND ur.tenant_id = u.tenant_id
            WHERE u.tenant_id = :tenant_id
            GROUP BY u.id
            ORDER BY
              CASE WHEN lower(u.email) = lower(:email) THEN 0 ELSE 1 END,
              CASE WHEN bool_or(ur.role = 'admin') THEN 0 ELSE 1 END,
              min(u.created_at) ASC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "email": email},
    )
    row = result.mappings().first()
    if row is None:
        raise RuntimeError(f"未找到租户管理员用户 {email}")
    user_id = str(row["id"])
    if str(row["email"]).lower() != email.lower():
        await conn.execute(
            text(
                """
                UPDATE users
                SET email = :email,
                    name = :name,
                    status = 'active',
                    updated_at = now()
                WHERE id = :user_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "email": email, "name": name},
        )
    return user_id


async def ensure_login_state(conn: AsyncConnection, tenant_id: str, user_id: str, password: str, completed: bool) -> None:
    await conn.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash,
                must_change_pwd = :must_change_pwd,
                status = 'active',
                updated_at = now()
            WHERE id = :user_id AND tenant_id = :tenant_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "password_hash": hash_password(password),
            "must_change_pwd": not completed,
        },
    )
    if completed:
        await conn.execute(
            text(
                """
                UPDATE tenants
                SET needs_onboarding = false,
                    updated_at = now()
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )


async def ensure_domain(conn: AsyncConnection, tenant_id: str, platform_user_id: str, domain: str) -> dict:
    existing = await admin_config_service.list_tenant_domains(conn, tenant_id)
    match = next((item for item in existing if item["domain"] == domain), None)
    if match is None:
        match = await admin_config_service.create_tenant_domain(
            conn,
            tenant_id=tenant_id,
            payload={
                "domain": domain,
                "spf_record": f"v=spf1 include:{domain} ~all",
                "dkim_record": f"k=rsa; p=demo-{domain}",
                "dmarc_record": f"v=DMARC1; p=none; rua=mailto:dmarc@{domain}",
                "verification_status": "pending",
                "warmup_level": 3,
                "daily_limit": 200,
            },
            platform_user_id=platform_user_id,
        )
    if match["verification_status"] != "verified":
        match = await admin_config_service.verify_tenant_domain(
            conn,
            tenant_id=tenant_id,
            domain_id=match["id"],
            platform_user_id=platform_user_id,
        )
    return match


async def ensure_team_users(conn: AsyncConnection, tenant_id: str, platform_user_id: str, slug: str) -> None:
    existing = await admin_config_service.list_tenant_users(conn, tenant_id)
    by_email = {item["email"].lower(): item for item in existing}
    for legacy_email, email, name, roles in [
        (f"operator@{slug}.test", f"operator@{slug}.example.com", "Operator Demo", ["operator"]),
        (f"viewer@{slug}.test", f"viewer@{slug}.example.com", "Viewer Demo", ["viewer"]),
    ]:
        legacy = by_email.get(legacy_email)
        current = by_email.get(email)
        if legacy and not current:
            updated = await admin_config_service.update_tenant_user(
                conn,
                tenant_id=tenant_id,
                user_id=legacy["id"],
                payload={
                    "email": email,
                    "name": name,
                    "roles": roles,
                    "password": TENANT_PASSWORD,
                    "must_change_pwd": False,
                    "status": "active",
                },
                platform_user_id=platform_user_id,
            )
            by_email[email] = updated
            by_email.pop(legacy_email, None)
            continue
        if legacy and current:
            await admin_config_service.delete_tenant_user(
                conn,
                tenant_id=tenant_id,
                user_id=legacy["id"],
                platform_user_id=platform_user_id,
            )
            by_email.pop(legacy_email, None)
        if email in by_email:
            continue
        await admin_config_service.create_tenant_user(
            conn,
            tenant_id=tenant_id,
            payload={
                "email": email,
                "name": name,
                "password": TENANT_PASSWORD,
                "roles": roles,
                "must_change_pwd": False,
                "status": "active",
            },
            platform_user_id=platform_user_id,
        )


async def ensure_companies(conn: AsyncConnection, tenant_id: str, user_id: str, slug: str) -> list[dict]:
    existing = await tenant_query_service.companies(conn, tenant_id)
    existing_names = {item["name"] for item in existing}
    demo_companies = [
        {
            "name": f"{slug.upper()} Electronics GmbH",
            "country": "DE",
            "website": f"https://buyer.{slug}.example",
            "industry": "PCB",
            "product_keywords": ["PCB", "FPC"],
            "industry_tags": ["electronics", "pcb"],
            "contact_name": "Anna Procurement",
            "contact_email": f"anna@buyer.{slug}.example",
            "contact_title": "Purchasing Manager",
        },
        {
            "name": f"{slug.upper()} Circuits Inc.",
            "country": "US",
            "website": f"https://sourcing.{slug}.example",
            "industry": "PCB",
            "product_keywords": ["HDI", "PCBA"],
            "industry_tags": ["electronics", "assembly"],
            "contact_name": "James Sourcing",
            "contact_email": f"james@sourcing.{slug}.example",
            "contact_title": "Sourcing Director",
        },
        {
            "name": f"{slug.upper()} Precision KK",
            "country": "JP",
            "website": f"https://precision.{slug}.example",
            "industry": "PCB",
            "product_keywords": ["FPC"],
            "industry_tags": ["precision", "pcb"],
            "contact_name": "Yuki Buyer",
            "contact_email": f"yuki@precision.{slug}.example",
            "contact_title": "Buyer",
        },
    ]
    for item in demo_companies:
        if item["name"] in existing_names:
            continue
        await tenant_ops_service.create_company(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload=item,
        )
    return await tenant_query_service.companies(conn, tenant_id)


async def ensure_group(conn: AsyncConnection, tenant_id: str, user_id: str, companies: list[dict]) -> dict:
    groups = await tenant_ops_service.list_groups(conn, tenant_id)
    name = "高优先级群组"
    group = next((item for item in groups if item["name"] == name), None)
    if group is None:
        group = await tenant_ops_service.create_group(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={"name": name, "description": "Demo seed group"},
        )
    members = await tenant_ops_service.list_group_members(conn, tenant_id, group["id"])
    if not members:
        await tenant_ops_service.add_group_members(
            conn,
            tenant_id=tenant_id,
            group_id=group["id"],
            user_id=user_id,
            payload={"tenant_company_ids": [item["id"] for item in companies[:2]]},
        )
    return await tenant_ops_service.get_group(conn, tenant_id, group["id"])


async def ensure_template(conn: AsyncConnection, tenant_id: str, user_id: str) -> dict:
    templates = await tenant_messaging_service.list_email_templates(conn, tenant_id)
    existing = next((item for item in templates if item["name"] == "Demo 自定义首触模板"), None)
    if existing is not None:
        return await tenant_messaging_service.get_email_template(conn, tenant_id, existing["id"])
    return await tenant_messaging_service.create_email_template(
        conn,
        tenant_id=tenant_id,
        user_id=user_id,
        payload={
            "name": "Demo 自定义首触模板",
            "category": "cold_outreach",
            "subject": "Hello {{company_name}}",
            "body_html": "<p>Hi {{contact_name}},</p><p>We would like to discuss PCB cooperation with {{company_name}}.</p>",
            "body_text": "Hi {{contact_name}}, We would like to discuss PCB cooperation with {{company_name}}.",
            "variables": [{"name": "company_name", "label": "公司名称"}, {"name": "contact_name", "label": "联系人"}],
            "source_type": "custom",
        },
    )


async def ensure_plan(
    conn: AsyncConnection,
    tenant_id: str,
    user_id: str,
    domain_id: str,
    sender_email: str,
    group_id: str,
    template_id: str,
) -> dict:
    plans = await tenant_messaging_service.list_sending_plans(conn, tenant_id)
    plan = next((item for item in plans if item["name"] == "Demo 首轮开发计划"), None)
    if plan is None:
        plan = await tenant_messaging_service.create_sending_plan(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "name": "Demo 首轮开发计划",
                "description": "Seeded demo sending plan",
                "recipient_source": "group",
                "recipient_config": {"group_id": group_id},
                "send_strategy": {"interval_seconds": [30, 120]},
                "sender_name": "ClientGet Demo",
                "sender_email": sender_email,
                "domain_id": domain_id,
            },
        )
    steps = await tenant_messaging_service.list_plan_steps(conn, tenant_id, plan["id"])
    if not steps:
        await tenant_messaging_service.create_plan_step(
            conn,
            tenant_id=tenant_id,
            plan_id=plan["id"],
            payload={"step_number": 1, "template_id": template_id, "delay_days": 0, "condition_type": "always"},
        )
        await tenant_messaging_service.create_plan_step(
            conn,
            tenant_id=tenant_id,
            plan_id=plan["id"],
            payload={"step_number": 2, "template_id": template_id, "delay_days": 3, "condition_type": "no_reply"},
        )
    recipients = await tenant_messaging_service.list_plan_recipients(conn, tenant_id, plan["id"])
    if not recipients:
        await tenant_messaging_service.lock_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan["id"])
    plan = await tenant_messaging_service.get_sending_plan(conn, tenant_id, plan["id"])
    if plan["status"] in {"draft", "scheduled", "paused"}:
        try:
            plan = await tenant_messaging_service.start_plan(conn, tenant_id=tenant_id, plan_id=plan["id"], user_id=user_id)
        except Exception:
            pass
    return plan


async def seed_email_activity(conn: AsyncConnection, tenant_id: str, plan_id: str) -> None:
    existing_count = (
        await conn.execute(
            text("SELECT count(*) FROM emails WHERE tenant_id = :tenant_id AND plan_id = :plan_id"),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
    ).scalar_one()
    if existing_count:
        return
    claimed = await tenant_messaging_service.claim_due_emails(conn, service_instance="demo-seed", limit=10)
    items = [item for item in claimed["items"] if item["plan_id"] == plan_id]
    for index, item in enumerate(items[:2], start=1):
        message_id = f"demo-msg-{plan_id}-{index}"
        await tenant_messaging_service.mark_email_sent(
            conn,
            email_id=item["email_id"],
            payload={"engagelab_message_id": message_id, "sent_at": datetime.now(timezone.utc).isoformat()},
        )
        await webhook_service.process_engagelab_event(
            conn,
            {"event_id": f"{message_id}-delivered", "message_id": message_id, "event": "delivered", "timestamp": datetime.now(timezone.utc).isoformat()},
        )
        await webhook_service.process_engagelab_event(
            conn,
            {"event_id": f"{message_id}-opened", "message_id": message_id, "event": "opened", "timestamp": datetime.now(timezone.utc).isoformat()},
        )
        if index == 1:
            await webhook_service.process_engagelab_event(
                conn,
                {
                    "event_id": f"{message_id}-replied",
                    "message_id": message_id,
                    "event": "replied",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reply_message_id": f"reply-{message_id}",
                    "reply_from_email": "buyer@example.com",
                    "reply_subject": "Re: demo",
                    "reply_body_text": "We are interested.",
                },
            )


async def seed_tenant(conn: AsyncConnection, platform_user_id: str, cfg: DemoTenantConfig) -> dict:
    tenant = await ensure_tenant(conn, platform_user_id, cfg)
    tenant_id = tenant["id"]
    admin_user_id = await get_tenant_admin_user_id(conn, tenant_id, cfg.admin_email, cfg.admin_name)
    await ensure_login_state(conn, tenant_id, admin_user_id, cfg.admin_password, cfg.completed)
    domain = await ensure_domain(conn, tenant_id, platform_user_id, f"mail.{cfg.slug}.demo.example.com")
    await ensure_team_users(conn, tenant_id, platform_user_id, cfg.slug)
    companies = await ensure_companies(conn, tenant_id, admin_user_id, cfg.slug)
    group = await ensure_group(conn, tenant_id, admin_user_id, companies)
    template = await ensure_template(conn, tenant_id, admin_user_id)
    if cfg.completed:
        await tenant_settings_service.complete_onboarding(conn, tenant_id=tenant_id)
        plan = await ensure_plan(
            conn,
            tenant_id=tenant_id,
            user_id=admin_user_id,
            domain_id=domain["id"],
            sender_email=f"hello@{domain['domain']}",
            group_id=group["id"],
            template_id=template["id"],
        )
        await seed_email_activity(conn, tenant_id, plan["id"])
    return {
        "tenant_id": tenant_id,
        "slug": cfg.slug,
        "admin_email": cfg.admin_email,
        "admin_password": cfg.admin_password,
        "completed": cfg.completed,
    }


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    summaries: list[dict] = []
    async with engine.begin() as conn:
        platform_user_id = await get_platform_admin_id(conn)
        for cfg in TENANTS:
            summaries.append(await seed_tenant(conn, platform_user_id, cfg))
    await engine.dispose()
    print("Seeded demo tenants:")
    for item in summaries:
        print(
            f"- slug={item['slug']} email={item['admin_email']} password={item['admin_password']} completed={item['completed']}"
        )
    print(f"- platform admin email={settings.admin_email} password={settings.admin_password or ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
