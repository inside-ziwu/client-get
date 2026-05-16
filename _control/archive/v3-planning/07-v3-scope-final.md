# V3 · 07 · Scope Final（本期实际开发范围 · 派生自 3 真源）

> **状态**：v1.0 起草（2026-05-06）— 用户决策"基于 3 真源重建最高真源 → 确定本期实际开发范围"
> **优先级**：本文件签字后 = **V3 最高真源**；与历史 [`00-v3-target-spec.md`](00-v3-target-spec.md) 决策追溯节冲突时以本文件为准
> **签字解锁**：Gate 5（启动 Wave 1 实施）
> **派生规则**：
> - **界面真源** [`mockups/`](mockups/) 24 个原型 → 决定"V3 做哪些 UI"
> - **业务真源** [`00-v3-business-goals.md`](00-v3-business-goals.md) → 决定"V3 做哪些业务规则"
> - **现状真源** [`02-current-implementation-gap-audit.md`](02-current-implementation-gap-audit.md) → 决定"V3 工作量在哪里"

## 0. 元数据

- 版本：v1.0（首版基于 3 真源派生）
- 起草日期：2026-05-06
- 用户签字：✅ **lay** · 2026-05-06（codex 两轮审查通过）
- 签字阻塞 Gate：Gate 5（启动 `/ce:work` 实施）

---

## 1. V3 一句话目标（与 business-goals §1 一致）

让 **PCB 外贸厂老板**（租户）在 ClientGet 平台上完成完整的 **"采集 → 客户库 → 邮件营销"** 业务闭环——首次配置完成后，租户从客户库勾选目标公司、新建邮件计划、按预热档位发送，**全程无需运营介入**；运营仅在 2 个节点参与：**租户创建** + **首采启动**。

**4 项必交付能力**（business-goals §3）：
- **R-1** 4 单元功能完整可用（backend / admin / tenant / PostgreSQL）
- **R-2** 反推采集闭环（励销云 stage1 + 腾道 stage2）
- **R-3** 完整邮件投递（域名 + 真发 + 状态追踪）
- **R-4** 上线 Sealos 生产

---

## 2. 24 个原型 × 业务依据 × 现状 × 本期范围（核心矩阵）

> 状态枚举：✅ 本期做 / ⛔ 本期不做（已 PASS 或推迟）/ 🆕 V3 新增模块

### 2.1 Admin 端 11 个原型

| # | 原型 | 业务依据（business-goals）| 现状（gap-audit Cn）| 本期范围 | OpenSpec change |
|---|---|---|---|:-:|---|
| 1 | `admin-ai-config.html` | §3 R-1 OpenRouter 配置（UC-04）| PASS | ⛔ 已就绪 | — |
| 2 | `admin-clean-companies.html` | §5.2 干净库（D-008=B）| C1 MISSING | ✅ 干净库 UI 入口 | v3-data-foundation |
| 3 | `admin-collection-tasks.html` | §4 流程闭环-运营启动首采（UC-10）| 现有按钮已实现（admin/CollectionTasks/index.tsx:230-302）；缺口 = 按 D-035 禁用 direct channel + 后端防御性拒绝 | ✅ 复核现有按钮 + 禁用 direct channel | v3-collection-pushback |
| 4 | `admin-contact-classification.html` 🆕 | §5.4 联系人职位分类规则（D-037）| C3 MISSING | ✅ 全新页面 | v3-contact-classification |
| 5 | `admin-customers.html`（= Tenants 管理）| §4 运营创建租户 + §5.4 域名验证（D-031 / D-002 / D-024）| C7 PARTIAL（Create Modal + 域名 Tab 缺）| ✅ Create Modal 加发件域名 + 起始预热档位；域名 Tab 调 EngageLab + 触发验证 + DNS 一键复制 | v3-email-delivery |
| 6 | `admin-data-sources.html` | §3 R-1 数据源凭证（UC-16，D-016）| PASS | ⛔ 已就绪 | — |
| 7 | `admin-email-templates.html` | §5.4 内容来源-平台模板 | PASS | ⛔ 已就绪 | — |
| 8 | `admin-intelligence-sources.html` | §3 R-1 情报源元信息 | PASS | ⛔ 已就绪 | — |
| 9 | `admin-scoring-templates.html` | §5.3 评分模板按行业（D-039）| C6 REWRITE | ✅ PCB 7 维默认模板 + 维度/档位/分值/默认权重 | v3-tenant-companies |
| 10 | `admin-tendata-raw.html` | §5.2 raw 数据查看（D-008-B 6 raw 模型）| C1 MISSING（属 raw 表重构）| ✅ raw 数据查看入口（伴随 cleanup_service 部署）| v3-data-foundation |
| 11 | `admin-warmup-rules.html` | §5.4 预热档位（D-013）| PASS | ⛔ 已就绪（sending worker 接入限速即可）| — |

