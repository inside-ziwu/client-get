from fastapi import APIRouter, Depends, Query

from app.core.responses import paginated_response, success_response
from app.security.dependencies import TenantAuthContext, get_current_tenant_user, require_tenant_roles
from app.services.tenant_messaging_service import TenantMessagingService

router = APIRouter(tags=["tenant-messaging"])
service = TenantMessagingService()


@router.get("/platform-templates")
async def list_platform_templates(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_platform_templates(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/platform-templates/{template_id}/copy")
async def copy_platform_template(
    template_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.copy_platform_template(
            context.connection,
            tenant_id=context.tenant_id,
            template_id=template_id,
            user_id=context.user_id,
        )
    )


@router.get("/email-templates")
async def list_email_templates(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_email_templates(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/email-templates")
async def create_email_template(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.create_email_template(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.post("/email-templates/ai-generate")
async def ai_generate_email_template(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.ai_generate_email_template(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/email-templates/{template_id}")
async def get_email_template(
    template_id: str,
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    return success_response(await service.get_email_template(context.connection, context.tenant_id, template_id))


@router.put("/email-templates/{template_id}")
async def update_email_template(
    template_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.update_email_template(
            context.connection,
            tenant_id=context.tenant_id,
            template_id=template_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.delete("/email-templates/{template_id}")
async def delete_email_template(
    template_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    await service.delete_email_template(
        context.connection,
        tenant_id=context.tenant_id,
        template_id=template_id,
        user_id=context.user_id,
    )
    return success_response({"deleted": True})


@router.post("/email-templates/{template_id}/clone")
async def clone_email_template(
    template_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.clone_email_template(
            context.connection,
            tenant_id=context.tenant_id,
            template_id=template_id,
            user_id=context.user_id,
        )
    )


@router.get("/email-templates/{template_id}/preview")
async def preview_email_template(
    template_id: str,
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    return success_response(await service.preview_email_template(context.connection, context.tenant_id, template_id))


@router.get("/sending-plans")
async def list_sending_plans(
    context: TenantAuthContext = Depends(get_current_tenant_user),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int | None = Query(None),
    page_size: int | None = Query(None),
) -> dict:
    result = await service.list_sending_plans(
        context.connection,
        context.tenant_id,
        status=status,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    if isinstance(result, dict):
        return paginated_response(result["items"], total=result["total"])
    return paginated_response(result, total=len(result))


@router.post("/sending-plans")
async def create_sending_plan(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.create_sending_plan(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/sending-plans/preview-recipients")
async def preview_group_recipients(
    group_id: str = Query(...),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    result = await service.preview_recipients_for_group(context.connection, context.tenant_id, group_id)
    return success_response(result)


@router.post("/sending-plans/complete-create")
async def create_complete_sending_plan(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.create_complete_sending_plan(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.post("/sending-plans/{plan_id}/complete-update")
async def complete_update_sending_plan(
    plan_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.complete_update_sending_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/sending-plans/{plan_id}")
async def get_sending_plan(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await service.get_sending_plan(context.connection, context.tenant_id, plan_id))


@router.patch("/sending-plans/{plan_id}")
async def patch_sending_plan(
    plan_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.update_sending_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.delete("/sending-plans/{plan_id}")
async def delete_sending_plan(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    await service.delete_sending_plan(
        context.connection,
        tenant_id=context.tenant_id,
        plan_id=plan_id,
        user_id=context.user_id,
    )
    return success_response({"deleted": True})


@router.post("/sending-plans/{plan_id}/schedule")
async def schedule_sending_plan(
    plan_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.schedule_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
            scheduled_at=payload.get("scheduled_at"),
        )
    )


@router.post("/sending-plans/{plan_id}/start")
async def start_sending_plan(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.start_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
        )
    )


@router.post("/sending-plans/{plan_id}/pause")
async def pause_sending_plan(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.pause_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
        )
    )


@router.post("/sending-plans/{plan_id}/resume")
async def resume_sending_plan(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.resume_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
        )
    )


@router.post("/sending-plans/{plan_id}/cancel")
async def cancel_sending_plan(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.cancel_plan(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            user_id=context.user_id,
        )
    )


@router.get("/sending-plans/{plan_id}/recipients")
async def list_plan_recipients(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_plan_recipients(context.connection, context.tenant_id, plan_id)
    return paginated_response(items, total=len(items))


@router.get("/sending-plans/{plan_id}/recipients/preview")
async def preview_plan_recipients(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.preview_plan_recipients(context.connection, tenant_id=context.tenant_id, plan_id=plan_id)
    return paginated_response(items, total=len(items))


@router.post("/sending-plans/{plan_id}/recipients/lock")
async def lock_plan_recipients(
    plan_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.lock_plan_recipients(context.connection, tenant_id=context.tenant_id, plan_id=plan_id)
    )


@router.post("/sending-plans/{plan_id}/recipients/append")
async def append_plan_recipients(
    plan_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.append_plan_recipients(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            payload=payload,
        )
    )


@router.get("/sending-plans/{plan_id}/steps")
async def list_plan_steps(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_plan_steps(context.connection, context.tenant_id, plan_id)
    return paginated_response(items, total=len(items))


@router.post("/sending-plans/{plan_id}/steps")
async def create_plan_step(
    plan_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.create_plan_step(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            payload=payload,
        )
    )


@router.put("/sending-plans/{plan_id}/steps/{step_id}")
async def update_plan_step(
    plan_id: str,
    step_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await service.update_plan_step(
            context.connection,
            tenant_id=context.tenant_id,
            plan_id=plan_id,
            step_id=step_id,
            payload=payload,
        )
    )


@router.delete("/sending-plans/{plan_id}/steps/{step_id}")
async def delete_plan_step(
    plan_id: str,
    step_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    await service.delete_plan_step(context.connection, tenant_id=context.tenant_id, plan_id=plan_id, step_id=step_id)
    return success_response({"deleted": True})


@router.get("/sending-plans/{plan_id}/preview")
async def preview_plan(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await service.preview_plan(context.connection, tenant_id=context.tenant_id, plan_id=plan_id))


@router.get("/sending-plans/{plan_id}/sample-emails")
async def sample_emails(plan_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.sample_emails(context.connection, tenant_id=context.tenant_id, plan_id=plan_id)
    return paginated_response(items, total=len(items))


@router.get("/emails/stats")
async def get_email_stats(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await service.email_stats(context.connection, context.tenant_id))


@router.get("/emails/stats/by-plan")
async def get_email_stats_by_plan(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.email_stats_by_plan(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/emails/stats/by-template")
async def get_email_stats_by_template(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.email_stats_by_template(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/emails/stats/by-step")
async def get_email_stats_by_step(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.email_stats_by_step(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/emails/stats/trend")
async def get_email_stats_trend(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.email_stats_trend(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/emails")
async def list_emails(
    limit: int = 100,
    cursor: str | None = None,
    plan_id: str | None = Query(None),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    page = await service.list_emails(context.connection, context.tenant_id, limit=limit, cursor=cursor, plan_id=plan_id)
    return paginated_response(
        page["items"],
        cursor=page["next_cursor"],
        has_more=page["has_more"],
        total=page["total"],
    )


@router.post("/emails/ai-analysis")
async def email_ai_analysis(context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator"))) -> dict:
    return success_response(await service.email_ai_analysis(context.connection, context.tenant_id))


@router.get("/emails/{email_id}")
async def get_email(email_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await service.get_email(context.connection, context.tenant_id, email_id))
