## Context

admin 客户数据页、tenant 公司列表和 tenant 优选客户都基于 V3 `clean_companies` 及其来源、联系人、贸易等字段展示客户公司。当前三处已经各自支持一部分筛选，但存在三类漂移：

- UI 维度不一致：tenant 有国家多选、来源多选、分数范围；admin 有进口额/次数、PCB 供应商、联系人数范围、成立日期年份范围等。
- 参数命名不一致：tenant 使用 `countries[]`、`sub_industries[]`、`product_tags[]`、`employee_scale[]`、`contacts_count_min/max`；admin 使用 `country`、`industry`、`tag`、`size`、`contact_min/contact_max` 等。
- 查询语义不一致：tenant 多选字段偏 OR 语义，admin 多数为单值或 min/max 语义，导致同一筛选意图无法稳定复现。

本 change 只处理“V3 公司基础数据筛选条件一致性”，覆盖 admin 客户数据页、tenant 公司列表、tenant 优选客户三处。tenant 仍必须受租户可见性约束；admin 客户数据页仍是平台运营视角，不引入租户私有分数、业务状态或数据状态。

## Goals / Non-Goals

**Goals:**

- 定义一套 shared clean-company filter contract，覆盖 admin 客户数据页、tenant 公司列表、tenant 优选客户共同可表达的筛选条件。
- 让三处 UI 呈现同一组基础筛选维度，并使用一致的标签、控件类型与档位选项。
- 让三处 API 入参与后端查询语义对齐，尤其是多选 OR、范围筛、档位筛和空值处理。
- 增加验证，证明相同基础筛选条件在 admin clean companies 和 tenant visible companies 上使用相同语义；结果集合差异只能来自 tenant 可见性约束。

**Non-Goals:**

- 不修改数据库 schema。
- 不修改采集、清洗、推送、评分 worker。
- 不改变 tenant company 可见性、RLS 或租户私有状态隔离。
- 不把 tenant 私有筛选条件强行加到 admin 客户数据页；例如 `score`、`business_status`、`data_status` 如继续保留，必须作为 tenant-only advanced filter 与共享基础筛选分组区分。
- 不处理 Prospects 或其他页面的筛选一致性；tenant 优选客户属于本 change 范围。

## Decisions

### Decision 1: 以 clean-company 基础筛选作为三处页面唯一对齐对象

对齐字段限定为三处页面都能基于 `clean_companies` 或 `clean_company_sources` 表达的基础数据：

| 维度 | 统一语义 |
| --- | --- |
| 关键词 | 公司名 / 标准名 / 域名模糊搜索 |
| 国家/地区 | 多选 OR，ISO3 值 |
| 细分行业 | 多选 OR，匹配 `industry_desc` 或 `industry_tags` |
| 产品标签 | 多选 OR，匹配 `product_tags` |
| 数据来源 | 多选 OR，匹配 `clean_company_sources.source_type` |
| 员工规模 | 最小 / 最大人数范围 |
| 成立日期 | 起止年份范围，文案显示“成立日期”，控件选择年份 |
| 进口额 | 最小 / 最大范围，字段为 `trade_amount_3y_usd` |
| 进口次数 | 最小 / 最大范围，字段为 `trade_count` |
| 联系人数 | 最小 / 最大联系人数量范围 |
| PCB 供应商 | 有 / 无供应商，基于 `pcb_suppliers` 是否为空 |

替代方案是直接让 tenant 复制 admin 现有参数，或让 admin 复制 tenant 现有参数。两者都会保留另一侧的历史命名和语义缺口；统一 shared contract 更稳，也便于后续复用。

最终筛选契约如下，实施前必须先按此表确认代码现状；如发现真实列名与表中不一致，先更新本表再继续：

| 字段 | UI 控件 | 共享外部参数 | 后端匹配字段 / 来源 | 范围 |
| --- | --- | --- | --- | --- |
| 关键词 | 单行输入 | `keyword` | `clean_companies.name` / `name_normalized` / `website` ILIKE | shared |
| 国家/地区 | 多选 Select | `countries[]` | `clean_companies.country_iso3 IN (...)`，值为 ISO3 | shared |
| 细分行业 | 多选 Select / tags | `sub_industries[]` | `clean_companies.industry_desc` 或 `industry_tags` OR 匹配 | shared |
| 产品标签 | 多选 Select / tags | `product_tags[]` | `clean_companies.product_tags` OR 匹配 | shared |
| 数据来源 | 多选 Select | `sources[]` | `clean_company_sources.source_type` OR 匹配 | shared |
| 员工规模 | 两个数字输入 | `employee_count_min` / `employee_count_max` | 将 `clean_companies.employee_num` 解析为可比较人数或区间后做范围匹配 | shared |
| 成立日期 | 两个年份输入 | `founded_year_from` / `founded_year_to` | `EXTRACT(YEAR FROM clean_companies.incorporation_date)`；UI 文案为“成立日期”，选择粒度为年份 | shared |
| 进口额 | 两个数字输入 | `trade_amount_min` / `trade_amount_max` | `clean_companies.trade_amount_3y_usd` | shared |
| 进口次数 | 两个数字输入 | `trade_count_min` / `trade_count_max` | `clean_companies.trade_count` | shared |
| 联系人数 | 两个数字输入 | `contact_count_min` / `contact_count_max` | `clean_companies.contacts_count` | shared |
| PCB 供应商 | 有/无 Select | `pcb_supplier_presence` | 取值为 `has` / `none`；匹配 `clean_companies.pcb_suppliers` 是否为空 | shared |
| 当前分 | 数字范围 | `min_score` / `max_score` | `tenant_companies.score` | tenant-only |
| 业务状态 | Select | `business_status` | `tenant_companies.business_status` | tenant-only |
| 数据状态 | Select | `data_status` | `tenant_companies.data_status` | tenant-only |