**Admin 端 11 模块**：本期开发 6 个（含 collection-tasks 复核）/ 不做 5 个

### 2.2 Tenant 端 13 个原型

| # | 原型 | 业务依据（business-goals）| 现状（gap-audit Cn）| 本期范围 | OpenSpec change |
|---|---|---|---|:-:|---|
| 12 | `tenant-companies.html` | §5.3 客户库（UC-17）+ 10 项筛选（D-038）+ 私有操作（D-022 4 件套：UC-21/22/23 + D-020 群组）| C4 MISSING + C5 MISSING + C6 MISSING | ✅ Drawer 4 件套 + 10 项筛选 + 调分先建 DB 字段 | v3-tenant-companies |
| 13 | `tenant-curated-customers.html` | §5.3 精选 = 群组（D-020）+ 共用 10 项筛选（D-038）| PARTIAL | ✅ 共用筛选组件 + 群组管理 | v3-tenant-companies |
| 14 | `tenant-dashboard.html` | §6 N-04 完整 Dashboard 推迟 V3.1+（D-032）| 极简空壳即可 | ⛔ V3 极简版（D-032）| — |
| 15 | `tenant-email-monitor.html` | §5.4 投递监控 6 指标（D-041，撤销 N-08/N-09）| C7 PARTIAL | ✅ 6 指标接 EngageLab 回写 + 详情时间轴 | v3-email-delivery |
| 16 | `tenant-intelligence.html` | §5.1 关键词配置（UC-06）+ 跨租户复用（D-009）| C2 综合 MISSING（前端 PARTIAL）| ✅ KeywordMaster 命中"已采过"分支提示 | v3-collection-pushback |
| 17 | `tenant-send-plans-detail.html` | §5.4 邮件计划监控（UC-28/29）| PASS（数据接 D-041 字段后即可）| ⛔ 已就绪 | — |
| 18 | `tenant-send-plans-new.html` | §5.4 新建邮件计划（UC-25 + D-033）| C7 PARTIAL | ✅ 移除目标策略 3 选 1 UI + 集成 classify(position) | v3-email-delivery + v3-contact-classification |
| 19 | `tenant-send-plans.html` | §5.4 邮件计划列表（UC-26）| PASS | ⛔ 已就绪 | — |
| 20 | `tenant-settings-ai-provider.html` | §3 R-1 OpenRouter 双入口（UC-04）| PASS | ⛔ 已就绪 | — |
| 21 | `tenant-settings-keywords.html` | §5.1 关键词配置（UC-06）| PASS | ⛔ 已就绪（功能与 tenant-intelligence 重叠，仅入口不同）| — |
| 22 | `tenant-settings-scoring.html` | §5.3 租户仅调权重（D-039）| C6 PARTIAL | ✅ 移除规则配置 UI，改为只调权重 | v3-tenant-companies |
| 23 | `tenant-settings-team.html` | §3 R-1 团队管理（UC-09，角色 admin/operator/viewer）| PASS | ⛔ 已就绪 | — |
| 24 | `tenant-templates.html` | §5.4 内容来源-租户模板 | PASS | ⛔ 已就绪 | — |

**Tenant 端 13 模块**：本期开发 6 个 / 极简 1 个（dashboard）/ 不做 6 个

### 2.3 后端 / Worker / DB（无 mockup 但本期必做）

