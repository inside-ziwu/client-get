"""生成国家假日种子数据。

用法：
  PYTHONPATH=/tmp/clientget-holidays-deps:. python scripts/generate_country_holidays.py 2026

脚本只在本地维护种子数据时运行；迁移只读取生成后的静态 JSON。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pycountry

try:
    import holidays
except ImportError as exc:  # pragma: no cover - 本地维护脚本的友好提示
    raise SystemExit("请先安装本地生成依赖：python -m pip install holidays") from exc


ROOT = Path(__file__).resolve().parents[1]
COUNTRIES_PATH = ROOT / "app" / "data" / "countries.json"
HOLIDAY_NAME_ZH_MAP_PATH = ROOT / "app" / "data" / "holiday_name_zh_map.json"


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    countries = json.loads(COUNTRIES_PATH.read_text(encoding="utf-8"))
    holiday_name_zh_map = json.loads(HOLIDAY_NAME_ZH_MAP_PATH.read_text(encoding="utf-8"))
    supported = holidays.list_supported_countries()
    rows: list[dict] = []

    for country in countries:
        alpha2 = _alpha2(country["iso3"])
        if not alpha2 or alpha2 not in supported:
            continue

        country_holidays = holidays.country_holidays(alpha2, years=[year], language="en_US")
        for day, name in sorted(country_holidays.items()):
            english_name = str(name)
            rows.append(
                {
                    "country_iso3": country["iso3"],
                    "date": day.isoformat(),
                    "name": holiday_name_zh_map.get(english_name, english_name),
                    "source": "seed",
                }
            )

    rows.sort(key=lambda item: (item["country_iso3"], item["date"], item["name"]))
    output_path = ROOT / "app" / "data" / f"country_holidays_{year}.json"
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    countries_with_holidays = len({item["country_iso3"] for item in rows})
    print(f"generated {len(rows)} holidays for {countries_with_holidays} countries -> {output_path}")


def _alpha2(iso3: str) -> str | None:
    if iso3 == "XKX":
        return "XK"
    country = pycountry.countries.get(alpha_3=iso3)
    return country.alpha_2 if country else None


if __name__ == "__main__":
    main()
