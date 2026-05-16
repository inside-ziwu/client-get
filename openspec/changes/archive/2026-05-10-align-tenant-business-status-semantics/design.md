## Context

`v3-tendata-cleaning-pipeline` 已经把租户公司展示从动态 join 改为 `tenant_companies.visibility_status` 物化，并把 `business_status` 收窄为长期运营阶段。当前数据库约束仍允许 `archived`，但该值没有当前产品动作支撑。本 change 要彻底移除 `archived` 作为租户公司业务阶段，最终合法值只保留 `new` / `in_group` / `in_plan` / `contacted`。

代码中仍有旧 V2/V3 混合语义残留：

- 评分完成后写 `pending_score` 或 `scored` 到 `tenant_companies.business_status`。
- 租户手工创建公司写 `pending_score`，并写旧 `data_status = complete/incomplete`。
- `/prospects/{id}/select` 与 `/prospects/{id}/exclude` 写 `selected` / `excluded`。
- dashboard 漏斗和前端共享类型仍展示旧评分状态机。

这会让清洗后已经 visible 的租户公司，在评分、手工创建或旧 prospect 操作时触发数据库 check constraint，或者让前端继续围绕不存在的状态展示。

## Goals / Non-Goals

**Goals:**

- 统一 `tenant_companies.business_status` 的语义：只表达长期运营阶段。
- 让评分流程不再写入旧 `business_status` 枚举。
- 让租户手工创建公司、dashboard/filter 与前端类型都接受新状态语义。
- 移除或停用旧 prospect select/exclude 交互入口，避免继续写入无产品语义的旧状态。
- 加入运营分组时必须将租户公司推进到 `in_group`。
- 从最后一个运营分组移除时，在不回退 `in_plan` / `contacted` 的前提下清理过期的 `in_group` 阶段。
- 服务商确认邮件投递成功后，将仍处于 `in_plan` 的租户公司推进到 `contacted`；发送成功但未确认投递的 `sent` 不推进公司级触达阶段。
- 通过迁移清理并移除 `archived` 业务阶段。
- 保持 `tenant_companies.visibility_status` 继续作为可见性门槛。
- 保持 `data_status` 继续作为系统派生的数据可运营性状态。
- 保持实现简单，不新增复杂状态机。

**Non-Goals:**

- 不改变腾道 raw → clean 清洗规则。
- 不改变 `clean_company_keywords` 或 `tenant_companies.visibility_status` 物化规则。
- 不重做评分模型、评分模板或 AI scoring 算法。
- 不引入新数据库表来承载运营阶段。
- 不恢复旧 `pending_score` / `scored` / `selected` / `excluded` 作为合法 `business_status`。
- 不保留 `archived` 作为 `tenant_companies.business_status` 合法值。

## Decisions

### D1. `business_status` 只保留长期运营阶段

活跃运营阶段为：

- `new`：新进入租户公司列表，还未进入分组或触达计划
- `in_group`：已进入租户运营分组
- `in_plan`：已进入发送计划
- `contacted`：服务商已确认邮件投递成功

`archived` 必须从 `tenant_companies.business_status` 中移除。历史 `archived` 行回填为 `new`，因为当前没有可验证的产品动作或审计依据能说明它们应处于哪个运营阶段；回到 `new` 是最小破坏策略。随后数据库 check constraint 收紧为仅允许 `new` / `in_group` / `in_plan` / `contacted`。

原因：这与 `v3-tendata-cleaning-pipeline` 的设计一致。评分状态、数据可运营性、可见性分别由其他字段/表表达，避免一个字段混合多套语义。

备选方案：放宽数据库约束继续允许旧状态。该方案能快速绕过错误，但会让新旧语义并存，后续筛选、取消订阅清理和 dashboard 继续混乱，不采用。

### D2. 评分状态不得写入 `business_status`

评分流程应通过以下位置表达评分结果：

- `company_scores`：单次评分记录、LLM pending、分数明细
- `scoring_jobs`：评分任务排队、租约、完成状态
- `tenant_companies.grade` / `tenant_companies.total_score` / `model_score` / `score`：租户公司当前评分摘要

评分完成时只更新评分摘要字段，不把 `business_status` 改成 `scored`。如果评分仍 pending，也不把 `business_status` 改成 `pending_score`。

原因：评分不是运营阶段。一个公司可以是 `new` 且已评分，也可以是 `in_group` 后重新评分。

### D3. 旧 select/exclude 入口不再进入状态语义

`selected` 是前端交互状态，不应有长期业务状态，也不应该继续保留为租户公司 API 动作。旧 `/prospects/{id}/select` 应移除、停用或返回明确错误；不得写 `selected`，也不得映射为 `in_group`。

`excluded` 也不在当前产品语义中。旧 `/prospects/{id}/exclude` 应移除、停用或返回明确错误；不得写 `excluded`，也不得映射为其他业务阶段。如果未来需要“排除”或“不感兴趣”的产品动作，必须另开 change 定义字段、入口和前端行为。

原因：当前没有被确认的 select/exclude 产品动作。为了 KISS，本 change 只消除旧状态写入风险，不发明新的运营语义。

### D4. 手工创建公司走当前 V3 schema

租户手工创建公司必须：

