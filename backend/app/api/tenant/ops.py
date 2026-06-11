from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.core.responses import paginated_response, success_response
from app.security.dependencies import TenantAuthContext, get_current_tenant_user, require_tenant_roles
from app.services.tenant_ops_service import TenantOpsService
from app.services.tenant_query_service import TenantQueryService
from app.services.tenant_scoring_weights_service import TenantScoringWeightsService

router = APIRouter(tags=["tenant-ops"])
ops_service = TenantOpsService()
query_service = TenantQueryService()
scoring_weights_service = TenantScoringWeightsService()


@router.get("/dashboard/funnel")
async def dashboard_funnel(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await ops_service.dashboard_funnel(context.connection, context.tenant_id))


@router.get("/companies/filters")
async def company_filters(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await ops_service.companies_filters(context.connection, context.tenant_id))


@router.get("/companies/export")
async def export_companies(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.export_companies(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/companies")
async def list_companies(
    # C5：10 项筛选参数
    keyword: str | None = Query(None, description="关键词（公司名/域名）"),
    country_iso3: str | None = Query(None, description="国家 ISO3"),
    countries: list[str] = Query(default=[], alias="countries[]", description="国家多选 OR"),
    industry_tags: list[str] = Query(default=[], alias="industry_tags", description="行业细分多选 OR"),
    sub_industries: list[str] = Query(default=[], alias="sub_industries[]", description="子行业多选 OR"),
    product_tags: list[str] = Query(default=[], alias="product_tags[]", description="产品标签多选 OR"),
    source_type: str | None = Query(None, description="数据来源"),
    sources: list[str] = Query(default=[], alias="sources[]", description="来源多选 OR"),
    incorporation_date_from: str | None = Query(None, description="成立日期起"),
    incorporation_date_to: str | None = Query(None, description="成立日期止"),
    reg_capital_min: float | None = Query(None, description="最低注册资金"),
    reg_capital_max: float | None = Query(None, description="最高注册资金"),
    employee_num: str | None = Query(None, description="公司规模"),
    trade_amount_min: float | None = Query(None, description="最低近三年进出口金额"),
    trade_amount_max: float | None = Query(None, description="最高近三年进出口金额"),
    trade_count_min: int | None = Query(None, description="最低进出口次数"),
    trade_count_max: int | None = Query(None, description="最高进出口次数"),
    business_status: str | None = Query(None, description="业务状态"),
    data_status: str | None = Query(None, description="数据状态"),
    score_min: float | None = Query(None, description="最低当前评分"),
    score_max: float | None = Query(None, description="最高当前评分"),
    contacts_count_min: int | None = Query(None, description="兼容旧参数：最少联系人数量"),
    contacts_count_max: int | None = Query(None, description="兼容旧参数：最多联系人数量"),
    contact_count_min: int | None = Query(None, description="最少联系人数量"),
    contact_count_max: int | None = Query(None, description="最多联系人数量"),
    founded_year_from: int | None = Query(None, description="成立年份起"),
    founded_year_to: int | None = Query(None, description="成立年份止"),
    employee_scales: list[str] = Query(default=[], alias="employee_scale[]", description="规模档位多选 OR"),
    employee_count_min: int | None = Query(None, description="最小员工人数"),
    employee_count_max: int | None = Query(None, description="最大员工人数"),
    pcb_supplier_presence: str | None = Query(None, description="PCB 供应商：has/none"),
    min_score: float | None = Query(None, description="最低分"),
    max_score: float | None = Query(None, description="最高分"),
    grade: str | None = Query(None, description="评级筛选（兼容旧参数，单选）"),
    grades: list[str] = Query(default=[], alias="grades[]", description="评级多选 OR"),
    group_id: str | None = Query(None, description="群组ID过滤"),
    collection_type: str | None = Query(None, description="采集类型：keyword/reverse"),
    limit: int = Query(50, ge=1, le=1000, description="每页条数"),
    cursor: str | None = Query(None, description="游标分页"),
    page: int | None = Query(None, ge=1, description="页码分页页号"),
    page_size: int | None = Query(None, ge=1, le=1000, description="页码分页每页条数"),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    effective_limit = page_size or limit
    offset = (page - 1) * effective_limit if page is not None else None
    items, total = await query_service.companies_page(
        context.connection,
        context.tenant_id,
        keyword=keyword,
        country_iso3=country_iso3,
        countries=countries or None,
        industry_tags=industry_tags or None,
        sub_industries=sub_industries or None,
        product_tags=product_tags or None,
        source_type=source_type,
        sources=sources or None,
        incorporation_date_from=incorporation_date_from,
        incorporation_date_to=incorporation_date_to,
        reg_capital_min=reg_capital_min,
        reg_capital_max=reg_capital_max,
        employee_num=employee_num,
        trade_amount_min=trade_amount_min,
        trade_amount_max=trade_amount_max,
        trade_count_min=trade_count_min,
        trade_count_max=trade_count_max,
        business_status=business_status,
        data_status=data_status,
        score_min=score_min,
        score_max=score_max,
        contact_count_min=contact_count_min,
        contact_count_max=contact_count_max,
        contacts_count_min=contacts_count_min,
        contacts_count_max=contacts_count_max,
        founded_year_from=founded_year_from,
        founded_year_to=founded_year_to,
        employee_scales=employee_scales or None,
        employee_count_min=employee_count_min,
        employee_count_max=employee_count_max,
        pcb_supplier_presence=pcb_supplier_presence,
        min_score=min_score,
        max_score=max_score,
        grades=grades or ([grade] if grade else None),
        group_id=group_id,
        collection_type=collection_type,
        limit=effective_limit + (0 if page is not None else 1),
        cursor=None if page is not None else cursor,
        offset=offset,
    )
    has_more = (page * effective_limit < total) if page is not None else len(items) > effective_limit
    page_items = items[:effective_limit]
    next_cursor = page_items[-1]["id"] if has_more and page_items else None
    return paginated_response(
        page_items,
        cursor=None if page is not None else next_cursor,
        has_more=has_more,
        total=total,
    )


@router.post("/companies")
async def create_company(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.create_company(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.post("/companies/batch-import")
async def batch_import_companies(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.batch_import_companies(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/companies/{company_id}")
async def get_company(company_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(
        await query_service.v3_company_detail(context.connection, context.tenant_id, company_id)
    )


@router.post("/companies/{company_id}/blacklist")
async def blacklist_company(
    company_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.blacklist_company(
            context.connection,
            tenant_id=context.tenant_id,
            company_id=company_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/companies/{company_id}/contacts")
async def company_contacts(company_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await query_service.v3_company_contacts(context.connection, context.tenant_id, company_id)
    return paginated_response(items, total=len(items))


@router.get("/prospects")
async def list_prospects(
    keyword: str | None = Query(None, description="关键词（公司名/域名）"),
    countries: list[str] = Query(default=[], alias="countries[]", description="国家多选 OR"),
    sub_industries: list[str] = Query(default=[], alias="sub_industries[]", description="子行业多选 OR"),
    product_tags: list[str] = Query(default=[], alias="product_tags[]", description="产品标签多选 OR"),
    sources: list[str] = Query(default=[], alias="sources[]", description="来源多选 OR"),
    employee_count_min: int | None = Query(None, description="最小员工人数"),
    employee_count_max: int | None = Query(None, description="最大员工人数"),
    trade_amount_min: float | None = Query(None, description="最低近三年进出口金额"),
    trade_amount_max: float | None = Query(None, description="最高近三年进出口金额"),
    trade_count_min: int | None = Query(None, description="最低进出口次数"),
    trade_count_max: int | None = Query(None, description="最高进出口次数"),
    contact_count_min: int | None = Query(None, description="最少联系人数量"),
    contact_count_max: int | None = Query(None, description="最多联系人数量"),
    founded_year_from: int | None = Query(None, description="成立年份起"),
    founded_year_to: int | None = Query(None, description="成立年份止"),
    pcb_supplier_presence: str | None = Query(None, description="PCB 供应商：has/none"),
    limit: int = Query(50, ge=1, le=1000, description="每页条数"),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    items = await query_service.prospects(
        context.connection,
        context.tenant_id,
        keyword=keyword,
        countries=countries or None,
        sub_industries=sub_industries or None,
        product_tags=product_tags or None,
        sources=sources or None,
        employee_count_min=employee_count_min,
        employee_count_max=employee_count_max,
        trade_amount_min=trade_amount_min,
        trade_amount_max=trade_amount_max,
        trade_count_min=trade_count_min,
        trade_count_max=trade_count_max,
        contact_count_min=contact_count_min,
        contact_count_max=contact_count_max,
        founded_year_from=founded_year_from,
        founded_year_to=founded_year_to,
        pcb_supplier_presence=pcb_supplier_presence,
        limit=limit,
    )
    return paginated_response(items, total=len(items))


@router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await ops_service.get_prospect(context.connection, context.tenant_id, prospect_id))


@router.patch("/prospects/{prospect_id}")
async def patch_prospect(
    prospect_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.update_prospect(
            context.connection,
            tenant_id=context.tenant_id,
            prospect_id=prospect_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.post("/prospects/{prospect_id}/select")
async def select_prospect(
    prospect_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    raise AppError(code="UNSUPPORTED_OPERATION", message="旧 select 入口已停用", status_code=410)


@router.post("/prospects/{prospect_id}/exclude")
async def exclude_prospect(
    prospect_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    raise AppError(code="UNSUPPORTED_OPERATION", message="旧 exclude 入口已停用", status_code=410)


@router.post("/prospects/{prospect_id}/blacklist")
async def blacklist_prospect(
    prospect_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.blacklist_company(
            context.connection,
            tenant_id=context.tenant_id,
            company_id=prospect_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.patch("/contacts/{contact_id}/set-default")
async def set_default_contact(
    contact_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.set_default_contact(
            context.connection,
            tenant_id=context.tenant_id,
            contact_id=contact_id,
            user_id=context.user_id,
        )
    )


@router.get("/groups")
async def list_groups(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.list_groups(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.post("/groups")
async def create_group(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.create_group(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/groups/{group_id}")
async def get_group(group_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await ops_service.get_group(context.connection, context.tenant_id, group_id))


@router.patch("/groups/{group_id}")
async def patch_group(
    group_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.update_group(
            context.connection,
            tenant_id=context.tenant_id,
            group_id=group_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    await ops_service.delete_group(
        context.connection,
        tenant_id=context.tenant_id,
        group_id=group_id,
        user_id=context.user_id,
    )
    return success_response({"deleted": True})


@router.get("/groups/{group_id}/members")
async def list_group_members(group_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.list_group_members(context.connection, context.tenant_id, group_id)
    return paginated_response(items, total=len(items))


@router.post("/groups/{group_id}/members/batch-add")
async def batch_add_group_members(
    group_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.add_group_members(
            context.connection,
            tenant_id=context.tenant_id,
            group_id=group_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.post("/groups/{group_id}/members/batch-remove")
async def batch_remove_group_members(
    group_id: str,
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    return success_response(
        await ops_service.remove_group_members(
            context.connection,
            tenant_id=context.tenant_id,
            group_id=group_id,
            user_id=context.user_id,
            payload=payload,
        )
    )


@router.get("/domains")
async def list_domains(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.list_domains(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/domains/{domain_id}")
async def get_domain(domain_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(await ops_service.get_domain(context.connection, context.tenant_id, domain_id))


@router.get("/domains/{domain_id}/history")
async def get_domain_history(domain_id: str, context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.get_domain_history(context.connection, context.tenant_id, domain_id)
    return paginated_response(items, total=len(items))


@router.get("/ai/usage-summary")
async def ai_usage_summary(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    return success_response(await ops_service.ai_usage_summary(context.connection, context.tenant_id))


@router.get("/ai/usage-trend")
async def ai_usage_trend(context: TenantAuthContext = Depends(require_tenant_roles("admin"))) -> dict:
    items = await ops_service.ai_usage_trend(context.connection, context.tenant_id)
    return paginated_response(items, total=len(items))


@router.get("/notifications")
async def list_notifications(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    items = await ops_service.list_notifications(context.connection, context.tenant_id, context.user_id)
    return paginated_response(items, total=len(items))


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    return success_response(
        await ops_service.mark_notification_read(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            notification_id=notification_id,
        )
    )


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    return success_response(
        await ops_service.mark_all_notifications_read(
            context.connection,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
    )


# ─── C6：评分权重 API ────────────────────────────────────────────────────────


@router.get("/scoring-weights")
async def list_scoring_weights(
    template_id: str | None = Query(None, description="模板 ID，不传则返回所有"),
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    """获取租户对指定模板的自定义维度权重列表。"""
    items = await scoring_weights_service.list_weights(
        context.connection,
        tenant_id=context.tenant_id,
        template_id=template_id,
    )
    return paginated_response(items, total=len(items))


@router.put("/scoring-weights")
async def upsert_scoring_weights(
    payload: dict,
    context: TenantAuthContext = Depends(require_tenant_roles("admin", "operator")),
) -> dict:
    """批量 upsert 租户维度权重。payload: {template_id, weights:[{dimension, weight}]}。"""
    result = await scoring_weights_service.upsert_weights(
        context.connection,
        tenant_id=context.tenant_id,
        payload=payload,
    )
    return success_response(result)
