# §Q-009 · R-1 实现度对照表（33 UC vs 当前代码）

> **目的**：把 R-1（D-006 = Sealos 已部署 4 单元）实际实现到什么程度，按业务流 33 UC 逐个评估，作为 V3 范围裁剪的事实基础。
> **生成时间**：2026-05-05
> **数据来源**：
> - Backend Agent 扫 `backend/app/{api,services,workers,repositories}/`
> - Frontend Agent 扫 `frontend/apps/{tenant,admin}/src/pages/` + `packages/shared-api/`
> - 真实 schema 状态：[`schema-current-2026-05-05.md`](../inputs/database/schema-current-2026-05-05.md)（alembic 0006）
> **关联**：[`02-er-schema-divergence.md`](02-er-schema-divergence.md) §6 + [`04-open-questions.md`](../04-open-questions.md) Q-009

## 0. 状态枚举

| 状态 | 含义 | V3 工作量 |
| --- | --- | --- |
| **PASS** | API + UI + Worker（如适用）齐全且联通；R-1 已 ready | 0（仅验证） |
| **PARTIAL** | 主路径在，缺关键分支 / 错误处理 / 配置入口 | 小 |
| **SKELETON** | 文件存在但占位；happy path 都没跑通 | 中 |
| **MISSING** | 完全没找到 | 大（from-scratch） |
| **MIGRATION-BLOCKED** | 代码已实现但 alembic 0006 缺迁移导致跑不起来 | 跑迁移即可（D-017） |
| **WORKER-NOT-DEPLOYED** | 代码已实现但 4 worker 未部署（D-006） | 部署即可 |

## 1. 33 UC 综合状态表

> "Backend" 与 "Frontend" 两列表示该层独立状态；"综合状态"取**最弱环节**作为 UC 整体状态（短板原则）。

