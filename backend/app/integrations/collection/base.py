from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CollectionTask:
    id: str
    keyword: str
    source_types: list[str]
    params: dict | None = None
    task_type: str = "competitor_search"
    # Populated by worker for buyer_lookup tasks from task.context
    competitor_names: list[str] = field(default_factory=list)
    # async (competitors: list[dict]) -> None
    # Called once after all search pages complete, before enrichment starts.
    on_partial: Any = None
    # async (competitor: dict) -> None
    # Called immediately after each company's detail + contacts are fetched.
    on_company_enriched: Any = None


@dataclass(slots=True)
class CollectionPayload:
    """CollectionPayload 中每条 dict 必须包含 target_table 字段，供 Worker 路由到 raw 表。

    外贸通 -> waimaotong_raw_companies
    腾道 -> tendata_raw_companies
    励销云 -> lixiaoyun_raw_companies
    """

    companies: list[dict] = field(default_factory=list)
    contacts: list[dict] = field(default_factory=list)
    competitors: list[dict] = field(default_factory=list)
    cursor: dict | None = None
    skip_source_ids: list[str] = field(default_factory=list)


class CollectionProvider:
    source_type: str

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        raise NotImplementedError
