## Why

线上排查确认腾道联系人主数据源是 `tendata_raw_contacts`，不是 `tendata_raw_companies.raw_payload.contacts`。当前 tenant 联系人展示只读取 `clean_contacts`，导致线上大量 `contacts_count > 0` 的可见公司在 tenant 详情中没有联系人明细。

## What Changes

- 修正 cleanup 链路：处理 `tendata_raw_companies` 时，除 `raw_payload.contacts` 外，还必须读取同 raw company 的 `tendata_raw_contacts` 并写入 `clean_contacts`。
- 增加一次性 backfill 能力：把已存在的 `tendata_raw_contacts` 经 `clean_company_sources(source_type='tendata')` 回填到 `clean_contacts`。
- 保持幂等：以 `clean_company_id + email` 去重更新联系人姓名、职位、电话，不重复插入。
- 保持 scope 单一：不改前端、不改 schema、不伪造没有 email 的联系人、不重新采集腾道数据。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `tenant-company-v3-contract`: tenant 联系人展示事实源补充 `tendata_raw_contacts → clean_contacts` 的清洗与历史回填要求。

## Impact

- **后端**：`backend/app/services/cleanup_service.py`，新增或扩展 backfill 脚本/服务，以及对应测试。
- **数据**：生产库历史 `tendata_raw_contacts` 可回填到 `clean_contacts`；不修改 schema。
- **验证**：覆盖 cleanup 新数据路径、backfill 历史路径、幂等重复运行、tenant 联系人 API 可见性。
- **不涉及**：前端展示、admin raw 页面、腾道重新采集、联系人分类规则、发送状态规则。
