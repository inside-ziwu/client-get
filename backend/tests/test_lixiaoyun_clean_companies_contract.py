from pathlib import Path


def test_list_sql_uses_clean_companies_table() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "FROM lixiaoyun_api_clean_companies c" in source


def test_list_sql_has_keyword_agg_cte_with_order() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "keyword_agg" in source
    assert "ORDER BY km.keyword_normalized" in source


def test_keyword_filter_matches_both_keyword_and_normalized() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "km.keyword ILIKE :keyword_filter" in source
    assert "km.keyword_normalized ILIKE :keyword_filter" in source


def test_industry_tag_exact_match() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "c.industry_tags = :industry_tag" in source


def test_uses_shared_reg_cap_and_employee_scale_case() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "def _reg_cap_case(" in source
    assert "def _employee_scale_case(" in source
    assert "REG_CAP_RANGE" in source
    assert "EMPLOYEE_SCALE_RANGE" in source


def test_list_order_by_created_at_desc() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "ORDER BY c.created_at DESC, c.id DESC" in source


def test_detail_sql_has_company_id_param() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert "WHERE c.id = :company_id" in source


def test_t1_regression_list_raw_companies_uses_shared_case() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert '_reg_cap_case("reg_capital")' in source
    assert '_employee_scale_case("employee_scale")' in source


def test_t1_regression_list_v3_raw_companies_uses_shared_case() -> None:
    source = Path("app/services/admin_collection_service.py").read_text()
    assert '_reg_cap_case("c.reg_cap")' in source
    assert '_employee_scale_case("c.scale")' in source