| UC | 名称 | Backend | Frontend | 综合状态 | V3 缺口（一句话） |
| --- | --- | --- | --- | --- | --- |
| UC-01 | 销售签约 | — | — | **N/A** | 线下流程，不进系统 |
| UC-02 | 运营创建租户 | PASS | PASS | **PASS** | ✅ 含默认评分维度 + 联系人规则初始化 |
| UC-03 | 租户首登 | PASS | PASS | **PASS** | ✅ Onboarding/Step1 含密码强度+验证 |
| UC-04 | 配 OpenRouter | PASS | PASS | **PASS** | ✅ 双入口含余额刷新+撤销 |
| UC-05 | **配发件域名（D-002 + D-024 修订）** | PARTIAL | PASS（admin 端） | **PARTIAL** | D-024 澄清：tenant 端无 UI 是设计而非缺口；缺的是后端调 EngageLab Domain API 做 DNS 验证的流程实现 |
| UC-06 | 配关键词 | PARTIAL | PASS | **PARTIAL** | 后端缺 KeywordMaster 跨租户判定（D-009 推迟） |
| UC-07 | 评分维度 | PASS | PARTIAL | **REWRITE** | 🟡 D-039 修订：admin 配模板 + 租户**仅调权重**；按行业分模板；PCB 行业 7 维含 PCB 供应商；clean_companies 加 factory_type + has_china_pcb_supplier；+3.5-4.5 天 |
| UC-08 | 联系人优先级规则 | PASS | PARTIAL | **REWRITE** | 🟡 D-037 重写：**整段从 tenant 端搬到 admin 端**；新增 4 张表 + admin/contact-classification 页面 + 删除 tenant/settings/contact-rules；+2 天工作量 |
| UC-09 | 邀请团队 | PASS | PASS | **PASS** | ✅ Admin + Tenant 双侧管理完整 |
| UC-10 | 运营启动首采 | PASS | **MISSING** | **MISSING** | 🔴 后端 API 完整 (`POST collection-keywords/trigger`)，前端 admin 端缺启动按钮 |
| UC-11 | 已收录关键词复用 | **MISSING** | — | **MISSING** | 🟡 D-009 = (A) 用户决策 V3 完整做：新建 keyword_master + UC-06 命中分支 + UC-11 fan-out（+3-4 天）|
| UC-12 | Worker 执行采集 | PASS | — | **WORKER-NOT-DEPLOYED** | 🟡 D-035 修订：V3 仅启用 tendata + lixiaoyun provider（外贸通推迟 V3.1+）；后端代码已全实现，worker 未部署 + alembic 0006 卡 0009 |
| UC-13 | 清洗去重 | PASS | — | **WORKER-NOT-DEPLOYED** | 🟡 cleanup_service 含 lease + 重试；同 UC-12 |
| UC-14 | 分发到租户 | PARTIAL | — | **PARTIAL** | 🟡 collection_task_keywords 链接逻辑在；无显式"分发到所有命中租户"流程（与 D-008 shared+sources 模型一致，分发隐含） |
| UC-15 | 运营查看采集进度 | PASS | PASS | **PASS** | ✅ Admin CollectionDashboard 完整 |
| UC-16 | 维护数据源凭证 | PASS | PASS | **PASS** | ✅ Admin DataSources 完整（含 D-016 多账号轮换） |
| UC-17 | 浏览客户列表 | PASS | PASS | **PARTIAL** | 🟡 D-038 修订：**新增 10 项筛选**（国家/行业/成立时间/注册资金/产品标签/公司规模/数据来源/进出口额/次数/联系人）；D-021/D-026 修订：删除"邮件状态"列；clean_companies 新加 8 字段 + 后端 filter API + 前端筛选 UI；+3.5-6 天 |
| UC-18 | 客户详情 | PASS | PARTIAL | **PARTIAL** | 详情 Drawer 缺评分/标签/备注的编辑入口 |
| UC-19 | 标记/取消精选 | PASS | PASS | **PARTIAL** | 🟡 D-020 群组模型 + D-038 精选列表共用 10 项筛选组件；Backend `prospect_status='selected'` vs 前端 `groups + group_members` 双轨实现 V3 时统一 |
| UC-20 | 拉黑客户 | PASS | PASS | **PASS** | ✅ 行内 Modal 带原因输入 |
| UC-21 | 调租户级评分 | PASS | **MISSING** | **MISSING** | 🔴 后端 API 完整（`prospects/update`），前端 Companies Drawer 缺评分表单 |
| UC-22 | 私有备注 | PARTIAL | **MISSING** | **MISSING** | 🔴 后端通过 jsonb payload，前端只展示不能编辑 |
| UC-23 | 私有标签 | PARTIAL | **MISSING** | **MISSING** | 🔴 同上 |
| UC-24 | 设主联系人 | PASS | **MISSING** | **OUT-OF-V3** | 🟢 D-033 取消：业务方修正"无主联系人概念"；后端 API + tenant_contacts.is_default 字段保留但 V3 不用；前端不补按钮 |
| UC-25 | 新建邮件计划 | PASS | PASS | **PARTIAL** | 🟡 D-033 修订：移除目标策略 3 选 1 UI（不再让租户选"主联系人/全部/自定义"）；目标自动按 UC-08 规则筛选；省一步向导 |
| UC-26 | 启动邮件计划 | PASS | PASS | **PASS** | ✅ start/pause/resume/cancel 按钮齐全 |
| UC-27 | Worker 发送邮件 | PASS | — | **WORKER-NOT-DEPLOYED** | 🟡 sending worker 代码已接 EngageLab API；worker 未部署 + emails 表空（D-018）→ 实际从未跑通 |
| UC-28 | 监控邮件计划 | PASS | PASS | **PASS** | ✅ 详情页含统计卡片+步骤+收件人+样本 |
| UC-29 | 暂停/取消计划 | PASS | PASS | **PASS** | ✅ 详情页按钮带确认 |
| UC-30 | 手动标已回复 | **MISSING** | SKELETON | **OUT-OF-V3** | 🟢 D-034 推迟 V3.1+：UC-30 完全不在 V3 范围；省 1 天工作量；emails.replied_at 字段保留但 V3 期间永远 NULL |
| UC-31 | 计划复盘 | PASS | PARTIAL | **PARTIAL** | 后端步骤级 KPI API 全；前端缺独立复盘报告/转化漏斗 UI |
| UC-32 | Tenant Dashboard | PARTIAL | PASS | **PARTIAL** | 后端 API 框架在，具体 widget 内容未细化 |
| UC-33 | 跨计划趋势 | PARTIAL | PARTIAL | **PARTIAL** | 后端粒度（日/周/月）未定义，前端缺 AI 分析展示 |

