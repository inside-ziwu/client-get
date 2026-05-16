from __future__ import annotations

import pycountry

_CHINESE_COUNTRY_ALIASES = {
    "中国": "CHN",
    "中华人民共和国": "CHN",
    "美国": "USA",
    "英国": "GBR",
    "德国": "DEU",
    "法国": "FRA",
    "意大利": "ITA",
    "西班牙": "ESP",
    "加拿大": "CAN",
    "澳大利亚": "AUS",
    "日本": "JPN",
    "韩国": "KOR",
    "印度": "IND",
    "马来西亚": "MYS",
    "新加坡": "SGP",
    "越南": "VNM",
    "泰国": "THA",
    "菲律宾": "PHL",
    "印度尼西亚": "IDN",
    "印尼": "IDN",
    "俄罗斯": "RUS",
    "巴西": "BRA",
    "墨西哥": "MEX",
    "土耳其": "TUR",
    "阿联酋": "ARE",
    "荷兰": "NLD",
}


def to_iso3(name_or_code: str) -> str | None:
    if name_or_code is None:
        return None

    value = name_or_code.strip()
    if not value:
        return None

    upper_value = value.upper()
    country = pycountry.countries.get(alpha_3=upper_value)
    if country is not None:
        return country.alpha_3

    country = pycountry.countries.get(alpha_2=upper_value)
    if country is not None:
        return country.alpha_3

    alias = _CHINESE_COUNTRY_ALIASES.get(value)
    if alias is not None:
        return alias

    try:
        return pycountry.countries.lookup(value).alpha_3
    except LookupError:
        pass

    try:
        matches = pycountry.countries.search_fuzzy(value)
    except LookupError:
        return None

    return matches[0].alpha_3 if matches else None
