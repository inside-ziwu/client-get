"""采集死子系统路由退役白名单。"""

import inspect

from app.main import create_app
from app.services.admin_collection_service import AdminCollectionService
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
