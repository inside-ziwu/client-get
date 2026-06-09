from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.responses import paginated_response, success_response
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.admin_collection_service import AdminCollectionService
from app.services.keyword_service import lookup_keyword_master, normalize_keyword

router = APIRouter(tags=["admin-collection"])
service = AdminCollectionService()


@router.get("/collection-keywords")
async def list_collection_keywords(
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    items = await service.list_collection_keywords(context.connection)
    return paginated_response(items, total=len(items))



@router.get("/collection/dashboard")
async def get_collection_dashboard(
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_dashboard(context.connection)
    return success_response(result)


@router.get("/collection/raw/{table}")
async def list_collection_raw(
    table: str,
    page: int = 1,
    page_size: int = 20,
    include_payload: bool = False,
    keyword: str | None = None,
    country: str | None = None,
    # lixiaoyun
    keyword_filter: str | None = None,
    found_date_start: str | None = None,
    found_date_end: str | None = None,
    reg_capital: str | None = None,
    employee_scale: str | None = None,
    contacts_filter: str | None = None,
    has_name_en: bool | None = None,
    has_domain: bool | None = None,
    # tendata
    industry: str | None = None,
    tag: str | None = None,
    size: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    count_min: int | None = None,
    count_max: int | None = None,
    pcb: str | None = None,
    contact_min: int | None = None,
    contact_max: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    method: str | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_raw_companies(
        context.connection,
        table=table, page=page, page_size=page_size,
        include_payload=include_payload,
        keyword=keyword, country=country,
        keyword_filter=keyword_filter, found_date_start=found_date_start,
        found_date_end=found_date_end, reg_capital=reg_capital,
        employee_scale=employee_scale, contacts_filter=contacts_filter,
        has_name_en=has_name_en, has_domain=has_domain,
        industry=industry, tag=tag, size=size,
        amount_min=amount_min, amount_max=amount_max,
        count_min=count_min, count_max=count_max,
        pcb=pcb, contact_min=contact_min, contact_max=contact_max,
        year_min=year_min, year_max=year_max, method=method,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/collection/clean-companies")
async def list_collection_clean(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    country: str | None = None,
    industry: str | None = None,
    tag: str | None = None,
    size: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    count_min: int | None = None,
    count_max: int | None = None,
    pcb: str | None = None,
    contact_min: int | None = None,
    contact_max: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_clean_companies(
        context.connection,
        page=page, page_size=page_size, keyword=keyword,
        country=country, industry=industry, tag=tag, size=size,
        amount_min=amount_min, amount_max=amount_max,
        count_min=count_min, count_max=count_max,
        pcb=pcb, contact_min=contact_min, contact_max=contact_max,
        year_min=year_min, year_max=year_max,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/raw/{provider}/companies")
async def list_v3_raw_companies(
    provider: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword_master_id: str | None = None,
    q: str | None = None,
    keyword: str | None = None,
    country_iso3: str | None = None,
    country: str | None = None,
    # lixiaoyun
    keyword_filter: str | None = None,
    found_date_start: str | None = None,
    found_date_end: str | None = None,
    reg_capital: str | None = None,
    employee_scale: str | None = None,
    contacts_filter: str | None = None,
    has_name_en: bool | None = None,
    has_domain: bool | None = None,
    # tendata
    industry: str | None = None,
    tag: str | None = None,
    size: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    count_min: int | None = None,
    count_max: int | None = None,
    pcb: str | None = None,
    contact_min: int | None = None,
    contact_max: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    method: str | None = None,
    # waimaotong
    source_keyword: str | None = None,
    source_competitor: str | None = None,
    has_contacts: bool | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_v3_raw_companies(
        context.connection,
        provider=provider,
        page=page,
        page_size=page_size,
        keyword_master_id=keyword_master_id,
        q=q or keyword,
        country_iso3=country_iso3 or country,
        keyword_filter=keyword_filter,
        found_date_start=found_date_start,
        found_date_end=found_date_end,
        reg_capital=reg_capital,
        employee_scale=employee_scale,
        contacts_filter=contacts_filter,
        has_name_en=has_name_en,
        has_domain=has_domain,
        industry=industry,
        tag=tag,
        size=size,
        amount_min=amount_min,
        amount_max=amount_max,
        count_min=count_min,
        count_max=count_max,
        pcb=pcb,
        contact_min=contact_min,
        contact_max=contact_max,
        year_min=year_min,
        year_max=year_max,
        method=method,
        source_keyword=source_keyword,
        source_competitor=source_competitor,
        has_contacts=has_contacts,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/raw/{provider}/companies/{raw_company_id}/debug")
async def get_v3_raw_company_debug(
    provider: str,
    raw_company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_v3_raw_company_debug(
        context.connection,
        provider=provider,
        raw_company_id=raw_company_id,
    )
    return success_response(result)


@router.get("/raw/{provider}/companies/{raw_company_id}/contacts")
async def list_v3_raw_company_contacts(
    provider: str,
    raw_company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows = await service.list_v3_raw_company_contacts(
        context.connection,
        provider=provider,
        raw_company_id=raw_company_id,
    )
    return paginated_response(rows, total=len(rows))


@router.get("/clean/companies")
async def list_v3_clean_companies(
    page: int = 1,
    page_size: int = 20,
    source_type: str | None = None,
    keyword: str | None = None,
    q: str | None = None,
    countries: list[str] = Query(default=[], alias="countries[]"),
    sub_industries: list[str] = Query(default=[], alias="sub_industries[]"),
    product_tags: list[str] = Query(default=[], alias="product_tags[]"),
    sources: list[str] = Query(default=[], alias="sources[]"),
    employee_count_min: int | None = None,
    employee_count_max: int | None = None,
    trade_amount_min: float | None = None,
    trade_amount_max: float | None = None,
    trade_count_min: int | None = None,
    trade_count_max: int | None = None,
    contact_count_min: int | None = None,
    contact_count_max: int | None = None,
    founded_year_from: int | None = None,
    founded_year_to: int | None = None,
    pcb_supplier_presence: str | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_v3_clean_companies(
        context.connection,
        page=page,
        page_size=page_size,
        source_type=source_type,
        keyword=q or keyword,
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
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


# ── 同行公司（peer_companies）──────────────────────


@router.get("/collection/peer-companies")
async def list_peer_companies(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    keyword_filter: str | None = None,
    found_date_start: date | None = None,
    found_date_end: date | None = None,
    reg_capital: str | None = None,
    employee_scale: str | None = None,
    contacts_count: str | None = None,
    has_name_en: bool | None = None,
    has_domain: bool | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_peer_companies(
        context.connection,
        page=page,
        page_size=page_size,
        keyword=keyword,
        keyword_filter=keyword_filter,
        found_date_start=found_date_start,
        found_date_end=found_date_end,
        reg_capital=reg_capital,
        employee_scale=employee_scale,
        contacts_count=contacts_count,
        has_name_en=has_name_en,
        has_domain=has_domain,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/collection/peer-companies/{peer_id}")
async def get_peer_company_detail(
    peer_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_peer_company_detail(context.connection, peer_id=peer_id)
    return success_response(result)



# ── 同行公司（清洗）──────────────────────


@router.get("/collection/lixiaoyun-clean-companies")
async def list_lixiaoyun_clean_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    keyword_filter: str | None = None,
    industry_tag: str | None = None,
    found_date_start: str | None = None,
    found_date_end: str | None = None,
    reg_capital: str | None = None,
    employee_scale: str | None = None,
    has_name_en: bool | None = None,
    has_domain: bool | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_lixiaoyun_clean_companies(
        context.connection,
        page=page,
        page_size=page_size,
        keyword=keyword,
        keyword_filter=keyword_filter,
        industry_tag=industry_tag,
        found_date_start=found_date_start,
        found_date_end=found_date_end,
        reg_capital=reg_capital,
        employee_scale=employee_scale,
        has_name_en=has_name_en,
        has_domain=has_domain,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/collection/lixiaoyun-clean-companies/{company_id}")
async def get_lixiaoyun_clean_company_detail(
    company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_lixiaoyun_clean_company_detail(
        context.connection, company_id=company_id
    )
    return success_response(result)


@router.get("/collection/peer-companies/{peer_id}/contacts")
async def list_peer_company_contacts(
    peer_id: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows = await service.list_peer_company_contacts(context.connection, peer_id=peer_id)
    return paginated_response(rows, total=len(rows))


@router.get("/collection/cleanup-health")
async def get_collection_cleanup_health(
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_cleanup_health(context.connection)
    return success_response(result)


@router.get("/collection-keywords/{keyword_normalized}/master-check")
async def keyword_master_check(
    keyword_normalized: str,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    """查询 keyword_master 命中情况。

    返回：
        matched=True 时：已入库，附带关联公司数和租户数
        matched=False 时：该关键词尚未被任何租户采集过

    URL 中的 keyword_normalized 会再次过归一化函数，保证一致性。
    """
    # 对路径参数再次归一化，防止 URL 编码差异
    kn = normalize_keyword(keyword_normalized)
    result = await lookup_keyword_master(context.connection, kn)
    if result is None:
        return success_response({"matched": False, "company_count": 0, "tenant_count": 0})
    return success_response(result)


# ── waimaotong clean companies ──────────────────────────────────


@router.get("/collection/wmt-clean-companies")
async def list_wmt_clean_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    country: str | None = None,
    industry: str | None = None,
    size: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    has_contacts: bool | None = None,
    grade: str | None = None,
    collection_type: str | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows, total = await service.list_wmt_clean_companies(
        context.connection,
        page=page,
        page_size=page_size,
        q=q,
        country=country,
        industry=industry,
        size=size,
        year_min=year_min,
        year_max=year_max,
        has_contacts=has_contacts,
        grade=grade,
        collection_type=collection_type,
    )
    return paginated_response(rows, total=total, has_more=(page * page_size < total))


@router.get("/collection/wmt-clean-companies/{company_id}")
async def get_wmt_clean_company(
    company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    result = await service.get_wmt_clean_company(
        context.connection,
        company_id=company_id,
    )
    return success_response(result)


@router.get("/collection/wmt-clean-companies/{company_id}/contacts")
async def list_wmt_clean_company_contacts(
    company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
) -> dict:
    rows = await service.list_wmt_clean_company_contacts(
        context.connection,
        company_id=company_id,
    )
    return paginated_response(rows, total=len(rows))
