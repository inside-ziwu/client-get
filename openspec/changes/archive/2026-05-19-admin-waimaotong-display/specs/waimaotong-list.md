## WMT-LIST-01: Admin 端 SHALL 展示外贸通公司列表

**Given** 用户访问 Admin 端 `/collection/waimaotong`
**When** 页面加载
**Then** 展示分页列表，包含 11 列：公司名、国家、域名、行业、员工规模、成立日期、注册地址、采集关键词、来源同行、联系人数、入库时间
**And** 默认按入库时间倒序排列

## WMT-LIST-02: 列表 SHALL 支持 8 项筛选

**Given** 用户在列表页操作筛选区
**When** 用户设置以下筛选条件之一或多个：
- 公司名（文本搜索，ILIKE 模糊匹配）
- 国家（下拉选择）
- 采集关键词（下拉选择）
- 来源同行（文本搜索，ILIKE 模糊匹配）
- 成立日期（年份范围，min/max）
- 员工规模（区间选择：tiny/small/medium/large）
- 行业（文本搜索，ILIKE 模糊匹配）
- 有联系人？（布尔开关，has_contacts = true）
**Then** 列表实时刷新，仅展示符合条件的记录

## WMT-LIST-03: 列表 SHALL 支持分页

**Given** 列表数据超过单页容量
**When** 用户翻页
**Then** 按分页参数加载对应页数据，展示总数和当前页码
