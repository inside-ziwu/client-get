"""租户评分查询携带采集类型正向证据。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.scoring_engine_service import ScoringEngineService


def _mapping_result(row):
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    return result


@pytest.mark.asyncio
async def test_tenant_score_reads_source_id_and_reverse_evidence():
    template = {
        "id": "11111111-1111-1111-1111-111111111111",
        "dimensions": [
            {
                "key": "pcb_supplier",
                "conditions": [
                    {"score": 20, "condition": "has_china_pcb_supplier"},
                    {"score": 10, "condition": "default"},
                ],
            }
        ],
        "grade_thresholds": {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0},
        "version": 1,
    }
    company = {
        "employee_size": None,
        "trade_amount_3y_usd": None,
        "trade_count": None,
        "contacts_count": 0,
        "data_source_tags": [],
        "source_tags": [],
        "source_id": "wmt-1",
        "has_source_competitor": True,
        "company_type_analysis": None,
        "industry": None,
    }
    conn = AsyncMock()
    conn.execute.side_effect = [
        _mapping_result(template),
        _mapping_result({"id": "22222222-2222-2222-2222-222222222222"}),
        _mapping_result(company),
        MagicMock(),
    ]

    result = await ScoringEngineService().score_tenant_company(
        conn,
        tenant_id="33333333-3333-3333-3333-333333333333",
        tenant_company_id=1,
    )

    company_sql = str(conn.execute.call_args_list[2].args[0])
    assert "wc.source_id" in company_sql
    assert "EXISTS" in company_sql
    assert "waimaotong_raw_companies" in company_sql
    assert "source_competitor" in company_sql
    assert result["total_score"] == 20
