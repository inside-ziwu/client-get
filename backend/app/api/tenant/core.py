from fastapi import APIRouter, Depends

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


@router.get("/ai-capabilities")
async def get_ai_capabilities(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    data = await service.ai_capabilities(context.connection, context.tenant_id, context.roles)
    return success_response(data)
