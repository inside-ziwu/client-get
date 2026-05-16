# V3 · 02 · Current Implementation Gap Audit（按 9 能力域）

> **状态**：v1.0 起草（2026-05-06）—— 用户决策"替换为 9 能力域"后重写
> **责任**：Claude Code 起草 → 用户签字 → Gate 4 解锁 Delivery Plan
> **证据基础**：[`03-r1-readiness-matrix.md`](03-r1-readiness-matrix.md)（33 UC × 状态）+ [`04-module-functional-matrix.md`](04-module-functional-matrix.md)（admin 11 + tenant 9 模块）+ [`mockups/`](mockups/)（24 个原型已确认）+ alembic 0006 真实 schema
> **关联**：[`00-v3-business-goals.md`](00-v3-business-goals.md) §3 R-1~R-4 / [`00-v3-target-spec.md`](00-v3-target-spec.md) §0.A 33 项决策
> **下游**：本文件签字 → [`03-v3-delivery-plan.md`](03-v3-delivery-plan.md) 编织 5 个 OpenSpec change → 实施

## 0. 元数据

- 版本：v1.0（首版按 9 能力域）
- 起草日期：2026-05-06
- 用户签字：__未签字__
- 阻塞 Gate：Gate 4（Delivery Plan）

---

## 1. 状态枚举（6 状态保持，新增"层"分解）

| 状态 | 定义 | 必备证据 |
| --- | --- | --- |
| `PASS` | 该层完整可用 | 真实运行日志 / DB row / 截图 |
| `PARTIAL` | 主路径在，缺关键分支 / 配置入口 | 已实现部分的证据 + 缺口说明 |
| `SKELETON` | 文件存在但占位 | 文件存在但未跑通的证据 |
| `MISSING` | 没找到实现 | 代码与 DB 双查无果 |
| `UNVERIFIED` | 可能实现了，证据不足 | 看到了文件但无法运行验证 |
| `BROKEN` | 实现存在但运行失败 | 失败日志 / 异常栈 |

**层分解**（每能力域按 6 层独立评估）：

```
原型(mockup) → 前端代码 → 后端 API → DB schema → Worker → E2E 真跑
   24 文件     React TSX    FastAPI    alembic     4 进程     真实数据
```

> ⚠️ **关键原则**：综合状态 = **最弱层**（短板原则）。原型 ✅ 不代表代码 ✅。

---

## 2. 9 能力域 Audit

> 每能力域一节，含：① 综合状态总表（一行）② 子项缺口表 ③ 关联 OpenSpec change

### 2.1 C1 · 数据库重构（D-008=B）

> **业务目标**：原 6 raw 表 → 拆为 4 raw（去外贸通）+ 2 clean（shared_companies / shared_contacts）+ 5 新表；建 cleanup_service 消费 cleanup_queue。

| 层 | 状态 | 证据 |
|---|:-:|---|
| 原型 | N/A | 数据库层无原型 |
| 前端代码 | N/A | — |
| 后端 API | `MISSING` | 当前走 jsonb payload，新 schema 未建 |
| **DB schema** | `MISSING` | alembic 至 0006，缺 0007~0013 + D-008 重构迁移；[`03-r1-readiness §5 D-008=B`](03-r1-readiness-matrix.md) 标 2-4 天工作量 |
| **Worker (cleanup_service)** | `MISSING` | [`03-r1-readiness §5`](03-r1-readiness-matrix.md) 明确 worker 不存在，2-4 天 from-scratch |
| E2E | N/A | — |
| **综合** | **MISSING** | 全 from-scratch |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C1-G1 | 拆 raw_companies → tendata_raw / lixiaoyun_raw（外贸通推迟 V3.1+，按 D-035） | M | D-008 / D-035 |
| C1-G2 | 建 shared_companies / shared_contacts 2 张干净表 + UNIQUE 约束 | M | D-008 |
| C1-G3 | 建 cleanup_queue + cleanup_service worker（含 lease + 重试 + 跨源合并 + 励销云不入 clean 规则） | L | D-008-B |
| C1-G4 | clean_companies **+11 字段**：D-038 9 个（国家/行业细分/成立时间/注册资金/产品标签/公司规模/数据来源/进出口额/进出口次数 + 联系人数量冗余 contact_count）+ D-039 2 个（factory_type / has_china_pcb_supplier）| M | D-038 / D-039-X.1 |
| C1-G5 | alembic 0007~0013 升级 + D-008 重构迁移 staging 验证 | M | D-017 |

