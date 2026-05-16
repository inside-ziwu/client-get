from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.schemas.ai_provider import OpenRouterConfigRequest
from app.schemas.tenants import TenantCreateRequest, TenantDetail, TenantListItem
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.tenant_ai_provider_service import TenantAiProviderService
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["admin-tenants"])
service = TenantService()
ai_provider_service = TenantAiProviderService()


@router.get("")
async def list_tenants(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    tenants = await service.list_tenants(context.connection)
    return paginated_response([TenantListItem(**item).model_dump() for item in tenants], total=len(tenants))


@router.post("")
async def create_tenant(
    payload: TenantCreateRequest,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    tenant = await service.create_tenant(
        context.connection,
        platform_user_id=context.platform_user_id,
        payload=payload.model_dump(),
    )
    return success_response(TenantDetail(**tenant).model_dump())


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    tenant = await service.get_tenant(context.connection, tenant_id)
    return success_response(TenantDetail(**tenant).model_dump())


@router.patch("/{tenant_id}")
async def patch_tenant(
    tenant_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    tenant = await service.update_tenant(context.connection, tenant_id=tenant_id, payload=payload)
    return success_response(TenantDetail(**tenant).model_dump())


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    tenant = await service.set_tenant_status(context.connection, tenant_id=tenant_id, status="suspended")
    return success_response(TenantDetail(**tenant).model_dump())


@router.post("/{tenant_id}/activate")
async def activate_tenant(tenant_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    tenant = await service.set_tenant_status(context.connection, tenant_id=tenant_id, status="active")
    return success_response(TenantDetail(**tenant).model_dump())


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    # Soft delete: archive the tenant so it no longer appears in list
    await service.set_tenant_status(context.connection, tenant_id=tenant_id, status="archived")
    return success_response({"deleted": True})


@router.get("/{tenant_id}/ai-provider/openrouter")
async def get_openrouter_config(
    tenant_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await ai_provider_service.get_config(
            context.connection,
            tenant_id=tenant_id,
            refresh_if_stale=True,
        )
    )


@router.put("/{tenant_id}/ai-provider/openrouter")
async def put_openrouter_config(
    tenant_id: str,
    payload: OpenRouterConfigRequest,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await ai_provider_service.upsert_config(
            context.connection,
            tenant_id=tenant_id,
            api_key=payload.api_key,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/{tenant_id}/ai-provider/openrouter")
async def delete_openrouter_config(
    tenant_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    await ai_provider_service.delete_config(
        context.connection,
        tenant_id=tenant_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.post("/{tenant_id}/ai-provider/openrouter/balance/refresh")
async def refresh_openrouter_balance(
    tenant_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await ai_provider_service.refresh_balance(
            context.connection,
            tenant_id=tenant_id,
            force=True,
        )
    )
