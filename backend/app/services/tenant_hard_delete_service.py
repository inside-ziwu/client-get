from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

TARGET_TENANT_SLUG = "t-019dc238"
TARGET_COMPANY_NAME = "muzi"


class TenantHardDeleteError(RuntimeError):
    pass


@dataclass(frozen=True)
class TenantRow:
    id: str
    slug: str
    name: str


class TenantHardDeleteService:
    """One-off cleanup for the approved Zhao Kui test tenant hard-delete change."""

    async def preview(
        self,
        conn: AsyncConnection,
        *,
        tenant_slug: str = TARGET_TENANT_SLUG,
    ) -> dict:
        tenant = await self._load_target_tenant(conn, tenant_slug)
        candidates = await self._load_muzi_candidates(conn, tenant.id)
        plan_ids = await self._plan_ids(conn, tenant.id)
        company_ids = [int(row["tenant_company_id"]) for row in candidates]
        contact_ids = await self._tenant_contact_ids_for_companies(conn, tenant.id, company_ids)
        counts = await self._counts(conn, tenant.id, company_ids, contact_ids, plan_ids)
        return {
            "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name},
            "muzi_candidates_count": len(candidates),
            "muzi_candidates": [dict(row) for row in candidates],
            "counts": counts,
            "plan_ids": plan_ids,
        }

    async def execute(
        self,
        conn: AsyncConnection,
        *,
        tenant_slug: str = TARGET_TENANT_SLUG,
        confirm: str,
        confirmed_company_ids: list[int] | None = None,
    ) -> dict:
        if tenant_slug != TARGET_TENANT_SLUG:
            raise TenantHardDeleteError(f"本操作只允许 tenant slug {TARGET_TENANT_SLUG}")
        if confirm != TARGET_TENANT_SLUG:
            raise TenantHardDeleteError("确认 token 不匹配，拒绝执行硬删除")

        preview = await self.preview(conn, tenant_slug=tenant_slug)
        company_ids = [int(row["tenant_company_id"]) for row in preview["muzi_candidates"]]
        if preview["muzi_candidates_count"] != 1:
            if not confirmed_company_ids:
                raise TenantHardDeleteError("muzi 精确匹配候选数量异常，拒绝执行硬删除")
            if sorted(confirmed_company_ids) != sorted(company_ids):
                raise TenantHardDeleteError(
                    "显式确认的 muzi 候选 ID 不完整或不匹配，拒绝执行硬删除"
                )
        elif confirmed_company_ids and sorted(confirmed_company_ids) != sorted(company_ids):
            raise TenantHardDeleteError("muzi 精确匹配候选数量异常，拒绝执行硬删除")

        tenant_id = preview["tenant"]["id"]
        contact_ids = await self._tenant_contact_ids_for_companies(conn, tenant_id, company_ids)
        plan_ids = preview["plan_ids"]

        await self._delete_sending_runtime(conn, tenant_id, plan_ids)
        await self._delete_groups(conn, tenant_id)
        await self._delete_muzi_company(conn, tenant_id, company_ids, contact_ids)
        verification = await self._verify(conn, tenant_id, company_ids)
        return {
            "tenant": preview["tenant"],
            "preview": preview,
            "verification": verification,
            "deleted_plan_ids": plan_ids,
            "deleted_tenant_company_ids": company_ids,
        }

    async def _load_target_tenant(self, conn: AsyncConnection, tenant_slug: str) -> TenantRow:
        if tenant_slug != TARGET_TENANT_SLUG:
            raise TenantHardDeleteError(f"本操作只允许 tenant slug {TARGET_TENANT_SLUG}")
        row = (
            await conn.execute(
                text("SELECT id, slug, name FROM tenants WHERE slug = :slug"),
                {"slug": tenant_slug},
            )
        ).mappings().first()
        if row is None:
            raise TenantHardDeleteError(f"找不到目标租户: {tenant_slug}")
        return TenantRow(id=str(row["id"]), slug=row["slug"], name=row["name"])

    async def _load_muzi_candidates(self, conn: AsyncConnection, tenant_id: str) -> list:
        result = await conn.execute(
            text(
                """
                SELECT
                  tc.id AS tenant_company_id,
                  tc.clean_company_id,
                  cc.name,
                  cc.name_normalized,
                  cc.country_iso3,
                  cc.website
                FROM tenant_companies tc
                JOIN clean_companies cc ON cc.id = tc.clean_company_id
                WHERE tc.tenant_id = :tenant_id
                  AND lower(cc.name) = :company_name
                ORDER BY tc.id
                """
            ),
            {"tenant_id": tenant_id, "company_name": TARGET_COMPANY_NAME},
        )
        return list(result.mappings().all())

    async def _plan_ids(self, conn: AsyncConnection, tenant_id: str) -> list[str]:
        result = await conn.execute(
            text(
                """
                SELECT id
                FROM sending_plans
                WHERE tenant_id = :tenant_id
                ORDER BY created_at, id
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [str(row["id"]) for row in result.mappings().all()]

    async def _tenant_contact_ids_for_companies(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        company_ids: list[int],
    ) -> list[int]:
        if not company_ids:
            return []
        result = await conn.execute(
            text(
                """
                SELECT tco.id
                FROM tenant_contacts tco
                JOIN tenant_companies tc
                  ON tc.clean_company_id = tco.clean_company_id
                 AND tc.tenant_id = tco.tenant_id
                WHERE tco.tenant_id = :tenant_id
                  AND tc.id = ANY(:company_ids)
                ORDER BY tco.id
                """
            ),
            {"tenant_id": tenant_id, "company_ids": company_ids},
        )
        return [int(row["id"]) for row in result.mappings().all()]

    async def _counts(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        company_ids: list[int],
        contact_ids: list[int],
        plan_ids: list[str],
    ) -> dict[str, int]:
        return {
            "tenant_companies": len(company_ids),
            "tenant_contacts": len(contact_ids),
            "groups": await self._tenant_count(conn, "groups", tenant_id),
            "group_members": await self._tenant_count(conn, "group_members", tenant_id),
            "sending_plans": len(plan_ids),
            "sequence_steps": await self._tenant_count(conn, "sequence_steps", tenant_id),
            "sending_plan_recipients": await self._tenant_count(
                conn, "sending_plan_recipients", tenant_id
            ),
            "sequence_enrollments": await self._tenant_count(
                conn, "sequence_enrollments", tenant_id
            ),
            "emails": await self._tenant_count(conn, "emails", tenant_id),
            "email_events": await self._tenant_count(conn, "email_events", tenant_id),
            "email_send_locks": await self._tenant_count(conn, "email_send_locks", tenant_id),
            "company_scores": await self._tenant_count(conn, "company_scores", tenant_id),
            "scoring_jobs": await self._tenant_count(conn, "scoring_jobs", tenant_id),
        }

    async def _tenant_count(self, conn: AsyncConnection, table: str, tenant_id: str) -> int:
        return (
            await conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            )
        ).scalar_one()

    async def _delete_sending_runtime(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        plan_ids: list[str],
    ) -> None:
        if not plan_ids:
            return
        await conn.execute(
            text(
                """
                DELETE FROM email_events
                WHERE tenant_id = :tenant_id
                  AND EXISTS (
                    SELECT 1
                    FROM emails e
                    WHERE e.tenant_id = :tenant_id
                      AND e.plan_id = ANY(CAST(:plan_ids AS uuid[]))
                      AND e.id = email_events.email_id
                      AND e.created_at = email_events.email_created_at
                  )
                """
            ),
            {"tenant_id": tenant_id, "plan_ids": plan_ids},
        )
        await conn.execute(
            text(
                """
                DELETE FROM email_send_locks
                WHERE tenant_id = :tenant_id
                  AND enrollment_id IN (
                    SELECT id
                    FROM sequence_enrollments
                    WHERE tenant_id = :tenant_id
                      AND plan_id = ANY(CAST(:plan_ids AS uuid[]))
                  )
                """
            ),
            {"tenant_id": tenant_id, "plan_ids": plan_ids},
        )
        for table in (
            "emails",
            "sequence_enrollments",
            "sending_plan_recipients",
            "sequence_steps",
            "sending_plans",
        ):
            await conn.execute(
                text(
                    f"""
                    DELETE FROM {table}
                    WHERE tenant_id = :tenant_id
                      AND plan_id = ANY(CAST(:plan_ids AS uuid[]))
                    """
                    if table != "sending_plans"
                    else """
                    DELETE FROM sending_plans
                    WHERE tenant_id = :tenant_id
                      AND id = ANY(CAST(:plan_ids AS uuid[]))
                    """
                ),
                {"tenant_id": tenant_id, "plan_ids": plan_ids},
            )

    async def _delete_groups(self, conn: AsyncConnection, tenant_id: str) -> None:
        await conn.execute(
            text("DELETE FROM group_members WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        await conn.execute(
            text("DELETE FROM groups WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )

    async def _delete_muzi_company(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        company_ids: list[int],
        contact_ids: list[int],
    ) -> None:
        if not company_ids:
            return
        await conn.execute(
            text(
                """
                DELETE FROM scoring_jobs
                WHERE tenant_id = :tenant_id
                  AND tenant_company_id = ANY(:company_ids)
                """
            ),
            {"tenant_id": tenant_id, "company_ids": company_ids},
        )
        await conn.execute(
            text(
                """
                DELETE FROM company_scores
                WHERE tenant_id = :tenant_id
                  AND tenant_company_id = ANY(:company_ids)
                """
            ),
            {"tenant_id": tenant_id, "company_ids": company_ids},
        )
        if contact_ids:
            await conn.execute(
                text(
                    """
                    DELETE FROM tenant_contacts
                    WHERE tenant_id = :tenant_id
                      AND id = ANY(:contact_ids)
                    """
                ),
                {"tenant_id": tenant_id, "contact_ids": contact_ids},
            )
        await conn.execute(
            text(
                """
                DELETE FROM tenant_companies
                WHERE tenant_id = :tenant_id
                  AND id = ANY(:company_ids)
                """
            ),
            {"tenant_id": tenant_id, "company_ids": company_ids},
        )

    async def _verify(self, conn: AsyncConnection, tenant_id: str, company_ids: list[int]) -> dict:
        remaining = {
            "tenant_companies": (
                await conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM tenant_companies
                        WHERE tenant_id = :tenant_id
                          AND id = ANY(:company_ids)
                        """
                    ),
                    {"tenant_id": tenant_id, "company_ids": company_ids},
                )
            ).scalar_one()
            if company_ids
            else 0,
            "groups": await self._tenant_count(conn, "groups", tenant_id),
            "group_members": await self._tenant_count(conn, "group_members", tenant_id),
            "sending_plans": await self._tenant_count(conn, "sending_plans", tenant_id),
            "sequence_steps": await self._tenant_count(conn, "sequence_steps", tenant_id),
            "sending_plan_recipients": await self._tenant_count(
                conn, "sending_plan_recipients", tenant_id
            ),
            "sequence_enrollments": await self._tenant_count(
                conn, "sequence_enrollments", tenant_id
            ),
            "emails": await self._tenant_count(conn, "emails", tenant_id),
            "email_events": await self._tenant_count(conn, "email_events", tenant_id),
            "email_send_locks": await self._tenant_count(conn, "email_send_locks", tenant_id),
        }
        return {"remaining": remaining, "complete": all(value == 0 for value in remaining.values())}
