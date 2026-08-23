from app.utils.industry import PCB_INDUSTRY_ALIASES, canonical_industry
from app.workers import wmt_lineage_repair


def test_canonical_industry_aliases():
    assert canonical_industry("PCB") == "PCB"
    assert canonical_industry(" pcb ") == "PCB"
    assert canonical_industry("电路板") == "PCB"
    assert canonical_industry("unknown") is None
    assert canonical_industry("") is None
    assert canonical_industry(None) is None


def test_lineage_repair_reuses_industry_aliases():
    assert wmt_lineage_repair._PCB_INDUSTRY_ALIASES == PCB_INDUSTRY_ALIASES
    assert all(alias == alias.lower() for alias in wmt_lineage_repair._PCB_INDUSTRY_ALIASES)
