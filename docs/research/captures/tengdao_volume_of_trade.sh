curl 'https://bizr.tendata.cn/api/bizr/v1/user/trade/company/report/0/volume_of_trade' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'content-type: application/json' \
  -b '<SAME_COOKIES_AS_DETAIL>; JSESSIONID=<JSESSIONID>' \
  -H 'referer: https://bizr.tendata.cn/enterprise' \
  --data-raw '{
    "catalog": "all",
    "country": "all",
    "startDate": "2023-05-01",
    "endDate": "2026-04-30",
    "productNames": [],
    "productTags": [],
    "importers": [],
    "exporters": [],
    "filterRepetitive": true,
    "tradeCountries": [],
    "hsCodes": [],
    "companyType": "IMPORTER",
    "keyword": "FILTERMATION MFG SDN BHD",
    "aliases": ["FILTERMATION MFG SDN BHD", "FILTERMATION MFG SDN. BHD", "...all aliases from BRIEF..."],
    "size": 50,
    "reportType": "volume_of_trade"
  }'

# 注意：aliases 数组来自 BRIEF 响应的 aliases[] 字段（全部 checked=true 的条目）