## 2. 综合统计

### 2.1 按状态分布

| 状态 | UC 数 | 占比（剔除 N/A） | UC 列表 |
| --- | --- | --- | --- |
| **PASS** | 12 | 38% | UC-02, 03, 04, 09, 15, 16, 17, 19, 20, 25, 26, 28, 29 |
| **PARTIAL** | 8 | 25% | UC-05, 06, 07, 08, 14, 18, 31, 32, 33 |
| **WORKER-NOT-DEPLOYED** | 3 | 9% | UC-12, 13, 27（代码 ready，等部署 + 迁移）|
| **MISSING** | 8 | 25% | UC-10, 11, 21, 22, 23, 24, 30 |
| **N/A** | 1 | — | UC-01 |
| **总计** | 32 + 1 | 100% | |

### 2.2 按业务阶段分布

| 阶段 | PASS | PARTIAL/WORKER 等 | MISSING | 评估 |
| --- | --- | --- | --- | --- |
| 0 销售（UC-01-02） | 1 | 0 | 0 | ✅ 完整 |
| 1 配置（UC-03-09） | 2 | 4 | 0 | 🟡 主路径在，UI 待打磨 |
| 2 采集（UC-10-16） | 2 | 3 | 2（UC-10 前端、UC-11） | 🟡 后端代码就绪；缺 admin 启动按钮 + alembic 升级 + worker 部署 |
| 3 客户库（UC-17-24） | 3 | 1 | 4 | 🔴 私有状态字段操作 UC-21~24 全缺前端 UI |
| 4 邮件（UC-25-30） | 4 | 1 | 1（UC-30）| 🟡 R-3 D-018 已确认从 0 起；UC-30 公司级中断未实现 |
| 5 复盘（UC-31-33） | 0 | 3 | 0 | 🟡 UI 全在，细节未完善 |

## 3. 重要发现（修正之前判断）

### 3.1 ✅ 前端没用 mock 数据

之前 memory 记录的"前端用 mock 数据"**已过时**。当前代码：

- `packages/shared-api/src/client.ts` 真实 axios + TanStack Query 5 + Zustand 5
- 整个前端**无 mock 数据**（agent 用 grep 验证 `mock` 关键字结果为空）
- 这意味着**只要后端 API 上线 + worker 部署，前端立即可用**

→ **D-006 的 R-1 实际比想象的更接近 ready**：4 个单元已部署 + 前端真接 API + 后端 API 大部分齐全。

### 3.2 ⚠️ R-1 ready 但 R-2/R-3 真正阻塞点是 4 个

V3 实施真正要做的事：

| 阻塞 | 描述 | 工作量 |
| --- | --- | --- |
| **B-1 alembic upgrade** | 0006 → 0013（D-017） | 中（迁移 + staging 验证） |
| **B-2 4 个 worker 部署到 Sealos** | collection-scheduler / collection / scoring / sending | 中（容器构建 + 部署） |
| **B-3 EngageLab 真实接入** | 域名验证流程 / API_USER 配置 / 实际首发 | 中（D-018 from-scratch） |
| **B-4 前端补 5 个 UC 的 UI** | UC-10（admin 启动按钮）+ UC-21~24（Companies Drawer 编辑入口）+ UC-30（手动标已回复） | 小（5 个 form / button，每个 0.5-1 天） |

**B-4 工作量最小但影响验收最大**——因为 UC-21~24 是租户日常操作的核心。

### 3.3 🔴 UC-30 公司级中断完全未实现

