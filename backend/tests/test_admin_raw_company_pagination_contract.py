from pathlib import Path


def test_admin_v3_raw_companies_page_size_is_capped_at_100() -> None:
    source = Path("app/api/admin/collection.py").read_text()

    assert "Query" in source
    assert "page: int = Query(1, ge=1)" in source
    assert "page_size: int = Query(20, ge=1, le=100)" in source


def test_admin_v3_lixiaoyun_raw_companies_query_uses_api_company_fields() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()

    assert "FROM lixiaoyun_api_companies c" in source
    assert "JOIN keyword_master km ON km.id = c.keyword_master_id" in source
    assert "c.entname_eng" in source
    assert "c.official_website" in source
    assert "to_timestamp(c.esdate / 1000)::date AS esdate" in source
    assert "ORDER BY c.collected_at DESC, c.id DESC" in source
    assert "c.raw_payload->>'company_name_en'" not in source
    assert "jsonb_array_length(c.raw_payload->'lx_contacts')" not in source
    assert "FROM lixiaoyun_raw_contacts" not in source
