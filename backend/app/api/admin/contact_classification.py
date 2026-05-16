"""Admin API：联系人职位分类管理（等级 / 类别 / 关键词 CRUD）。"""

from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.contact_classification_service import ContactClassificationService

router = APIRouter(prefix="/contact-classification", tags=["admin-contact-classification"])
service = ContactClassificationService()


# ── 等级 ──────────────────────────────────────────────────────────────────────

@router.get("/levels")
async def list_levels(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    """返回完整层级树（等级 → 类别 → 关键词）。"""
    items = await service.list_levels(context.connection)
    return paginated_response(items, total=len(items))


@router.post("/levels")
async def create_level(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """新建等级（name, display_name, sort_order, is_sendable）。"""
    item = await service.create_level(context.connection, payload)
    return success_response(item)


@router.put("/levels/{level_id}")
async def update_level(
    level_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """更新等级属性（含 is_sendable）。"""
    item = await service.update_level(context.connection, level_id, payload)
    return success_response(item)


@router.delete("/levels/{level_id}")
async def delete_level(
    level_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """删除等级（CASCADE 删除关联类别和关键词）。"""
    await service.delete_level(context.connection, level_id)
    return success_response({"deleted": True})


# ── 类别 ──────────────────────────────────────────────────────────────────────

@router.post("/categories")
async def create_category(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """新建类别（level_id, name, display_name, sort_order）。"""
    item = await service.create_category(context.connection, payload)
    return success_response(item)


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """删除类别（CASCADE 删除关联关键词）。"""
    await service.delete_category(context.connection, category_id)
    return success_response({"deleted": True})


# ── 关键词 ────────────────────────────────────────────────────────────────────

@router.post("/keywords")
async def add_keywords(
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """批量添加关键词（body: {category_id: str, keywords: string[]}）。"""
    category_id: str = payload["category_id"]
    keywords: list[str] = payload["keywords"]
    inserted = await service.add_keywords(context.connection, category_id, keywords)
    return paginated_response(inserted, total=len(inserted))


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """删除单个关键词。"""
    await service.delete_keyword(context.connection, keyword_id)
    return success_response({"deleted": True})