业务流 §4.2 Q17 / §4.7 / UC-30 都明确"任一联系人回复 → 整公司其他联系人停发"，但：
- 后端无 `mark_email_replied` API 端点
- 后端无 company_level_interrupt 业务逻辑
- 前端无操作入口
- emails 表预留 `replied_at` 字段（迁移 0006 已建）

是否做？决策（[`04-open-questions.md`](../04-open-questions.md) 拟新增 D-020 / D-021）：
- **(a)** V3 实施完整 UC-30（含公司级中断逻辑）
- **(b)** V3 仅实现"标记已回复"按钮（不做公司级中断）→ 后续 V3.1
- **(c)** V3 暂不做 UC-30，业务流 Q17 推迟

### 3.4 ✅ UC-19"精选" = "CuratedCustomers 群组"——D-020 已决策

用户 2026-05-05 澄清：**精选 = 群组功能**（CuratedCustomers 前端页面 = 把干净数据放入群组的 UI）。

数据流（D-025）：
```
原始数据(raw) → 清洗合并 → 干净数据(shared_*) → 租户视图(tenant_companies/_contacts)
                                                       ↓
                                                   评分等级
                                                       ↓
                                              租户筛选 → 加入群组（= 精选）
```

**实现**：精选用 `groups` + `group_members` 多对多模型；不需要 `is_curated` 字段（**D-011 取消**）。

业务流 §3.5 Q12 字段 ① "是否精选 = 加入 /curated-customers 列表"——与该模型一致，只是用户进一步明确了"精选 = 群组"等价。

⚠️ **V3 实施时需核对**：Backend agent 报告 UC-19 用 `prospect_status='selected'`（单字段），前端用 `groups + group_members`（多对多）——可能是双轨实现的历史遗留，V3 时统一到群组模型。

## 4. R-1 已 ready 的功能精确清单（用户验收用）

> 这些 UC 现状是 PASS，部署在 Sealos 4 单元（backend + admin + tenant + DB）就能用：

| 阶段 | UC | 名称 |
| --- | --- | --- |
| 0 | UC-02 | 运营创建租户 |
| 1 | UC-03 | 租户首登 |
| 1 | UC-04 | 配 OpenRouter API key |
| 1 | UC-09 | 团队邀请 |
| 2 | UC-15 | 采集 dashboard（**但无真实数据**，因 worker 未跑） |
| 2 | UC-16 | 数据源凭证管理 |
| 3 | UC-17 | 客户列表（**但无真实数据**） |
| 3 | UC-19 | 精选群组（CuratedCustomers） |
| 3 | UC-20 | 拉黑 |
| 4 | UC-25 | 新建邮件计划（**但发不出去**） |
| 4 | UC-26 | 启动邮件计划（同上） |
| 4 | UC-28 | 监控（同上） |
| 4 | UC-29 | 暂停/取消 |

> 注：UC-15/17/25/26/28 标"但无真实数据"——意味 UI 跑得通但需要 worker 跑起来才能验收完整闭环。

## 5. V3 实施工作量重新估算（基于 R-1 实际状态 + D-008 = B 重构）

> 用户 2026-05-05 决策 D-008 = B（重构 6 raw + 2 clean）后**工作量翻倍**：原 9-15 天 → 现 **14-25 天**。

