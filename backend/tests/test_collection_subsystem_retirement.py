"""采集死子系统路由退役白名单。"""

import inspect
import re

from app.main import create_app
from app.services.admin_collection_service import AdminCollectionService
from app.services.admin_config_service import AdminConfigService
from app.services.scoring_engine_service import ScoringEngineService


def _route_keys():
    return {
        (method, route.path)
        for route in create_app().routes
        for method in getattr(route, "methods", set())
    }


def test_removed_collection_routes_are_absent():
    routes = _route_keys()
    removed = {
        ("GET", "/admin/api/v1/collection-tasks"),
        ("GET", "/admin/api/v1/data-sources"),
        ("POST", "/admin/api/v1/data-sources"),
        ("PATCH", "/admin/api/v1/data-sources/{source_type}"),
        ("PATCH", "/admin/api/v1/data-sources/{source_type}/config"),
        ("GET", "/admin/api/v1/data-sources/{source_type}/credentials"),
        ("POST", "/admin/api/v1/data-sources/{source_type}/credentials"),
        ("PATCH", "/admin/api/v1/data-sources/{source_type}/credentials/{credential_id}"),
        ("DELETE", "/admin/api/v1/data-sources/{source_type}/credentials/{credential_id}"),
        ("GET", "/admin/api/v1/collection-keywords"),
        ("GET", "/admin/api/v1/collection/dashboard"),
        ("GET", "/admin/api/v1/collection/raw/{table}"),
        ("GET", "/admin/api/v1/collection/clean-companies"),
        ("GET", "/admin/api/v1/clean/companies"),
        ("GET", "/admin/api/v1/collection/peer-companies"),
        ("GET", "/admin/api/v1/collection/peer-companies/{peer_id}"),
        ("GET", "/admin/api/v1/collection/peer-companies/{peer_id}/contacts"),
        ("GET", "/admin/api/v1/collection/cleanup-health"),
        ("GET", "/admin/api/v1/collection-keywords/{keyword_normalized}/master-check"),
        ("GET", "/internal/api/v1/collection/credentials/{source_type}"),
        ("GET", "/t/{slug}/api/v1/keywords"),
        ("POST", "/t/{slug}/api/v1/keywords"),
        ("PATCH", "/t/{slug}/api/v1/keywords/{keyword_id}"),
        ("DELETE", "/t/{slug}/api/v1/keywords/{keyword_id}"),
    }
    assert routes.isdisjoint(removed)


def test_four_admin_data_pages_keep_their_api_routes():
    routes = _route_keys()
    retained = {
        ("GET", "/admin/api/v1/raw/{provider}/companies"),
        ("GET", "/admin/api/v1/raw/{provider}/companies/{raw_company_id}/debug"),
        ("GET", "/admin/api/v1/raw/{provider}/companies/{raw_company_id}/contacts"),
        ("GET", "/admin/api/v1/collection/lixiaoyun-clean-companies"),
        ("GET", "/admin/api/v1/collection/lixiaoyun-clean-companies/{company_id}"),
        ("GET", "/admin/api/v1/collection/wmt-clean-companies"),
        ("GET", "/admin/api/v1/collection/wmt-clean-companies/{company_id}"),
        ("GET", "/admin/api/v1/collection/wmt-clean-companies/{company_id}/contacts"),
    }
    assert retained <= routes


def test_global_platform_score_is_not_a_runtime_capability():
    assert not hasattr(ScoringEngineService, "score_clean_company")

    signature = inspect.signature(AdminCollectionService.list_wmt_clean_companies)
    source = inspect.getsource(AdminCollectionService.list_wmt_clean_companies)
    assert "system_grade" not in signature.parameters
    assert 'item["system_grade"]' not in source
    assert 'item["system_score"]' not in source


def test_retired_collection_tables_have_no_runtime_service_methods_or_sql():
    removed_config_methods = {
        "list_data_sources",
        "create_data_source",
        "get_data_source",
        "patch_data_source",
        "patch_data_source_config",
        "list_data_source_credentials",
        "create_data_source_credential",
        "patch_data_source_credential",
        "delete_data_source_credential",
        "_load_credential_row",
        "_serialize_data_source",
        "_serialize_credential",
        "_mask_secret",
    }
    removed_collection_methods = {
        "list_clean_companies",
        "list_v3_clean_companies",
        "get_cleanup_health",
        "_dedupe_tenants",
        "list_peer_companies",
        "get_peer_company_detail",
        "list_peer_company_contacts",
        "_peer_filter_parts",
        "_format_peer_row",
    }
    retired_tables = {
        "data_source_credentials",
        "data_sources",
        "peer_company_contacts",
        "peer_company_sources",
        "peer_company_keywords",
        "peer_companies",
        "clean_company_keywords",
        "clean_company_sources",
        "clean_contacts",
        "clean_companies",
        "tenant_keyword",
    }

    assert removed_config_methods.isdisjoint(dir(AdminConfigService))
    assert removed_collection_methods.isdisjoint(dir(AdminCollectionService))

    runtime_source = "\n".join(
        (
            inspect.getsource(AdminConfigService),
            inspect.getsource(AdminCollectionService),
        )
    )
    for table in retired_tables:
        assert re.search(rf"\b{re.escape(table)}\b", runtime_source) is None
