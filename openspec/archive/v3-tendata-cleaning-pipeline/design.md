## Context

当前 V3 数据基础层已经具备 `tendata_raw_companies`、`clean_companies`、`clean_company_sources`、`clean_company_keywords`、`tenant_keyword`、`tenant_companies` 等表。业务上，租户先订阅 tenant 关键词，系统归一到平台关键词 `keyword_master`，平台关键词触发励销云 stage 1 找中国同行，再由腾道 stage 2 反查海外买家。腾道 raw 的平台关键词归属来自触发它的反推链路，而不是腾道天然提供。

完整链路是：租户订阅 tenant 关键词 → 系统归一到平台关键词 → 平台关键词触发励销云 stage 1 找中国同行/供应商 → 腾道 stage 2 基于这些中国同行/供应商反查海外买家 → 腾道 raw 继承触发链路上的平台关键词 → 腾道 raw 清洗进平台干净库 → 干净公司继承平台关键词 → 订阅该平台关键词的租户通过 `tenant_companies` 看到这些公司。

本 change 假设腾道 raw 已经存在，不讨论腾道采集任务如何恢复。重点是：腾道 raw 清洗入平台干净库时，必须保留公司实体、来源证据、平台关键词关联；订阅对应平台关键词的租户必须在公司列表看到这些干净公司，并在租户私有状态层继续评分、标记、分组、发信。

## Goals / Non-Goals

**Goals:**

- 建立腾道 raw → clean_companies 的平台实体清洗 v1 规则。
- 建立 clean 公司继承 raw 平台关键词的规则。
- 建立订阅租户的公司可见性物化规则。
- 明确取消 tenant 关键词时的隐藏规则，尤其是多关键词覆盖场景。
- 保持实现简单、可追溯、可重跑。

**Non-Goals:**

- 不恢复或改造腾道 stage 2 采集任务触发。
- 不改变励销云 stage 1 跨天续采。
- 不在本 change 定义 AI 评分模型或自动评分规则。
- 不引入复杂模糊去重、同义词合并或人工合并后台。
- 不要求所有联系人在第一版完成深度清洗；联系人清洗可后续单独细化。

## Decisions

### D1. 入库门槛：公司名 + 国家

腾道 raw 必须同时具备公司名和 `country_iso3` 才能进入 `clean_companies`。缺少国家的 raw 不进入干净库。

原因：跨国同名公司误合并风险高；第一版宁可少入库，也不要把实体合错。被跳过的 raw 应保留在 raw 层，可通过 cleanup 状态或错误信息追溯。

### D2. 第一版去重主规则：`normalized_name + country_iso3`

第一版用公司名归一结果与国家作为 clean 公司主去重规则。

原因：该规则与现有 `clean_companies` 唯一约束匹配，足够简单、可验证。`source_id` / `globiz_id` / `tax_no` / website 暂作为来源证据和补充字段，不作为第一版跨来源主合并键。

### D3. 字段合并策略按字段类型区分

全局原则是非空补空，但摘要字段与集合字段例外：

- 数值摘要字段 `trade_amount_3y_usd` / `trade_count` / `contacts_count` 保留最新来源摘要。
- 描述摘要字段 `industry_desc` / `employee_num` 保留最新来源摘要。
- 证据集合字段 `product_tags` / `pcb_suppliers` / `aliases` 追加去重。

原因：贸易次数、贸易金额、联系人数量和行业/规模是来源摘要，不应取最大值伪造业务口径；产品标签、中国供应商、别名则是证据集合，累积更符合排查和筛选需要。

### D4. 平台关键词继承：raw → clean company keyword relation

清洗成功后，如果 `tendata_raw_companies.keyword_master_id` 存在，系统必须写入干净公司与该平台关键词的关联。同一干净公司被多个平台关键词发现时，追加关联，不覆盖。

原因：租户侧展示依赖 tenant 关键词归一后的平台关键词。若 clean 公司没有继承平台关键词，admin 干净库可见但租户侧无法分发。

### D4.1. `clean_company_keywords` 是平台命中关系，必须保留

`clean_company_keywords` 表达“某个干净公司被哪些平台关键词发现/命中”。它属于平台层，不属于租户私有状态。取消租户关键词订阅时，不删除 `clean_company_keywords`；只更新该租户自己的 `tenant_keyword` 与 `tenant_companies.visibility_status`。

原因：同一个平台关键词和同一家公司可能服务多个租户。删除平台命中关系会影响其他租户和后续物化补偿。

### D4.2. 缺平台关键词的 raw 可补 clean，但不新增命中关系

如果腾道 raw 缺少 `keyword_master_id`，它可以进入 `clean_companies` 并作为来源证据补充平台干净公司资料，但不能新增 `clean_company_keywords`，也不能单独触发 `tenant_companies` 物化。

如果缺关键词 raw 合并到一个已经因其他来源/关键词而可见的 clean 公司，租户可能看到被补充后的公司资料；这属于 clean 公司整体资料被多来源补充，而不是该 raw 自己扩大了租户可见范围。

