## 1. Schema 与现状核对

- [x] 1.1 核对 `clean_companies` 当前唯一约束是否支持 `normalized_name + country_iso3` 去重主规则。
- [x] 1.2 核对 `tendata_raw_companies.keyword_master_id` 在现有数据中的可用性，并记录缺失数据的处理方式。
- [x] 1.3 为 `tenant_companies` 添加 `visibility_status` 字段，取值 `visible` / `hidden`，并补充适合租户列表查询的索引。
- [x] 1.4 历史 `tenant_companies.visibility_status` 按 active tenant 关键词覆盖回填，不能默认全量 visible。
- [x] 1.5 确认 `tenant_companies(tenant_id, clean_company_id)` 唯一约束存在，作为物化 upsert 幂等基础。
- [x] 1.6 调整 `tenant_companies.business_status` 约束，移除 `selected`，新增 `in_group`，保留 `new` / `in_plan` / `contacted` / `archived`。
- [x] 1.7 将历史 `business_status = selected` 回填为 `new`；如存在有效 `group_members`，再由分组关系重算为 `in_group`。
- [x] 1.8 实现或集中封装 `data_status` 系统判断规则：`missing_contacts` / `insufficient_data` / `ready`。
- [x] 1.9 统计 `company_scores`、`group_members`、`scoring_jobs` 的现有数据量与可映射比例，明确保留、归档或删除策略。
- [x] 1.10 将 `company_scores.tenant_company_id`、`group_members.tenant_company_id`、`scoring_jobs.tenant_company_id` 对齐为 `bigint` 并补外键到 `tenant_companies(id)`；不能做 uuid 到 bigint 强制转换。
- [x] 1.11 核对并对齐 `group_members.tenant_contact_id` 与 `tenant_contacts.id` 的类型和外键。
- [x] 1.12 核对 `clean_company_sources` 与 `clean_company_keywords` 的唯一约束和索引是否满足幂等 upsert，并确认 `clean_company_keywords` 保留为平台命中关系。

## 2. 平台实体清洗

- [x] 2.1 实现腾道 raw 入库门槛：缺公司名或缺 `country_iso3` 时不写入 `clean_companies`，并保留可排查状态。
- [x] 2.2 实现 `normalized_name + country_iso3` 的 clean 公司 upsert 路径。
- [x] 2.3 实现全局非空补空合并规则。
- [x] 2.4 实现数值摘要字段 `trade_amount_3y_usd` / `trade_count` / `contacts_count` 按 raw `created_at` 保留最新来源摘要。
- [x] 2.5 实现描述摘要字段 `industry_desc` / `employee_num` 按 raw `created_at` 保留最新来源摘要。
- [x] 2.6 实现证据集合字段 `product_tags` / `pcb_suppliers` / `aliases` 追加去重。
- [x] 2.7 实现 `clean_company_sources` 腾道来源证据 upsert。

## 3. 平台关键词继承

- [x] 3.1 清洗成功后，将 `tendata_raw_companies.keyword_master_id` 继承到干净公司与平台关键词关联。
- [x] 3.2 确保同一干净公司被多个平台关键词发现时追加关联，不覆盖旧关联。
- [x] 3.3 为缺失 `keyword_master_id` 的腾道 raw 记录清晰的不可分发/待排查状态。
- [x] 3.4 缺失 `keyword_master_id` 的腾道 raw 可以补充 clean 公司资料和来源证据，但不得新增 `clean_company_keywords`，不得单独触发租户物化。

## 4. 租户可见性物化

- [x] 4.1 实现 clean 公司关联平台关键词后，查找所有 active `tenant_keyword` 并 upsert `tenant_companies` 可见状态。
- [x] 4.2 实现租户新增关键词时，将该平台关键词已有 clean 公司补齐到该租户 `tenant_companies`。
- [x] 4.3 更新租户公司列表查询，以 `tenant_companies.visibility_status = visible` 决定基础展示，不再直接依赖 `clean_company_keywords + tenant_keyword` 动态 join。
- [x] 4.4 更新租户公司详情入口，以物化可见状态作为租户访问门槛。
- [x] 4.5 更新评分、分组、发信等继续运营入口，以 `tenant_companies.visibility_status = visible` 作为访问/操作门槛。
- [x] 4.6 确保 `data_status` 不影响基础显示，只用于数据可运营性提示、筛选或排序。
- [x] 4.7 确保未评分公司仍可展示，评分字段允许为空。

## 5. 取消订阅与覆盖重算

