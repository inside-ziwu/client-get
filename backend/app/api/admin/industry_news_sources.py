from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.responses import success_response
from app.schemas.industry_news import IndustryNewsSourceToggle
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.industry_news.service import IndustryNewsService
from app.workers.industry_news_fetch import trigger_fetch

router = APIRouter(prefix="/industry-news-sources", tags=["admin-industry-news-sources"])
service = IndustryNewsService()
PlatformContext = Annotated[PlatformAuthContext, Depends(get_current_platform_user)]


@router.get("")
async def list_industry_news_sources(context: PlatformContext) -> dict:
    sources = await service.list_sources(context.connection, get_settings().instance_id)
    return success_response(sources)


@router.post("/fetch", status_code=202)
async def trigger_industry_news_fetch(context: PlatformContext) -> dict:
    del context  # 后台任务必须用 get_engine() 开新连接，不得复用请求事务
    result = await trigger_fetch(instance_id=get_settings().instance_id)
    return success_response(result)


@router.patch("/{source_id}")
async def patch_industry_news_source(
    source_id: str,
    payload: IndustryNewsSourceToggle,
    context: PlatformContext,
) -> dict:
    return success_response(
        await service.set_source_active(
            context.connection,
            instance_id=get_settings().instance_id,
            source_id=source_id,
            is_active=payload.is_active,
        )
    )
