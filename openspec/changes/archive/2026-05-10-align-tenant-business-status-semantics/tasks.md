## 1. 后端回归用例

- [x] 1.1 增加或更新评分测试，覆盖 visible 租户公司评分完成后不写 `business_status = scored`，且评分摘要字段仍更新。
- [x] 1.2 增加或更新 LLM pending 评分测试，覆盖 pending 状态保存在评分记录或任务中，不写 `business_status = pending_score` / `scoring`。
- [x] 1.3 增加或更新租户手工创建公司测试，覆盖 bigint tenant company identity、`business_status = new`、合法 `data_status` 与 `visibility_status = visible`。
- [x] 1.4 增加或更新 prospect select/exclude 测试，覆盖旧入口被移除或停用，且不会写入 `selected` / `excluded`。
- [x] 1.5 增加非法 `business_status` 更新测试，断言服务层返回 validation error，而不是依赖数据库约束失败。
- [x] 1.6 增加 dashboard/filter contract 测试，覆盖漏斗只返回 `new` / `in_group` / `in_plan` / `contacted`，且 dashboard overview、dashboard funnel、companies filters 只统计或派生 `visibility_status = visible` 公司。
- [x] 1.7 增加分组测试，覆盖 visible 租户公司加入分组后 `business_status = in_group`；从非最后一个分组移除保持 `in_group`；从最后一个分组移除且当前为 `in_group` 时回退 `new`；当前为 `in_plan` / `contacted` 时不回退。
- [x] 1.8 增加 migration/schema 测试，覆盖 `archived` 历史值回填为 `new`，且数据库约束不再接受 `archived`。
- [x] 1.9 增加发信阶段测试，覆盖 `mark_email_sent(sent)` 不推进公司 `business_status`，且 `WebhookService.process_engagelab_event(delivered)` 将对应 `in_plan` 租户公司推进为 `contacted`。

## 2. 数据库与后端状态语义收口

- [x] 2.1 新增 Alembic migration：将历史 `tenant_companies.business_status = 'archived'` 回填为 `new`。
- [x] 2.2 在同一 migration 中收紧 `tenant_companies_business_status_check`，只允许 `new` / `in_group` / `in_plan` / `contacted`。
- [x] 2.3 修改 `backend/app/services/scoring_service.py`，评分完成或 pending 时不再更新 `tenant_companies.business_status` 为旧评分状态。
- [x] 2.4 核对评分摘要字段更新路径，保留 `grade` / `total_score` / `model_score` / `score` 等现有评分表达。
- [x] 2.5 修改 `backend/app/services/tenant_ops_service.py` 的手工创建公司路径，使用当前 V3 schema：不写 UUID 到 bigint id，写 `business_status = new`、合法 `data_status`、`visibility_status = visible`。
- [x] 2.6 移除或停用旧 `/prospects/{id}/select` 与 `/prospects/{id}/exclude` 入口；不得映射到其他业务阶段。
- [x] 2.7 为更新公司状态与列表筛选的服务层增加允许值校验：只接受 `new` / `in_group` / `in_plan` / `contacted`。
- [x] 2.8 修改 `dashboard_overview`、`dashboard_funnel` 与 `companies_filters`，按新业务阶段统计并只使用 `visibility_status = visible` 公司作为租户端展示口径。
- [x] 2.9 修改分组流程：visible 租户公司加入分组后必须写 `business_status = in_group`；从非最后一个分组移除保持 `in_group`；从最后一个分组移除且当前为 `in_group` 时回退 `new`；当前为 `in_plan` / `contacted` 时不回退。
- [x] 2.10 修改发信回调流程：`sent` 只更新邮件或联系人发送状态，不推进公司级 `business_status`；服务商 webhook 确认 `delivered` 后，才将对应 `in_plan` 且 `visibility_status = visible` 的租户公司推进为 `contacted`。
- [x] 2.11 对齐发送链路 V3 bigint 关联列：`emails.tenant_contact_id`、`sending_plan_recipients.tenant_company_id`、`sending_plan_recipients.tenant_contact_id`、`sequence_enrollments.tenant_contact_id` 不再保留旧 UUID tenant company/contact 引用。

## 3. 前端与共享类型

- [x] 3.1 修改 `frontend/packages/shared-types/src/enums.ts` 中 `TenantCompanyStatus` 为新业务阶段枚举。
- [x] 3.2 修改 tenant dashboard 漏斗文案和阶段集合，移除旧评分/选中状态阶段。
- [x] 3.3 删除 `frontend/packages/shared-api/src/tenant/prospects.ts` 中旧 `select` / `exclude` client 方法。
- [x] 3.4 移除 tenant 端调用 prospect select/exclude 的 UI 与 mutation；保留黑名单等已有明确动作。
- [x] 3.5 核对 tenant 公司列表、详情、编辑表单和筛选项，确保只提交或展示当前合法 `business_status`。
- [x] 3.6 保留“已评分公司”等评分指标，但其来源不得依赖 `business_status = scored`。

## 4. 验证

- [x] 4.1 运行后端目标测试，至少覆盖 migration/schema、评分、租户公司创建、prospect 状态、dashboard/filter、分组、hidden 公司入口。
- [x] 4.2 运行与租户端相关的前端类型检查或构建。
- [x] 4.3 用 `rg` 核对后端生产代码不再写 `pending_score` / `scoring` / `scored` / `selected` / `excluded` / `replied` / `converted` / `archived` 到 `tenant_companies.business_status`。
- [x] 4.4 用 `rg` 核对前端共享类型和 tenant 页面不再把旧状态或 `archived` 当作合法 tenant company business status。
- [x] 4.5 记录仍未覆盖的旧测试夹具或历史文案，并明确它们是否属于当前 change 范围：旧 `business_status` 值仍可能出现在历史 Alembic migration / downgrade、邮件状态、租户状态、情报状态或前端局部变量名中；这些不是当前运行时代码向 `tenant_companies.business_status` 写旧枚举，当前 change 不改写历史迁移或非 tenant company 状态语义。
