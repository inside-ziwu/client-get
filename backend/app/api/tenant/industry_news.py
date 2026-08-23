from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.responses import paginated_response, success_response
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.industry_news.service import IndustryNewsService

router = APIRouter(tags=["tenant-industry-news"])
service = IndustryNewsService()
TenantContext = Annotated[TenantAuthContext, Depends(get_current_tenant_user)]
CategoryFilter = Annotated[
    list[str], Query(default_factory=list, alias="category[]", description="类别多选")
]
SourceFilter = Annotated[
    list[str], Query(default_factory=list, alias="source_id[]", description="来源多选")
]
PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=100)]


@router.get("/industry-news/items")
async def list_industry_news_items(
    context: TenantContext,
    category: CategoryFilter,
    source_id: SourceFilter,
    lang: str | None = None,
    unread_only: bool = False,
    page: PageParam = 1,
    page_size: PageSizeParam = 50,
) -> dict:
    items, total = await service.list_items(
        context.connection,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        instance_id=get_settings().instance_id,
        categories=category or None,
        source_ids=source_id or None,
        lang=lang,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    return paginated_response(items, total=total, has_more=page * page_size < total)


@router.get("/industry-news/filters")
async def list_industry_news_filters(context: TenantContext) -> dict:
    return success_response(
        await service.list_filter_options(
            context.connection,
            tenant_id=context.tenant_id,
            instance_id=get_settings().instance_id,
        )
    )


@router.post("/industry-news/items/{item_id}/read")
async def mark_industry_news_read(item_id: str, context: TenantContext) -> dict:
    return success_response(
        await service.mark_read(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            instance_id=get_settings().instance_id,
            item_id=item_id,
        )
    )