**OpenSpec change**：`v3-data-foundation` (Wave 1)

---

### 2.2 C2 · KeywordMaster 跨租户复用（D-009=A）

> **业务目标**：A 租户已采过的关键词，B 租户配同关键词时**立即看到 A 当年采到的全量历史数据**（零等待）。

| 层 | 状态 | 证据 |
|---|:-:|---|
| 原型 | `PASS` | `tenant-intelligence.html` + `tenant-settings-keywords.html` 含跨租户提示 |
| 前端代码 | `PARTIAL` | tenant/Intelligence 已有 keyword 输入；缺"已采过 → 立即可见"分支提示 |
| 后端 API | `MISSING` | UC-06 当前无 keyword_master 命中判定；UC-11 fan-out 未实现 |
| DB schema | `MISSING` | 缺 `keyword_master` 表 + `tenant_keyword` 关联表 |
| Worker | `MISSING` | UC-11 fan-out worker 无（命中老关键词时把历史数据复制到新租户视图） |
| E2E | `MISSING` | 当前无法验证跨租户复用 |
| **综合** | **MISSING** | UC-06 + UC-11 联动 from-scratch |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C2-G1 | 新建 `keyword_master` 表（关键词归一化 + 首次采集时间） | S | D-009 |
| C2-G2 | 拆 `collection_keywords` 与 `keyword_master` 解耦 | M | D-009 |
| C2-G3 | UC-06 改：租户配关键词时查 keyword_master 判定"已采/未采" | M | D-009 |
| C2-G4 | UC-11 fan-out worker：命中老关键词 → 把命中公司复制进新租户 tenant_companies 视图 | M | D-009 |
| C2-G5 | UC-12/14 改写：collection_task 关键词归一化、命中分发 | M | D-009 |

**OpenSpec change**：`v3-collection-pushback` (Wave 2)

---

### 2.3 C3 · 联系人职位分类（D-037）

> **业务目标**：admin 中央配 4 张表（等级 / 类别 / 关键词 + 是否投递开关），所有租户继承使用。整段从 tenant 端搬到 admin 端。

| 层 | 状态 | 证据 |
|---|:-:|---|
| **原型** | `PASS` | `mockups/admin-contact-classification.html` 已设计（V3 新增页面） |
| 前端代码 | `MISSING` | admin 端无该模块；tenant 端有 router.tsx + Settings/ContactRules + Onboarding StepContactRules + shared-api queryKeys 全套老模块待删除（codex H-03 验证） |
| 后端 API | `MISSING` | classify(position) 函数 + admin CRUD API 未实现；tenant 端 settings.py contact-rules API 待删 |
| DB schema | `MISSING` | 缺 `position_classification_levels` / `_categories` / `_keywords` 3 表 + `v_tenant_contact_classified` 视图（方案 A，B-03 拍板） |
| Worker | N/A | 不需要独立 worker |
| E2E | `MISSING` | — |
| **综合** | **MISSING** | from-scratch + 模块搬迁 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C3-G1 | 新建 3 张 position_classification_* 表 + `v_tenant_contact_classified` 视图（方案 A，B-03 拍板）| S | D-037 |
| C3-G2 | admin/contact-classification 页面（按原型实现） | M | D-037 |
| C3-G3 | classify(position) 函数：切词 + 集合交集 + 取最高等级 + 未命中不投递 | M | D-037 |
| C3-G4 | 删除 tenant/Settings/contact-rules 模块（双侧不兼容禁用） | S | D-037 / D-024 |
| C3-G5 | 业务方初始关键词清单导入（A级老板/创始人/采购、B级技术、X级销售/HR） | S | D-037 |
| C3-G6 | 邮件计划新建时自动调用 classify 取联系人 | S | D-037 / UC-08 |

