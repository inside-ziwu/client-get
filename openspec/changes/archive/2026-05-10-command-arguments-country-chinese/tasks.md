## 1. Admin 展示与筛选定位

- [x] 1.1 定位 admin 客户数据/干净公司库列表、详情中的国家展示位置。
- [x] 1.2 定位 admin 客户数据/干净公司库国家筛选控件、筛选参数和后端查询路径。
- [x] 1.3 核对现有 `country_iso3` 清洗、筛选、去重链路，确认本 change 不改变内部 ISO3 语义。

## 2. 国家中文化工具

- [x] 2.1 在前端共享模块新增小型国家映射 helper，优先放入 `frontend/packages/shared-types/src/countries.ts` 并从 `@shared/types` 导出。
- [x] 2.2 第一版以 ISO3 到中文名称为主，至少覆盖 `USA -> 美国`、`CHN -> 中国`、`DEU -> 德国`，并按现有前端国家 options 补齐必要项。
- [x] 2.3 中文输入原样展示；未知 ISO3 或未知字符串原样保留，禁止使用 fuzzy first-match 或别名猜测。
- [x] 2.4 不引入大型 i18n/国家库，不新增数据库国家表。

## 3. Admin 客户数据展示/筛选接入

- [x] 3.1 将国家中文化规则接入 admin 客户数据/干净公司库列表国家列。
- [x] 3.2 将国家中文化规则接入 admin 客户数据/干净公司库详情国家字段。
- [x] 3.3 将国家筛选控件改为中文 label、ISO3 value。
- [x] 3.4 修正 admin 现有国家筛选 options 中美国 value，确保 `美国` 的 value 是 `USA`，不是 `US`。
- [x] 3.5 确保所有国家筛选 option 的 label 为中文、value 为 ISO3。
- [x] 3.6 确保用户侧选择 `中国` 时后端筛选执行使用 `CHN`；选择 `美国` 时后端筛选执行使用 `USA`。
- [x] 3.7 将同一共享映射接入 tenant 客户数据列表、详情、精选客户等国家展示位置。
- [x] 3.8 将 tenant 国家筛选控件从自由输入 tags 改为共享国家 options 多选，中文 label、ISO3 value，并保持后端查询使用 ISO3。
- [x] 3.9 将 tenant 已选国家筛选摘要/chip 接入共享映射，确保已选 `USA` 时人类可读显示为 `国家: 美国`，但请求参数仍为 `USA`。
- [x] 3.10 确保 raw company、clean company、租户筛选、供应商调用等机器执行链路仍使用 `country_iso3` 或供应商要求的原始参数。

## 4. 数据 Update 边界

- [x] 4.1 明确记录本 change 不 update admin 客户数据/干净公司库国家字段。
- [x] 4.2 确保实施中不新增修改干净公司库国家值的 SQL、迁移脚本或生产数据脚本。
- [x] 4.3 确保前后端改动不要求新增国家中文字段或修改现有数据库 schema。

## 5. 验证

- [x] 5.1 添加国家中文化工具测试：`USA` → `美国`、`CHN` → `中国`、`DEU` → `德国`、`日本` → `日本`、未知值原样保留。
- [x] 5.2 添加 admin 客户数据展示测试，覆盖 `USA` 展示为 `美国`、未知 ISO3 保持可追溯显示。
- [x] 5.3 添加筛选边界测试：前端/人类可读值 `美国` 能筛选命中后端 `USA` 数据。
- [x] 5.4 添加 tenant 展示/筛选测试，覆盖 tenant 公司列表、公司详情、精选客户中 `USA` 展示为 `美国`，tenant 国家筛选选择 `美国` 时请求仍传 `USA`，已选筛选摘要/chip 显示 `国家: 美国`。
- [x] 5.5 添加或运行回归测试，证明 `country_iso3` 去重与筛选链路未被中文化改动影响。
- [x] 5.6 运行与改动匹配的 lint、单元测试或集成测试，并记录结果。

## 6. 线上国家样本补全

- [x] 6.1 只读查询线上 PostgreSQL `clientget` 库中客户/采集相关表的 distinct 国家值。
- [x] 6.2 按线上实际 ISO3 样本补全前端小型 `ISO3 -> 中文` 映射表。
- [x] 6.3 更新国家本地化测试，覆盖线上新增国家样本。
- [x] 6.4 重新运行国家本地化测试、shared-types type-check、admin/tenant build。

## 7. Tenant 线上公司列表国家列验收追踪

- [x] 7.1 确认线上 `clean_companies.country_iso3` 中 `COL` 为合法 ISO3 样本，期望展示为 `哥伦比亚`；`IDN` 期望展示为 `印度尼西亚`。
- [x] 7.2 确认本地 tenant 构建产物和 ACR 镜像 `clientget-tenant:2026.05.11-r4/r5` 已包含 `COL -> 哥伦比亚`、`IDN -> 印度尼西亚`。
- [x] 7.3 排查时曾确认 `tenant.xinanpcb.com` 加载旧资源 `index-CIj0DvYb.js` / `countries-Z90Ynl-Y.js`，该旧国家 chunk 只包含少量映射，缺少 `COL` 与 `IDN`。
- [x] 7.4 复验时确认 `tenant.xinanpcb.com` 已加载新资源 `index-BVCUbvej.js` / `countries-BkL6iqPT.js`，新国家 chunk 包含 `COL -> 哥伦比亚` 与 `IDN -> 印度尼西亚`；旧 chunk 仍可被直接访问，但最新 HTML 不再引用。
- [x] 7.5 结论：tenant 公司列表国家列仍显示 `COL/IDN` 的根因是浏览器或线上实例曾加载旧 tenant 静态资源，不是数据库值异常，也不是前端映射缺失；刷新到新资源后应显示中文。
