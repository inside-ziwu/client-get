## Why

`v3-tendata-cleaning-pipeline` 已将 `tenant_companies.business_status` 重新定义为长期运营阶段，并通过数据库约束移除了 `pending_score` / `scored` / `selected` / `excluded` 等旧评分或交互状态。但后端评分、租户手工建公司、prospect 选中/排除、dashboard 漏斗和前端类型仍有旧语义残留，清洗后的租户公司进入运营动作时可能触发数据库约束错误或展示口径错位。

需要用一个小 change 收口 `business_status` 的语义迁移，让租户公司状态、评分结果、分组、发信和列表展示重新对齐。

## What Changes

- 明确 `business_status` 只表达租户公司长期运营阶段；本 change 的活跃运营阶段收口为 `new` / `in_group` / `in_plan` / `contacted`。
- 移除后端写入 `pending_score` / `scored` / `selected` / `excluded` 到 `tenant_companies.business_status` 的路径。
- 评分流程只写评分字段、评分记录或评分任务状态，不再用 `business_status` 表达“待评分/已评分”。
- 租户手工创建公司使用 V3 bigint `tenant_companies.id`、新 `business_status` 与新 `data_status` 枚举。
- 移除或停用旧 prospect select/exclude 交互入口；不得把 `selected` / `excluded` 映射成新的业务阶段。
- 加入运营分组时必须将租户公司阶段推进为 `in_group`。
- 从运营分组移除时按剩余成员关系收口 `in_group`：仍在其他分组则保持，离开最后一个分组且当前仍为 `in_group` 则回退 `new`，已进入 `in_plan` / `contacted` 则不回退。
- 仅当服务商确认邮件 `delivered` 后，才将对应 `in_plan` 租户公司推进为 `contacted`；`sent` 只表示已发出，不推进公司级触达阶段。
- tenant dashboard overview、dashboard funnel、companies filters、共享类型与前端状态文案按新状态语义更新；租户端展示统计口径只包含 `visibility_status = visible` 公司。
- 彻底移除 `tenant_companies.business_status = archived`：清理历史值、收紧数据库约束、移除前后端合法枚举。
- 保持腾道 raw → clean 清洗主链路不变；本 change 不改腾道采集、清洗规则或 `clean_company_keywords` 物化规则。

## Capabilities

### New Capabilities
- `tenant-company-status-semantics`: 约束租户公司 `business_status`、评分状态、手工创建与前端展示之间的语义边界。

### Modified Capabilities
- 无。

## Impact

- 后端：
  - `backend/app/services/scoring_service.py`
  - `backend/app/services/tenant_ops_service.py`
  - `backend/app/api/tenant/ops.py`
  - 可能涉及 `backend/app/services/tenant_query_service.py`、`backend/app/services/tenant_messaging_service.py`
- 前端：
  - `frontend/packages/shared-types/src/enums.ts`
  - `frontend/apps/tenant/src/pages/Dashboard/index.tsx`
  - `frontend/apps/tenant/src/pages/Companies/index.tsx`
  - 其他读取或传递 `business_status` 的租户端页面/API 类型
- 测试：
  - 后端租户公司、评分、分组、发信、dashboard/filter contract 测试
  - 前端类型检查或 tenant 构建
- 数据库：
  - 新增迁移，将历史 `business_status = archived` 回填为 `new`，并将 check constraint 收紧为 `new` / `in_group` / `in_plan` / `contacted`。