原因：显示范围只由平台关键词命中关系决定；公司资料可以被多来源补充。缺关键词 raw 不能新增可见范围，但也不必阻断它对平台干净库资料质量的补充。

### D5. 租户显示通过物化状态，而不是每次动态 join

当 clean 公司关联到某个平台关键词时，系统应找到所有 active `tenant_keyword` 订阅该平台关键词的租户，并为这些租户 upsert `tenant_companies` 可见状态。`tenant_companies` 增加 `visibility_status` 字段，取值为 `visible` / `hidden`；租户公司列表以 `visibility_status = visible` 为基础展示依据。

新增字段时，历史 `tenant_companies` 不能简单默认全量 `visible`。迁移回填必须按“该租户是否仍有 active tenant 关键词覆盖该 clean 公司”计算：

- 仍有 active 覆盖：`visibility_status = visible`
- 无 active 覆盖：`visibility_status = hidden`
- 新物化写入：`visibility_status = visible`

原因：业务口径是“订阅决定显示，评分决定运营优先级”。物化后，租户状态、评分、备注、标签、分组、发信都有稳定的租户侧锚点。

### D6. 取消订阅只在无其他 active 关键词覆盖时隐藏

租户取消某个 tenant 关键词时，系统应重新计算该租户对受影响 clean 公司的关键词覆盖。只有当该租户没有任何 active tenant 关键词还能覆盖该公司时，才隐藏该租户的 `tenant_companies` 记录。

原因：同一家公司可能关联多个平台关键词，租户也可能订阅多个关键词。取消一个关键词不应误隐藏仍被其他 active 关键词覆盖的公司。

### D7. 隐藏时清空该租户的私有运营状态

当取消订阅导致某家公司对该租户不再可见时，系统应同时清空该租户对这家公司的私有运营状态。基于当前真实 schema，第一版确定清空 `tenant_companies` 主表中明确属于租户运营判断的字段：

- `business_status` 重置为 `new`
- `model_score` 清空
- `score` 清空
- `note` 清空
- `tags` 清空为 `{}`

同时清理或失效该租户围绕这家公司产生的可继续运营关系：

- 删除该租户公司对应的 `group_members`
- 删除或取消该租户公司对应的 pending/leased 类 `scoring_jobs`
- 删除或归档该租户公司对应的 `company_scores`；第一版如果没有审计保留要求，优先删除以保证重新订阅按新客户开始

发送计划、邮件发送历史等历史事实不建议硬删，但所有继续运营入口必须以 `tenant_companies.visibility_status = visible` 作为门槛，不能继续拿 hidden 公司发信。

`data_status` 表示系统判断的数据可运营性，不等同于租户主观运营判断。隐藏时不把旧 `data_status` 当作可复用状态；重新订阅或重新物化为 visible 时，系统必须重新计算 `data_status`。平台干净公司、来源证据、平台关键词关联不受影响。

原因：业务上选择方案 B：租户不再订阅覆盖这家公司的关键词时，这家公司不再属于该租户当前运营资产。以后如果该租户重新订阅并再次看到这家公司，应按新客户重新开始，避免旧评分或旧运营判断误导当前运营。

### D8. `business_status` 表达运营阶段，不表达前端交互状态

`business_status` 只表达租户对公司的长期运营阶段，取值为：

- `new`：新进入租户公司列表，还未处理
- `in_group`：已进入运营分组
- `in_plan`：已进入触达计划
- `contacted`：已触达
- `archived`：已归档

当前真实库中的 `selected` 是前端交互状态，不应作为长期业务状态入库，应从 `business_status` 约束中移除。真正属于哪个分组仍由 `group_members` 表表达，`in_group` 只表示公司已经进入分组运营阶段。

历史数据迁移时，已有 `business_status = selected` 不应默认迁移为 `in_group`。第一版统一回填为 `new`；如果同一租户公司存在有效 `group_members` 记录，可由分组关系重算为 `in_group`。

原因：把“用户当前选中某条记录”和“客户处于哪个运营阶段”混在同一字段，会导致筛选、批量操作、取消订阅清空状态时口径混乱。

### D9. `data_status` 由系统判断数据可运营性

`data_status` 表达公司数据是否够运营，由系统根据公司资料和联系人可用性判断，不由租户手动判断。第一版取值保持：

- `ready`：资料和联系人条件基本可运营
- `missing_contacts`：公司存在，但缺可用联系人
- `insufficient_data`：公司基础资料不足

`data_status` 不决定公司是否显示；显示由 `visibility_status` 决定。第一版系统判断规则：

- `missing_contacts`：该 clean 公司没有可用联系人，或该租户没有可用 `tenant_contacts`
- `insufficient_data`：公司缺少核心识别/运营资料，例如公司名、国家以外的关键资料过少，且没有可用联系人
- `ready`：不满足上述两个问题，资料和联系人条件基本可运营

