curl 'https://bizr.tendata.cn/api/contactx/v3/contacts/internet?userId=79446&companyName=POSIFLOW+RETAIL+PRIVATE+LIMITED&website=posiflow.in&country=IND&taxNo=AAOCP1889K&size=20&tid=INDI6d2d38e51b0338f13b702e9613d9d44e' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'referer: https://bizr.tendata.cn/enterprise' \
  -b '<SAME_COOKIES>; JSESSIONID=<JSESSIONID>; token=<TOKEN_UUID>; userId=<USER_ID>'

# 参数说明：
# - userId:       登录用户 ID（固定）
# - companyName:  买家英文名（URL encoded）
# - website:      来自 BRIEF.website 或 T3.websites[0]
# - country:      3位国家码
# - taxNo:        来自 BRIEF.taxNo（可为空）
# - size:         每页条数
# - tid:          来自 BRIEF.tid

# 注意：此端点爬取企业官网上的邮件地址，返回的 name 字段是域名而非真实姓名
# content[].uniqueKey 用于去重（与 linkedin 端点一致）
