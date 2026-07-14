from fastapi import APIRouter, Body, Depends
from starlette.responses import Response

from app.core.responses import paginated_response, success_response
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.admin_config_service import AdminConfigService

router = APIRouter(tags=["admin-config"])
service = AdminConfigService()


@router.get("/dashboard/overview")
async def get_dashboard_overview(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(await service.get_platform_dashboard(context.connection))


@router.get("/scoring-templates")
async def list_platform_scoring_templates(
    industry: str | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_platform_scoring_templates(context.connection, industry=industry)
    return paginated_response(items, total=len(items))


@router.post("/scoring-templates")
async def create_platform_scoring_template(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_platform_scoring_template(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/scoring-templates/{template_id}")
async def get_platform_scoring_template(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(await service.get_platform_scoring_template(context.connection, template_id))


@router.put("/scoring-templates/{template_id}")
async def update_platform_scoring_template(
    template_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_platform_scoring_template(
            context.connection,
            template_id=template_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/scoring-templates/{template_id}")
async def delete_platform_scoring_template(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    await service.delete_platform_scoring_template(context.connection, template_id)
    return success_response({"deleted": True})


@router.get("/scoring-templates/{template_id}/versions")
async def list_platform_scoring_template_versions(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_platform_scoring_template_versions(context.connection, template_id)
    return paginated_response(items, total=len(items))


@router.get("/intelligence-sources")
async def list_intelligence_sources(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_intelligence_sources(context.connection)
    return paginated_response(items, total=len(items))


@router.post("/intelligence-sources")
async def create_intelligence_source(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_intelligence_source(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.post("/intelligence-sources/batch-import")
async def batch_import_intelligence_sources(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    created = await service.batch_import_intelligence_sources(
        context.connection,
        items=items,
        platform_user_id=context.platform_user_id,
    )
    return paginated_response(created, total=len(created))


@router.patch("/intelligence-sources/{source_id}")
async def patch_intelligence_source(
    source_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.patch_intelligence_source(
            context.connection,
            source_id=source_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/intelligence-sources/{source_id}")
async def delete_intelligence_source(
    source_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    await service.delete_intelligence_source(
        context.connection,
        source_id=source_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.get("/email-templates")
async def list_platform_email_templates(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_platform_email_templates(context.connection)
    return paginated_response(items, total=len(items))


@router.post("/email-templates")
async def create_platform_email_template(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_platform_email_template(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/email-templates/{template_id}")
async def get_platform_email_template(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(await service.get_platform_email_template(context.connection, template_id))


@router.put("/email-templates/{template_id}")
async def update_platform_email_template(
    template_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_platform_email_template(
            context.connection,
            template_id=template_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/email-templates/{template_id}")
async def delete_platform_email_template(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    await service.delete_platform_email_template(
        context.connection,
        template_id=template_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.get("/email-templates/{template_id}/preview")
async def get_platform_email_template_preview(
    template_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(await service.get_platform_email_template_preview(context.connection, template_id))


@router.get("/warmup-rules")
async def list_warmup_rules(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_warmup_rules(context.connection)
    return paginated_response(items, total=len(items))


@router.put("/warmup-rules")
async def put_warmup_rules(payload: dict, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        await service.put_warmup_rules(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/ai-config/models")
async def list_ai_models(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_ai_models(context.connection)
    return paginated_response(items, total=len(items))


@router.post("/ai-config/models")
async def create_ai_model(payload: dict, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        await service.create_ai_model(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.patch("/ai-config/models/{model_id}")
async def patch_ai_model(
    model_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.patch_ai_model(
            context.connection,
            model_id=model_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/ai-config/models/{model_id}")
async def delete_ai_model(model_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    await service.delete_ai_model(
        context.connection,
        model_id=model_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.get("/ai-config/scene-defaults")
async def list_ai_scene_defaults(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_ai_scene_defaults(context.connection)
    return paginated_response(items, total=len(items))


@router.put("/ai-config/scene-defaults")
async def put_ai_scene_defaults(
    payload: list = Body(...),
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.put_ai_scene_defaults(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/ai-config/pricing")
async def get_ai_pricing(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(await service.get_ai_pricing(context.connection))


@router.put("/ai-config/pricing")
async def put_ai_pricing(payload: dict, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        await service.put_ai_pricing(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(tenant_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_tenant_users(context.connection, tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/tenants/{tenant_id}/users")
async def create_tenant_user(
    tenant_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_tenant_user(
            context.connection,
            tenant_id=tenant_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.patch("/tenants/{tenant_id}/users/{user_id}")
async def patch_tenant_user(
    tenant_id: str,
    user_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_tenant_user(
            context.connection,
            tenant_id=tenant_id,
            user_id=user_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def delete_tenant_user(
    tenant_id: str,
    user_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    await service.delete_tenant_user(
        context.connection,
        tenant_id=tenant_id,
        user_id=user_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.get("/tenants/{tenant_id}/domains")
async def list_tenant_domains(
    tenant_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_tenant_domains(context.connection, tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/tenants/{tenant_id}/domains")
async def create_tenant_domain(
    tenant_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_tenant_domain(
            context.connection,
            tenant_id=tenant_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.post("/tenants/{tenant_id}/domains/{domain_id}/verify")
async def verify_tenant_domain(
    tenant_id: str,
    domain_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.verify_tenant_domain(
            context.connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/tenants/{tenant_id}/domains/{domain_id}")
async def get_tenant_domain(
    tenant_id: str,
    domain_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(await service.get_tenant_domain(context.connection, tenant_id, domain_id))


@router.patch("/tenants/{tenant_id}/domains/{domain_id}")
async def update_tenant_domain(
    tenant_id: str,
    domain_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_tenant_domain(
            context.connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/tenants/{tenant_id}/domains/{domain_id}")
async def delete_tenant_domain(
    tenant_id: str,
    domain_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> Response:
    await service.delete_tenant_domain(
        context.connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        platform_user_id=context.platform_user_id,
    )
    return Response(status_code=204)
