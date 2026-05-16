from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.security.dependencies import TenantAuthContext, require_tenant_roles
from app.services.tenant_team_service import TenantTeamService

router = APIRouter(tags=["tenant-team"])
service = TenantTeamService()


@router.get("/team/users")
async def list_team_users(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    items = await service.list_users(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/team/users")
async def create_team_user(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    return success_response(
        await service.create_user(
            context.connection,
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            payload=payload,
        )
    )


@router.patch("/team/users/{user_id}")
async def update_team_user(
    user_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    return success_response(
        await service.update_user(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=user_id,
            actor_user_id=context.user_id,
            payload=payload,
        )
    )


@router.delete("/team/users/{user_id}")
async def delete_team_user(
    user_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin")),
) -> dict:
    await service.delete_user(
        context.connection,
        tenant_id=context.tenant_id,
        user_id=user_id,
        actor_user_id=context.user_id,
    )
    return success_response({"deleted": True})
