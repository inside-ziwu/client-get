from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.core.responses import success_response
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.tenant_query_service import TenantQueryService

router = APIRouter(tags=["tenant-core"])
service = TenantQueryService()


@router.get("/dashboard/overview")
async def dashboard_overview(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    data = await service.dashboard_overview(
        context.connection,
        tenant_id=context.tenant_id,
        is_admin="admin" in context.roles,
    )
    return success_response(data)


@router.get("/dashboard/email-stats")
async def dashboard_email_stats(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    today = date.today()
    sd = service._parse_filter_date(start_date) if start_date else today - timedelta(days=29)
    ed = service._parse_filter_date(end_date) if end_date else today
    data = await service.email_stats_by_date_range(context.connection, context.tenant_id, sd, ed)
    return success_response(data)


@router.get("/dashboard/plan-overview")
async def dashboard_plan_overview(
    plan_id: str | None = Query(None),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    data = await service.plan_overview(context.connection, context.tenant_id, plan_id=plan_id)
    return success_response(data)


@router.get("/dashboard/daily-quota")
async def dashboard_daily_quota(
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    data = await service.daily_quota(context.connection, context.tenant_id)
    return success_response(data)


@router.get("/dashboard/llm-balance")
async def dashboard_llm_balance(
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    data = await service.llm_balance(context.connection, context.tenant_id)
    return success_response(data)


@router.get("/ai-capabilities")
async def get_ai_capabilities(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    data = await service.ai_capabilities(context.connection, context.tenant_id, context.roles)
    return success_response(data)
