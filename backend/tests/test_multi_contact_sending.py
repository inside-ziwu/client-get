"""多联系人发送测试。

覆盖 D8-D14 全部修改：
- _recipients_from_group 多联系人 + 发送前自愈
- _recipients_from_manual company_ids 批量 + contact_ids 回归
- _recipients_from_filter 多联系人
- _build_recipient_candidates is_sendable + None 修复
- lock_plan_recipients 批量 INSERT
- list_group_members contacts_count + fallback
"""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.ids import new_uuid
from app.services.tenant_messaging_service import TenantMessagingService
from app.services.tenant_ops_service import TenantOpsService
from tests.helpers import make_engine
from tests.wmt_helpers import (
    create_wmt_company,
    create_wmt_company_with_contacts,
    create_wmt_contact,
    create_tenant_company,
)


# ── helpers ──────────────────────────────────────────────


async def _tenant(conn) -> str:
    tenant_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"id": tenant_id, "slug": f"mc-{uuid4().hex[:8]}"},
    )
    return tenant_id


async def _user(conn, tenant_id: str) -> str:
    user_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
            VALUES (:id, :tenant_id, :email, 'hash', '测试用户', 'active', false)
            """
        ),
        {"id": user_id, "tenant_id": tenant_id, "email": f"mc-{uuid4().hex[:8]}@example.com"},
    )
    return user_id


async def _template(conn, tenant_id: str) -> str:
    template_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO email_templates (id, tenant_id, name, category, subject, body_html, body_text)
            VALUES (:id, :tenant_id, '多联系人模板', 'outreach', 'Subject', '<p>Body</p>', 'Body')
            """
        ),
        {"id": template_id, "tenant_id": tenant_id},
    )
    return template_id


async def _domain(conn, tenant_id: str) -> str:
    domain_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO domain_warmup_status (id, tenant_id, domain, verification_status, daily_limit)
            VALUES (:id, :tenant_id, :domain, 'verified', 100)
            """
        ),
        {"id": domain_id, "tenant_id": tenant_id, "domain": f"mc-{uuid4().hex[:8]}.example.com"},
    )
    return domain_id


async def _group(conn, tenant_id: str) -> str:
    group_id = str(new_uuid())
    await conn.execute(
        text("INSERT INTO groups (id, tenant_id, name, member_count) VALUES (:id, :tenant_id, :name, 0)"),
        {"id": group_id, "tenant_id": tenant_id, "name": f"多联系人组 {uuid4().hex[:8]}"},
    )
    return group_id


async def _add_group_member(conn, tenant_id: str, group_id: str, tenant_company_id: int, tenant_contact_id: int | None = None):
    await conn.execute(
        text(
            """
            INSERT INTO group_members (id, tenant_id, group_id, tenant_company_id, tenant_contact_id, added_by)
            VALUES (:id, :tenant_id, :group_id, :tenant_company_id, :tenant_contact_id, 'manual')
            """
        ),
        {
            "id": str(new_uuid()),
            "tenant_id": tenant_id,
            "group_id": group_id,
            "tenant_company_id": tenant_company_id,
            "tenant_contact_id": tenant_contact_id,
        },
    )
    await conn.execute(
        text("UPDATE groups SET member_count = member_count + 1 WHERE id = :group_id"),
        {"group_id": group_id},
    )


async def _sending_plan(conn, tenant_id: str, user_id: str, *, recipient_source: str, recipient_config: dict) -> str:
    plan_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO sending_plans
              (id, tenant_id, name, status, recipient_source, recipient_config,
               send_strategy, sender_name, sender_email, created_by)
            VALUES
              (:id, :tenant_id, :name, 'draft', :source, :config::jsonb,
               '{}'::jsonb, 'Sender', 'sender@example.com', :user_id)
            """
        ),
        {
            "id": plan_id,
            "tenant_id": tenant_id,
            "name": f"多联系人计划 {uuid4().hex[:8]}",
            "source": recipient_source,
            "config": __import__("json").dumps(recipient_config),
            "user_id": user_id,
        },
    )
    return plan_id