**OpenSpec change**：`v3-contact-classification` (Wave 2)

---

### 2.4 C4 · 客户库私有操作（4 件套：UC-21 调分 / UC-22 备注 / UC-23 标签 / D-020 群组管理；D-022 已确认必做）

> **业务目标**：tenant Companies 详情 Drawer 提供 4 个编辑入口。
> **codex 修订**（B-02 / H-02 2026-05-06）：① 4 件套不再叫"UC-21~24"——D-033 已取消 UC-24 主联系人；第 4 件套是 D-020 群组管理。② 4 件套后端不是统一 PARTIAL——UC-21 调分后端 + DB 都 MISSING，需先补；UC-22/23/D-020 后端已 PASS。

| 层 | UC-21 调分 | UC-22 备注 | UC-23 标签 | D-020 群组 |
|---|:-:|:-:|:-:|:-:|
| 原型 | ✅ | ✅ | ✅ | ✅ |
| 前端代码 | 🔴 MISSING | 🔴 MISSING | 🔴 MISSING | 🟡 部分（行内入口） |
| **后端 API** | **🔴 MISSING**（patch API 仅更新 notes/tags/business_status）| ✅ PASS | ✅ PASS | ✅ PASS（groups + group_members 服务齐全）|
| **DB schema** | **🔴 MISSING**（tenant_companies 无调分字段）| ✅ | ✅ | ✅ |
| E2E | 🔴 | 🔴 | 🔴 | 🔴 |
| **综合** | **MISSING** | PARTIAL | PARTIAL | PARTIAL |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| **C4-G0A** 🆕 | DB：tenant_companies 加调分字段（建议 `score_adjustment int` ±20 + `score_adjusted_at` + `score_adjusted_by` + `score_adjust_reason text`，**不直接覆盖 total_score 保留模型分**）| S | UC-21 / D-022 / codex B-02 |
| **C4-G0B** 🆕 | 后端：扩展 `PATCH /prospects/{id}` 支持 score_adjustment 字段 + 审计写入 | S | UC-21 / B-02 |
| **C4-G0C** 🆕 | scoring worker：等级映射时 `final_score = total_score + score_adjustment`（兜底约束 ±20） | S | UC-21 / D-039 |
| C4-G1 | tenant/Companies Drawer 评分调整表单（按原型 `scoreAdjEdit`） | S | UC-21 / D-022 |
| C4-G2 | tenant/Companies Drawer 私有备注 textarea（按原型 `noteEdit`） | S | UC-22 / D-022 |
| C4-G3 | tenant/Companies Drawer 私有标签 add/remove（按原型 `tagsEdit`） | S | UC-23 / D-022 |
| C4-G4 | 批量加入群组（按原型 `showBatchAddGroup` + 加入群组 Modal） | S | UC-19 / D-020 |
| C4-G5 | 拉黑/取消拉黑入口（[`03-r1-readiness UC-20`](03-r1-readiness-matrix.md) 已 PASS，仅样式对齐原型） | S | UC-20 |

**OpenSpec change**：`v3-tenant-companies` (Wave 2)

---

### 2.5 C5 · 客户库 10 项筛选（D-038）

> **业务目标**：客户列表 + 精选列表共用同一筛选组件（多选 OR：国家/行业/产品标签/数据来源 + 档位筛：成立时间/注册资金/规模/进出口额/次数/联系人数量）。

