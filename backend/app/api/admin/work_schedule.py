from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.admin_work_schedule_service import AdminWorkScheduleService

router = APIRouter(prefix="/work-schedule", tags=["admin-work-schedule"])
service = AdminWorkScheduleService()


@router.get("/rule-sets")
async def list_rule_sets(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    items = await service.list_rule_sets(context.connection)
    return paginated_response(items, total=len(items))


@router.post("/rule-sets")
async def create_rule_set(payload: dict, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        await service.create_rule_set(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/rule-sets/{rule_set_id}")
async def get_rule_set(rule_set_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(await service.get_rule_set(context.connection, rule_set_id))


@router.patch("/rule-sets/{rule_set_id}")
async def update_rule_set(
    rule_set_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_rule_set(
            context.connection,
            rule_set_id=rule_set_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/rule-sets/{rule_set_id}")
async def delete_rule_set(rule_set_id: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    await service.delete_rule_set(
        context.connection,
        rule_set_id=rule_set_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.post("/rule-sets/{rule_set_id}/countries")
async def assign_countries_to_rule_set(
    rule_set_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.assign_countries_to_rule_set(
        context.connection,
        rule_set_id=rule_set_id,
        iso3_list=payload.get("countries") or payload.get("iso3_list") or [],
        platform_user_id=context.platform_user_id,
    )
    return paginated_response(items, total=len(items))


@router.delete("/rule-sets/{rule_set_id}/countries/{iso3}")
async def remove_country_from_rule_set(
    rule_set_id: str,
    iso3: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.remove_country_from_rule_set(
            context.connection,
            rule_set_id=rule_set_id,
            iso3=iso3,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/countries")
async def list_countries(
    search: str | None = None,
    has_rule_set: bool | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_countries(context.connection, search=search, has_rule_set=has_rule_set)
    return paginated_response(items, total=len(items))


@router.get("/countries/{iso3}")
async def get_country(iso3: str, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(await service.get_country(context.connection, iso3))


@router.patch("/countries/{iso3}")
async def update_country(
    iso3: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.update_country(
            context.connection,
            iso3=iso3,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.get("/countries/{iso3}/holidays")
async def list_holidays(
    iso3: str,
    year: int | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_holidays(context.connection, iso3=iso3, year=year)
    return paginated_response(items, total=len(items))


@router.post("/countries/{iso3}/holidays")
async def create_holiday(
    iso3: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    return success_response(
        await service.create_holiday(
            context.connection,
            iso3=iso3,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.patch("/countries/{iso3}/holidays/{holiday_id}")
async def update_holiday(
    iso3: str,
    holiday_id: str,
    payload: dict,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    _ = iso3
    return success_response(
        await service.update_holiday(
            context.connection,
            holiday_id=holiday_id,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )


@router.delete("/countries/{iso3}/holidays/{holiday_id}")
async def delete_holiday(
    iso3: str,
    holiday_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    _ = iso3
    await service.delete_holiday(
        context.connection,
        holiday_id=holiday_id,
        platform_user_id=context.platform_user_id,
    )
    return success_response({"deleted": True})


@router.get("/default-rule")
async def get_default_rule(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(await service.get_default_rule(context.connection))


@router.patch("/default-rule")
async def update_default_rule(payload: dict, context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        await service.update_default_rule(
            context.connection,
            payload=payload,
            platform_user_id=context.platform_user_id,
        )
    )