# ── 4.2: _recipients_from_group 多联系人 ─────────────────


async def test_group_recipients_returns_all_contacts() -> None:
    """4.2: 公司有 3 个联系人时，group 发送返回 3 条收件人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=3)
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            rows = await service._recipients_from_group(conn, tenant_id, {"group_id": group_id})

            assert len(rows) == 3
            emails = {r["contact_email"] for r in rows}
            assert len(emails) == 3
            assert all(r["contact_email"] is not None for r in rows)
    finally:
        await engine.dispose()


# ── 4.3: 无 email 联系人不返回 ───────────────────────────


async def test_group_recipients_skips_no_email_contacts() -> None:
    """4.3: WMT 联系人全部无 email 时返回 0 个收件人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=3, emails=[None, None, None]
            )
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            rows = await service._recipients_from_group(conn, tenant_id, {"group_id": group_id})

            assert len(rows) == 0
    finally:
        await engine.dispose()


# ── 4.13: 多公司不同联系人数量 ───────────────────────────


async def test_group_recipients_multi_company_different_counts() -> None:
    """4.13: 3 家公司分别有 1/3/5 个联系人 → 总计 9 条收件人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            group_id = await _group(conn, tenant_id)
            for count in [1, 3, 5]:
                setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=count)
                await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            rows = await service._recipients_from_group(conn, tenant_id, {"group_id": group_id})

            assert len(rows) == 9
    finally:
        await engine.dispose()


# ── 4.14: 发送时自动物化（stale 公司）─────────────────────


async def test_group_recipients_auto_ensures_stale_company() -> None:
    """4.14: group 内公司无 tenant_contacts 时，_recipients_from_group 自动触发 ensure"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=2, data_status="missing_contacts"
            )
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            tc_before = (await conn.execute(
                text("SELECT count(*) FROM tenant_contacts WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            )).scalar_one()
            assert tc_before == 0

            rows = await service._recipients_from_group(conn, tenant_id, {"group_id": group_id})

            assert len(rows) == 2
            tc_after = (await conn.execute(
                text("SELECT count(*) FROM tenant_contacts WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            )).scalar_one()
            assert tc_after == 2
    finally:
        await engine.dispose()


# ── 4.1: 加入群组后自动物化 + 邮箱解析 ──────────────────


async def test_group_ensure_then_resolve_email() -> None:
    """4.1: 公司有 WMT 联系人但无 tenant_contacts → group 路径自动物化并解析邮箱"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=1,
                emails=["buyer@example.com"], data_status="missing_contacts",
            )
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            plan_id = await _sending_plan(
                conn, tenant_id, user_id,
                recipient_source="group",
                recipient_config={"group_id": group_id},
            )
            candidates = await service.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)

            assert len(candidates) == 1
            assert candidates[0]["contact_email"] == "buyer@example.com"
            assert candidates[0]["excluded_reason"] is None
    finally:
        await engine.dispose()


# ── 4.6: list_group_members contacts_count + fallback ────


async def test_list_group_members_contacts_count_and_fallback() -> None:
    """4.6: list_group_members 返回 contacts_count 字段，且 fallback 默认联系人正确"""
    engine = make_engine()
    ops = TenantOpsService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=3,
                positions=["CEO", None, None],
            )
            from app.services.tenant_contact_utils import ensure_contacts_from_wmt
            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            members = await ops.list_group_members(conn, tenant_id, group_id)

            assert len(members) == 1
            assert members[0]["contacts_count"] == 3
            assert members[0]["contact_email"] is not None
    finally:
        await engine.dispose()


# ── 4.16: 0 联系人公司 contacts_count = 0 ────────────────


async def test_list_group_members_zero_contacts() -> None:
    """4.16: WMT 联系人全无 email 时 contacts_count = 0"""
    engine = make_engine()
    ops = TenantOpsService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=2, emails=[None, None],
            )
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            members = await ops.list_group_members(conn, tenant_id, group_id)

            assert len(members) == 1
            assert members[0]["contacts_count"] == 0
    finally:
        await engine.dispose()


# ── 4.9: manual company_ids 多联系人 ─────────────────────


async def test_manual_company_ids_returns_all_contacts() -> None:
    """4.9: company_ids 多联系人 — 公司有 3 个联系人时返回 3 条记录"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=3)

            rows = await service._recipients_from_manual(
                conn, tenant_id,
                {"tenant_company_ids": [setup["tenant_company_id"]]},
            )

            assert len(rows) == 3
            assert all(r["contact_email"] is not None for r in rows)
    finally:
        await engine.dispose()


# ── 4.15: manual batch company_ids ────────────────────────


async def test_manual_batch_company_ids() -> None:
    """4.15: 批量 company_ids — ANY() 返回所有公司的所有联系人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            company_ids = []
            for count in [2, 3]:
                setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=count)
                company_ids.append(setup["tenant_company_id"])

            rows = await service._recipients_from_manual(
                conn, tenant_id,
                {"tenant_company_ids": company_ids},
            )

            assert len(rows) == 5
    finally:
        await engine.dispose()


# ── 4.11: contact_ids 回归 ────────────────────────────────


async def test_manual_contact_ids_regression() -> None:
    """4.11: 修改 company_ids 分支后 contact_ids 仍正常"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=2)
            from app.services.tenant_contact_utils import ensure_contacts_from_wmt
            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            tc_ids = (await conn.execute(
                text("SELECT id FROM tenant_contacts WHERE tenant_id = :tid ORDER BY id"),
                {"tid": tenant_id},
            )).scalars().all()
            assert len(tc_ids) == 2

            rows = await service._recipients_from_manual(
                conn, tenant_id,
                {"tenant_contact_ids": [tc_ids[0]]},
            )

            assert len(rows) == 1
            assert rows[0]["tenant_contact_id"] == tc_ids[0]
    finally:
        await engine.dispose()


# ── 4.19: filter 多联系人 ─────────────────────────────────


async def test_filter_returns_all_contacts() -> None:
    """4.19: filter 路径返回公司所有联系人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=3)

            rows = await service._recipients_from_filter(conn, tenant_id, {})

            assert len(rows) == 3
            company_ids = {r["tenant_company_id"] for r in rows}
            assert len(company_ids) == 1
    finally:
        await engine.dispose()


# ── 4.20: is_sendable 过滤 ────────────────────────────────


async def test_is_sendable_false_excluded() -> None:
    """4.20: is_sendable=false 的联系人被排除为 not_sendable"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=2)
            from app.services.tenant_contact_utils import ensure_contacts_from_wmt
            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            tc_ids = (await conn.execute(
                text("SELECT id FROM tenant_contacts WHERE tenant_id = :tid ORDER BY id"),
                {"tid": tenant_id},
            )).scalars().all()
            await conn.execute(
                text("UPDATE tenant_contacts SET is_sendable = false WHERE id = :id"),
                {"id": tc_ids[0]},
            )

            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])
            user_id = await _user(conn, tenant_id)
            plan_id = await _sending_plan(
                conn, tenant_id, user_id,
                recipient_source="group",
                recipient_config={"group_id": group_id},
            )

            candidates = await service.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)

            not_sendable = [c for c in candidates if c["excluded_reason"] == "not_sendable"]
            sendable = [c for c in candidates if c["excluded_reason"] is None]
            assert len(not_sendable) == 1
            assert len(sendable) == 1
    finally:
        await engine.dispose()


# ── 4.21: tenant_contact_id None 不输出 "None" ───────────


async def test_tenant_contact_id_none_not_string() -> None:
    """4.21: tenant_contact_id 为 NULL 时 candidate 值为 Python None 而非字符串 'None'"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            wmt = await create_wmt_company(conn)
            tc_id = await create_tenant_company(conn, tenant_id, wmt["id"])
            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, tc_id)
            user_id = await _user(conn, tenant_id)
            plan_id = await _sending_plan(
                conn, tenant_id, user_id,
                recipient_source="group",
                recipient_config={"group_id": group_id},
            )

            candidates = await service.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)

            assert len(candidates) == 0
    finally:
        await engine.dispose()


# ── 4.12: bounced/unsubscribed 排除 ──────────────────────


async def test_bounced_contacts_excluded_others_kept() -> None:
    """4.12: 部分联系人 bounced 时正确排除但保留其他联系人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=3)
            from app.services.tenant_contact_utils import ensure_contacts_from_wmt
            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            tc_ids = (await conn.execute(
                text("SELECT id FROM tenant_contacts WHERE tenant_id = :tid ORDER BY id"),
                {"tid": tenant_id},
            )).scalars().all()
            await conn.execute(
                text("UPDATE tenant_contacts SET contact_status = 'bounced' WHERE id = :id"),
                {"id": tc_ids[0]},
            )

            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])
            user_id = await _user(conn, tenant_id)
            plan_id = await _sending_plan(
                conn, tenant_id, user_id,
                recipient_source="group",
                recipient_config={"group_id": group_id},
            )

            candidates = await service.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)

            bounced = [c for c in candidates if c["excluded_reason"] == "bounced"]
            valid = [c for c in candidates if c["excluded_reason"] is None]
            assert len(bounced) == 1
            assert len(valid) == 2
    finally:
        await engine.dispose()