| 层 | 状态 | 证据 |
|---|:-:|---|
| **原型** | `PASS` | `tenant-companies.html` + `tenant-curated-customers.html` 含 10 项筛选 UI |
| 前端代码 | `MISSING` | 当前 Companies/index.tsx 无 10 项筛选组件 |
| 后端 API | `MISSING` | filter API 未支持 9 个新维度 |
| **DB schema** | `MISSING` | clean_companies +11 字段（见 C1-G4：D-038 9 + D-039 2） |
| Worker | `PARTIAL` | cleanup 时需把 9 字段映射到 clean_companies；product_tags 需 AI 回填 |
| E2E | `MISSING` | — |
| **综合** | **MISSING** | 跨 DB / API / UI 三层 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C5-G1 | clean_companies +11 字段（合并到 C1-G4：D-038 9 个 + D-039 2 个） | — | D-038 / D-039-X.1 |
| C5-G2 | cleanup_service 9 字段映射 | M | D-038 |
| C5-G3 | product_tags AI 回填（基于公司描述/产品） | M | D-038 |
| C5-G4 | 后端 filter API 支持 10 维多选 OR + 档位筛 | M | D-038 |
| C5-G5 | 前端筛选组件（共用 Companies + CuratedCustomers） | M | D-038 |

**OpenSpec change**：`v3-tenant-companies` (Wave 2)

---

### 2.6 C6 · 默认评分模板（D-039 + D-039-X.1）

> **业务目标**：admin 配按行业的评分模板（含维度/档位/分值/默认权重，PCB 7 维），租户**仅调权重**。等级 S/A/B/C/D 阈值固定。

| 层 | 状态 | 证据 |
|---|:-:|---|
| **原型** | `PASS` | `admin-scoring-templates.html` + `tenant-settings-scoring.html` |
| 前端代码 | `PARTIAL` | admin/ScoringTemplates 已有；tenant Settings/Scoring 还能配规则（应改为只调权重）|
| 后端 API | `PARTIAL`（codex M-03 精确化）| **admin platform 模板**：已有 industry 字段查询雏形（`admin_config_service.py:330,357`）；**tenant 权重分离**：未实现；**D-039 PCB 7 维默认模板**：未实现 |
| **DB schema** | `MISSING` | `scoring_templates` 按行业模板需对齐 + 新建 `tenant_scoring_weights` 表（租户级权重覆盖）；clean_companies +2 字段（factory_type / has_china_pcb_supplier，合并 C1-G4）|
| Worker (scoring) | `WORKER-NOT-DEPLOYED` | 代码 ready，未部署到 Sealos |
| E2E | `MISSING` | — |
| **综合** | **REWRITE** | 按行业 + 模板/权重分离 = 大改 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C6-G1 | scoring_templates 表加 industry 字段 + tenant_scoring_weights 表 | S | D-039 |
| C6-G2 | factory_type LLM 推断（cleanup 时调 OpenRouter） | M | D-039-X.1 |
| C6-G3 | has_china_pcb_supplier 反推默认 true | S | D-039-X.1 |
| C6-G4 | admin/ScoringTemplates 按行业 UI（PCB 7 维 + 维度/档位/分值/默认权重） | M | D-039 |
| C6-G5 | tenant/Settings/Scoring 改为"仅调权重"（删除规则配置） | S | D-039 |
| C6-G6 | scoring worker 等级映射 + 兜底（档位外 / 缺失 = 0 分） | M | D-039 |
| C6-G7 | scoring worker 部署到 Sealos | S | C8 共用 |

**OpenSpec change**：`v3-tenant-companies` (Wave 2)

---

### 2.7 C7 · 邮件投递端到端（R-3 + UC-25~29）

> **业务目标**：配域名 → 创建邮件计划 → 真实发送 → 状态追踪 全链路。EngageLab 通道 + 租户自有域名 + 平台预热档位约束。

