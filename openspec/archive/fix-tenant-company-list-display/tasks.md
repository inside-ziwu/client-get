## 1. 复现与断点定位

- [x] 1.1 在 tenant 公司列表接口样例中确认联系人数量显示错误的具体字段路径
- [x] 1.2 在 tenant 公司详情联系人接口样例中确认联系人姓名、职位、邮箱、电话的错位或缺失路径
- [x] 1.3 记录问题属于后端返回缺字段、前端类型不匹配、前端渲染 fallback 错误，或多者叠加
- [x] 1.4 选取同一 `clean_company_id`，对照 admin 侧联系人事实与 tenant 侧 API/UI 展示

## 2. 后端契约修复

- [x] 2.1 为 `TenantQueryService.companies` 增加 `contacts_count` 返回断言测试
- [x] 2.2 为 `TenantQueryService.v3_company_detail` 增加 `contacts_count` 返回断言测试
- [x] 2.3 为 `TenantQueryService.v3_company_contacts` 增加联系人 `name`、`position`、`email`、`phone` 返回断言测试
- [x] 2.4 如测试暴露缺口，修正 tenant 查询 SQL 和响应 mapping，确保读取当前 `clean_companies` / `clean_contacts` 字段
- [x] 2.5 确认 `contacts_count = 0` 保持数字 0 返回，不被转换成 null 或省略

## 3. 前端展示修复

- [x] 3.1 对齐 shared tenant company/contact 类型，补齐 `contacts_count`、联系人 `position`、`phone` 字段
- [x] 3.2 修正 tenant 公司列表联系人列使用 nullish 判断，确保 `0` 显示为 `0`
- [x] 3.3 修正公司详情 Drawer 联系人数量展示，保持与列表一致
- [x] 3.4 修正联系人明细表和 `normalizeContact`，优先使用当前 V3 字段 `name`、`position`、`email`、`phone`
- [x] 3.5 联系人明细表展示电话列，字段为空时显示占位，不影响姓名/职位/邮箱展示

## 4. 验证与收尾

- [x] 4.1 为腾道 collection raw 入库补 RED 测试：顶层 `contacts` 必须保留到 `tendata_raw_companies.raw_payload.contacts`
- [x] 4.2 为 cleanup 补 RED 测试：raw contacts 清洗后必须生成 `clean_contacts`，并让 tenant 联系人接口返回姓名、职位、邮箱、电话
- [x] 4.3 运行匹配的后端单测，覆盖 tenant 公司列表、详情与联系人明细
- [x] 4.4 运行 tenant 前端 typecheck 或 build，确认类型与渲染无回归
- [x] 4.5 如本地数据可用，手工验证同一 `clean_company_id` 在 admin 有联系人时，tenant 公司列表、详情和联系人明细正确展示联系人数量、姓名、职位、邮箱、电话
- [x] 4.6 更新本 change 的任务勾选状态：已用 `clean_company_id=534` 服务层样本验证列表 `contacts_count=1`、详情 `contacts_count=1`、联系人明细 `Jane Buyer / Purchasing Manager / jane@example.com / +1-555` 正常返回；本地未启动完整浏览器登录态。
