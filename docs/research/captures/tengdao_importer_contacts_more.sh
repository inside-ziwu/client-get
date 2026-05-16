curl 'https://bizr.tendata.cn/api/contactx/v2/contacts/more?tid=INDI6d2d38e51b0338f13b702e9613d9d44e&page=1&size=20&_t=1777535254060' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'referer: https://bizr.tendata.cn/enterprise' \
  -b 'JSESSIONID=<JSESSIONID>; token=<TOKEN_UUID>; userId=<USER_ID>'

# 注意事项：
# - 路径: /api/contactx/v2/contacts/more  ← v2，不是 v3
# - 参数: tid（公司唯一ID）, page（从1开始，不是0）, size, _t（时间戳，可省略）
# - 不需要 globizId / linkedInCompanyId，只需 tid
# - POSIFLOW tid = INDI6d2d38e51b0338f13b702e9613d9d44e（印度）
# - FILTERMATION tid = MYSN8fef573bbb52eb4519c1917faa18c1ea（马来西亚）

# 响应格式预期（与 linkedin/internet 端点类似）：
# {
#   "number": 0,
#   "size": 20,
#   "totalElements": N,
#   "content": [ { id, name, position, email, emailVerify, ... } ],
#   "atts": { "contactTotal": N }
# }
