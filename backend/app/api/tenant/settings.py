from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.schemas.ai_provider import OpenRouterConfigRequest
from app.schemas.tenant_settings import (
    KeywordCreateRequest,
    KeywordUpdateRequest,
    ScoringTemplateUpdateRequest,
)
from app.security.dependencies import TenantAuthContext, get_current_tenant_user, require_tenant_roles
from app.services.tenant_ai_provider_service import TenantAiProviderService
from app.services.tenant_settings_service import TenantSettingsService

router = APIRouter(tags=["tenant-settings"])
service = TenantSettingsService()
ai_provider_service = TenantAiProviderService()


@router.get("/keywords")
async def list_keywords(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_keywords(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/keywords")
async def create_keyword(
    payload: KeywordCreateRequest,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    item = await service.create_keyword(
        context.connection,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        payload=payload.model_dump(),
    )
    return success_response(item)


@router.patch("/keywords/{keyword_id}")
async def update_keyword(
    keyword_id: str,
    payload: KeywordUpdateRequest,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    item = await service.update_keyword(
        context.connection,
        tenant_id=context.tenant_id,
        keyword_id=keyword_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return success_response(item)


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    await service.delete_keyword(context.connection, tenant_id=context.tenant_id, keyword_id=keyword_id)
    return success_response({"deleted": True})


@router.get("/scoring-templates")
async def get_scoring_templates(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    items = await service.get_scoring_templates(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.put("/scoring-templates/{template_id}")
async def update_scoring_template(
    template_id: str,
    payload: ScoringTemplateUpdateRequest,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    item = await service.update_scoring_template(
        context.connection,
        tenant_id=context.tenant_id,
        template_id=template_id,
        user_id=context.user_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return success_response(item)


@router.post("/onboarding/complete")
async def complete_onboarding(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    await service.complete_onboarding(context.connection, tenant_id=context.tenant_id)
    return success_response({"completed": True})


@router.get("/settings/ai-provider/openrouter")
async def get_openrouter_config(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    return success_response(
        await ai_provider_service.get_config(
            context.connection,
            tenant_id=context.tenant_id,
            refresh_if_stale=True,
        )
    )


@router.put("/settings/ai-provider/openrouter")
async def put_openrouter_config(
    payload: OpenRouterConfigRequest,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    return success_response(
        await ai_provider_service.upsert_config(
            context.connection,
            tenant_id=context.tenant_id,
            api_key=payload.api_key,
            user_id=context.user_id,
        )
    )


@router.delete("/settings/ai-provider/openrouter")
async def delete_openrouter_config(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    await ai_provider_service.delete_config(
        context.connection,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )
    return success_response({"deleted": True})


@router.post("/settings/ai-provider/openrouter/balance/refresh")
async def refresh_openrouter_balance(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    return success_response(
        await ai_provider_service.refresh_balance(
            context.connection,
            tenant_id=context.tenant_id,
            force=True,
        )
    )
