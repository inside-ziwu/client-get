# V3 · 00 · Target Spec（完整规格 + 决策追溯）

> 📌 **想看纯业务目标？** → [`00-v3-business-goals.md`](00-v3-business-goals.md)（不含决策追溯、实现状态、工作量）
>
> 本文件给**开发实施者**看，含 23 项用户决策（D-001 ~ D-029）+ Phase 1.5 修订 + schema 重构标注 + 工作量估算 + 业务流条款失效记录等过程性内容。

> **状态**：v0.2 草稿（AI 从 [`docs/business-flow-DRAFT.md`](../../docs/business-flow-DRAFT.md) 提炼 + 2026-05-05 用户决策落地）
> **责任**：AI 起草 → 用户审 → 用户签字
> **Gate**：本文件未签字前，[Gate 1](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止下游所有阶段
> **关联 Open Questions**：[A1, A2, A3](../04-open-questions.md#a-范围与基线最关键)

## 0. 元数据

- **版本**：v0.2（含 2026-05-05 用户决策）
- **起草人**：Claude Code（基于 business-flow-DRAFT.md 2855 行提炼 + aoqi 仓库调研）
- **用户签字**：__未签字（v0.2 整体未签字；以下是已拍板的局部决策）__
- **输入材料**：
  - [`docs/business-flow-DRAFT.md`](../../docs/business-flow-DRAFT.md)（更新 2026-05-01，Q1-Q24 ✅ + UC-01~UC-33 ✅）
  - [`docs/spec-collection-module.md`](../../docs/spec-collection-module.md) v1.4（采集模块主规范）
  - [`docs/spec-tendata-provider.md`](../../docs/spec-tendata-provider.md) v1.0（腾道 Provider）
  - [`docs/spec-phase1.5-collection-pipeline-refactor.md`](../../docs/spec-phase1.5-collection-pipeline-refactor.md)（D1-D4 结构债）
  - [`docs/plan-phase1-implementation.md`](../../docs/plan-phase1-implementation.md)（T-1~T-6 任务拆分）
  - [`docs/plan-waimaotong-adapter.md`](../../docs/plan-waimaotong-adapter.md) v2
  - [`_control/inputs/reference-impl-aoqi.md`](../inputs/reference-impl-aoqi.md)（参考实现调研，**不是真源**）

## 0.A 已确认决策（2026-05-05 用户拍板）

> 按 [`AGENTS.md` §6 单一真源原则](../../AGENTS.md#6-单一真源原则最高优先级)，本节是 V3 真源。任何参考材料与本节冲突均**以本节为准**。

| # | 决策 | 影响 |
| --- | --- | --- |
| **D-001（D-008 后修订）** | V3 代码起点 = `backend/`，**完全独立**，**不复用** aoqi/sysdev-ft-marketing 代码；**允许在 V3 实施时重构 raw/clean 层**以对齐业务流数据管道（D-008 决策 B 派生）| aoqi 仅作参考蓝本；现有 13 个 alembic 迁移 + 4 个 worker 是 V3 基础；**业务流 ER 与 schema 偏差通过 V3 新迁移补齐**（D-008 选 B → 拆 shared_* / 建 raw 6 + clean 2 表 + 新建 cleanup worker）|
| **D-002** | 邮件发送 = **EngageLab + 租户自有发件域名（架构 C）**：发件 `From: @<租户域名>`，`Reply-To = From`，回信回到租户自己邮箱（不经平台 inbound）。**域名配置全流程在 admin 端**（D-024）：运营在 admin/Tenants 详情页添加域名 → EngageLab 自动生成 SPF/DKIM/DMARC 记录 → **运营配置该域名的 DNS 记录**（DNS 写入由平台运营负责，不要求租户 IT 操作）→ 运营在 admin 端点"验证" → 验证通过即可发。**租户端无任何域名 UI 入口**（不输入 SMTP 凭证，也不提交域名）| UC-05 改为"admin 端域名验证流程"；§9 复用 `domain_warmup_status`（D-013）；**回信路径见 D-007（架构 C 维持）** |
| **D-004** | 一个租户支持 **N 个发件域名** | `tenant_email_domains` 是 1:N 关系 |
| **D-005** | 邮件 `Reply-To` **默认 = `From`**（同一邮箱收发） | UI 无 Reply-To 输入项；sending worker 默认省略该 header |
| **D-006** | V3 R-1 起点 = Sealos 已部署 4 单元（`clientget-backend` + `admin` + `tenant` + PostgreSQL） | 4 个 worker（collection-scheduler / collection / scoring / sending）+ EngageLab 集成是 V3 必补 |
| **D-007** | **维持 D-002 架构 C，放弃 EngageLab Inbound 自动检测**：回信回到租户自己邮箱（`Reply-To = From = 租户域名邮箱`）；业务流 §4.5 原样保留（**1.0 不做 IMAP / 仅 UI 手动标"已回复"**）；UC-30 手动标记保留 | EngageLab 仅用作"出口通道"（发件 + DKIM 验证），不做 inbound webhook；自动回复检测推迟到 V3.1+ |
| **D-017 ✅ = (B)** | 分两阶段升级（用户 2026-05-05 决策）| Stage 1：生产升 0006→0013（现有 7 迁移）+ smoke test；Stage 2：V3 新增重构迁移（D-008 拆 shared_*+建 6 raw+2 clean / D-009 keyword_master / D-012 matched_keywords / D-015 lixiaoyun_raw_*）；前置：pg_dump 完整备份 + 本地 docker staging 验证 + 0009 phase1 迁移源码 review + 回滚预案；派生子决策 D-017-B.1~4 |
| **D-018 ✅ = (A)** | R-3 邮件投递 = from-scratch 实施（用户 2026-05-05 决策）| Slice 3 标"从零实施"；含 sending worker 部署 + EngageLab API_USER/API_KEY 接入 + 至少 1 个测试租户域名通过验证 + 实发首封邮件给 t-019dc236 / t-019dc238 测试收件箱 |
| **D-019** | V3 E2E 测试租户 = 复用现有 active 租户 `t-019dc236` + `t-019dc238` | 跳过新建测试租户步骤；inputs/test-data 模板 A/B 字段直接填这两个 slug |
| **D-020** | "精选"概念分歧（业务流 = is_curated 字段 vs 前端 = 群组管理）| 决定 UC-19 状态 + tenant_companies 是否补 is_curated 字段；详见 [`03-r1-readiness-matrix.md`](03-r1-readiness-matrix.md) §3.4 |
| **D-021** | UC-30 公司级中断 V3 范围 | 工作量差异 0.5-3 天；详见 [`03-r1-readiness-matrix.md`](03-r1-readiness-matrix.md) §3.3 |
| **D-022** | UC-21~24 前端 Companies Drawer 编辑入口 V3 必做 | 1.5 天工作量；后端 API 已 ready 仅缺前端 Form |
| **D-023** | UC-32/33 widget 规格由业务方明确 | 业务流 §6 挂起项 |
| **D-024** | UC-05 配域名 = 仅 admin 端，tenant 端无任何 UI 入口（用户 2026-05-05 澄清） | UC-05 状态判定：admin 端 UI 已有 PASS，tenant 端 MISSING 不是缺口；后端 DNS 验证流程是 V3 实施重点 |
| **D-020 ✅** | "精选" = 前端 CuratedCustomers"群组"模型（用户 2026-05-05 澄清）| 不加 is_curated 字段（**D-011 取消**）；查 `group_members` 即知是否精选；业务流 §3.5 Q12 字段 ① "是否精选 = 加入 /curated-customers 列表"与该模型一致 |
| **D-011 ❌取消** | ~~tenant_companies.is_curated 加独立 bool 字段~~ | 由 D-020 取代：精选用 group_members 实现，不需要字段 |
| **D-025（D-008 后修订）** | V3 数据流模型 | 采集 → **6 张 raw 表**（waimaotong/tendata/lixiaoyun × companies/contacts，D-008 选 B）→ **cleanup_service worker** → **clean_companies / clean_contacts**（D-008 选 B 新建）→ 租户视图(tenant_*，按关键词分发) → 评分 → 租户筛选 → 加入群组（= 精选）|
| **D-008 ✅ = (B)** | **重构为业务流 6 raw + 2 clean 模型**（用户 2026-05-05 决策） | 拆 `shared_companies / shared_contacts / company_sources` → 建 6 raw + 2 clean = 8 张新表 + 新建 cleanup_service worker（~500 行）；Phase 1.5 D2/D3/D4 重新打开为 V3 必修；V3 工作量 9-15 → **14-25 天**；4 个子决策 D-008-B.1~4 派生待决策 |
| **D-009 ✅ = (A)** | **V3 完整做 UC-11 跨租户关键词复用**（用户 2026-05-05 决策） | 新建 `keyword_master` 表 + 拆 `collection_keywords` → `tenant_keyword(M:N keyword_master)`；UC-06 加"归一查 master 命中"分支；UC-11 fan-out 实现（master 历史 → 新租户立即可见）；业务流 §3.4 完整满足；V3 工作量 14-25 → **17-29 天**；4 个子决策 D-009-A.1~4 派生 |
| **D-010 ✅ = (A)** | 实际 Schema 命名为准（用户 2026-05-05 决策） | 业务流 ER 中 SendingPlanTarget / TenantEmailTemplate / EmailSendLog 等 3 处剩余命名按实际 schema（sending_plan_recipients / email_templates / emails+email_events）；V3 文档加注解释 |
| **D-012 ✅ = (A)** | matched_keywords jsonb 数组（用户 2026-05-05 决策）| `tenant_companies` + `clean_companies` 都加 `matched_keywords jsonb`（含 GIN 索引）；删 `tenant_companies.keyword_id` 单 FK；UC-17 按关键词筛选用 `@>` 查询；与业务流 §9.0 "M:N 优先数组"原则一致 |
| **D-013 ✅ = (A)** | 复用 domain_warmup_status（用户 2026-05-05 决策）| 不新建 tenant_email_domains；该表已含 spf_record/dkim_record/dmarc_record/verification_status/dns_verified_at 等 D-002 必需字段；admin 端域名管理 API 直接用此表；命名职责合一（域名生命周期 = EngageLab 验证 + 预热档位）|
| **D-014 ✅ = (A)** | emails.reply_* 字段保留 V3 不写入（用户 2026-05-05 决策）| 5 个回信字段（reply_message_id / reply_from_email / reply_subject / reply_body_text / reply_received_at）保留 schema；V3 default NULL；与 D-007 一致；未来 V3.1+ 接 Inbound 直接复用 |
| **D-015 ✅ = (i)（含 D-008-B.3）** | 励销云数据落 lixiaoyun_raw_* 走业务流原版（用户 2026-05-05 决策）| 建 `lixiaoyun_raw_companies` + `lixiaoyun_raw_contacts`（D-008=B 6 raw 模型完整）；cleanup_service 加规则 `source_type='lixiaoyun'` → 标 done **不入 clean_**（业务流 §2.5 ✅）；`competitor_companies` 表 V3 暂留，实施时评估去留 |
| **D-016 ✅ = (A)** | 多账号轮换已实现到 V3（用户 2026-05-05 决策）| `data_source_credentials` 含 rotation_order / current_day_used / current_day_reset_at / consecutive_error_count 字段已就绪；业务流 UC-16 异常 A3 "Phase 2" 标注过时；V3 启用现有字段实现轮换 |
| **D-021 ✅ = (Other)（D-034 修订）** | ~~UC-30 仅联系人级标记~~ → **D-034 整体推迟 V3.1+**（业务方 2026-05-05 二次修正）| UC-30 完全不在 V3；emails.replied_at V3 期间永远 NULL；UC-17 客户列表仍删除"邮件状态"列（D-021 该项保留）|
| **D-026 ✅** | 邮件状态粒度 = 联系人级（业务方对齐）| 业务流 §3.5 Q13（公司行聚合）/ §4.2 Q17（公司级中断）/ §4.6 末 5 态聚合优先级 / §4.7 Q22（公司级中断下游）**全部在 V3 范围内失效**；前置 §B 5 态聚合规则决策关闭（不需要） |
| **D-022 ✅ = (A)（2026-05-06 修订）** | V3 全做客户库私有操作 4 件套前端 Drawer 入口（用户 2026-05-05 决策；2026-05-06 二次确认 + B-02 修订）| 评分调整 + 备注 textarea + 标签 add/remove + **群组管理**（D-020 精选 = 群组；原"主联系人"D-033 已取消）；按 mockup `tenant-companies.html` 实现；UC-21 调分需先建 DB 字段（score_adjustment 不覆盖 total_score）+ 扩展 PATCH API + scoring final_score 计算（codex B-02）；UC-22/23/D-020 后端已 PASS；工作量 1.5 天 + UC-21 后端 0.5 天 |
| **D-023 ✅ = (a)** | AI 提议默认 widget 集（用户 2026-05-05 决策）| UC-32: 客户总览 / 来源分布 / 邮件累计 / AI 余额 / 最近活动 / 待处理 6 widget；UC-33: 计划列表 / 趋势折线图 / 筛选 3 widget；按业务流 §4.8 落地；V3 实施时如发现不足再迭代 |
| **D-027 ✅ = (a)** | EngageLab API_USER = 平台单账号全局（用户 2026-05-05 决策）| 所有租户域名挂在 1 个 EngageLab 账号下；`email_providers` 表 1 行；当租户量 ≥ 20 或某租户量极大时 V3.1+ 重新评估拆分 |
| **D-028 ✅ = (c)** | admin 端域名验证失败 = 完整诊断 + 一键复制 DNS（用户 2026-05-05 决策）| admin/Tenants 详情页域名管理：显示 SPF/DKIM/DMARC/MX 逐项验证状态 + 一键复制 EngageLab 给的 DNS 记录（供运营自己粘到 DNS 管理后台；DNS 写入由平台运营负责）；运营效率 |
| **D-029 ✅ = (A)（D-032 修订）** | 未表态 UC 在 V3，**但 UC-31/32/33 经 D-032 推迟**（业务方 2026-05-05 修正）| UC-04/07/08/09/17~24 在 V3；UC-31/32/33 推迟 V3.1+ |
| **D-030 ✅** | 明确 admin 创建表单维持现状（业务方 2026-05-05 确认；2026-05-06 据实修订）| 实际表单字段 = 租户名称 / 行业 / 联系人 / 联系电话 / 管理员邮箱 / 管理员姓名 / 管理员密码（**原本就无邀请邮件 + 临时密码字段**）；明确 V3 不增加邀请邮件链接 + 临时密码流程；账号信息线下交租户；UC-02/UC-03 措辞调整 |
| **D-031 ✅** | 域名 + 预热档位在创建租户时同步配置（业务方 2026-05-05 修正）| 修订 D-002/D-024：admin/Tenants 创建表单含"发件域名"+"起始预热档位"字段；UC-02 与 UC-05 合并到一个表单 |
| **D-032 ✅** | UC-31/32/33 推迟 V3.1+（业务方 2026-05-05 修正）| 修订 D-023 + D-029；V3 不做完整复盘 widget / Dashboard 多维 widget / 跨计划趋势；3 个页面 V3 上线时可极简版（UC-31 仅基础统计 / UC-32 重定向到 /companies / UC-33 不暴露入口）；省 1.5-2 天 |
| ~~**D-033** ⏳ 调研中~~ | ~~UC-24 设主联系人 + UC-25 目标策略~~ | **已被下方 D-033 ✅ = (A) 替代**（aoqi 调研已返回） |
| **D-034 ✅** | UC-30 整体推迟 V3.1+（业务方 2026-05-05 二次修正）| 修订 D-021；V3 不做手动标已回复 / 已回复状态识别 / 公司级中断；emails.replied_at V3 期间永远 NULL；序列按时间表完整推进；省 1 天工作量 |
| **D-033 ✅ = (A)** | UC-25 目标策略 = "按 UC-08 规则自动筛选"单一选项（业务方 2026-05-05 修正 + aoqi 调研参考）| UC-24 取消；UC-25 不让租户选目标策略，自动取该公司所有匹配 UC-08 优先级序列的联系人；后端借鉴 aoqi `v_buyer_contacts` 视图模式；业务流 §3.6 末段 / §4.1 Q15 / UC-24 整段失效；`tenant_contacts.is_default` 字段保留但 V3 不写入；前端 UC-25 移除目标策略选择 UI / UC-18 移除"设为主联系人"按钮；省 0.5 天 |
| **D-035 ✅** | 外贸通采集整体推迟 V3.1+（业务方 2026-05-05 三次修正）| V3 仅反推路径：励销云 stage 1（中国同行）+ 腾道 stage 2（海外买家反查）；waimaotong provider 不实现；D-008=B 6 raw 实际仅用 4 raw（tendata + lixiaoyun）；客户库 V3 期间全部精准客户（直采=0）；业务流 §2.1 路径 A / §2.7 外贸通 1000/天 / §3.3 直采标签 V3 不生效；省 2-3 天 |
| **D-036 ✅ = (A)** | 多步骤序列模型 = ClientGet 1 plan + N steps（aoqi 调研 + 用户 2026-05-05 决策）| 维持现有 schema（sending_plans + sequence_steps + sequence_enrollments）；不切换 aoqi N plan + linked 模型；与业务流 §4.2 Q16 + §9.8 ER 一致；D-034 后无回复中断 → 两模型功能等价；0 天工作量 |
| **D-037 ✅** | **联系人职位分类规则**（用户 2026-05-05 苏格拉底澄清落档）| 4 层模型：等级（admin 可增删 + is_sendable 开关）→ 类别 → 关键词；admin 单一权威配置（tenant 端 UC-08 整段删除）；匹配规则 = 词边界 + 大小写忽略 + 取最高等级；未命中 = 不投递；新增 4 张表 + 1 视图 `position_classification_*`；V3 上线前业务方需提供初始关键词清单；详细见 [`04-open-questions.md` §M](../04-open-questions.md)；+2 天工作量 |
| **D-038 ✅** | **客户列表 / 精选列表 10 项筛选**（用户 2026-05-05 苏格拉底澄清落档；2026-05-06 第 10 项更正 + D-039 档位修订）| clean_companies 新加 **9 字段**；档位筛选（成立时间/注册资金/公司规模/进出口额/次数/联系人数量）+ 多选 OR（国家/行业/产品标签/数据来源）；**档位与 D-039 评分一致**（D-039 Q2=a）；档位默认值见 [`04-open-questions.md` §N.4](../04-open-questions.md)；+3.5-6 天工作量 |
| **D-039 ✅** | **默认评分规则 7 维**（用户 2026-05-06 决策 b/a/b/加/a/a + D-039-X.1 字段填充策略）| 平台模板 + 租户**仅调权重**（Q1=b，业务流 UC-07 修订）；档位与 D-038 一致（Q2=a）；**按行业分模板**（Q3=b，PCB 维度仅 PCB 行业）；clean_companies 加 `factory_type` + `has_china_pcb_supplier` 2 字段（**11 字段总计**）；等级 S/A/B/C/D 阈值 `90/70/50/30`；档位外 / NULL 兜底 0 分；数据来源维度 V3 保留（Q6=a，全部 A 档）；7 维：工厂性质 / 工厂规模 / 进出口额 / 进出口次数 / 联系人（有采购）/ 数据来源 / PCB 供应商；**D-039-X.1**：factory_type 用 LLM 推断（cleanup_service 调 LLM 基于公司名/行业）+ has_china_pcb_supplier 反推路径默认 true；详细见 [`04-open-questions.md` §O](../04-open-questions.md)；+4-5.5 天工作量（含 LLM 推断）|
| **D-040 ✅** | **V3 范围限定 PCB 行业** + 移除复盘流程描述（用户 2026-05-06 修订）| business-goals §1 一句话目标删"复盘"；§2 服务谁改"PCB 外贸厂"；§4 流程闭环删"复盘"节点；D-039 行业分模板架构保留（多行业扩展预留）但 V3 期间只配 PCB 模板；非 PCB 行业租户 V3.1+ 再开放；工作量基本不变（D-032 已节省复盘工作）|
| **D-041 ✅** | **投递监控 6 项指标 V3 必做**（撤销 N-08 + N-09；用户 2026-05-06 决策）| 详 business-goals §5.4 投递监控；以原型 `_control/v3/mockups/tenant-email-monitor.html` 为准：发送量 / 送达率（含软退信 / 无效邮箱明细）/ 独立打开率（含开信追踪）/ 软退信 / 举报垃圾邮件 / 退订；EngageLab `open_tracking=true` + webhook 回写或 API 拉取；emails 表加字段 first_opened_at / open_count / soft_bounce / invalid_email / report_spam / unsubscribe + 新建 email_events 表；+1.5-2 天工作量 |
| **D-003** | 单一真源 = `_control/v3/00-v3-target-spec.md`；参考材料冲突由用户拍板，AI 不自决 | 见 [`AGENTS.md` §6](../../AGENTS.md#6-单一真源原则最高优先级) |

## 0.B V3 整体范围（用户 2026-05-05 口述 v0.3）

> 来源：用户口述。详细 UC 映射 / 验收标准 / Non-goals 收敛 待 v0.4。

V3 必须 ready 的 4 项：

| # | 范围项 | 状态 | 后续动作 |
| --- | --- | --- | --- |
| **R-1** | **Sealos 已部署 4 单元（backend + admin + tenant + DB）的功能全部 ready**（D-006） | 🟢 已澄清；🟢 已对照（Q-009 完成，详见 [`03-r1-readiness-matrix.md`](03-r1-readiness-matrix.md)）| **结论**：12 UC PASS / 8 UC PARTIAL / 3 UC WORKER 未部署 / 8 UC MISSING（其中 5 UC 仅缺前端 UI）。整体 V3 工作量 9-15 天 |
| **R-2** | **采集闭环 ready**：外贸通直采 + 励销云 stage 1 + 腾道 stage 2 反推 | ✅ 范围明确 | 对应业务流 UC-06、10、11、12、13、14、15、16 |
| **R-3** | **邮件投递流程 ready** | ✅ 范围明确 | 对应业务流 UC-25、26、27、28、29、30 + D-002 架构 C |
| **R-4** | **上线到 Sealos 应用和数据库** | ✅ 范围明确 | 对应业务流 §15 + V3-DEPLOY-001 |

> ⚠️ **R-1 阻塞**：必须先确认"线上已发布功能"是哪份代码 / 哪个环境，才能在 §2 Scope 收敛 33 UC 子集。

用户**未明确**的部分（[`04-open-questions.md`](../04-open-questions.md) §I 新增）：
- 配置类 UC（UC-04 OpenRouter / UC-07 评分维度 / UC-08 联系人优先级 / UC-09 团队邀请）—— 是否在 V3 范围内？
- 客户库浏览/操作类（UC-17~24 含私有备注/标签/精选/拉黑/调评分/主联系人）—— 是否在 V3 范围内？
- 复盘类（UC-31~33）—— 是否在 V3 范围内？

这些**默认按"v0.1 草稿命题"保留**（业务流 1.0 全部），等 R-1 澄清后再判断是否裁剪。

---

## 1. V3 Objective（一句话目标）

> **V3 完成意味着外贸厂老板（租户）可以在平台上完成完整的"采集 → 客户库 → 邮件营销 → 复盘"业务闭环**——首次配置完成后，租户从客户库勾选目标公司、新建邮件计划、按预热档位发送、手动标记回复、查看复盘，全程无需运营介入；运营只在两个节点参与：**租户创建**（UC-02）+ **首采启动**（UC-10）。

来源：业务流 §0、§10.2 业务流闭环（L2810-2822）

## 2. Scope（范围）

### 2.1 全部 33 个用例（UC-01 ~ UC-33）

> 来源：业务流 §8 用例图（L451-2292）。每个 UC 对应至少 1 个验收 ID（待写入 [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)）。

| 阶段 | UC | 用例 | Actor | V3 验收 ID（候选） |
| --- | --- | --- | --- | --- |
| 0 销售 | UC-01 | 销售签约（线下） | 销售 | — 不进系统验收 |
| 0 销售 | UC-02 | 运营创建租户 | 运营 | V3-AUTH-001 / V3-TENANT-001 |
| 1 配置 | UC-03 | 租户首次登录 | 租户 owner | V3-AUTH-002 |
| 1 配置 | UC-04 | 配置 OpenRouter API Key | 租户 OR 运营 | V3-CFG-001 |
| 1 配置 | ~~UC-05~~ | ~~配置 SMTP 发件邮箱~~ → **D-002 修订**：见 §16 #Q-002 | ~~租户~~ → 平台运营 | ~~V3-MAIL-001~~ → 改为运营管理 EngageLab 凭证 |
| 1 配置 | UC-06 | 配置关键词 | 租户 | V3-COL-001 |
| 1 配置 | UC-07 | 配置评分维度 | 租户 | V3-CFG-002 |
| 1 配置 | UC-08 | 配置联系人优先级规则 | 租户 | V3-CFG-003 |
| 1 配置 | UC-09 | 邀请团队成员 | 租户 owner | V3-CFG-004 |
| 2 采集 | UC-10 | 运营启动首采 | 运营 | V3-COL-002 |
| 2 采集 | UC-11 | 已收录关键词自动复用 | 系统 | V3-COL-003 |
| 2 采集 | UC-12 | 系统执行采集任务 | 系统 + 数据源 | V3-COL-004 |
| 2 采集 | UC-13 | 系统清洗去重合并 | 系统 | V3-COL-005 |
| 2 采集 | UC-14 | 系统分发到租户客户库 | 系统 | V3-COL-006 |
| 2 采集 | UC-15 | 运营查看采集进度 | 运营 | V3-COL-007 |
| 2 采集 | UC-16 | 运营维护数据源凭证 + **EngageLab 发件凭证（D-002 新加）** | 运营 | V3-COL-008、V3-MAIL-001（合并） |
| 3 客户库 | UC-17 | 浏览客户列表 | 租户 | V3-CRM-001 |
| 3 客户库 | UC-18 | 查看客户详情 | 租户 | V3-CRM-002 |
| 3 客户库 | UC-19 | 标记/取消精选 | 租户 | V3-CRM-003 |
| 3 客户库 | UC-20 | 拉黑客户 | 租户 | V3-CRM-004 |
| 3 客户库 | UC-21 | 调整租户级评分 | 租户 | V3-CRM-005 |
| 3 客户库 | UC-22 | 添加/编辑私有备注 | 租户 | V3-CRM-006 |
| 3 客户库 | UC-23 | 添加/移除私有标签 | 租户 | V3-CRM-007 |
| ~~3 客户库~~ | ~~UC-24~~ | ~~设置主联系人~~ | — | **已取消（D-033 ✅）**：业务方 2026-05-05 修正"无主联系人概念"；UC-24 整段失效；`tenant_contacts.is_default` 字段保留但 V3 不写入 |
| 4 邮件 | UC-25 | 新建邮件计划 | 租户 | V3-MAIL-002 |
| 4 邮件 | UC-26 | 启动邮件计划 | 租户/系统 | V3-MAIL-003 |
| 4 邮件 | UC-27 | 系统执行邮件发送 | 系统 + SMTP | V3-MAIL-004 |
| 4 邮件 | UC-28 | 监控邮件计划状态 | 租户 | V3-MAIL-005 |
| 4 邮件 | UC-29 | 暂停/取消邮件计划 | 租户 | V3-MAIL-006 |
| 4 邮件 | UC-30 | 手动标"已回复" | 租户 | V3-MAIL-007 |
| 5 复盘 | UC-31 | 查看邮件计划复盘 | 租户 | V3-RVW-001 |
| 5 复盘 | UC-32 | 查看 Tenant Dashboard | 租户 | V3-RVW-002 |
| 5 复盘 | UC-33 | 跨计划趋势分析 | 租户 | V3-RVW-003 |

### 2.2 必修结构债（来自 Phase 1.5 D1-D4）

> 来源：[`docs/spec-phase1.5-collection-pipeline-refactor.md`](../../docs/spec-phase1.5-collection-pipeline-refactor.md)、业务流 §5 差距清单（L412-426）

| ID | 缺口 | V3 验收 ID |
| --- | --- | --- |
| D1 | 多租户关联缺口（第 2 个租户加同关键词时拿不到完整数据） | V3-COL-006（UC-14 异常 A1） |
| D2 | `tendata_raw_contacts` / `lixiaoyun_raw_contacts` 未独立成表（嵌在 raw_payload JSON） | V3-COL-005 / V3-DB-001 |
| D3 | `clean_contacts` 干净联系人库未建（业务必需） | V3-COL-005 / V3-DB-002 |
| D4 | cleanup_queue 双唯一索引冲突丢数据 | V3-COL-005（UC-13 异常 A2） |

## 3. Non-goals（明确不做）

> 来源：业务流文档明确标 "1.0 不做" 的所有项

1. **重采机制**：1.0 完全不做（既不自动也不手动）— 来源 §1.4（L48）
2. **B2 反推路径**：外贸通反推（`reverse_lookup`）1.0 不做、未来加 — 来源 §2.1（L66）
3. **CRM 销售漏斗**：潜在→接触→谈单→成交 不做，产品聚焦"邮件营销进度" — 来源 §3.5（L231）、§4.8（L409）
4. **「选中」字段持久化**：临时 UI 交互态不入库 — 来源 §3.5（L230）
5. ~~**IMAP 自动检测**~~ → **D-034 整体推迟 V3.1+**：UC-30 手动标"已回复"也不做；客户回信回租户邮箱（不经平台），平台无操作入口；emails.replied_at V3 期间永远 NULL
6. ~~**邮件状态：投递失败/退信**：1.0 不显式记录退信~~ → **D-041 撤销（2026-05-06）**：以 EngageLab 软退信 / 无效邮箱 / 举报垃圾 / 退订回写做送达分级；emails 加 soft_bounce / invalid_email / report_spam / unsubscribe 字段；详 business-goals §5.4 投递监控
7. ~~**邮件状态：已打开未回复**：不做开信追踪~~ → **D-041 撤销（2026-05-06）**：EngageLab `open_tracking=true` 做开信追踪；emails 加 first_opened_at / open_count 字段；不嵌平台自有像素（仍由 EngageLab 处理）
8. ~~**"已回复"事件下游反应**~~ → **D-034 推迟 V3.1+**（配套 UC-30 不做）
9. **复盘：模板级 A/B 对比**：不做 — 来源 §4.8（L405）
10. **复盘：客户来源 ROI 对比**（直采 vs 精准）：不做 — 来源 §4.8（L406）
11. **复盘：联系人质量反推**：不做 — 来源 §4.8（L407）
12. **数据源凭证多账号轮换**：1.0 范围外，Phase 2 — 来源 UC-16 异常 A3（L1349）
13. **跨数据源同公司合并**：B2 未启用前用不上，Phase 2 落地 — 来源 §2.6（L116-117）
14. **租户自配 SMTP 发件邮箱**（D-002 决策）：发件由 EngageLab 平台集中发；租户不输入 SMTP host/port/账号/密码；不需要 `tenant_smtp_credentials` 表
15. **复用 aoqi/sysdev-ft-marketing 仓库代码**（D-001 决策）：V3 从 `backend/` 继续做；aoqi 仅作业务逻辑参考，**不做代码迁移**

## 4. User Journeys（用户路径）

> 来源：业务流 §10.2（L2810-2822）

### 4.1 路径 A：采集闭环

```
[运营 UC-02 创建租户]
  → [租户 UC-03~05 首登 + 配 OpenRouter + 配 SMTP]
  → [租户 UC-06 配关键词]
       ├─ 已收录 → UC-11 系统自动复用 → 客户库立即可见
       └─ 未收录 → UC-10 运营启动 → UC-12 系统采集（双路径并行）
                                       → UC-13 清洗 → UC-14 分发 → 客户库可见
```

### 4.2 路径 B：邮件营销闭环（2026-05-06 修订：D-022 / D-033 / D-034 / D-041）

> 流程图只画 V3 正向主链路；推迟 / 取消项见 §3 Non-goals + 决策表（D-032 / D-033 / D-034 / D-041）。

```
[租户 UC-17 浏览客户列表]
  → [UC-18 详情] / [UC-19 加入群组 / UC-20 拉黑 / UC-21 调分 / UC-22 备注 / UC-23 标签]
       （D-022 私有操作 4 件套：调分 + 备注 + 标签 + 群组）
  → [勾选 N 家公司 → UC-25 新建邮件计划]
       （D-033：自动按 UC-08 / classify 取联系人，无目标策略 3 选 1）
  → [UC-26 启动 → UC-27 系统按预热档位发送（EngageLab）]
  → [UC-28 监控状态] / [UC-29 暂停或取消]
       （D-041 6 项指标：发送量 / 送达率 / 独立打开率 / 软退信 / 举报垃圾 / 退订）
  → [客户回信到租户自己邮箱（不经平台）]
  → [V3 主链路终点]
```

### 4.3 路径 C：运营日常

```
[UC-15 查看采集进度] / [UC-16 维护凭证] / [偶发 UC-10 启动新关键词]
```

## 5. Core Capabilities（核心能力清单，分层）

| 能力域 | 前端可见（UI） | 后端 API | Worker | DB | Sealos |
| --- | --- | --- | --- | --- | --- |
| 租户与权限 | admin/tenants、tenant/login | `/admin/api/v1/tenants`、`/t/{slug}/api/v1/users` | — | tenants / users / user_roles | admin、backend |
| AI 配置 | tenant/settings/ai-provider、admin 详情页 | `/t/{slug}/api/v1/ai-provider` | — | tenant_ai_provider_configs | backend |
| **租户域名验证（D-002 架构 C）** | tenant/settings/sender-domain（提交域名）+ admin/email-providers（验证管理） | `/t/{slug}/api/v1/sender-domain`、`/admin/api/v1/email-providers` | — | `tenant_email_domains`（**新表，租户域名 + EngageLab 验证状态 + DNS 记录**）+ `email_providers`（平台级 EngageLab 账号配置） | admin、backend、tenant |
| 关键词 | tenant/settings/keywords | `/t/{slug}/api/v1/keywords` | — | keywords_master / tenant_keywords / collection_keywords | backend |
| 评分 / 联系人规则 | tenant/settings/scoring、contact-rules | `/t/{slug}/api/v1/scoring`、`/contact-rules` | scoring worker | scoring_templates / contact_rules / scoring_jobs | backend、scoring worker |
| 采集 | admin/collection（dashboard / credentials / 启动） | Internal API + admin API | collection、collection_scheduler workers | data_sources / data_source_credentials / collection_tasks / 6 张原始表 / cleanup_queue | backend、collection worker、collection-scheduler worker |
| 清洗与分发 | — | — | cleanup worker（含在 collection worker 或独立） | clean_companies / clean_contacts / tenant_companies / tenant_contacts | collection worker |
| 客户库 | tenant/companies、curated-customers、详情页 | `/t/{slug}/api/v1/companies`、`/contacts` | — | tenant_companies / tenant_contacts | backend |
| 邮件计划 | tenant/send-plans、模板、监控 | `/t/{slug}/api/v1/send-plans` | sending worker | sending_plans / sending_plan_steps / sending_plan_targets / emails / email_events / email_send_locks | backend、sending worker |
| 预热（平台） | admin/warmup-rules | `/admin/api/v1/warmup-rules` | sending worker 受限 | warmup_rules / warmup_rule_levels / domain_warmup_status / domain_daily_usage | admin、backend |
| 邮件模板 | admin/email-templates、tenant/templates | `/admin/api/v1/email-templates`、`/t/{slug}/api/v1/templates` | — | platform_email_templates / email_templates | backend、admin |
| 复盘 / Dashboard | tenant/dashboard、email-monitor、send-plans 详情 | `/t/{slug}/api/v1/metrics` | — | 聚合查询 sending_plan_target_status + emails | backend |

> 来源：业务流 §8 各 UC 中链接的前端页面 + spec-collection-module.md §8.1

## 6. Collection Workflow（采集流程）

> 来源：业务流 §2（L52-149）+ spec-collection-module.md v1.4

### 6.1 双路径并行（V3 范围）

```
[运营 UC-10 点启动一个关键词（未收录）]
  ├──→ 路径 A：直采
  │      外贸通 SEARCH→DETAIL→CONTACT → waimaotong_raw_companies + waimaotong_raw_contacts
  │      collection_type = 'direct_search'
  │
  └──→ 路径 B：反推
        Stage 1: 励销云搜中国同行 → lixiaoyun_raw_companies（不进清洗）
        Stage 2: 用 Stage 1 同行清单喂腾道 → tendata_raw_companies（+ 联系人，D2 必修独立成表）
                 [B2 外贸通反推 1.0 不做]
```

### 6.2 容量约束

- **每日上限**：1000 条/数据源/天（HTTP 爬取风控约束，§2.7 L120）
- **理论日峰**：3000 条/天（三池独立）
- **超额处理**：跨日续跑

### 6.3 清洗与分发

- 清洗源：外贸通 + 腾道原始（励销云**不进清洗**，§2.5 L107-110）
- 产物：`clean_companies` + `clean_contacts`（**D3 必修建表**）
- 多租户分发：UC-14 反查 `tenant_keywords` 命中租户 → UPSERT `tenant_companies` + `tenant_contacts`（**D1 必修**）

### 6.4 关键词归一规则（§1.3 L37-42）

- 大小写无关 + 去空格 + 去标点
- `PCB-board` / `pcb board` / `PCB BOARD` = **同**关键词
- `PCB` / `printed circuit board` = **两**个关键词（同义不识别）
- 仅英文

## 7. Email Sending Workflow（邮件发送流程）

> 来源：业务流 §4（L268-411）+ UC-25~30

### 7.1 计划结构（§4.2、Q16）

- 单封 OR 多步骤序列（租户决定）
- 多步骤：租户自定义每步延迟天数（如 Day 1 / Day 4 / Day 8）
- 中断条件：对方回复后停止后续 — **公司级中断**（同公司任一联系人回复 → 整公司其他联系人停发）

### 7.2 内容来源（§4.3、Q18，4 选 1）

- 租户级模板库
- 平台级模板库
- AI 实时生成（OpenRouter）
- 直接现写

### 7.3 启动 + 速率（§4.4，D-002 修订）

- 启动方式：手动 / 定时（租户选）
- 发送速率：受 admin 配置的预热档位**全平台统一**约束（租户不能突破档位）
- **D-002 架构 C 落地**：
  - 发件 `From`：**租户自有域名邮箱**（如 `marketing@abc.com`）—— 租户品牌完整
  - 发件通道：EngageLab API（API_USER + API_KEY 在 admin 端管理）
  - DNS 验证：租户提供域名 → 平台运营在 EngageLab 添加 → 发 SPF/DKIM/DMARC 记录给租户 → 租户 IT 配 DNS → 验证通过即可发
  - 回信路径：`Reply-To` = 租户邮箱（默认 = `From`）→ 客户回信回到**租户自己邮箱**，**不经平台**（与业务流 §4.5 "1.0 不做 IMAP" 一致）
  - 业务流 UC-05 修订为"**域名验证流程**"，不是 SMTP 配置（详见 [`04-open-questions.md`](../04-open-questions.md) §H Q-002）

### 7.4 5 态状态机（§4.6、Q21）

```
未开始 → 投递中 → 投递完成
                    ├─→ 已回复（租户手动标，UC-30）
                    │
[创建后任意点] ────→ 已取消（租户主动停 / 拉黑客户 / 公司级中断触发）
```

聚合规则（公司行从联系人状态聚合）：业务流 §4.6 末尾标"挂起，1.0 实施时需补一个聚合优先级表"——**V3 决策项 §B**

## 8. Worker Responsibilities（Worker 职责矩阵）

> 来源：业务流 UC-12/13/14/27 + `_control/01-code-roots.md` §3

| Worker | 输入 | 输出 | 状态机 | 幂等键 | 重试 | V3 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| `collection_scheduler` | 时间触发 | 入队 collection_tasks | — | 关键词级排队 | — | V3-WORKER-001 |
| `collection` | collection_tasks pending | 写 6 张 raw 表 + cleanup_queue 入队 | pending→running→done/failed | task_id + lease | 指数退避，3 次 | V3-WORKER-002 |
| `cleanup`（collection 内或独立） | cleanup_queue pending | UPSERT clean_companies/contacts，触发 UC-14 分发 | pending→processing→done/failed | (raw_table, raw_row_id) UNIQUE | 3 次后标 failed | V3-WORKER-003 |
| `scoring` | scoring_jobs pending | 写 company_scores | pending→leased→completed/failed/waiting_balance | scoring_job_id + lease | — | V3-WORKER-004 |
| `sending` | sending_plan_targets 队列 | 调 **EngageLab API**（D-002）发邮件 + 写 emails / email_events | 5 态见 §7.4 | email_send_locks UNIQUE | EngageLab 4xx 重试，5xx 标 done（1.0 不区分失败）；30904 quota exceeded 退避 | V3-WORKER-005 |

> 🟡 **决策项 §C**：`run_collection_scheduler.py` 与 `run_collection_scheduler_worker.py` 命名近似（[`04-open-questions.md`](../04-open-questions.md) #B2）——是否合并 / 谁是真入口？

## 9. Data Objects（核心数据对象）

> 来源：业务流 §9 ER 图（L2298-2792）+ [`_control/inputs/database/README.md`](../inputs/database/README.md)

V3 范围内的关键表（按 ER 图 9 子节）：

| 分组 | 实体 | 备注 |
| --- | --- | --- |
| 9.1 用户 | tenants / users / user_roles | UC-02、UC-03、UC-09 |
| 9.2 关键词 | keywords_master(待建) / tenant_keywords(待建) / collection_keywords(已建) | 命名待统一 |
| 9.3 采集原始库 6 张 | waimaotong_raw_* / tendata_raw_* / lixiaoyun_raw_* | D2 必修：tendata/lixiaoyun raw_contacts 独立成表 |
| 9.4 清洗干净库 | **clean_companies / clean_contacts** | D3 必修：clean_contacts 未建 |
| 9.5 租户视图层 | tenant_companies / tenant_contacts | 含私有状态字段 §3.5 L216-225 |
| 9.6 配置 | data_source_credentials / tenant_ai_provider_configs / **`tenant_email_domains`（D-002 架构 C：租户域名 + EngageLab 验证状态 + DNS 记录）** / **`email_providers`（D-002 架构 C：平台级 EngageLab 账号 API_USER/API_KEY）** / scoring_templates / contact_rules / platform_scoring_templates / platform_email_templates / email_templates / warmup_rules | 9 个配置实体（D-002 用 `tenant_email_domains` + `email_providers` 替代原 `tenant_smtp_credentials`） |

> 🔴 **D-008 = B（用户 2026-05-05 决策）**：上述 §9 描述按 shared+sources 模型——V3 实施时**需重构**为业务流原版 6 raw + 2 clean 模型。即：
>
> - 删 `shared_companies / shared_contacts / company_sources` 3 张表
> - 新建 `waimaotong_raw_companies / waimaotong_raw_contacts / tendata_raw_companies / tendata_raw_contacts / lixiaoyun_raw_companies / lixiaoyun_raw_contacts` 6 张原始表（业务流 §9.3 字段定义）
> - 新建 `clean_companies / clean_contacts` 2 张干净表（业务流 §9.4 字段定义）
> - 新建 `cleanup_service` worker（消费 `cleanup_queue`，UPSERT raw → clean，励销云原始 → 直接标 done 不入 clean，符合业务流 §2.5）
> - `competitor_companies` 表的去留待 D-008-B.3 子决策（详见 [`04-open-questions.md`](../04-open-questions.md) §L）
| 9.7 任务/队列 | collection_tasks / cleanup_queue / scoring_jobs | scoring_jobs 已建（迁移 0003） |
| 9.8 邮件营销 | sending_plans / sending_plan_steps / sending_plan_targets / emails / email_events / email_send_locks | 命名 vs schema.sql 待对齐 |

> 🟡 **决策项 §D**：业务流 ER 图与现有 schema.sql 命名有偏差（如 `sending_plan_targets` vs `sending_plan_recipients`、`keywords_master` 是否新建）。是 ER 改 schema 还是 schema 改 ER？这是 [`04-open-questions.md`](../04-open-questions.md) #A2/A3 的具体表现。

## 10. Tenant Isolation Rules（租户隔离规则）

> 来源：业务流 §3.5（L198-244）+ §2.4（L100-105）+ [`_control/inputs/database/RLS_POLICY_MATRIX.md`](../inputs/database/RLS_POLICY_MATRIX.md)

### 10.1 数据可见性矩阵

| 数据层 | admin 运营 | 租户 |
| --- | :---: | :---: |
| 6 张原始库 | ✅ 全部可见 | ❌ 不可见 |
| 干净库 (clean_*) | ✅ 全部可见 | ✅ 命中关键词的租户可见 |
| 租户视图层 (tenant_companies/contacts) | ✅ 全部 | ✅ 仅本租户 |
| 私有状态字段（精选/拉黑/评分/备注/标签/主联系人/邮件状态） | ❌（隔离强） | ✅ 仅本租户 |
| 邮件计划 | ❌ | ✅ 仅本租户 |

### 10.2 强制 RLS 表清单（D-002 架构 C 修订）

`tenants`、`users`、`tenant_companies`、`tenant_contacts`、`tenant_ai_provider_configs`、**`tenant_email_domains`**（新增 RLS：租户只看到自己的域名 + 验证状态）、`scoring_templates` / `_versions`、`company_scores`、`contact_rules`、`company_blacklist`、`groups`、`group_members`、`email_templates`（租户级）、`sending_plans` / `_steps` / `_recipients`、`emails` / `email_events`、`tenant_keywords`、`competitor_companies`（待确认）、`tenant_tags`（待建）、`notifications`（按 user）、`audit_logs`（按 tenant）

**不强制 RLS**（平台级表）：`email_providers`（EngageLab 账号配置，仅 admin 可见）

具体策略以 [`RLS_POLICY_MATRIX.md`](../inputs/database/RLS_POLICY_MATRIX.md) 为准。

### 10.3 跨租户共享表（不强制 RLS，但读时按 matched_keywords / data_sources 过滤）

`shared_companies`、`shared_contacts`、`clean_companies`、`clean_contacts`、`keywords_master`、6 张 raw 表（仅 admin）

## 11. Permissions（权限）

> 来源：业务流 §1.1 L25 + §8.0 Actor 清单 + UC-02 / UC-09 + schema.sql `user_role` ENUM (`admin/operator/viewer`)

### 11.1 平台级

- **平台运营（admin）**：管理租户、运营动作（UC-02 / UC-10 / UC-15 / UC-16），操作 admin 端

### 11.2 租户级（租户内 RBAC，1.0 不做细分）

- **owner**（默认主账号）：完整租户操作权
- **member**（被邀请，角色不细分，对应 schema.sql 的 `operator`）：可视化 + 操作客户库 + 建邮件计划

> 🟡 **决策项 §E**：业务流 §8.0 标"租户内部不细分角色，由 RBAC 权限控制"，但 schema.sql 的 `user_role` ENUM 含 `viewer`——V3 是否启用 `viewer` 角色？

## 12. Edge Cases（边界条件）

> 来源：业务流 §6 挂起的二阶问题（L429-447） + 各 UC 的 异常路径

### 12.1 V3 必处理（来自 UC 异常路径）

| 场景 | 来源 | 处理 |
| --- | --- | --- |
| 数据源凭证失效 | UC-12 A1 | 任务暂停 + 告警 admin → UC-16 |
| 数据源限流 429 | UC-12 A2 | 指数退避重试 |
| 数据源 5xx | UC-12 A3 | 重试 N 次失败 → 任务标失败，次日重试 |
| 当日额度耗尽 | UC-12 A4 | 任务挂起，等次日 0 点重置 |
| cleanup 双唯一索引冲突 | UC-13 A2、Phase 1.5 D4 | **必修**：避免 INSERT...ON CONFLICT DO NOTHING 丢数据 |
| 多租户漏数据 | UC-14 A1、Phase 1.5 D1 | **必修**：第 2 个租户加同关键词时也要拿到完整数据 |
| 拉黑后正在发邮件计划 | UC-20 A1 | 弹窗警告 + 取消未发步骤 |
| SMTP 250 但实际退信 | UC-27 A1 | **D-041 修订（2026-05-06）**：以 EngageLab webhook 回写为准；soft_bounce / invalid_email 字段写入 emails 表；不再"发出 = 投递完成"统一处理 |
| ~~租户忘标"已回复"导致骚扰~~ | ~~§4.5 trade-off~~ | **D-034 推迟 V3.1+**：UC-30 整体不做；序列按时间表完整推进，无回复中断 |

### 12.2 挂起到 §16 Open Questions

业务流 §6 中 17 个挂起项中以下 6 项**直接影响 V3 验收**：

- 多关键词竞争同数据源时的调度策略（FIFO？均匀切分？运营手动？）
- 租户首采体验承诺（一天可能 0 条入库）
- 系统默认评分等级具体级别（"最高"是几级？租户级规则与系统默认的关系？）
- 联系人优先级规则边缘 case（无邮箱 / 无职位 / 同职位多人）
- 邮件序列最大步骤数上限
- 预热档位具体形式 + 是平台共用还是租户独立

## 13. Metrics（关键指标）

> V3 上线后用什么指标判断健康。来源：业务流 §4.8（复盘维度）+ UC-32 Dashboard

### 13.1 业务侧指标（租户可见）

- 客户总数 / 已精选数 / 已拉黑数（UC-32 顶部卡）
- 客户来源分布：直采 vs 精准（UC-32）
- 累计投递数 / 回复数 / 整体回复率（UC-31、UC-32）
- 邮件计划列表 + 跨计划趋势（UC-33）
- AI 余额 + 当月预估消耗（UC-32）

### 13.2 平台侧指标（运营可见，admin/dashboard）

- 各数据源当日已用 / 1000 上限 / 队列长度
- cleanup_queue 健康（pending / failed / 最早 pending 时长）
- 任务异常告警（UC-15 dashboard）
- 各 worker 错误率
- DB 慢查询、连接数

## 14. E2E Acceptance Criteria（端到端验收）

> 完整 18 项详见 [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)。本节仅列 **P0 主链路**（必须 Sealos 上跑通）

| # | E2E 场景 | 关键 UC |
| --- | --- | --- |
| E2E-1 | 运营建租户 + 租户首登 + 配 OpenRouter + 配 SMTP | UC-02、03、04、05 |
| E2E-2 | 配关键词（未收录）→ 运营启动 → 真实采集（直采 + 反推 stage1+2）→ 入库 → 客户库可见 | UC-06、10、12、13、14 |
| E2E-3 | 已收录关键词被另一租户复用 → 立即看到完整数据（D1 修复验证） | UC-06b、UC-11 |
| E2E-4 | 跨租户隔离：A 看不到 B 的私有状态 | UC-19~24 + RLS |
| E2E-5 | 客户库筛选 → 勾选 → 新建邮件计划（多步骤序列 + AI 内容）→ 启动 → 真实送达测试邮箱 → 状态回写 | UC-17、25、26、27 |
| E2E-6 | 收件人回复 → 租户手动标"已回复"→ 公司级中断生效（同公司其他人未发邮件被取消） | UC-30 |
| E2E-7 | 计划复盘 + Dashboard + 跨计划趋势 | UC-31~33 |
| E2E-8 | 数据源凭证失效 → 告警 → 运营更新 → 任务恢复 | UC-16 |
| E2E-9 | Worker 重启不丢任务 | 各 worker 状态 |
| E2E-10 | 拉黑客户后正在跑的邮件计划被取消未发步骤 | UC-20 |

## 15. Sealos Deployment Acceptance Criteria

> 来源：[`backend/docs/SEALOS_DEPLOYMENT.md`](../../backend/docs/SEALOS_DEPLOYMENT.md) v0.2 已定义的 **8 个部署单元**

### 15.1 8 个部署单元（来自 SEALOS_DEPLOYMENT.md）

| # | 单元 | 类型 | 域名建议 |
| --- | --- | --- | --- |
| 1 | Sealos `PostgreSQL` | 数据库 | — |
| 2 | `clientget-backend` | 后端 API | `api.example.com` |
| 3 | `clientget-collection-scheduler` | Worker | — |
| 4 | `clientget-collection-worker` | Worker | — |
| 5 | `clientget-scoring-worker` | Worker | — |
| 6 | `clientget-sending-worker` | Worker（含 EngageLab 调用） | — |
| 7 | `clientget-admin` | 前端 SPA | `admin.example.com` |
| 8 | `clientget-tenant` | 前端 SPA | `tenant.example.com` |

### 15.2 验收标准

- 8 个部署单元全部 Running，副本数 ≥ 1
- 镜像 tag 与 V3 release 一致
- Alembic 迁移到 head（当前 v0.2 最新版本号 0013，V3 实施时可能新增 0014+）
- DB 迁移成功 + 无数据漂移（业务流 §5 差距清单全部解决）
- 关键 env 变量已配（具体清单见 [`inputs/sealos/applications.md`](../inputs/sealos/applications.md)，仅含 key 名）
- 健康检查通过（前端 SPA index.html 可访问 / 后端 `/healthz` / 各 worker heartbeat）
- EngageLab 域名验证通过（D-002 架构 C：至少 1 个测试租户域名验证状态 = `verified`）
- 跑通 §14 全部 E2E（10 个场景 + R-1/R-2/R-3 用户范围 4 项）

## 16. Open Questions（V3 启动前未决问题）

关联 [`_control/04-open-questions.md`](../04-open-questions.md)：

### V3 范围相关

- **Q-001**（=A1）：V3 整体范围 — **用户口述中**（暂未签字）
- **Q-002**（D-002 引出，新增）：**业务流 UC-05 / §4.4 与 D-002 决策冲突，UC-05 需要重新设计**：
  - 租户配置页是否完全去掉"邮件账号配置"入口？还是保留"发件人显示名 + 回信地址"自定义？
  - EngageLab 凭证管理在 admin 端哪个页面？（建议新增 admin/email-providers）
  - 发件邮箱**池化策略**：每租户绑定 1 个发件域名？多租户共用 1 个池？还是按预热档位分配？
  - 业务流 §4.4 "保护发件邮箱信誉" 现在由**平台运营**保障（不再是租户责任）
- **Q-003**：业务流 ER 图（§9）与 schema.sql 命名偏差如何收口？— **§D 待逐项确认**（用户决策：每个偏差由用户拍板）
- **Q-004**：5 态聚合优先级（§B）— **未决**，aoqi 调研显示这是 ClientGet 新加能力，[`reference-impl-aoqi.md`](../inputs/reference-impl-aoqi.md) §5.2 给了建议
- **Q-005**：`run_collection_scheduler.py` vs `run_collection_scheduler_worker.py` 谁是真入口 — §C 决策
- **Q-006**：租户内角色 — V3 是否启用 `viewer` ENUM 值？— §E 决策

### 实施前需读代码确认

- **F1**：`backend/app/models/` 空目录——后端无 ORM？所有数据访问走 repositories 裸 SQL？— Step 4 Gap Audit 时确认
- **F2**：`scoring_jobs` / `waimaotong_raw_contacts` 未回写 schema.sql（设计真源漂移）
- **F3**：月度分区由"启动钩子"创建，钩子在何处未读确认

### 业务流 §6 挂起 6 项（见 §12.2）

来源 business-flow-DRAFT.md L429-447。

---

## A. PM 关键决策（用户拍板后才能进入 Step 3）

> ⚠️ 以下 6 项决策直接影响 V3 范围与 Acceptance Matrix。AskUserQuestion 会逐项问。

### §A 命题

**V3 = "业务流 DRAFT 1.0 全部 33 个 UC + Phase 1.5 D1-D4 必修结构债"** ——是否同意？

### §B 5 态聚合规则

业务流 §4.6 末尾标"挂起，1.0 实施时需补一个聚合优先级表"。建议三态升 5 态：
`已取消 > 投递中 > 未开始 > 已回复 > 投递完成`（已取消优先；已回复算"完成"分支）

### §C Worker 启动入口

合并 `run_collection_scheduler.py` + `run_collection_scheduler_worker.py` 为一份？还是分定时调度 vs 长期 worker？

### §D ER 图 vs schema 命名收口

以**业务流 ER 图为业务真源**，schema.sql 由 V3 实施时调整？还是以 schema.sql 为代码真源，ER 图按代码改？

### §E 租户内角色

V3 是否启用 `viewer` 角色？还是只 owner + operator？

### §F blueprint vs docs/spec-* 权威关系

docs/spec-* + business-flow-DRAFT 优先（2026-04-30 后产物）？还是 blueprint 00-09 优先？

---

## PM Review Checklist（用户签字前自检）

- [ ] §1 Objective 1 句话讲得清
- [ ] §2 Scope 33 个 UC 全部确认在 V3 范围内
- [ ] §3 Non-goals 13 条全部认同
- [ ] §4 User Journeys 路径 A（采集）+ B（邮件）+ C（运营）都画清
- [ ] §6/§7 流程与业务流 §2/§4 一致
- [ ] §10 租户隔离规则与 RLS 矩阵一致
- [ ] §14 E2E 至少 10 条且 Sealos 上可复现
- [ ] §16 Open Questions 关联到 04-open-questions.md
- [ ] §A-§F 6 项 PM 决策已拍板

签字行：

```
__________________________ (用户)   日期：__________
```
