# tenant 端关键词采集数据：行业分发 + 采集类型展示

- 日期：2026-06-09
- 状态：brainstorm 结论，待工程审查 / OpenSpec change
- 前置：admin 端采集类型筛选已上线（change: admin-customer-page-optimization）

## 背景与问题

admin 端已能按采集类型（关键词采集 / 精准反推）区分客户数据，tenant 端需要同样的区分能力。但调研发现更根本的问题：**关键词采集数据在现有机制下永远不会进入 tenant 端**。

### 生产数据调研结论（2026-06-09）

- `waimaotong_clean_companies` 中关键词采集数据 4035 条（持续增长中），精准反推 4146 条。
- tenant 端增量分发完全依赖关键词血缘：`fan_out.py` 和 `wmt_lineage_repair.py` 均按 `keyword_master_ids @> [订阅的 keyword_master_id]` 推送；而关键词采集数据仅 30 条有 `keyword_master_ids`，且 lineage_repair 的血缘回填只走精准反推链路（立小云 source_competitor），不覆盖关键词采集。
- 关键词采集数据的关键词存在 `raw_payload->'source_keywords'`：1360 条 (34%) 有真实英文词（PCB、pcb assembly 等），2585 条 (66%) 为字符串 `nan`（legacy 导入丢失，不可恢复）。
- 公司级 `industry` 字段仅 30% 覆盖，且为外贸通英文多值标签，与 `tenants.industry` 体系无法对齐——**不能作为匹配锚点**。
- `tenants.industry` 现状：3 个 active 租户，值为 `PCB`、`PCB`、`电路板`（自由文本）。
- 租户当前订阅关键词仅中文「线路板」「电路板」，英文采集词接不进现有订阅体系。

## 已确认决策

| # | 决策 | 内容 |
|---|------|------|
| D1 | 分发锚点 | 按「数据批次打行业标」：`data_source_tags` 含 `外贸通关键词采集` 的整批数据视为 PCB 行业数据；不用公司级 industry 字段匹配 |
| D2 | 推送范围 | 全量推送（含 66% 关键词为 nan 的数据），共 4035+ 条 |
| D3 | 行业规则存储 | 不加新字段/映射表，规则硬编码在 worker 常量（含 `PCB` ≡ `电路板` 别名）；出现第二个采集行业时再抽象（YAGNI） |
| D4 | 分发实现位置 | `wmt_lineage_repair` 自愈循环新增一条行业 fan-out SQL，与现有关键词 fan-out 并列；增量数据随循环自动分发，无需新触发点 |
| D5 | tenant 列表 UI | 新增「采集类型」列 + 筛选（关键词采集 / 精准反推），后端返回 `collection_type` 计算字段，口径与 admin 端一致（包含 `外贸通关键词采集` → keyword，否则 reverse） |
| D6 | tenant 详情页 | 透出采集类型 |
| D7 | 不做 | 来源关键词透出（`matched_keywords` 维持现状空数组）、关键词血缘回填、公司级行业匹配、采集计划表 |

## 需求清单

### R1 行业 fan-out（后端 worker）

- `wmt_lineage_repair.py` 新增 SQL：将 `data_source_tags @> '["外贸通关键词采集"]'::jsonb` 的公司插入 `tenant_companies`，目标租户为 `status='active'` 且 `industry = ANY(['PCB', '电路板'])`。
- `data_status` 计算复用现有 fan-out 的 CASE 逻辑（missing_contacts / insufficient_data / ready）。
- `ON CONFLICT (tenant_id, clean_company_id) DO UPDATE` 幂等，与现有 SQL 一致。

### R2 tenant 公司列表采集类型（后端 + 前端）

- `tenant_query_service.companies_page` 返回 `collection_type`（keyword / reverse），API 增加筛选参数。
- tenant 前端公司列表新增「采集类型」列与筛选项。

### R3 tenant 公司详情采集类型

- `v3_company_detail` 返回 `collection_type`，详情页展示。

## 验收要点

- 行业 fan-out 跑一轮后，PCB/电路板租户的 tenant_companies 包含全部关键词采集公司。
- 非 PCB 行业租户（未来如有）不受影响。
- tenant 列表按采集类型筛选结果与 admin 端口径一致。
- 重复执行 lineage_repair 不产生重复行（幂等）。
- 既有 source_type/sources/product_tags 筛选参数传参不再 500（jsonb 修复回归）。

## 工程审查结论（2026-06-09 /plan-eng-review + Codex outside voice）

| # | 决策 | 内容 |
|---|------|------|
| 1A | 顺手修存量 bug | `tenant_query_service.py:248/251/636` 三处 `data_source_tags && text[]` 改 jsonb 包含语法 + 回归测试 |
| 2A | 单向分发 | 行业 fan-out 只进不出，与现有关键词 fan-out 语义一致 |
| 3A | DRY 收口 | collection_type 口径抽共享模块（标签常量 + SQL 片段常量 + 判定函数），admin/tenant/worker 三处引用；接受「共享常量 + 各处 SQL 表达式」的现实（Codex#9） |
| 4A | 测试深度 | worker 用 SQL 字符串断言（仓库约定）+ dev 库手动跑一轮验证；DB 集成测试基设进 TODOS（D12） |
| 7A | 多租户语义确认 | 未来新建 PCB 行业租户自动接收全量批次数据，规则即语义，不加开关 |
| 8A | GIN 索引 | alembic 迁移给 `data_source_tags` 加 GIN（jsonb_path_ops）——Codex#2 推翻初审 YAGNI 判断 |
| 9A | 行业匹配归一化 | `lower(trim(t.industry))` 比对，别名表存小写，消灭大小写/空格静默漏推 |
| 10A | product_tags 同修 | 生产库实锤 product_tags 也是 jsonb，`:231` 同类 bug 一并修，grep 确认无第五处 |
| 11B | 驳回一次性脚本 | 维持自愈循环方案：采集程序外部写库、无写入入口可挂分发；增量持续到来（调研期间 3945→4035） |
| 12A/13A | TODOS | DB 集成测试需求挂靠现有条目；「第二行业出现时规则数据化」新增条目 |

