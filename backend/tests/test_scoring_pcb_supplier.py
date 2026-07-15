"""has_china_pcb_supplier 评分条件:按采集类型判定(openspec change score-pcb-supplier-by-collection-type)"""

from app.services.scoring_engine_service import evaluate_company

# 与生产模板一致的维度定义:精准反推(有中国 PCB 供应商)20 分,否则 default 10 分
PCB_SUPPLIER_DIMENSION = [
    {
        "key": "pcb_supplier",
        "name": "PCB 供应商",
        "conditions": [
            {"label": "A — 有中国 PCB 供应商", "score": 20, "condition": "has_china_pcb_supplier"},
            {"label": "B — 无中国 PCB 供应商", "score": 10, "condition": "default"},
        ],
    }
]
THRESHOLDS = {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0}


def _score(company_data: dict) -> int:
    result = evaluate_company(PCB_SUPPLIER_DIMENSION, THRESHOLDS, company_data)
    return result["total_score"]


class TestHasChinaPcbSupplier:
    def test_reverse_collection_scores_20(self):
        """腾道标签或反推公司证据 = 精准反推，得 20 分。"""
        assert _score({"data_source_tags": ["腾道"]}) == 20
        assert _score({"data_source_tags": [], "has_source_competitor": True}) == 20

    def test_keyword_collection_scores_default_10(self):
        """含「外贸通关键词采集」标签 = 关键词采集 = 无中国 PCB 供应商,落 default 10 分"""
        assert _score({"data_source_tags": ["外贸通关键词采集"]}) == 10

    def test_unknown_and_manual_do_not_score_as_reverse(self):
        """无正向证据和手工录入均不得视为有中国 PCB 供应商。"""
        assert _score({"data_source_tags": None}) == 10
        assert _score({}) == 10
        assert _score({"source_id": "manual-123", "data_source_tags": ["腾道"]}) == 10

    def test_string_encoded_jsonb_is_parsed(self):
        """jsonb 以字符串形态返回时应先解析再判定"""
        assert _score({"data_source_tags": '["外贸通关键词采集"]'}) == 10
        assert _score({"data_source_tags": '["腾道"]'}) == 20