联系人筛选最终采用用户自选数值区间，不再使用 `0`、`1-3`、`4-10`、`11-30`、`30+` 固定档位。三处页面 UI 使用最小联系人数 / 最大联系人数输入，外部参数为 `contact_count_min` / `contact_count_max`。后端统一匹配 `clean_companies.contacts_count >= contact_count_min` 与 `<= contact_count_max`。

区间类筛选的前端交互统一为“字段名 + 起始输入 + `～` + 结束输入”的紧凑组合，不再使用“止”“截止”作为第二个输入的 label。筛选条件最终采用单一平铺网格，不显示“基础条件”“区间条件”“租户专属”等分类标题或 key；tenant-only 筛选仍只在 tenant 页面出现，但在视觉上作为同一批筛选操作项平铺展示。

筛选控件的暗文案必须使用业务可读提示，不再暴露“多选 OR”这类实现语义。多选类控件统一提示“选择…”或“输入后回车”，区间输入统一提示“起始/结束/最低/最高”等用户语义。筛选项上下行距必须显式设置，不能依赖 Form.Item 的默认或 `0` margin 造成换行贴在一起。

员工规模最终采用用户自选数值区间，不再使用 `tiny/small/medium/large` 固定枚举。三处页面 UI 使用最小人数 / 最大人数输入，外部参数为 `employee_count_min` / `employee_count_max`。后端必须把 `clean_companies.employee_num` 解析为可比较的人数或区间后做范围匹配；不能使用 `employee_num IN (...)` 精确匹配，也不能继续暴露 `employee_scale[]` 作为 shared 参数。

PCB 供应商参数直接迁移为 `pcb_supplier_presence`，取值为 `has` / `none`。不保留旧 `pcb=yes/no` 兼容层；前端、shared API 类型、admin API 入参和服务层一次性改到 canonical 参数，避免新旧两套语义长期并存。影响范围仅限当前前端与后端同仓调用；若实施时发现外部系统直接调用旧 `pcb` 参数，必须先暂停并更新本 change 再继续。

用户裁决：2026-05-11 已将员工规模从固定枚举改为用户自选数值区间，并决定 PCB 供应商参数直接迁移到 `pcb_supplier_presence`，不保留旧 `pcb=yes/no` 兼容层。2026-05-11 进一步确认联系人数也改为用户自选数值区间，区间控件中间统一使用 `～`。2026-05-11 最新确认筛选区不再按“基础条件 / 区间条件 / 租户专属”分类展示，而是平铺所有筛选操作项，移除分类 key / 标题，仅保留实际操作控件。后续实施以本表为准；实施中若发现代码真实字段或外部调用关系与表不一致，必须先更新本表再继续。

### Decision 2: 前端沉淀共享筛选配置和 mapper

在 shared 前端包内沉淀筛选配置、档位选项和 API mapper，让 admin 与 tenant 页面从同一份定义生成请求参数。页面仍可以各自排版，但不再各自手写字段名和档位。

替代方案是只同步两个页面的 JSX。这样短期改动少，但参数再次漂移的概率高，且难以测试 mapper。

### Decision 3: 后端保留路由边界，但复用查询语义

tenant `/api/v1/companies` 与 admin `/admin/api/v1/clean/companies` 保持独立路由和鉴权边界；在服务层对齐参数解析和 SQL 条件生成。tenant 查询额外叠加 `tenant_companies.tenant_id` 与 `visibility_status = 'visible'`，admin 查询不叠加租户可见性。

替代方案是新增一个共用后端 endpoint。该方案会扩大鉴权和返回结构风险，不符合本次 KISS 范围。

### Decision 4: tenant-only 筛选与共享基础筛选分组隔离

若 tenant 公司列表继续保留 `score`、`business_status`、`data_status` 等租户私有筛选，UI 和 mapper 必须将其标为 tenant-only advanced filters，不计入与 admin 客户数据页必须一致的基础筛选组。

替代方案是删除所有 tenant-only 筛选。删除会改变既有 tenant 能力，风险高于本 change 的目标；除非实施时发现这些筛选本来不可用或无产品价值，否则不作为默认路径。

## Risks / Trade-offs

- **[Risk] 联系人数既有档位与 min/max 范围表达不一致** → 三处页面 UI 统一改为数值区间，shared 参数为 `contact_count_min` / `contact_count_max`；测试覆盖 shared mapper 与 admin / tenant 后端参数透传。
- **[Risk] 员工规模固定枚举无法覆盖真实数据分布** → 改为用户自选数值区间，shared 参数为 `employee_count_min` / `employee_count_max`。
- **[Risk] PCB 供应商新旧参数并存造成长期维护成本** → 直接迁移到 `pcb_supplier_presence=has|none`，不保留旧 `pcb=yes|no` 兼容层；实施前确认没有外部调用方。
- **[Risk] admin 全量 clean companies 与 tenant visible companies 结果数量不同被误认为不一致** → 验收只比较筛选语义和命中条件，不要求两个页面返回相同数量；tenant 结果必须是 admin 结果按可见性裁剪后的子集。
- **[Risk] 前端共享配置过度抽象** → 只共享字段定义、选项、mapper 和测试，不抽象复杂布局组件；页面布局保持本地简单实现。
- **[Risk] 与 active change `v3-tenant-companies` 的 C5 筛选任务重叠** → 本 change 只收口 tenant 与 admin 客户数据页一致性；实施时先检查该 change 的未完成任务，避免重复改动同一行为。