| 类型 | 工作 | 业务依据 | 现状 | OpenSpec change |
|---|---|---|---|---|
| DB 重构 | alembic 0006→0013 升级 | §3 R-1 4 单元 + D-017 | C8 MIGRATION-BLOCKED | v3-data-foundation |
| DB 重构 | D-008=B 拆 raw + 建 clean + 5 新表 + 11 新字段 | §5.2 数据流 + D-008/038/039 | C1 MISSING | v3-data-foundation |
| Worker | cleanup_service（多源合并 + 励销云不入 clean）| §5.2 干净库唯一来源 = 腾道 | C1 MISSING | v3-data-foundation |
| Worker | UC-11 fan-out（跨租户复用）| §5.1 跨租户复用 + D-009 | C2 MISSING | v3-collection-pushback |
| Worker | sending worker 部署 + EngageLab 接入 | §3 R-3 + D-018 | C7 WORKER-NOT-DEPLOYED | v3-email-delivery |
| Worker | scoring worker 部署 + 等级映射 + 兜底 | §5.3 双层评分 + D-039 | C6 WORKER-NOT-DEPLOYED | v3-tenant-companies |
| Worker | webhook 接入 EngageLab 回写（D-041）| §5.4 投递监控 6 指标 | C7-G11 MISSING | v3-email-delivery |
| Worker | 4 worker base class（retry / heartbeat / 幂等 / 错误日志）| §3 R-1 4 单元 | C8-G5 MISSING（监控 / 日志 / 重试 / 幂等待补）| v3-data-foundation（模板）|
| 部署 | Sealos 9 部署单元（PostgreSQL + admin + tenant + backend + 4 原 worker + cleanup_service）| §3 R-4 + §5.5 + D-008-B | C8 MISSING | v3-data-foundation |
| 部署 | EngageLab 真接入 + 1 测试租户首发 | §3 R-3 + D-018 | C9 MISSING | v3-email-delivery（Slice 5）|

---

## 3. 业务规则 → 实施位置交叉表（business-goals §5 全细则映射，codex High-01 修订）

