"""行业别名归一。

租户 ``tenants.industry`` 存原值（varchar(100)），动态源存规范值（如 PCB）。
"""

from __future__ import annotations

INDUSTRY_ALIASES: dict[str, str] = {
    "pcb": "PCB",
    "电路板": "PCB",
}

PCB_INDUSTRY_ALIASES: list[str] = [key for key, value in INDUSTRY_ALIASES.items() if value == "PCB"]


def canonical_industry(value: str | None) -> str | None:
    """把租户行业原值归一为规范值；无法识别则返回 None。"""
    if value is None:
        return None
    key = value.strip().lower()
    if not key:
        return None
    return INDUSTRY_ALIASES.get(key)