取消订阅导致隐藏后，重新订阅或重新物化为 visible 时必须重算 `data_status`，避免旧数据状态污染新一轮运营。

原因：`visibility_status` 决定看不看得到，`data_status` 决定好不好运营，`business_status` 决定运营到哪一步。三者必须分开。

### D10. 租户列表以物化可见状态为准

租户公司列表、详情、评分、分组、发信等继续运营入口不应再以 `clean_company_keywords + tenant_keyword` 动态 join 作为基础可见判断。动态关键词关系只负责计算、补齐和重算 `tenant_companies.visibility_status`；用户实际看到什么、能继续运营什么，以 `tenant_companies.visibility_status = visible` 为准。

原因：如果列表继续依赖动态 join，取消订阅后的 hidden 状态会被绕过，导致“后台已隐藏、前台仍可见”的业务错位。

### D11. 关联运营表必须对齐 `tenant_companies.id`

`company_scores.tenant_company_id`、`group_members.tenant_company_id`、`scoring_jobs.tenant_company_id` 的业务语义都是指向 `tenant_companies.id`。当前真实库中 `tenant_companies.id` 是 `bigint`，这些字段却是 `uuid` 且缺少到 `tenant_companies` 的外键，实施时必须统一改为 `bigint` 并补充外键约束。

同时需要核对 `group_members.tenant_contact_id`，因为 `tenant_contacts.id` 当前也是 `bigint`，若该字段语义指向 `tenant_contacts.id`，也应同步对齐为 `bigint` 并补外键。

原因：这些表承载评分、分组和评分任务，如果 ID 类型不一致，系统会出现“租户公司主表存在，但评分/分组/任务无法可靠关联”的断链问题。

迁移策略：

- 先统计 `company_scores`、`group_members`、`scoring_jobs`、`group_members.tenant_contact_id` 的现有数据量与可映射比例
- 如果为空或没有可可靠映射的业务数据，优先清空/重建这些引用列并补外键
- 如果存在可保留历史数据，必须通过明确映射关系回填到当前 `tenant_companies.id`；不能做 uuid → bigint 强制类型转换
- 无法映射的孤儿数据必须归档或删除，并记录数量
- 外键补充必须在数据清理完成后执行

### D12. 最新来源摘要以 raw 采集/创建时间为准

“最新来源摘要”第一版以 raw 行的 `created_at` 作为比较依据；如果后续 raw 表存在更精确的 enrichment fetched time，可在单独 change 中替换口径。重跑清洗时，同一 clean 公司同一摘要字段只接受更新的 raw 摘要覆盖旧摘要，避免处理顺序决定结果。

原因：数值摘要和描述摘要是来源摘要，不是聚合指标。必须有稳定时间依据，才能保证清洗可重跑。

### D13. 租户物化必须依赖唯一约束幂等

`tenant_companies` 必须保持 `UNIQUE (tenant_id, clean_company_id)`。所有通过平台关键词命中写入租户公司的逻辑都必须基于这个唯一约束 upsert，避免清洗重跑、补偿扫描、新订阅补齐产生重复租户公司。

## Risks / Trade-offs

- [误合并] `normalized_name + country_iso3` 可能合并同名不同主体 → 第一版接受该风险，后续通过来源证据和人工审计发现问题后再引入更强身份键。
- [漏合并] 同一家公司不同名称写法可能形成多条 clean 公司 → 第一版避免复杂模糊匹配，后续再补人工合并或别名规则。
- [关键词缺失] raw 没有 `keyword_master_id` 会导致 clean 公司无法分发给租户 → raw 可进入 admin 排查视图，但不能物化到租户公司列表；cleanup health 应暴露缺关键词归因风险。
- [物化状态漂移] tenant 关键词变更后 `tenant_companies` 可见字段可能滞后 → 订阅/取消订阅动作必须同步触发可见性重算；worker 可补偿扫描。
- [运营状态清空] 方案 B 会让租户取消订阅后丢失该公司私有评分、备注、标签、分组等历史运营状态 → 这是当前业务选择；如后续需要保留历史，可单独设计审计日志或归档视图。
- [关联表不一致] 当前真实库中部分运营表的 `tenant_company_id` 类型与 `tenant_companies.id` 不一致，且缺少外键 → 本 change 实施前必须完成 schema 对齐，否则评分、分组、任务链路会断链。
- [历史回填误展示] `visibility_status` 历史数据若默认全量 visible，会绕过订阅覆盖判断 → 必须按 active tenant 关键词覆盖回填。
- [缺关键词 raw 间接展示] 缺 `keyword_master_id` 的 raw 合并到已可见 clean 公司后，可能补充租户可见资料 → 当前接受该行为，但禁止它新增平台命中关系或扩大可见范围。
- [联系人断层] `contacts_count` 可能有值但 `clean_contacts` 为空 → 本 change 不把联系人深度清洗作为完成前置，但应记录为后续联系人清洗任务风险。