| business-goals §5 业务规则 | 来源 | 实施位置 | 关联 OpenSpec change |
|---|---|---|---|
| §5.1 关键词仅英文 + 归一化（大小写无关 + 去空格 + 去标点）| §5.1 L80 | tenant-intelligence 输入校验 + 后端归一化函数 | v3-collection-pushback |
| §5.1 关键词配置者 = 租户自己 / 数量上限无 | §5.1 L81 | tenant-intelligence + tenant-settings-keywords（无后端限制）| v3-collection-pushback |
| §5.1 跨租户复用（A 已采 B 立即可见）| §5.1 L82 | KeywordMaster + UC-11 fan-out worker | v3-collection-pushback |
| §5.2 反推数据源（励销云 stage1 + 腾道 stage2）| §5.2 L86 | collection worker（已 ready，按 D-035 仅启用 tendata + lixiaoyun provider）| v3-collection-pushback |
| §5.2 每日上限 1000 条 / 数据源 / 天 | §5.2 L87 | collection scheduler 限速 + data_source_credentials.daily_limit | v3-collection-pushback |
| §5.2 数据流 raw → clean → tenant 视图分发 | §5.2 L88-91 | cleanup_service + tenant_companies fan-out | v3-data-foundation + v3-collection-pushback |
| §5.2 励销云数据不入干净库（仅作 stage 2 输入）| §5.2 L89-90 | cleanup_service 规则（source_type='lixiaoyun' → 标 done 不入 clean）| v3-data-foundation |
| §5.2 干净库唯一来源 = 腾道（V3 期间）| §5.2 L90 | cleanup_service 唯一 INSERT 入口 | v3-data-foundation |
| §5.3 客户列表 1 行 = 1 公司（不论命中几关键词）| §5.3 L95 | clean_companies UNIQUE 约束 + tenant_companies fan-out 去重 | v3-data-foundation |
| §5.3 来源标签 = 精准（V3 期间客户库全为反推产出）| §5.3 L96 | clean_companies.sources 字段 + UI 展示 | v3-data-foundation |
| §5.3 客户库 10 项筛选（含联系人数量档位）| §5.3 L97-100 | tenant-companies + tenant-curated-customers + clean_companies +11 字段 | v3-tenant-companies |
| §5.3 双层评分（admin 配模板 + 租户调权重）| §5.3 L101-103 | admin-scoring-templates + tenant-settings-scoring + scoring worker | v3-tenant-companies |
| §5.3 PCB 7 维 + 等级 S/A/B/C/D 阈值 + 档位外/缺失 = 0 分 | §5.3 L104-106 | scoring worker 等级映射 + 兜底 + clean_companies +2 字段 | v3-tenant-companies |
| §5.3 租户私有状态层（群组 / 拉黑 / 调分 / 备注 / 标签）| §5.3 L107-111 | tenant-companies Drawer + UC-21 后端先建字段 + groups/group_members | v3-tenant-companies |
| §5.4 EngageLab 通道 + 租户自有域名 | §5.4 L115 | admin-customers 域名 Tab + sending worker | v3-email-delivery |
| §5.4 域名验证（DNS 由平台运营配 SPF/DKIM/DMARC）| §5.4 L116 | admin-customers Create Modal + 域名 Tab + EngageLab Domain API | v3-email-delivery |
| §5.4 回信路径（客户回信 → 租户邮箱，不经平台）| §5.4 L117 | sending worker 邮件头设置 `Reply-To = From = 租户域名邮箱`；平台无 inbound | v3-email-delivery |
| §5.4 发送速率（受预热档位约束，租户不能突破）| §5.4 L118 | sending worker + domain_warmup_status.daily_limit 限速 | v3-email-delivery |
| §5.4 邮件状态联系人级 4 态（未开始 / 投递中 / 投递完成 / 已取消）| §5.4 L119 | emails 表 + sending worker 状态机 | v3-email-delivery |
| §5.4 投递监控 6 指标（D-041）| §5.4 L120 | tenant-email-monitor + emails 表加字段 + email_events + EngageLab webhook | v3-email-delivery |
| §5.4 联系人职位分类（admin 中央配 4 层模型）| §5.4 L121-124 | admin-contact-classification + 3 表 + 1 视图 + classify(position) | v3-contact-classification |
| §5.4 邮件计划自动取联系人（无目标策略 3 选 1）| §5.4 L125-126 | tenant-send-plans-new + classify 集成 | v3-email-delivery + v3-contact-classification |
| §5.4 多步骤序列（按时间表 + 第 N 轮发未发过的其他联系人）| §5.4 L127 | sending worker sequence 推进逻辑 + email_send_locks 去重 | v3-email-delivery |
| §5.4 邮件计划结构（单封 OR 多步骤序列 + 间隔天数）| §5.4 L129-130 | tenant-send-plans-new + sequence_steps 表 | v3-email-delivery |
| §5.4 内容来源 4 选 1（租户模板 / 平台模板 / AI 生成 / 现写）| §5.4 L131 | tenant-send-plans-new 内容选择 UI + 4 路 API | v3-email-delivery |
| §5.5 Sealos 9 部署单元（PostgreSQL + 3 应用 + 4 原 worker + cleanup_service）| §5.5 L134-138 + D-008-B 新增 cleanup_service | 5 worker 容器化 + k8s yaml | v3-data-foundation |

---

## 4. Non-Goals 明确清单（V3 不做）

> 来自 business-goals §6 + 后续决策推迟。本期**完全不实现**——无代码、无 UI、无数据写入。

### 4.1 业务能力推迟（business-goals §6.1）

| # | 不做 | 理由 |
|---|---|---|
| N-01 | 外贸通直采路径 | 仅反推（D-035）|
| N-02 | 回复识别（IMAP / Inbound webhook / 手动标已回复）| D-034 推迟 V3.1+ |
| N-03 | 公司级中断（任一回复 → 整公司停发）| D-021 / D-034 推迟 |
| N-04 | 完整 Tenant Dashboard / 跨计划趋势 | D-032 推迟（V3 极简空壳）|
| N-05 | 主联系人概念 | D-033 取消 |
| N-06 | 重采机制 | 数据冻结 |
| N-07 | 租户首登邀请邮件 + 临时密码 | D-030 线下交账号 |

