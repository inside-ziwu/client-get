# Codex Review · 07-v3-scope-final.md（派生准确性）

> 审查日期：2026-05-06
> 审查范围：仅验证 07-v3-scope-final.md 是否准确派生自 3 真源
> 不审：00-target-spec / 03-delivery-plan / 5 OpenSpec change / mockups / business-goals 改动建议

## 0. 总体结论

`_control/v3/07-v3-scope-final.md` 的主体派生方向基本成立：24 个 mockup 已全部进入 §2.1 + §2.2，business-goals §6 的 N-01~N-18 已全部列入 §4，gap-audit C1~C9 也都能在 §2 或 §2.3 找到落点。因此它可以作为 V3 Scope Final 的候选稿继续推进。但当前不建议直接签字：报告发现 2 个 High、5 个 Medium、2 个 Low，主要集中在 business-goals §5 细则映射不完整、§6.1 成功标准与 business-goals §7.2 不完全一致、部署单元数量表述冲突，以及若干 gap-audit 状态引用写成局部状态或外部来源。建议先修订 07 后再签字。

## 1. 派生完整性验证（A 类）

| 检查 | 状态 | 证据 |
|---|:-:|---|
| 24 mockups 全覆盖 | ✅ | mockup 文件清单严格为 24 个：admin 11 个 + tenant 13 个；07 §2.1 列出 1-11 行，见 `_control/v3/07-v3-scope-final.md:36-50`；07 §2.2 列出 12-24 行，见 `_control/v3/07-v3-scope-final.md:54-70`。 |
| business-goals §5 业务规则全映射 | ⚠️ | 07 §3 已覆盖主要模块规则，见 `_control/v3/07-v3-scope-final.md:91-109`；但 business-goals §5 中的若干细则没有独立实施位置，见 `_control/v3/00-v3-business-goals.md:79-82`、`:87`、`:95-96`、`:118`、`:128`、`:132`。详见 High-01。 |
| Non-Goals N-01~N-18 全列 | ✅ | business-goals N-01~N-18 位于 `_control/v3/00-v3-business-goals.md:147-178`；07 §4 对应列出 N-01~N-18，含 D-041 撤销 N-08/N-09，见 `_control/v3/07-v3-scope-final.md:117-148`。 |
| 9 能力域 C1~C9 全覆盖 | ✅ | gap-audit C1~C9 综合矩阵见 `_control/v3/02-current-implementation-gap-audit.md:317-325`；07 §2.1/§2.2/§2.3 覆盖 C1~C9，见 `_control/v3/07-v3-scope-final.md:41-49`、`:58-68`、`:78-87`。 |

### 1.1 24 个 mockup 覆盖明细

