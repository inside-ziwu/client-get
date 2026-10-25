"""采集来源口径的单一真源。"""

from collections.abc import Iterable
from typing import Literal

KEYWORD_COLLECTION_TAG = "外贸通关键词采集"
KEYWORD_TAG_JSONB = """'["外贸通关键词采集"]'::jsonb"""
TENGDAO_COLLECTION_TAG = "腾道"
TENGDAO_TAG_JSONB = """'["腾道"]'::jsonb"""
INSTANTLY_COLLECTION_TAG = "Instantly"
INSTANTLY_TAG_JSONB = """'["Instantly"]'::jsonb"""

CollectionType = Literal["manual", "keyword", "reverse", "unknown"]
CollectionTypeTag = Literal["manual", "keyword", "reverse", "instantly"]


def compute_collection_type(
    data_source_tags: Iterable[str] | None,
    *,
    source_id: str | None = None,
    has_source_competitor: bool = False,
) -> CollectionType:
    """按 manual > keyword > reverse 的正向证据判定采集类型。"""
    tags = set(data_source_tags or [])
    if source_id and source_id.startswith("manual-"):
        return "manual"
    if KEYWORD_COLLECTION_TAG in tags:
        return "keyword"
    if TENGDAO_COLLECTION_TAG in tags or has_source_competitor:
        return "reverse"
    return "unknown"


def compute_collection_types(
    data_source_tags: Iterable[str] | None,
    *,
    source_id: str | None = None,
    has_source_competitor: bool = False,
) -> list[CollectionTypeTag]:
    """列表展示用的全部采集类型；Instantly 独立于优先级叠加，有 Instantly 时不显示 unknown。"""
    tags = set(data_source_tags or [])
    primary = compute_collection_type(
        tags,
        source_id=source_id,
        has_source_competitor=has_source_competitor,
    )
    types: list[CollectionTypeTag] = [] if primary == "unknown" else [primary]
    if INSTANTLY_COLLECTION_TAG in tags:
        types.append("instantly")
    return types


def build_collection_type_filter(
    collection_type: str | None,
    *,
    company_alias: str = "wc",
) -> str | None:
    """生成与 ``compute_collection_types`` 同口径的 PostgreSQL 过滤条件。"""
    source_id = f"{company_alias}.source_id"
    tags = f"COALESCE({company_alias}.data_source_tags, '[]'::jsonb)"
    manual = f"COALESCE({source_id}, '') LIKE 'manual-%'"
    keyword = f"{tags} @> {KEYWORD_TAG_JSONB}"
    # data_source_tags 的 GIN 索引是 jsonb_path_ops，只能命中 @>，不能用 ? 运算符
    instantly = f"{tags} @> {INSTANTLY_TAG_JSONB}"
    source_competitor = f"""EXISTS (
        SELECT 1
        FROM waimaotong_raw_companies wr_collection_source
        WHERE wr_collection_source.sys_company_id = {company_alias}.sys_company_id
          AND NULLIF(BTRIM(wr_collection_source.source_competitor), '') IS NOT NULL
    )"""
    reverse_evidence = f"({tags} @> {TENGDAO_TAG_JSONB} OR {source_competitor})"

    if collection_type == "manual":
        return manual
    if collection_type == "keyword":
        return f"NOT ({manual}) AND {keyword}"
    if collection_type == "instantly":
        return instantly
    if collection_type == "reverse":
        return f"NOT ({manual}) AND NOT ({keyword}) AND {reverse_evidence}"
    if collection_type == "unknown":
        return (
            f"NOT ({manual}) AND NOT ({keyword}) AND NOT {reverse_evidence} "
            f"AND NOT ({instantly})"
        )
    return None