### 4.2 邮件营销不做项（business-goals §6.2）

| # | 不做 | 理由 |
|---|---|---|
| ~~N-08~~ | ~~开信追踪~~ | **D-041 撤销**：EngageLab `open_tracking=true` 做开信追踪 |
| ~~N-09~~ | ~~退信记录~~ | **D-041 撤销**：以 EngageLab webhook 回写做送达分级 |
| N-10 | "已回复"事件下游联动 | 配套 N-02 推迟 |
| N-11 | 模板 A/B 测试 | 不做营销分析平台 |
| N-12 | 租户自配 SMTP 凭证 | EngageLab 集中通道（D-027）|

### 4.3 范围边界（business-goals §6.3）

| # | 不做 | 理由 |
|---|---|---|
| N-13 | 服务非 PCB 行业租户 | D-040 PCB 行业垂直 SaaS |
| N-14 | 自助注册 | 运营线下签约 → admin 创建 |
| N-15 | CRM 销售漏斗 | 聚焦邮件营销执行 |
| N-16 | "选中"字段持久化 | 临时 UI 状态不入库 |
| N-17 | 客户来源 ROI / 联系人质量反推 / 跨计划趋势 | 配套 N-04 推迟 |
| N-18 | 数据源凭证多账号扩展 | 现有能力够用 |

---

## 5. 5 个 OpenSpec change 范围归属

| change | 覆盖原型（mockup）| 覆盖业务规则 | Wave | 工作量档 |
|---|---|---|:-:|:-:|
| **v3-data-foundation** | admin-clean-companies / admin-tendata-raw | §5.2 数据流 / §5.5 部署 | 1 | L |
| **v3-collection-pushback** | admin-collection-tasks（复核）/ tenant-intelligence | §5.1 关键词跨租户复用 / §5.2 反推 | 2 | M |
| **v3-email-delivery** | admin-customers（域名 Tab + Create）/ tenant-email-monitor / tenant-send-plans-new（部分）| §5.4 邮件营销全链路 + D-041 监控 | 2 | L |
| **v3-tenant-companies** | tenant-companies / tenant-curated-customers / tenant-settings-scoring / admin-scoring-templates | §5.3 客户库 + 私有操作 + 评分 | 2 | L |
| **v3-contact-classification** | admin-contact-classification（🆕）+ tenant-send-plans-new（部分）| §5.4 联系人职位分类（D-037）| 2 | M |

**汇总**（24 = 12 开发 + 1 极简 + 11 不做）：

- **本期开发 12 个**：admin（clean-companies / collection-tasks 复核 / contact-classification 🆕 / customers / scoring-templates / tendata-raw）+ tenant（companies / curated-customers / email-monitor / intelligence / send-plans-new / settings-scoring）
- **V3 极简 1 个**：tenant-dashboard（D-032）
- **已 PASS 不开发 11 个**：
  - admin 5 个：ai-config / data-sources / email-templates / intelligence-sources / warmup-rules
  - tenant 6 个：send-plans-detail / send-plans / settings-ai-provider / settings-keywords / settings-team / templates

---

## 6. 本期验收清单

### 6.1 业务侧成功标准

#### 6.1.1 与 business-goals §7.2 一致的 5 项（原文）

- [ ] ≥ 1 个真实租户的真实关键词跑通完整采集 → 邮件投递闭环
- [ ] ≥ 1 封真实邮件被真实收件人在真实邮箱收到
- [ ] 客户库有 ≥ 50 个真实采集的客户
- [ ] 邮件计划有 ≥ 5 个真实发送过的步骤
- [ ] 跨租户隔离测试通过（A 私有状态 B 不可见）

#### 6.1.2 补充验收（派生自 business-goals §5.4 投递监控规则 + D-041，非 §7.2 原文）

- [ ] D-041 投递监控 6 指标真实回写（发送量 / 送达率 / 独立打开率 / 软退信 / 举报垃圾 / 退订）

### 6.2 18 V3-* 验收 ID 映射（详见 [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)）