- [x] 5.1 实现 tenant 关键词取消订阅后的受影响 clean 公司集合计算。
- [x] 5.2 对每个受影响 clean 公司，检查该租户是否仍有其他 active tenant 关键词覆盖。
- [x] 5.3 仅在无其他 active 关键词覆盖时，将对应 `tenant_companies.visibility_status` 更新为 `hidden`。
- [x] 5.4 取消最后一个覆盖关键词导致隐藏时，清空该租户公司主表私有运营状态：`model_score`、`score`、`note` 置空，`tags` 清空，`business_status` 重置为 `new`。
- [x] 5.5 隐藏时删除该租户公司对应的 `group_members`，删除或取消 pending/leased 类 `scoring_jobs`，删除或归档 `company_scores`。
- [x] 5.6 重新订阅或重新物化为 visible 时，重新计算 `data_status`。
- [x] 5.7 覆盖多关键词场景的单元测试或集成测试。

## 6. 验证与验收

- [x] 6.1 测试缺国家腾道 raw 不进入 clean 公司。
- [x] 6.2 测试缺公司名腾道 raw 不进入 clean 公司。
- [x] 6.3 测试相同 normalized name + country 合并为一条 clean 公司。
- [x] 6.4 测试普通字段非空补空。
- [x] 6.5 测试最新来源摘要字段按 raw `created_at` 覆盖旧摘要，重跑顺序不影响结果。
- [x] 6.6 测试集合字段追加去重。
- [x] 6.7 测试 clean 公司继承多个平台关键词关联。
- [x] 6.8 测试缺 `keyword_master_id` 的 raw 不新增 `clean_company_keywords`，不单独触发租户物化。
- [x] 6.9 测试励销云 stage 1 触发来源的腾道 raw，最终按平台关键词清洗、继承并物化给订阅租户。
- [x] 6.10 测试历史 `tenant_companies.visibility_status` 按 active 覆盖回填，不默认全量 visible。
- [x] 6.11 测试已订阅租户自动看到新 clean 公司。
- [x] 6.12 测试新订阅租户能看到历史 clean 公司。
- [x] 6.13 测试取消单个关键词但仍有其他关键词覆盖时公司保持可见。
- [x] 6.14 测试取消最后一个覆盖关键词时公司不再在租户列表显示。
- [x] 6.15 测试取消最后一个覆盖关键词时，`tenant_companies.visibility_status = hidden`，且租户列表不会因为平台关键词关系仍存在而继续显示该公司。
- [x] 6.16 测试取消最后一个覆盖关键词时，该租户公司主表私有运营状态被清空，分组、评分任务、评分记录被清理或失效，但平台干净公司与来源证据不被删除。
- [x] 6.17 测试 hidden 公司不能通过详情、评分、分组、发信入口继续运营。
- [x] 6.18 测试取消单个关键词但仍有其他关键词覆盖时，该租户对该公司的私有运营状态保留。
- [x] 6.19 测试 `business_status` 不再接受 `selected`，并接受 `in_group`；历史 `selected` 迁移为 `new` 或由有效分组重算为 `in_group`。
- [x] 6.20 测试 `data_status` 系统判断规则，并测试重新物化 visible 后会重算。
- [x] 6.21 测试 `company_scores`、`group_members`、`scoring_jobs` 可通过 `bigint tenant_company_id` 正确关联 `tenant_companies`。
- [x] 6.22 测试 `group_members.tenant_contact_id` 可通过 `bigint tenant_contact_id` 正确关联 `tenant_contacts`。
- [x] 6.23 运行匹配的后端测试，并记录未覆盖或阻塞原因。

  2026-05-10 验证记录：
  - `cd backend && .venv/bin/python -m pytest tests/test_tendata_cleaning_pipeline.py`：7 passed。
  - 早前匹配回归：`tests/test_tendata_cleaning_pipeline.py tests/test_phase1_e2e.py::test_cleanup_service_batch tests/test_v3_data_foundation_schema.py tests/test_v3_data_foundation_api_contract.py tests/test_fan_out_worker.py tests/test_collection_pushback_slice2.py tests/test_provider_raw_schema_alignment.py`：27 passed。
  - 早前全量 `cd backend && .venv/bin/python -m pytest tests`：114 passed, 10 skipped, 10 failed；失败中 9 个为 admin/platform login 种子凭据 `INVALID_CREDENTIALS` 相关，另 1 个 cleanup batch 已在匹配回归中修复并通过。