| 层 | 状态 | 证据 |
|---|:-:|---|
| **原型** | `PASS` | `tenant-send-plans*.html` + `tenant-email-monitor.html` + `admin-customers.html` 域名 Tab + `admin-warmup-rules.html` 全部齐全 |
| 前端代码 | `PARTIAL` | tenant/SendPlans/EmailMonitor 已有；admin 域名 Tab 缺"添加域名调 EngageLab" + "触发验证按钮" + "DNS 一键复制" |
| 后端 API | `PARTIAL` | sending 接 EngageLab 已写；UC-05 域名验证流程未实现；UC-25 目标策略 3 选 1 UI 已删，只留群组（D-033） |
| DB schema | `PARTIAL` | emails / email_events / domain_warmup_status 表在；emails 表当前为 0 行（D-018 from-scratch） |
| **Worker (sending)** | `WORKER-NOT-DEPLOYED` | 代码就绪，未部署；emails 表空 = 实际从未跑通 |
| E2E | `MISSING` | 必须等 worker 部署 + 域名验证 + 真实发件 |
| **综合** | **PARTIAL → MISSING** | 投递链路实际 0 邮件 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C7-G1 | admin 创建租户 Modal 加"发件域名 + 起始预热档位" 2 字段 + 事务建 domain_warmup_status | S+M | D-031 |
| C7-G2 | admin 域名 Tab：添加域名 API 改调 EngageLab Domain API 写 SPF/DKIM/DMARC | M | D-002 / D-024 |
| C7-G3 | admin 域名 Tab：触发验证 API + 前端按钮 + 状态轮询 | M | D-002 / D-024 |
| C7-G4 | admin 域名 Tab：DNS 记录"一键复制" clipboard 按钮 | S | D-028 |
| C7-G5 | sending worker 部署到 Sealos | S | C8 共用 |
| C7-G6 | EngageLab API_USER 配置 + 1 测试租户首发拨测 | S | D-018 |
| C7-G7 | UC-25 邮件计划新建时自动按 UC-08 / classify 规则筛联系人 | S | D-033 / D-037 |
| C7-G8 | emails 表写入 + 状态回写（联系人级 4 态：未开始/投递中/投递完成/已取消） | M | UC-27 |
| C7-G9 | 预热档位限速逻辑（sending worker 受 domain_warmup_status.daily_limit 约束） | M | D-013 |
| **C7-G10** 🆕 | emails 表加追踪字段（first_opened_at / open_count / soft_bounce / invalid_email / report_spam / unsubscribe）+ 建 email_events 表 | S | **D-041** |
| **C7-G11** 🆕 | sending worker 调 EngageLab 设 `open_tracking=true` + 接入 EngageLab webhook（opens / bounces / spam / unsubscribe）+ 签名校验 + 兜底 API 拉取 | M | **D-041** |
| **C7-G12** 🆕 | tenant EmailMonitor 6 指标接 EngageLab 回写（按 `mockup tenant-email-monitor.html`）+ 详情时间轴 + 退信原因 tag | M | **D-041** |

**OpenSpec change**：`v3-email-delivery` (Wave 2)

> **D-041 影响**（2026-05-06 撤销 N-08 / N-09）：开信追踪 + 退信记录 V3 必做；本能力域 +1.5-2 天工作量。

---

### 2.8 C8 · Worker 部署 + alembic 升级（R-4 / D-006）

> **业务目标**：4 个 worker（collection-scheduler / collection / scoring / sending） + cleanup_service（C1 新增）部署到 Sealos；alembic 0006 → 0013 升级 + D-008 重构迁移。

| 层 | 状态 | 证据 |
|---|:-:|---|
| 原型 | N/A | 部署层无原型 |
| 前端代码 | N/A | — |
| 后端 API | `PASS` | 4 worker 代码已实现（[`03-r1-readiness §3.1`](03-r1-readiness-matrix.md)） |
| DB schema | `MIGRATION-BLOCKED` | alembic 真值停在 0006，迁移 0007~0013 + D-008 重构未跑 |
| **Worker** | `WORKER-NOT-DEPLOYED` | 容器构建配置 + Sealos 部署清单未提供 |
| E2E | `MISSING` | 部署完才能 E2E |
| **综合** | **PARTIAL** | 代码全 ready，部署 + 迁移阻塞 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C8-G1 | Dockerfile + 容器构建（4 worker + cleanup_service） | M | R-4 |
| C8-G2 | Sealos 部署清单（k8s yaml / 调度配置 / 健康检查） | M | R-4 |
| C8-G3 | alembic 0006 → 0013 升级 + staging 验证 | S | D-017 |
| C8-G4 | D-008 重构迁移（含数据迁移 + 回滚预案） | M | D-008 |
| C8-G5 | worker 监控 / 日志 / 重试 / 幂等（V3-WORKER-001/002 验收） | M | R-4 |

