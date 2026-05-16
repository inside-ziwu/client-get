## Why

租户端新建公司保存时报错，会阻断运营人员手工补充客户数据。调研已复现两个具体失败点：新建表单提示用户输入 `DE / US / JP` 这类 ISO2 国家码，但后端直接写入要求 ISO3 的 `clean_companies.country_iso3`；填写联系人邮箱时，后端把 bigint tenant company id 转成字符串后传入联系人补写查询，asyncpg 拒绝字符串参数。

## What Changes

- 修复租户端新建公司保存失败的问题，确保有效的手工公司资料可以成功创建或关联 clean company，并创建当前租户可见的 tenant company。
- 将新建公司国家输入收口到 ISO3：前端优先使用已有中文国家选择器并提交 ISO3 value，后端对国家值做最小规范化/校验，避免 ISO2 或英文长名直接撞数据库约束。
- 修复联系人补写链路中的 tenant company bigint id 类型不匹配，确保填写联系人邮箱时也能保存成功。
- 保留现有重复创建幂等行为：同一租户重复创建同一可见公司时返回已有 tenant company，不暴露唯一约束错误。
- 对保存失败场景给出明确的校验错误或业务错误，不把可预期输入问题暴露为 500 / 数据库约束异常。
- 增加覆盖国家 ISO2/ISO3 输入、联系人邮箱、重复创建和错误反馈的验证。

## Capabilities

### New Capabilities

- 无

### Modified Capabilities

- `tenant-company-status-semantics`: 补充并验证租户手动新建公司必须使用当前 V3 tenant company schema、ISO3 国家键、当前状态语义与清晰错误反馈完成保存。

## Impact

- **前端**：涉及 `frontend/apps/tenant/src/pages/Companies/index.tsx` 的新建公司国家控件、payload 映射和错误展示；可复用 `@shared/types` 的 `countryOptionsZh()` / `displayCountryName()`。
- **后端**：涉及 `backend/app/services/tenant_ops_service.py` 的国家值规范化、`clean_companies` 写入、联系人补写 id 类型处理和异常边界；如需要再收紧 `backend/app/api/tenant/ops.py` 请求 schema。
- **测试**：补充后端 API/service 测试与前端表单提交/错误展示测试；必要时增加手工验收记录。
- **数据与部署**：原则上不新增迁移；若排查确认是字段类型、约束或索引缺失导致，需在 design 中记录迁移与回滚要求。