Codex 吸收项（无决策，直接进任务）：#4 筛选链路补全（ops.py 参数、company-filters.tsx 三件套、shared-api 类型）、#5 筛选选项前端硬编码、#7 collection_type 字段命名统一、#8 列头数组/空态 colSpan、#9 共享模块同时导出 SQL 片段。

### 实施任务清单

- [ ] **T1 (P1)** 抽 `collection_source` 共享模块（标签常量 + jsonb SQL 片段 + keyword/reverse 判定函数），admin service 改为引用
- [ ] **T2 (P1)** `wmt_lineage_repair.py` 新增行业 fan-out SQL（jsonb 包含 + lower/trim 行业别名归一化 + `tenants.status='active'` + data_status CASE 复用 + ON CONFLICT 幂等），更新模块 docstring
- [ ] **T3 (P1)** alembic 迁移：`data_source_tags` 加 GIN 索引（jsonb_path_ops）
- [ ] **T4 (P1)** `tenant_query_service.py`：修 4 处 jsonb 潜伏 bug（source_type/sources×3 + product_tags:231，grep 确认无第五处）；companies_page / v3_company_detail 返回 `collection_type`；新增 collection_type 筛选
- [ ] **T5 (P1)** `ops.py` GET /companies 增加 collection_type 参数透传
- [ ] **T6 (P1)** 前端：shared-api 类型 + company-filters.tsx（FilterValues/EMPTY_FILTERS/buildParams，选项硬编码关键词采集/精准反推）+ 列表加列（列头数组、空态 colSpan 同步）+ 详情展示
- [ ] **T7 (P1)** 测试：worker SQL 断言套件、共享模块口径测试（admin 现有 7 测试迁移）、tenant 筛选三分支、source_type/sources/product_tags 回归测试（CRITICAL）、ops 参数透传
- [ ] **T8 (P2)** dev 库跑一轮 lineage repair 验证（PCB 租户全量收到、幂等、data_status 分级正确），前端手动 QA

### NOT in scope

- 来源关键词透出（matched_keywords 维持空数组）— D7 决策，等业务需要再做
- 关键词血缘回填（1360 条英文词进 keyword_master）— 行业分发方案使其不必要
- 行业分发开关 — 7A 驳回，YAGNI
- 行业回收逻辑 — 2A 接受单向分发
- DB 集成测试基设 — 进 TODOS（D12）
- 行业规则数据化 — 进 TODOS（D13），第二行业出现时触发
- 前端自动化测试 — tenant 前端无测试框架（TODOS 既有条目）

### 失败模式

| 路径 | 失败方式 | 测试 | 错误处理 | 用户可见性 |
|---|---|---|---|---|
| 行业 fan-out SQL 类型/语法错误 | 循环内抛异常 | SQL 断言 + dev 库验证 | repair loop try/except 记日志，服务不崩 | 分发停滞，日志可见 |
| 行业别名未登记（如「线路板」） | 静默漏推 | 无 | 无 | **静默** — D3 已知残余风险，缓解：worker 常量旁注释「新增租户行业写法需登记别名」 |
| ON CONFLICT 冲突路径 | 重复行 | SQL 断言 + dev 库幂等验证 | UNIQUE 约束兜底 | 无影响 |
| 既有筛选回归（jsonb 修复） | 筛选 500 | 回归测试（CRITICAL） | FastAPI 500 | 明确报错 |

### 并行化

Lane A（后端，串行）：T1 → T2/T3/T4/T5 → T7；Lane B（前端 T6）依赖 T4/T5 的 API 契约定稿后启动。改动量小，建议单 worktree 顺序实施，无需并行。

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found (absorbed) | 10 findings：5 决策（7A/8A/9A/10A/11B）+ 5 吸收进任务 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 4 issues（1A/2A/3A/4A 全部落定），16 测试 GAP 全部纳入 T7 |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **CODEX:** 10 条发现全部处置：8A 推翻初审 YAGNI 加 GIN 索引、10A 实锤 product_tags jsonb 同修、9A 行业归一化、7A 语义确认、11B 驳回一次性脚本（写入入口前提不成立）、#4/#5/#7/#8/#9 吸收进 T1-T6。
- **CROSS-MODEL:** 初审与 Codex 在 GIN 索引（初审 YAGNI vs Codex 加）、方案形态（循环 vs 一次性脚本）两处分歧，分别采纳 Codex（8A）和维持初审（11B），其余互补。
- **VERDICT:** ENG CLEARED — ready to implement（下一步：建 OpenSpec change `tenant-keyword-collection-distribution`）

NO UNRESOLVED DECISIONS