**OpenSpec change**：`v3-data-foundation` (Wave 1)

---

### 2.9 C9 · EngageLab 真接入 + 测试租户首发

> **业务目标**：在 Sealos 实环境用 t-019dc236 / t-019dc238 跑通完整闭环（采集 → 邮件投递 → 真实收件箱）。

| 层 | 状态 | 证据 |
|---|:-:|---|
| 原型 | N/A | 验收层 |
| 前端代码 | `PASS` | 全链路 UI 已就绪（待 C4~C7 实施完成） |
| 后端 API | `PARTIAL` | 沿用 C7 |
| DB schema | `PARTIAL` | 沿用 C1 / C7 |
| Worker | `WORKER-NOT-DEPLOYED` | 沿用 C8 |
| **E2E** | `MISSING` | 需所有依赖完成 |
| **综合** | **MISSING** | 终验收 |

**子项缺口**：

| # | 缺口 | 工作量档 | 关联决策 |
|---|---|:-:|---|
| C9-G1 | EngageLab 账号 + 域名 + API_USER 配置 | S | D-002 / D-018 |
| C9-G2 | 1 个真实租户域名 DNS 配置（线下） | S | D-031 |
| C9-G3 | 1 个真实关键词全链路：配 → 反推 → 客户库 → 邮件计划 → 真实发件 | M | E2E |
| C9-G4 | A/B 双租户隔离测试（V3-AUTH-001 / V3-COL-007） | S | D-024 |
| C9-G5 | 失败/重试场景（V3-WORKER-001/002） | S | R-4 |

**OpenSpec change**：`v3-email-delivery`（验收用例归此 change）

---

## 3. 综合状态矩阵

> 9 能力域 × 6 层 × 4 个 OpenSpec change 一图总览。

| 能力 | 原型 | 前端 | 后端 | DB | Worker | E2E | 综合 | OpenSpec change | Wave |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|:-:|
| C1 数据库重构 | — | — | 🔴 | 🔴 | 🔴 | — | **MISSING** | v3-data-foundation | 1 |
| C2 KeywordMaster | ✅ | 🟡 | 🔴 | 🔴 | 🔴 | 🔴 | **MISSING** | v3-collection-pushback | 2 |
| C3 联系人分类 | ✅ | 🔴 | 🔴 | 🔴 | — | 🔴 | **MISSING** | v3-contact-classification | 2 |
| C4 私有操作 | ✅ | 🔴 | 🟡 | ✅ | — | 🔴 | **PARTIAL** | v3-tenant-companies | 2 |
| C5 10 项筛选 | ✅ | 🔴 | 🔴 | 🔴 | 🟡 | 🔴 | **MISSING** | v3-tenant-companies | 2 |
| C6 评分模板 | ✅ | 🟡 | 🟡 | 🔴 | ⚙️ | 🔴 | **REWRITE** | v3-tenant-companies | 2 |
| C7 邮件投递 | ✅ | 🟡 | 🟡 | 🟡 | ⚙️ | 🔴 | **PARTIAL** | v3-email-delivery | 2 |
| C8 部署 + 迁移 | — | — | ✅ | ⚙️ | ⚙️ | 🔴 | **PARTIAL** | v3-data-foundation | 1 |
| C9 真接入首发 | — | ✅ | 🟡 | 🟡 | ⚙️ | 🔴 | **MISSING** | v3-email-delivery | 2 |

> 图例：✅ PASS / 🟡 PARTIAL / 🔴 MISSING / ⚙️ WORKER-NOT-DEPLOYED / — N/A

---

## 4. 重点检查清单（来自 ChatGPT §8）

> 用户签字前必须逐条核对，避免"过度乐观陷阱"。