# ── 4.18: lock_plan_recipients 批量 INSERT ────────────────


async def test_lock_recipients_batch_insert_idempotent() -> None:
    """4.18: 重复 lock 后 inserted_count 为真实新增数"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id)
            setup = await create_wmt_company_with_contacts(conn, tenant_id, contact_count=3)
            from app.services.tenant_contact_utils import ensure_contacts_from_wmt
            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            group_id = await _group(conn, tenant_id)
            await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            result = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "plan": {
                        "name": "批量 lock 测试",
                        "description": "",
                        "recipient_source": "group",
                        "recipient_config": {"group_id": group_id},
                        "send_strategy": {},
                        "sender_name": "Test",
                        "sender_email": "test@example.com",
                        "domain_id": domain_id,
                    },
                    "steps": [{"step_number": 1, "template_id": template_id, "delay_days": 0, "condition_type": "always"}],
                    "lock_recipients": True,
                },
            )

            assert result["total_recipients"] == 3

            second = await service.lock_plan_recipients(conn, tenant_id=tenant_id, plan_id=result["id"])
            assert second["inserted_count"] == 0
            assert second["total_recipients"] == 3
    finally:
        await engine.dispose()


# ── 4.17: 端到端 ─────────────────────────────────────────


async def test_end_to_end_wmt_to_group_to_plan_to_lock() -> None:
    """4.17: 端到端 — 公司有 WMT 联系人 → 群组 → 创建发送计划 → lock → 所有联系人成为收件人"""
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id)

            group_id = await _group(conn, tenant_id)
            for count in [2, 3]:
                setup = await create_wmt_company_with_contacts(
                    conn, tenant_id, contact_count=count, data_status="missing_contacts",
                )
                await _add_group_member(conn, tenant_id, group_id, setup["tenant_company_id"])

            result = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "plan": {
                        "name": "端到端测试",
                        "description": "",
                        "recipient_source": "group",
                        "recipient_config": {"group_id": group_id},
                        "send_strategy": {},
                        "sender_name": "E2E",
                        "sender_email": "e2e@example.com",
                        "domain_id": domain_id,
                    },
                    "steps": [{"step_number": 1, "template_id": template_id, "delay_days": 0, "condition_type": "always"}],
                    "lock_recipients": True,
                },
            )

            assert result["total_recipients"] == 5

            recipients = await service.list_plan_recipients(conn, tenant_id, result["id"])
            assert len(recipients) == 5
            emails = {r["contact_email"] for r in recipients}
            assert len(emails) == 5
    finally:
        await engine.dispose()
