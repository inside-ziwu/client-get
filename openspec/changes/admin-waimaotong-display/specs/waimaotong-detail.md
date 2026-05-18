## WMT-DETAIL-01: 详情 Sheet SHALL 展示公司基本信息

**Given** 用户在列表页点击某条公司记录
**When** 详情 Sheet 打开
**Then** 展示基本信息区：公司名(company_name)、国家(country)、网站(website，可点击链接)、行业(industry)、电话(phone)、员工规模(employee_size)、成立年份(founded_year)、描述(description)、注册地址(full_address)、产品(products，tag 列表)

## WMT-DETAIL-02: 详情 Sheet SHALL 展示采集信息

**Given** 详情 Sheet 已打开
**Then** 展示采集信息区：采集关键词(source_keyword)、来源同行(source_competitor)、来源类型(source_type)、是否验证(id_verified)、API ID(api_company_id)

## WMT-DETAIL-03: 详情 Sheet SHALL 展示联系人列表

**Given** 详情 Sheet 已打开
**When** 加载关联联系人
**Then** 展示联系人表格，列：姓名(name)、职位(position)、部门(department)、邮箱(email)、邮箱状态(email_status)、电话(phone)、LinkedIn(linkedin)、来源(source)
**And** 不展示 mobile、whatsapp 字段

## WMT-DETAIL-04: 详情 Sheet 联系人为空时 SHALL 展示空状态

**Given** 某公司 has_contacts = false 或联系人数为 0
**When** 打开该公司详情
**Then** 联系人区域展示空状态提示