| mockup | 07 落点 | 状态核对 |
|---|---|---|
| `_control/v3/mockups/admin-ai-config.html` | `_control/v3/07-v3-scope-final.md:40` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/admin-clean-companies.html` | `_control/v3/07-v3-scope-final.md:41` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/admin-collection-tasks.html` | `_control/v3/07-v3-scope-final.md:42` | 已覆盖，标 ✅ 本期做；状态引用需补 gap-audit 证据，详见 Medium-03。 |
| `_control/v3/mockups/admin-contact-classification.html` | `_control/v3/07-v3-scope-final.md:43` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/admin-customers.html` | `_control/v3/07-v3-scope-final.md:44` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/admin-data-sources.html` | `_control/v3/07-v3-scope-final.md:45` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/admin-email-templates.html` | `_control/v3/07-v3-scope-final.md:46` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/admin-intelligence-sources.html` | `_control/v3/07-v3-scope-final.md:47` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/admin-scoring-templates.html` | `_control/v3/07-v3-scope-final.md:48` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/admin-tendata-raw.html` | `_control/v3/07-v3-scope-final.md:49` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/admin-warmup-rules.html` | `_control/v3/07-v3-scope-final.md:50` | 已覆盖，标 ⛔ 已就绪；sending worker 限速仍需在 C7 落地，详见 Medium-04。 |
| `_control/v3/mockups/tenant-companies.html` | `_control/v3/07-v3-scope-final.md:58` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/tenant-curated-customers.html` | `_control/v3/07-v3-scope-final.md:59` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/tenant-dashboard.html` | `_control/v3/07-v3-scope-final.md:60` | 已覆盖，标 ⛔ V3 极简版。 |
| `_control/v3/mockups/tenant-email-monitor.html` | `_control/v3/07-v3-scope-final.md:61` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/tenant-intelligence.html` | `_control/v3/07-v3-scope-final.md:62` | 已覆盖，标 ✅ 本期做；C2 状态应避免写成 PARTIAL，详见 Medium-02。 |
| `_control/v3/mockups/tenant-send-plans-detail.html` | `_control/v3/07-v3-scope-final.md:63` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/tenant-send-plans-new.html` | `_control/v3/07-v3-scope-final.md:64` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/tenant-send-plans.html` | `_control/v3/07-v3-scope-final.md:65` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/tenant-settings-ai-provider.html` | `_control/v3/07-v3-scope-final.md:66` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/tenant-settings-keywords.html` | `_control/v3/07-v3-scope-final.md:67` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/tenant-settings-scoring.html` | `_control/v3/07-v3-scope-final.md:68` | 已覆盖，标 ✅ 本期做。 |
| `_control/v3/mockups/tenant-settings-team.html` | `_control/v3/07-v3-scope-final.md:69` | 已覆盖，标 ⛔ 已就绪。 |
| `_control/v3/mockups/tenant-templates.html` | `_control/v3/07-v3-scope-final.md:70` | 已覆盖，标 ⛔ 已就绪。 |

### 1.2 business-goals §5 到 07 §3 映射核对

| business-goals 规则 | 来源 | 07 实施位置 | 状态 |
|---|---|---|:-:|
| 关键词仅英文、归一化、配置者、无数量上限 | `_control/v3/00-v3-business-goals.md:79-82` | 07 只写“关键词归一化 + 跨租户复用”，见 `_control/v3/07-v3-scope-final.md:95` | ⚠️ 不完整 |
| 跨租户复用 | `_control/v3/00-v3-business-goals.md:82` | tenant-intelligence + KeywordMaster + UC-11 fan-out，见 `_control/v3/07-v3-scope-final.md:95` | ✅ |
| 反推采集数据源 | `_control/v3/00-v3-business-goals.md:86` | collection worker + admin 启动按钮，见 `_control/v3/07-v3-scope-final.md:96` | ✅ |
| 每日上限 1000 条 / 数据源 / 天 | `_control/v3/00-v3-business-goals.md:87` | 07 §3 未列独立实施位置 | ⚠️ 缺映射 |
| 数据流 raw → clean → tenant | `_control/v3/00-v3-business-goals.md:88-91` | cleanup_service + data foundation，见 `_control/v3/07-v3-scope-final.md:97` | ✅ |
| 客户 1 行 = 1 公司、来源标签精准 | `_control/v3/00-v3-business-goals.md:95-96` | 07 §3 未列独立实施位置 | ⚠️ 缺映射 |
| 10 项筛选 | `_control/v3/00-v3-business-goals.md:97-100` | tenant-companies + curated + clean fields，见 `_control/v3/07-v3-scope-final.md:98` | ✅ |
| 双层评分、PCB 7 维、S/A/B/C/D | `_control/v3/00-v3-business-goals.md:101-106` | scoring templates + worker，见 `_control/v3/07-v3-scope-final.md:99-100` | ✅ |
| 租户私有状态层 | `_control/v3/00-v3-business-goals.md:107-111` | tenant-companies Drawer + groups，见 `_control/v3/07-v3-scope-final.md:101` | ✅ |
| EngageLab 通道、域名验证、回信路径、发送速率 | `_control/v3/00-v3-business-goals.md:115-118` | 域名和通道有映射，见 `_control/v3/07-v3-scope-final.md:102-103`；回信路径和发送速率没有独立映射 | ⚠️ 不完整 |
| 联系人级 4 态、投递监控 6 指标 | `_control/v3/00-v3-business-goals.md:119-120` | emails 表 + EmailMonitor + webhook，见 `_control/v3/07-v3-scope-final.md:104-105` | ✅ |
| 联系人职位分类 | `_control/v3/00-v3-business-goals.md:121-128` | admin-contact-classification + classify，见 `_control/v3/07-v3-scope-final.md:106-107` | ✅，但“第 N 轮发未发过其他联系人”未单列 |
| 邮件计划结构、内容来源 4 选 1 | `_control/v3/00-v3-business-goals.md:129-132` | 多步骤序列有映射，见 `_control/v3/07-v3-scope-final.md:108`；内容来源 4 选 1未单列 | ⚠️ 不完整 |
| Sealos 8 部署单元 | `_control/v3/00-v3-business-goals.md:134-139` | 07 写入 §3 和 §2.3，见 `_control/v3/07-v3-scope-final.md:86`、`:109` | ⚠️ 数量冲突，详见 Medium-01 |

## 2. 派生准确性抽样（B 类）

### 2.1 ✅ 本期做：5 个抽样

| 抽样 | 07 写法 | gap-audit 依据 | 判断 |
|---|---|---|:-:|
| `admin-clean-companies.html` | C1 MISSING，✅ 干净库 UI 入口，见 `_control/v3/07-v3-scope-final.md:41` | C1 综合 MISSING，DB 和 cleanup_service MISSING，见 `_control/v3/02-current-implementation-gap-audit.md:52-56` | ✅ 准确 |
| `admin-contact-classification.html` | C3 MISSING，✅ 全新页面，见 `_control/v3/07-v3-scope-final.md:43` | C3 前端、API、DB、E2E 均 MISSING，见 `_control/v3/02-current-implementation-gap-audit.md:106-112` | ✅ 准确 |
| `admin-customers.html` | C7 PARTIAL，✅ 域名 Tab + EngageLab 验证，见 `_control/v3/07-v3-scope-final.md:44` | C7 前端、API、DB PARTIAL，域名验证缺口 C7-G1~G4，见 `_control/v3/02-current-implementation-gap-audit.md:224-239` | ✅ 准确 |
| `tenant-companies.html` | C4/C5/C6 缺口，✅ Drawer 4 件套 + 10 项筛选 + 调分字段，见 `_control/v3/07-v3-scope-final.md:58` | C4 私有操作缺前端和调分 DB/API，C5 筛选 MISSING，C6 评分 REWRITE，见 `_control/v3/02-current-implementation-gap-audit.md:136-156`、`:166-184`、`:194-214` | ✅ 准确 |
| `tenant-email-monitor.html` | C7 PARTIAL，✅ 6 指标接 EngageLab 回写，见 `_control/v3/07-v3-scope-final.md:61` | C7-G10~G12 明确 D-041 字段、webhook、EmailMonitor 6 指标缺口，见 `_control/v3/02-current-implementation-gap-audit.md:245-247` | ✅ 准确 |

### 2.2 ⛔ 本期不做：5 个抽样

| 抽样 | 07 写法 | gap-audit / business-goals 依据 | 判断 |
|---|---|---|:-:|
| `admin-ai-config.html` | PASS，⛔ 已就绪，见 `_control/v3/07-v3-scope-final.md:40` | business-goals 将 OpenRouter 配置列入 R-1，见 `_control/v3/00-v3-business-goals.md:49`；gap-audit 未列入 C1~C9 缺口 | ✅ 可接受 |
| `admin-data-sources.html` | PASS，⛔ 已就绪，见 `_control/v3/07-v3-scope-final.md:45` | business-goals 仍要求凭证维护流程通，见 `_control/v3/00-v3-business-goals.md:193`；07 未把该页面列为缺口 | ✅ 可接受 |
| `admin-warmup-rules.html` | PASS，⛔ 已就绪，见 `_control/v3/07-v3-scope-final.md:50` | C7-G9 仍要求 sending worker 受 warmup daily_limit 约束，见 `_control/v3/02-current-implementation-gap-audit.md:244` | ⚠️ UI 不做可以，但限速后端需在 §3 映射 |
| `tenant-dashboard.html` | §6 N-04，⛔ V3 极简版，见 `_control/v3/07-v3-scope-final.md:60` | N-04 明确完整 Dashboard / 跨计划趋势推迟，见 `_control/v3/00-v3-business-goals.md:154` | ✅ 准确 |
| `tenant-send-plans.html` | PASS，⛔ 已就绪，见 `_control/v3/07-v3-scope-final.md:65` | C7 原型 PASS，邮件计划列表不在 C7-G1~G12 缺口中心，见 `_control/v3/02-current-implementation-gap-audit.md:224-247` | ✅ 可接受 |

### 2.3 §5 OpenSpec change 覆盖抽样

| ✅ 项 | 07 §2 归属 | 07 §5 归属 | 判断 |
|---|---|---|:-:|
| `admin-clean-companies.html` | `_control/v3/07-v3-scope-final.md:41` | v3-data-foundation，见 `_control/v3/07-v3-scope-final.md:156` | ✅ |
| `admin-tendata-raw.html` | `_control/v3/07-v3-scope-final.md:49` | v3-data-foundation，见 `_control/v3/07-v3-scope-final.md:156` | ✅ |
| `tenant-intelligence.html` | `_control/v3/07-v3-scope-final.md:62` | v3-collection-pushback，见 `_control/v3/07-v3-scope-final.md:157` | ✅ |
| `tenant-send-plans-new.html` | `_control/v3/07-v3-scope-final.md:64` | v3-email-delivery + v3-contact-classification，见 `_control/v3/07-v3-scope-final.md:158`、`:160` | ✅ |
| `tenant-settings-scoring.html` | `_control/v3/07-v3-scope-final.md:68` | v3-tenant-companies，见 `_control/v3/07-v3-scope-final.md:159` | ✅ |

结论：§5 的 5 个 change 覆盖了 §2.1 + §2.2 的所有 ✅ UI 项；但 §5 后的说明行有计数错误，见 Low-01。

### 2.4 §6.1 业务侧成功标准一致性

| business-goals §7.2 | 07 §6.1 | 判断 |
|---|---|:-:|
| ≥ 1 个真实租户的真实关键词跑通完整采集 → 邮件投递闭环，见 `_control/v3/00-v3-business-goals.md:197` | 同项，见 `_control/v3/07-v3-scope-final.md:171` | ✅ |
| ≥ 1 封真实邮件被真实收件人在真实邮箱收到，见 `_control/v3/00-v3-business-goals.md:198` | 同项，见 `_control/v3/07-v3-scope-final.md:172` | ✅ |
| 客户库有 ≥ 50 个真实采集的客户，见 `_control/v3/00-v3-business-goals.md:199` | 同项，见 `_control/v3/07-v3-scope-final.md:173` | ✅ |
| 邮件计划有 ≥ 5 个真实发送过的步骤，见 `_control/v3/00-v3-business-goals.md:200` | 同项，见 `_control/v3/07-v3-scope-final.md:174` | ✅ |
| 跨租户隔离测试通过，见 `_control/v3/00-v3-business-goals.md:201` | “A 私有状态 B 不可见”，见 `_control/v3/07-v3-scope-final.md:175` | ✅ 更具体 |
| 无 D-041 独立成功标准 | D-041 投递监控 6 指标真实回写，见 `_control/v3/07-v3-scope-final.md:176` | ⚠️ 07 多出 1 条 |

结论：07 §6.1 与 business-goals §7.2 不是严格一致；新增 D-041 成功标准有业务依据（business-goals §5.4，见 `_control/v3/00-v3-business-goals.md:120`），但不是 §7.2 原文。

## 3. 真源冲突（C 类）

### 3.1 07 与 mockups 的冲突

未发现“mockup 有、07 完全漏列”的冲突。24 个文件均已列入 07 §2.1 + §2.2，证据见 `_control/v3/07-v3-scope-final.md:36-70`。

发现 1 个需要澄清的弱冲突：`tenant-dashboard.html` 原型包含较完整工作台内容，例如评分覆盖率、评分漏斗等，见 `_control/v3/mockups/tenant-dashboard.html:63-65`、`:151-160`；07 将其标为“V3 极简版（D-032）”，见 `_control/v3/07-v3-scope-final.md:60`。这与 business-goals N-04 推迟完整 Dashboard 一致，见 `_control/v3/00-v3-business-goals.md:154`，因此不是 blocker，但 07 可以明确“原型保留，V3 只接基础统计，不按全原型交付”。

### 3.2 07 与 business-goals 的冲突

存在 2 类冲突或不一致。

第一，business-goals §5 的若干细则没有进入 07 §3 实施位置交叉表。例如每日上限 1000 条见 `_control/v3/00-v3-business-goals.md:87`，客户 1 行 = 1 公司与来源标签精准见 `_control/v3/00-v3-business-goals.md:95-96`，发送速率见 `_control/v3/00-v3-business-goals.md:118`，内容来源 4 选 1见 `_control/v3/00-v3-business-goals.md:132`；07 §3 目前只有 15 行聚合规则，见 `_control/v3/07-v3-scope-final.md:95-109`。

第二，business-goals §5.5 写 Sealos 集群上跑 8 个部署单元，其中后台 worker 是 4 个，见 `_control/v3/00-v3-business-goals.md:136-139`；07 §2.3 又写“Sealos 5 worker 容器 + k8s yaml”，见 `_control/v3/07-v3-scope-final.md:86`，并在 §3 写“Sealos 8 部署单元（含 4 worker + cleanup_service）”，见 `_control/v3/07-v3-scope-final.md:109`。如果含 cleanup_service，则不是 8 个部署单元。

### 3.3 07 与 gap-audit 的冲突

存在 3 个需要修订的状态引用问题。

第一，gap-audit C2 综合状态是 MISSING，见 `_control/v3/02-current-implementation-gap-audit.md:84` 和综合矩阵 `_control/v3/02-current-implementation-gap-audit.md:318`；07 在 `tenant-intelligence.html` 行写 “C2 PARTIAL”，见 `_control/v3/07-v3-scope-final.md:62`。如果 07 想表达前端局部 PARTIAL，应写“C2 综合 MISSING；前端 PARTIAL”。

第二，07 在 `admin-collection-tasks.html` 行引用“按钮已 PASS（codex B-01）+ D-035 限制”，见 `_control/v3/07-v3-scope-final.md:42`；但 3 真源里的 gap-audit C1~C9 没有“codex B-01”证据入口，相关采集缺口主要在 C2 和 C8，见 `_control/v3/02-current-implementation-gap-audit.md:72-96`、`:255-279`。这使该行派生证据不够自洽。

第三，07 §2.3 写“4 worker base class（retry / heartbeat / 幂等）”现状为 C8 SKELETON，见 `_control/v3/07-v3-scope-final.md:85`；gap-audit C8 没有 SKELETON 状态，而是 DB MIGRATION-BLOCKED、Worker WORKER-NOT-DEPLOYED、E2E MISSING，见 `_control/v3/02-current-implementation-gap-audit.md:263-267`，并把 worker 监控/日志/重试/幂等列为 C8-G5 缺口，见 `_control/v3/02-current-implementation-gap-audit.md:277`。

## 4. Blocker / High / Medium / Low

### Blocker

未发现必须推翻 07 派生方向的 blocker。24 个 mockup、N-01~N-18、C1~C9 均已进入 07 的范围框架，见 `_control/v3/07-v3-scope-final.md:36-87`、`:117-148`。

### High

| ID | Finding | 证据 | 建议 |
|---|---|---|---|
| High-01 | business-goals §5 业务规则没有全部映射到 07 §3。漏掉或未单列的细则包括：关键词仅英文/数量无上限、每日上限 1000 条、客户 1 行 = 1 公司、来源标签精准、发送速率、回信路径不经平台、内容来源 4 选 1、第 N 轮发未发过其他联系人。 | business-goals 来源见 `_control/v3/00-v3-business-goals.md:79-82`、`:87`、`:95-96`、`:117-118`、`:128`、`:132`；07 §3 现有映射见 `_control/v3/07-v3-scope-final.md:95-109`。 | 签字前补齐 07 §3 行级映射。可以不新增工作量，但必须写清“实施位置”：API 校验、collection scheduler 限速、clean company 唯一行约束、tenant UI 标签、sending worker 限速、模板选择 UI/API、sequence recipient selection。 |
| High-02 | 07 §6.1 与 business-goals §7.2 不严格一致：07 多出 D-041 投递监控 6 指标真实回写。该项有 business-goals §5.4 依据，但不是 §7.2 成功标准原文。 | business-goals §7.2 只有 5 条，见 `_control/v3/00-v3-business-goals.md:195-201`；07 §6.1 有 6 条，新增项见 `_control/v3/07-v3-scope-final.md:176`。 | 若检查项要求“与 §7.2 一致”，则把 D-041 从 §6.1 移到“补充验收 / 功能验收”或明确标注“新增自 §5.4，不是 §7.2 原文”。 |

### Medium

| ID | Finding | 证据 | 建议 |
|---|---|---|---|
| Medium-01 | Sealos 部署单元数量表述冲突：business-goals 是 8 个部署单元含 4 worker；07 同时写 5 worker 容器和“8 部署单元含 cleanup_service”。 | business-goals 8 单元见 `_control/v3/00-v3-business-goals.md:136-139`；07 5 worker 见 `_control/v3/07-v3-scope-final.md:86`；07 “8 部署单元含 cleanup_service”见 `_control/v3/07-v3-scope-final.md:109`；gap-audit C8 要 4 worker + cleanup_service，见 `_control/v3/02-current-implementation-gap-audit.md:257`。 | 统一为“9 个部署单元 = 原 8 + cleanup_service”或“8 应用单元 + 1 cleanup worker”，避免签字后部署清单口径冲突。 |
| Medium-02 | C2 状态引用不准确：07 写 C2 PARTIAL，但 gap-audit C2 综合是 MISSING。 | 07 行见 `_control/v3/07-v3-scope-final.md:62`；gap-audit C2 综合 MISSING 见 `_control/v3/02-current-implementation-gap-audit.md:84`、`:318`。 | 改为“C2 综合 MISSING（前端 PARTIAL）”。 |
| Medium-03 | `admin-collection-tasks.html` 的 ✅ 依据引用了“codex B-01”，不属于本次明确的 3 真源。 | 07 行见 `_control/v3/07-v3-scope-final.md:42`；gap-audit C2/C8 相关范围见 `_control/v3/02-current-implementation-gap-audit.md:72-96`、`:255-279`。 | 用 gap-audit C2/C8 的缺口语言重写，或在 07 注明该行仅为“按 D-035 复核 UI 行为”，不要把外部审查代号作为派生证据。 |
| Medium-04 | 预热档位 UI 标“已就绪”可以成立，但 business-goals 的发送速率规则没有在 07 §3 独立映射。 | 07 `admin-warmup-rules.html` 见 `_control/v3/07-v3-scope-final.md:50`；business-goals 发送速率见 `_control/v3/00-v3-business-goals.md:118`；gap-audit C7-G9 见 `_control/v3/02-current-implementation-gap-audit.md:244`。 | 在 07 §3 增加“发送速率 / 预热档位限速 → sending worker + domain_warmup_status.daily_limit”。 |
| Medium-05 | 07 §2.3 的“4 worker base class”现状写 C8 SKELETON，但 gap-audit C8 没有这个状态，且 C8-G5 是缺口。 | 07 行见 `_control/v3/07-v3-scope-final.md:85`；gap-audit C8 状态见 `_control/v3/02-current-implementation-gap-audit.md:263-267`；C8-G5 见 `_control/v3/02-current-implementation-gap-audit.md:277`。 | 改为“C8-G5 MISSING/PARTIAL：worker 监控 / 日志 / 重试 / 幂等待补”，不要写 SKELETON。 |

### Low

| ID | Finding | 证据 | 建议 |
|---|---|---|---|
| Low-01 | 07 §5 后说明写“6 个原型已 PASS 不开发”，但后面列了 11 个名称。 | `_control/v3/07-v3-scope-final.md:162`。 | 改为“11 个原型已 PASS 不开发”，或拆成 admin 5 + tenant 6。 |
| Low-02 | 07 §2.1/§2.2 的汇总语句和 §5 说明口径不完全一致：§2 说 Admin 不做 6、Tenant 不做 7，其中包含 tenant-dashboard 极简版；§5 又把 tenant-dashboard 单独列为 1 个极简版。 | `_control/v3/07-v3-scope-final.md:52`、`:72`、`:162-163`。 | 保持一种口径：建议写“本期开发 11 个；已 PASS 不开发 11 个；极简保留 1 个；总计 23? ”不合适，因为总数应 24。更清晰写法是“开发 11；已 PASS 11；极简 1；另 admin-collection 复核算开发项”。 |

## 5. 给用户的“无技术背景版”摘要

1. 这份 07 没有跑偏：24 个界面原型都被纳入了，18 个不做项也都列了，9 个缺口能力域也都有去处。
2. 现在还不建议签字，因为“业务规则 → 实施位置”的表漏了几个细规则；这些规则不是大新功能，但如果不写进去，后面开发容易漏。
3. 邮件投递监控 D-041 在业务目标里确实要做，但 07 把它加进“业务侧成功标准”后，已经不再和 business-goals §7.2 原文完全一致，需要标清楚来源。
4. 部署口径要改清楚：到底是 8 个部署单元，还是加 cleanup_service 后变 9 个；现在 07 两种说法混在一起。
5. 建议修完 High-01、High-02、Medium-01、Medium-02 后再签字；其余 Medium/Low 可以同步小改。

