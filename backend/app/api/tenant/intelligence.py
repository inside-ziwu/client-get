from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.intelligence_service import IntelligenceService

router = APIRouter(tags=["tenant-intelligence"])
service = IntelligenceService()


@router.get("/intelligence/subscriptions")
async def get_subscriptions(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.get_subscriptions(context.connection, context.tenant_id, context.user_id)
    return paginated_response(items, total=len(items))


@router.put("/intelligence/subscriptions")
async def put_subscriptions(payload: dict, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.put_subscriptions(
        context.connection,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        payload=payload,
    )
    return paginated_response(items, total=len(items))


@router.get("/intelligence/articles")
async def list_articles(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await service.list_articles(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/intelligence/articles/{article_id}")
async def get_article(article_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await service.get_article(context.connection, context.tenant_id, article_id))


@router.post("/intelligence/articles/{article_id}/read")
async def read_article(article_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(
        await service.mark_article_status(context.connection, tenant_id=context.tenant_id, article_id=article_id, status="read")
    )


@router.post("/intelligence/articles/{article_id}/star")
async def star_article(article_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(
        await service.mark_article_status(context.connection, tenant_id=context.tenant_id, article_id=article_id, status="starred")
    )


@router.post("/intelligence/articles/{article_id}/archive")
async def archive_article(article_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(
        await service.mark_article_status(context.connection, tenant_id=context.tenant_id, article_id=article_id, status="archived")
    )