- [ ] 采集是否只是配置，而不是真实采集 → 当前真实状态：**未跑通**（worker 未部署 + alembic 卡 0006）
- [ ] worker 是否真的处理任务，而不是只存在服务文件 → **未部署**（C8）
- [ ] 邮件是否真实发送，而不是只保存配置 → **emails 表 0 行**（C7 / D-018）
- [ ] 状态是否回写 → **未验证**（依赖 sending 实跑）
- [ ] tenant_id 是否贯穿关键表和查询 → **PASS**（[`03-r1-readiness §3.4`](03-r1-readiness-matrix.md)）
- [ ] 是否有幂等和重试 → **PARTIAL**（cleanup_service 含 lease + 重试，sending 待验证）
- [ ] 是否有错误日志 → **未验证**
- [ ] Sealos 上的服务是否对应当前代码 → **未对齐**（4 worker 不在 Sealos 部署清单）
- [ ] 把"代码存在"误判为"功能完成"→ **本审计已严格区分 6 层，不含此误判**
- [ ] 把"配置测试通过"误判为"E2E 通过"→ E2E 全部 MISSING，无此误判
- [ ] 把"docs 中的规划"误判为"已实现"→ 24 原型全部 ✅ 但代码侧老老实实标 🔴/🟡

---

## 5. 已知缺口（先验来自前期盘点）

| # | 描述 | 已映射到能力域 |
|---|---|---|
| **F1** | `backend/app/models/` 是空目录 — ORM 模型层缺位 | 影响 C1 / C7 全部数据访问 |
| **F2** | `scoring_jobs`（迁移 0003）/ `waimaotong_raw_contacts`（迁移 0012）未回写 schema.sql | C8-G3 alembic 升级时同步对齐 |
| **D5** | 前端无 `tests/` 或 `__tests__/` | 影响 V3-UI-001 验证；建议各 change 实施时补关键路径单测 |
| **B2** | `run_collection_scheduler.py` vs `run_collection_scheduler_worker.py` 命名近似 | C8-G2 Sealos 部署清单时澄清 |

---

## 6. 9 能力域 → 6-Slice → 5 OpenSpec change 三方映射

> 让 03-v3-delivery-plan 6-Slice 骨架与 9 能力域、5 OpenSpec change 三向对齐。

```
6 Slice (delivery-plan)        9 能力域 (本文件)              5 OpenSpec change
────────────────────────       ─────────────────             ─────────────────────
Slice 0 开发基线                C8 部署 + 迁移                v3-data-foundation
                                                              ├── alembic 升级
                                                              └── 容器化基线

Slice 1 真实采集闭环             C1 数据库重构                 v3-data-foundation
                                C2 KeywordMaster              v3-collection-pushback
                                                              ├── admin 启动按钮 (UC-10)
                                                              └── 反推 stage1+2

Slice 2 去重 + 租户隔离          C1 cleanup_service            v3-data-foundation
                                                              + v3-collection-pushback

Slice 3 真实邮件投递             C7 邮件投递端到端              v3-email-delivery
                                C9 真接入首发

Slice 4 Worker 可靠性             C8 + 各 worker 部署           跨 change（共用基础设施）

Slice 5 Sealos E2E 发布          C9 真接入首发                v3-email-delivery
                                                              （E2E 验收）

附加（非 Slice 直接对应）：
                                C3 联系人分类                 v3-contact-classification
                                C4 私有操作                   v3-tenant-companies
                                C5 10 项筛选                  v3-tenant-companies
                                C6 评分模板                   v3-tenant-companies
```

---

## 7. PM Review Checklist（用户签字前）

- [ ] §2 9 能力域每域综合状态准确
- [ ] §3 综合矩阵 9×6 状态符合实际
- [ ] §4 重点检查清单全部走过一遍
- [ ] §5 已知缺口都已映射到具体能力域
- [ ] §6 三方映射没有漏域 / 漏 change
- [ ] D-022 已确认（私有操作 UI V3 必做，已记入 C4）
- [ ] 综合状态用最弱层（短板原则），未把"原型已齐"当作"已实现"

签字行：

```
__________________________ (用户)   日期：__________
```

---

> **本文件不含**：具体天数估算（→ 03-v3-delivery-plan）、change 内部 task 拆分（→ openspec/changes/*/tasks.md）、E2E 用例细节（→ 04-v3-e2e-test-plan）。