P0（不通过 = 不上线）：V3-AUTH-001 / V3-COL-001~007 / V3-MAIL-001~006 / V3-WORKER-001/002 / V3-DEPLOY-001 = **17 项**
P1：V3-UI-001 = **1 项**

### 6.3 主链路 E2E 场景（business-goals §7.1）

- 场景 1：运营 admin 创建新租户 + 配域名 + DNS → 租户登录 → 配 OpenRouter
- 场景 2：租户配新关键词 → 运营启动首采 → 反推（励销云 → 腾道）→ 客户入库
- 场景 3：A 租户采过的关键词，B 租户配同关键词 → B 立即看到 A 当年客户
- 场景 4：勾选 N 家公司 → 新建邮件计划 → 真实发送 → 测试收件箱真收到
- 场景 5：A/B 双租户私有状态隔离
- 场景 6：数据源凭证失效 → 运营更新 → 任务恢复

---

## 7. 上线后观察期（business-goals §7.3）

- 持续观察 2 周
- 关键指标：邮件投递成功率 / 租户使用频率 / 运营介入次数

---

## 8. 当前业务规模（business-goals §8）

- 5 个租户（3 archived + 2 active）
- V3 主要服务这 2 个 active 租户的真实业务
- 上线时间：~4-6 周后

---

## 9. PM Review Checklist（签字前）

- [ ] §1 V3 一句话目标与 business-goals §1 一致
- [ ] §2.1 Admin 11 模块本期范围分类（6 开发 / 5 不做）合理
- [ ] §2.2 Tenant 13 模块本期范围分类（6 开发 / 1 极简 / 6 不做）合理
- [ ] §2.3 后端/Worker/DB 工作清单完整（4 worker + cleanup_service + alembic）
- [ ] §3 业务规则 → 实施位置交叉表无遗漏
- [ ] §4 Non-Goals 18 项明确（含 D-041 撤销 N-08/N-09）
- [ ] §5 5 个 OpenSpec change 覆盖完整无重叠
- [ ] §6 验收清单与 business-goals §7 一致
- [ ] 本文件签字后作为 V3 最高真源（高于 00-target-spec 历史决策池）

签字行：

```
__________lay______________ (用户)   日期：__2026-05-06__
```

**签字依据**：
- codex 第 1 轮审查（2H + 5M + 2L = 9 处 finding）已全修
- codex 第 2 轮验证 9 处全过 + 新发现 R2-Low-01（§9 Checklist 数字）已修
- 派生自 3 真源（mockups + business-goals + gap-audit）准确

**生效**：本文件签字后 = V3 最高真源；Gate 5 解锁，可启动 Wave 1（v3-data-foundation）。

---

## 10. 与其他文档关系

| 文档 | 关系 | 是否需要同步修订 |
|---|---|:-:|
| [`mockups/`](mockups/) | 界面真源 → 本文件派生 | 否（本文件依赖它）|
| [`00-v3-business-goals.md`](00-v3-business-goals.md) | 业务真源 → 本文件派生 | 否（本文件依赖它）|
| [`02-current-implementation-gap-audit.md`](02-current-implementation-gap-audit.md) | 现状真源 → 本文件派生 | 否（本文件依赖它）|
| [`00-v3-target-spec.md`](00-v3-target-spec.md) | 历史决策池 + 业务流 + ER | 旧最高真源；本文件签字后降级为"决策追溯 + 设计参考"，不再是范围权威 |
| [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md) | 18 V3-* 验收 ID | 由本文件 §6.2 引用 |
| [`03-v3-delivery-plan.md`](03-v3-delivery-plan.md) | 6-Slice × 5 change 节奏 | 由本文件 §5 派生（按本文件签字范围实施）|
| `openspec/changes/v3-*/` | 5 个 change 骨架 | 由本文件 §5 派生 |

---

> **本文件不含**：每 change 内部 task 拆分（→ openspec/changes/*/tasks.md）、E2E 用例细节（→ 04-v3-e2e-test-plan.md）、决策追溯历史（→ 00-target-spec §0.A 33 项决策表）、worker 部署 yaml（→ Slice 0 交付物）。