| 类别 | 子项 | 工作量 |
| --- | --- | --- |
| **数据库** | alembic 0006→0013 升级（D-017） | 0.5 天（含 staging） |
| **数据库** | 加 `tenant_companies.matched_keywords[]`（D-012；D-011 已取消）| 0.5 天 |
| **🔴 数据库重构（D-008=B + D-035 修订）** | 拆 shared_* + 建 **4 raw**（tendata + lixiaoyun，外贸通推迟）+ 2 clean 表 + alembic 4-6 迁移 + 数据迁移 | **2-4 天**（D-035 省 1 天）|
| **🔴 cleanup_service worker（D-008=B 新增）** | 新建消费 cleanup_queue 的 worker，含 raw → clean UPSERT、跨源合并、励销云不入 clean 规则、Phase 1.5 D4 索引设计 | **2-4 天** |
| **🟡 KeywordMaster + UC-11（D-009=A 新增）** | 新建 keyword_master 表 + 拆 collection_keywords + UC-06 命中分支 + UC-11 fan-out worker + UC-12/14 改写 | **3-4 天** |
| ~~UC-30 仅联系人级标记~~ → **D-034 推迟 V3.1+** | 不做 | **0 天**（省 1 天） |
| **🟢 UC-31/32/33 推迟 V3.1+（D-032）** | 不做完整复盘 widget / Dashboard 多维 / 趋势折线 | **0 天**（省 1.5-2 天）|
| **🟡 联系人职位分类规则（D-037 新增）** | 4 张表 + admin 页面 + classify(position) 函数 + 业务方初始关键词清单 | **+2 天** |
| **🟡 客户列表 10 项筛选（D-038 新增）** | clean_companies 新加 9 字段 + cleanup 映射 + product_tags AI 回填 + 后端 filter API + 前端筛选 UI（共用客户列表 + 精选列表）| **+3.5-6 天** |
| **🟡 默认评分规则（D-039 + D-039-X.1）** | clean_companies 加 factory_type + has_china_pcb_supplier 2 字段 + admin 评分模板管理（按行业）+ 租户调权重 UI + scoring worker + 等级映射 + 兜底 + **factory_type LLM 推断 + has_china_pcb_supplier 反推默认 true** | **+4-5.5 天** |
| **部署** | 4 worker 容器构建 + Sealos 部署 | 1-2 天 |
| **配置** | EngageLab 接入 + 1 个测试租户域名验证（D-002 架构 C） | 1 天 |
| **前端 UI** | UC-10 admin 启动按钮 | 0.5 天 |
| **前端 UI** | UC-21~24 Companies Drawer 编辑入口（4 个表单） | 1.5 天 |
| **前端 UI** | UC-30 邮件计划详情手动标已回复按钮（取决于 D-020/D-021）| 0.5-2 天 |
| **后端** | UC-30 mark_email_replied API + 公司级中断（取决于 D-020/D-021） | 0-3 天 |
| **后端** | UC-05 域名验证流程（接 EngageLab Domain API）| 1-2 天 |
| **测试** | E2E：用 t-019dc236 / t-019dc238 跑全链路 | 1 天 |
| **缓冲** | bug 修复 / Sealos 部署调试 | 2 天 |
| **总计** | | **21.5-36.5 天**（D-032/033/034/035 省 5-6 天 - D-037 加 2 天 - D-038 加 3.5-6 天 - D-039+X.1 加 4-5.5 天）|

> D-008=B 重构 + D-009=A UC-11 完整 + UC-30/31/32/33 推迟 V3.1+ → 在原 9-15 天基础上**新增 6-12 天**。
> 用户决策方向：
> - 数据管道核心做完整版（D-008 / D-009 / D-017）—— 长期可维护性优先
> - 业务侧"复盘 + 回复识别"全推迟 V3.1+（D-032 / D-034）—— 先把"采集 + 投递" 主链路上线，复盘等真实使用一段后再做
> - 简化租户创建 + 域名配置流程（D-030 / D-031）—— 运营效率优先

## 6. 待用户拍板（新增 / 修订）

| # | 决策 | 来源 | 影响 |
| --- | --- | --- | --- |
| **D-020** | 业务流"精选" = 前端"CuratedCustomers 群组"吗？是 → UC-19 PASS；否 → 需补 is_curated 字段 + 简单"加入精选"开关 | §3.4 | UC-19 状态 + tenant_companies 字段 |
| **D-021** | UC-30 公司级中断 V3 范围 | §3.3 | 0.5-3 天工作量差异 |
| **D-022** | UC-21~24 私有状态前端 UI 是否在 V3 必做 | §3.2 | 1.5 天工作量 |
| **D-023** | UC-32/33 Dashboard / 趋势的 widget 详细规格谁来定 | §1 | 业务方需明确 widget 列表 |

详见 [`04-open-questions.md`](../04-open-questions.md) §J 表格末尾。