- 不显式写入 UUID 到 bigint identity `tenant_companies.id`
- 使用 `business_status = 'new'`
- 使用 `data_status` 的当前合法值：`ready` / `missing_contacts` / `insufficient_data`
- 写 `visibility_status = 'visible'`
- 使用当前真实字段名：`note` / `tags` 等，不继续写旧字段名导致静默断裂或 SQL 错误

原因：手工创建不是腾道清洗主链路，但它是同一张租户公司表的入口，必须和新 schema 对齐。

### D5. Dashboard 与前端类型跟随新语义

租户 dashboard 漏斗应围绕新长期运营阶段展示：

`new` / `in_group` / `in_plan` / `contacted`

dashboard overview、dashboard funnel 与 companies filters 的租户端展示统计口径必须只包含 `tenant_companies.visibility_status = 'visible'` 且未删除的公司。hidden 公司不进入租户端展示指标。

“已评分公司”继续通过 `grade IS NOT NULL` 或评分摘要字段统计，不从 `business_status = scored` 推断，但同样只统计 visible 公司。前端共享类型中的 `TenantCompanyStatus` 应更新为新枚举。

原因：前端继续展示旧状态会误导运营，也可能提交数据库不接受的状态值。

### D6. 继续运营入口必须维持 visible 门槛

评分、分组、发信、详情等入口继续以 `tenant_companies.visibility_status = 'visible'` 作为访问门槛。本 change 只修复阶段语义，不放宽 hidden 公司访问。

原因：这是 `v3-tendata-cleaning-pipeline` 的核心边界，不能被状态语义收口顺手破坏。

### D7. 分组移除只回退过期的 `in_group`

分组成员关系仍由 `group_members` 表表达。`business_status = in_group` 是给 dashboard/filter 使用的长期阶段摘要，因此需要在移出分组时避免摘要过期：

- 若公司从某个分组移除，但仍存在其他 `group_members`，保持 `in_group`。
- 若公司从最后一个分组移除，且当前 `business_status = in_group`，回退为 `new`。
- 若公司已是 `in_plan` / `contacted`，移出分组不回退，避免把更晚阶段倒退到 `new`。

原因：这保持状态摘要和真实分组关系一致，同时不引入复杂状态机。

### D8. 投递成功推进 `contacted`

只有服务商 webhook 确认邮件 `delivered` 后，对应租户公司若仍处于 `in_plan`，才应推进为 `contacted`。本系统 worker 的 `sent` 只表示邮件已交给服务商或进入发送通道，不代表收件方服务器已接受，因此不得推进公司级触达阶段。

这与 `tenant_contacts.status = contacted` 是不同粒度：联系人状态可以表达发送动作后的联系人触达尝试，公司状态表达公司已进入确认投递阶段。

原因：如果 `contacted` 被 `sent` 提前推进，dashboard 会把尚未确认投递的公司统计为已触达；如果 `contacted` 只是合法枚举但没有明确推进动作，dashboard 漏斗会出现不可达阶段。以 `delivered` 作为唯一推进条件，是更清晰的业务语义。

### D9. 发送链路关联列跟随 V3 bigint tenant company/contact

`tenant_companies.id` 与 `tenant_contacts.id` 已迁移为 bigint 后，发送链路表中仍引用租户公司或联系人 ID 的列必须一并对齐，否则 `mark_email_sent`、发送计划收件人、服务商 webhook 无法可靠关联到当前 V3 租户公司/联系人。

本 change 在 migration 中将 `emails.tenant_contact_id`、`sending_plan_recipients.tenant_company_id`、`sending_plan_recipients.tenant_contact_id`、`sequence_enrollments.tenant_contact_id` 转为 bigint。由于当前线上没有真实 `company_scores`、`group_members`、`scoring_jobs` 旧运营数据，同类发送链路旧运营数据也不作为迁移真源；无法从旧 UUID 安全映射到新 bigint 的发送链路运行态数据清理后重建。

原因：`delivered -> contacted` 必须能从 webhook email 回查到当前租户联系人和租户公司。保持 uuid 列会让新 bigint ID 无法写入或 join，导致阶段闭环不可达。

## Risks / Trade-offs

- [旧前端按钮语义变化] `select` 不再作为业务动作存在 → 移除或停用旧入口；如果未来需要批量临时选择，应只在前端本地状态中表达。
- [exclude 无替代动作] `exclude` 不映射为其他业务阶段 → 当前保留黑名单等已有明确动作；如果需要排除原因后续另开 change。
- [历史 archived 回填] 历史 `archived` 回填为 `new` 可能让少量旧归档公司回到新阶段 → 当前线上无真实旧运营数据，且没有产品动作支撑 archived；回填前用迁移或验证查询记录数量。
- [测试夹具残留旧枚举] 一些测试或 temp table 可能仍 seed `selected` → 实施时只更新当前需求相关测试，不为旧状态放宽生产约束。
- [前端展示短期变动] dashboard 漏斗指标会从评分状态变成运营阶段 → 用“已评分公司”独立指标保留评分进度感知。
- [阶段自动回退边界] 只有仍处于 `in_group` 的公司会在离开最后一个分组后回退 `new`，避免影响已经进入发送计划或已触达的公司。
- [发送链路运行态清理] 旧发送计划收件人、序列 enrollment、邮件运行态若仍是旧 UUID 引用，无法安全映射到 V3 bigint 主键 → 当前线上无真实旧运营数据，按最小破坏策略清理运行态并让后续计划重新生成。
