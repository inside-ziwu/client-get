# Codex Code Review · 第 2 轮 — V3 Plan 修复验证

> 审查日期：2026-05-06
> 审查范围：第 1 轮 22 处 finding 修复验证 + 新引入风险检查
> 第 1 轮报告：_control/reviews/codex-code-review-v3-plan-prep.md

## 0. 总体结论

第 1 轮 22 处 finding 中，**15 处已完全修复，6 处部分修复，1 处因 D-041 已失效/不适用**。但本轮发现 4 个新的或残留的一致性问题，其中 **N-01 是签字阻塞**：V3 最高权威 `_control/v3/00-v3-target-spec.md` 仍保留“不开信追踪 / 不记录退信 / 主联系人 / UC-30 手动标已回复 / 公司级中断”等旧口径，和 D-041、D-033、D-034 冲突。建议用户**暂不签字**；先修 N-01、N-02、N-03，再做一次轻量 diff 复核。

## 1. Finding 修复验证表

| ID | 第 1 轮问题 | 修复状态 | 残留 / 备注 |
|---|---|:-:|---|
| B-01 | UC-10 admin 启动按钮被误判为 MISSING | ⚠️ 部分修复 | `openspec/changes/v3-collection-pushback/tasks.md:12-20` 已改为“复核现有按钮 + D-035 限制 direct channel”，且 `proposal.md:10` 明确按钮已存在；但 `_control/v3/03-v3-delivery-plan.md:156-158` 仍写“加启动首采按钮”，`proposal.md:52` 也仍写“加按钮”。 |
| B-02 | UC-21 评分调整后端 / DB 没就绪 | ✅ 完全修复 | `openspec/changes/v3-tenant-companies/tasks.md:16-31` 已把 T-TC-08/09A/09B 放在前端 T-TC-20 前；`_control/v3/02-current-implementation-gap-audit.md:147-149` 明确 `score_adjustment` 不覆盖 `total_score`，用 `final_score = total_score + score_adjustment`。 |
| B-03 | 联系人分类数据模型与 D-037/M.1 不一致 | ⚠️ 部分修复 | tasks 主体已改为 3 表 + `v_tenant_contact_classified` 视图：`tasks.md:13-22`；但 `proposal.md:48` 仍写 `position_classification_compiled` 缓存，`proposal.md:74` / `82` 仍写新增 4 张表，`tasks.md:9` / `72` 仍写 4 表。 |
| B-04 | 邮件 tasks 把开信 / 退信继续列为 Non-goals | ✅ 完全修复 | 修复后的业务目标 `00-v3-business-goals.md:120` 加 D-041 投递监控，`163-164` 标 N-08/N-09 已撤销；`v3-email-delivery/proposal.md:54-58` 明确开信追踪和退信记录 V3 必做；`tasks.md:49-70` 已拆 DB 字段、webhook、监控 UI；`02-gap-audit.md:245-251` 加 C7-G10/G11/G12；`04-open-questions.md:140` 新增 D-041。另见新问题 N-01：最高真源未同步。 |
| B-05 | T-DF-10 要直接改 CLAUDE.md，违反工作区规则 | ✅ 完全修复 | `openspec/changes/v3-data-foundation/tasks.md:14` 已改为记录到 `_control/v3/slices/slice-0-dev-runtime-baseline.md`，并明确不直接改 AGENTS.md / CLAUDE.md。 |
| B-06 | Acceptance Matrix ID 映射不完整 / 错位 | ✅ 完全修复 | `_control/v3/01-v3-acceptance-matrix.md:29-40` 已覆盖 D-035、D-002/D-024/D-031、D-041；`V3-COL-004` 在 `32` 单独覆盖 cleanup_service +11 字段。 |
| H-01 | Wave 1 被过度声明为 Wave 2 全部硬依赖 | ⚠️ 部分修复 | `_control/v3/03-v3-delivery-plan.md:21-22` 和 `v3-data-foundation/proposal.md:17-25` 已区分 C3 软依赖；但 `v3-data-foundation/proposal.md:68` 仍写“全部 4 个 Wave 2 change 阻塞等待本 change 完成”，与 C3 软依赖冲突。 |
| H-02 | C4 4 件套仍混入 UC-24 主联系人 | ✅ 完全修复 | `02-gap-audit.md:129-153`、`v3-tenant-companies/tasks.md:12-20`、`proposal.md:11` 都已改为 UC-21 调分 + UC-22 备注 + UC-23 标签 + D-020 群组。另见 N-01：最高真源仍有旧 UC-24。 |
| H-03 | contact-rules 删除范围太窄 | ✅ 完全修复 | `v3-contact-classification/tasks.md:43-53` 覆盖 5 处：tenant 路由、页面目录、Onboarding、shared-api/queryKeys、后端 settings.py，并加全仓残留搜索。 |
| H-04 | clean_companies +9 字段应改为 +11 字段 | ✅ 完全修复 | `02-gap-audit.md:65`、`178-179`，`03-delivery-plan.md:21` / `146`，`v3-data-foundation/proposal.md:14` / `35`，`v3-tenant-companies/tasks.md:8` 均已写 D-038 9 + D-039 2 = +11。 |
| H-05 | Data Foundation Why 没分清生产 / 迁移 / V3 重构 | ✅ 完全修复 | `v3-data-foundation/proposal.md:8-15` 已拆三层：生产停 0006、0007~0013 已写未上线、schema.sql 漂移 + V3 新字段/worker 未实现。 |
| H-06 | tenant-companies 写不阻塞主链，但实际阻塞 Slice 5 | ✅ 完全修复 | `v3-tenant-companies/proposal.md:3-5` 和 `tasks.md:3` 明确“不阻塞 Slice 3，阻塞 Slice 5 E2E”；`03-delivery-plan.md:98` 写 Slice 5 前置依赖包含 tenant-companies。 |
| M-01 | D-035 后 direct channel 需明确处理 | ✅ 完全修复 | `v3-collection-pushback/tasks.md:16-18` 已要求 UI 隐藏/禁用 direct，后端拒绝 `channel=direct`。 |
| M-02 | level/category 字段少 display_name / sort_order / timestamps | ⚠️ 部分修复 | `v3-contact-classification/tasks.md:17-19` 已补 display_name、sort_order、created_at；但 category 没有 updated_at，和用户本轮“含 display_name / sort_order / created_at / updated_at”的核对要求不完全一致。 |
| M-03 | C6 评分模板现状描述不精确 | ✅ 完全修复 | `02-gap-audit.md:194-200` 明确 admin platform 模板已有 industry 查询雏形，tenant 权重分离和 PCB 7 维未实现。 |
| M-04 | compiled 表如果保留需补重建 / 失效策略 | ⚠️ 部分修复 | 方案 A 本应删除 compiled；`v3-contact-classification/tasks.md:15` 和 `proposal.md:33` 已说不做 compiled，但 `proposal.md:48` 又写 compiled 缓存。 |
| M-05 | 拨测语义和 EngageLab 状态需区分 | ✅ 不适用 / 已被 D-041 覆盖 | D-041 后改做送达分级与投递监控，`v3-email-delivery/tasks.md:49-70` 已新增追踪、webhook、监控 UI；原 finding 不再按旧语义判断。 |
| L-01 | C2-G0 引用不存在 | ✅ 完全修复 | 修复后 `02-gap-audit.md:86-95` 仅保留 C2-G1~G5；本轮 `rg C2-G0 _control/v3 openspec/changes/v3-*` 未发现残留。 |
| L-02 | 4 个 tasks.md review 输出文件名不统一 | ✅ 完全修复 | 5 个 tasks 均统一为 `_control/reviews/ce-review-v3-*.md`、`gstack-eng-review-v3-*.md`、`codex-code-review-v3-*.md`，见 `v3-data-foundation/tasks.md:61-64`、`v3-collection-pushback/tasks.md:61-64`、`v3-email-delivery/tasks.md:87-90`、`v3-tenant-companies/tasks.md:98-101`、`v3-contact-classification/tasks.md:65-68`。 |

## 2. 新引入的问题（如有）

### N-01 · Blocker · 最高真源 `00-v3-target-spec.md` 未同步 D-041 / D-033 / D-034

`AGENTS.md` 规定 `_control/v3/00-v3-target-spec.md` 是 V3 唯一权威，但该文件仍保留多处旧口径：

- `_control/v3/00-v3-target-spec.md:59` 仍写 D-022 = UC-21~24 + 主联系人切换，和 `04-open-questions.md:138` 的 D-022 修订版冲突。
- `_control/v3/00-v3-target-spec.md:139` 仍把 UC-24“设置主联系人”列入 V3 UC 表，和 `04-open-questions.md:130` 的 D-033“UC-24 取消”冲突。
- `_control/v3/00-v3-target-spec.md:170-171` 仍写“1.0 不显式记录退信 / 不做开信追踪”，和 `04-open-questions.md:140` D-041 以及 `00-v3-business-goals.md:120` 冲突。
- `_control/v3/00-v3-target-spec.md:200-205` 仍写主联系人、目标策略、UC-30 手动标已回复、公司级中断、UC-31~33 复盘，和 D-033/D-034/D-032 冲突。
- `_control/v3/00-v3-target-spec.md:406` 仍写 SMTP 250 但退信时状态仍“投递完成”，和 D-041 送达分级冲突。

影响：即使下游 OpenSpec tasks 大多修好了，签字时仍会以最高真源为准，导致后续实现者重新按旧规则开发。**此项不修，不建议用户签字。**

### N-02 · High · Delivery Plan 仍有第 1 轮已修 finding 的残留执行指令

`_control/v3/03-v3-delivery-plan.md` 仍有两处会误导执行：

- `03-v3-delivery-plan.md:122` 仍要求把命令补到 `CLAUDE.md`，和 B-05 修复后的 `v3-data-foundation/tasks.md:14` 冲突。
- `03-v3-delivery-plan.md:156-158` 仍把 UC-10 写成“admin/CollectionTasks 加启动首采按钮”，和 B-01 修复后的 `v3-collection-pushback/tasks.md:14-18` 冲突。

影响：Delivery Plan 是 Gate 5 前置文件；即使 tasks 正确，执行者按 Delivery Plan 走仍可能重复造按钮或改不该改的文件。

### N-03 · High · `v3-contact-classification` proposal 仍混入 compiled / 4 表口径

该问题是 B-03/M-04 的直接残留，但严重程度足以单列：

- `openspec/changes/v3-contact-classification/proposal.md:33` 说不做 compiled。
- 同一文件 `proposal.md:48` 又要求 `position_classification_compiled` 表预编译加速。
- `proposal.md:74` / `82` 写新增 4 张表；`tasks.md:9` / `72` 也写 4 表，但正确口径应是 3 表 + 1 视图，见 `tasks.md:13-20`。

影响：同一个 change 内自相矛盾，实施时可能重新引入 compiled 表，推翻用户拍板的方案 A。

### N-04 · Medium · `v3-email-delivery` proposal 的 Impact 没同步 D-041 DB 改动

`openspec/changes/v3-email-delivery/tasks.md:53-55` 已新增 emails 追踪字段和 `email_events` 事件表任务；但 `proposal.md:72` 仍写“domain_warmup_status / emails 已有，不加新表”。如果 `email_events` 在目标 schema 中确实已有，应把 tasks 改成“对齐/扩展”；如果没有，就应修 proposal Impact。

影响：不阻塞方向，但会让 DB migration 工作量和 review 范围被低估。

## 3. 残留风险（如有）

1. **D-037 字段 timestamps 口径仍需定死**：`04-open-questions.md:144-151` 的 M.1 对 category/keyword 只写了 created_at，用户本轮核对要求提到 updated_at。建议在修 N-03 时一次性决定：level/category/keyword 三表是否全部都要 `created_at` + `updated_at`。

2. **C3 软依赖仍有一句硬阻塞口径**：`v3-data-foundation/proposal.md:22-25` 写 C3 可提前启动，但 `proposal.md:68` 写全部 4 个 Wave 2 change 阻塞。建议改成“3 个硬阻塞 + C3 软依赖”。

3. **B-04 在下游已修，但最高真源未修**：业务目标、Gap Audit、email-delivery tasks 都已按 D-041 修；真正风险集中在 `_control/v3/00-v3-target-spec.md`，不要只修 OpenSpec。

4. **Review 输出文件名已统一，但 Delivery Plan 状态列仍写待创建**：`03-v3-delivery-plan.md:266-270` 仍显示 5 个 change `__待创建__`，而本轮这些目录已存在。不是签字阻塞，但会让 PM 误判进度。

## 4. 给用户的"无技术背景版"摘要

- **暂不建议签字**：22 个老问题大多修好了，但最高权威文件还留着旧规则；签了会让后续开发按旧规则跑偏。
- **最要紧修 3 处**：`00-v3-target-spec.md` 同步 D-041/D-033/D-034；`03-v3-delivery-plan.md` 删除“改 CLAUDE.md / 新加启动按钮”残留；`v3-contact-classification/proposal.md` 删除 compiled 和 4 表口径。
- **邮件追踪方向已经确认**：开信追踪、退信、送达分级已经在 business-goals、gap-audit、email-delivery tasks 里进了 V3 必做。
- **客户库 4 件套方向基本正确**：调分已补 DB/API/scoring 前置，群组替代主联系人也写进 tenant-companies。
- **建议收尾方式**：先修 N-01~N-03，再让 Codex 做一次只看 5 个文件的 15 分钟轻量复核。

## 5. 原始需求 → 已实现 / 未实现 对照清单

| 原始需求 | 状态 | 证据 |
|---|:-:|---|
| 只检查第 1 轮 22 处 finding 是否修复 | ✅ 已实现 | 本报告 §1 覆盖 B-01~B-06、H-01~H-06、M-01~M-05、L-01~L-02。 |
| 找出修复过程中是否引入新问题 | ✅ 已实现 | 本报告 §2 列 N-01~N-04。 |
| 不修改被审文件 / 不写代码 | ✅ 已实现 | 本轮只新增 review 报告，未修改 `_control/v3/*` 或 `openspec/changes/v3-*` 被审文件。 |
| 报告写到指定路径 | ✅ 已实现 | `_control/reviews/codex-code-review-v3-plan-prep-round2.md`。 |
| 每条 finding 有具体路径或行号 | ✅ 已实现 | §1 每行均含路径与行号引用。 |
| 简体中文 | ✅ 已实现 | 全文中文。 |
| 是否建议用户签字 | ✅ 已实现 | §0 与 §4 明确：暂不建议签字，先修 N-01~N-03。 |

## 6. 逐项核验证据日志

> 本节用于把 §1 的表格证据展开，便于 PM 或下一轮 Codex 直接按文件跳转复核。结论不重复扩写，只记录“查了什么、看到什么、判断是什么”。

### B-01 核验证据

- 核对对象：`v3-collection-pushback` proposal/tasks + Delivery Plan。
- `openspec/changes/v3-collection-pushback/tasks.md:12-20`：标题已改成“UC-10 admin 启动按钮复核 + D-035 channel 限制”。
- `openspec/changes/v3-collection-pushback/tasks.md:14`：明确按钮已实现，不再 from-scratch。
- `openspec/changes/v3-collection-pushback/tasks.md:16-18`：任务变成复核现有 triggerMutation、禁用 direct、后端拒绝 direct。
- `openspec/changes/v3-collection-pushback/proposal.md:10`：Why 中也承认 `triggerMutation`、API、行内按钮已存在。
- 残留：`_control/v3/03-v3-delivery-plan.md:157` 仍写“加启动首采按钮”。
- 判断：OpenSpec tasks 已修，但 Gate 5 文件仍会误导执行，因此部分修复。

### B-02 核验证据

- 核对对象：tenant-companies tasks/proposal + Gap Audit C4。
- `openspec/changes/v3-tenant-companies/tasks.md:16`：新增“DB + 后端先行”小节。
- `openspec/changes/v3-tenant-companies/tasks.md:18`：先做 alembic 字段，含 `score_adjustment` 和审计字段。
- `openspec/changes/v3-tenant-companies/tasks.md:19`：再扩展 `PATCH /prospects/{id}`。
- `openspec/changes/v3-tenant-companies/tasks.md:20`：再改 scoring worker 用 final_score 计算。
- `openspec/changes/v3-tenant-companies/tasks.md:29-31`：前端评分表单排在 DB/API/scoring 之后。
- `_control/v3/02-current-implementation-gap-audit.md:147-149`：同样明确不覆盖 `total_score`。
- 判断：完全修复。

### B-03 核验证据

- 核对对象：contact-classification proposal/tasks + Gap Audit C3。
- `_control/v3/02-current-implementation-gap-audit.md:109`：Gap Audit 写 3 表 + `v_tenant_contact_classified` 视图。
- `_control/v3/02-current-implementation-gap-audit.md:118`：C3-G1 同样写 3 表 + 视图。
- `openspec/changes/v3-contact-classification/tasks.md:13-20`：tasks 主体已按 3 表 + 1 视图拆任务。
- `openspec/changes/v3-contact-classification/proposal.md:26-33`：proposal 数据模型段也写 3 表 + 1 视图，并声明不做 compiled。
- 残留 1：`proposal.md:48` 又写 `position_classification_compiled` 表预编译加速。
- 残留 2：`proposal.md:74` / `82` 仍写 4 张表。
- 残留 3：`tasks.md:9` / `72` 仍写 4 表。
- 判断：部分修复，且残留会引导实现重新建 compiled 表。

### B-04 核验证据

- 核对对象：business-goals、email-delivery proposal/tasks、gap-audit、open-questions。
- `_control/v3/00-v3-business-goals.md:120`：§5.4 新增 D-041 投递监控 6 指标。
- `_control/v3/00-v3-business-goals.md:163-164`：N-08/N-09 已删除线标撤销。
- `openspec/changes/v3-email-delivery/proposal.md:54-58`：新增 D-041，开信追踪和退信记录列为必做。
- `openspec/changes/v3-email-delivery/tasks.md:53-70`：已有 DB 字段、webhook、EmailMonitor UI 任务。
- `_control/v3/02-current-implementation-gap-audit.md:245-247`：C7-G10/G11/G12 已加。
- `_control/04-open-questions.md:140`：D-041 新决策已登记。
- 判断：指定修复面完全修复；但最高真源未同步，单列 N-01。

### B-05 核验证据

- 核对对象：data-foundation tasks + Delivery Plan。
- `openspec/changes/v3-data-foundation/tasks.md:14`：T-DF-10 明确只写 `_control/v3/slices/slice-0-dev-runtime-baseline.md`。
- 同行明确“不直接改 AGENTS.md / CLAUDE.md”。
- 同行把 AGENTS/CLAUDE 更新降级为“人类维护者待补建议”。
- 残留：`_control/v3/03-v3-delivery-plan.md:122` 仍写补 `CLAUDE.md`。
- 判断：B-05 在 tasks 层完全修复；Delivery Plan 残留列 N-02。

### B-06 核验证据

- 核对对象：Acceptance Matrix 18 项。
- `_control/v3/01-v3-acceptance-matrix.md:28-45`：18 项候选已完整列出。
- `_control/v3/01-v3-acceptance-matrix.md:31`：V3-COL-003 写 D-035 不调外贸通。
- `_control/v3/01-v3-acceptance-matrix.md:32`：V3-COL-004 补 cleanup_service 字段结构化。
- `_control/v3/01-v3-acceptance-matrix.md:36`：V3-MAIL-001 是 admin 创建租户时配域名 + 预热档位。
- `_control/v3/01-v3-acceptance-matrix.md:40`：V3-MAIL-005 含 D-041 追踪字段。
- 判断：完全修复。

### H-01 核验证据

- 核对对象：Delivery Plan Wave 原则 + data-foundation proposal。
- `_control/v3/03-v3-delivery-plan.md:21`：明确 C3 是软依赖。
- `_control/v3/03-v3-delivery-plan.md:22`：写 C3 可在 Wave 1.A 后提前启动。
- `openspec/changes/v3-data-foundation/proposal.md:17-23`：硬依赖与软依赖分开列。
- `openspec/changes/v3-data-foundation/proposal.md:25`：写 Wave 1.A + 1.B 后解锁主体并行，C3 可提前启动。
- 残留：`proposal.md:68` 仍写“全部 4 个 Wave 2 change 阻塞等待本 change 完成”。
- 判断：部分修复。

### H-02 核验证据

- 核对对象：Gap Audit C4 + tenant-companies proposal/tasks。
- `_control/v3/02-current-implementation-gap-audit.md:129`：标题已改为 UC-21 调分、UC-22 备注、UC-23 标签、D-020 群组。
- `_control/v3/02-current-implementation-gap-audit.md:132`：说明 UC-24 主联系人已取消。
- `openspec/changes/v3-tenant-companies/tasks.md:12-20`：tasks 同步为 4 件套新口径。
- `openspec/changes/v3-tenant-companies/proposal.md:11`：proposal 明确第 4 件套不是主联系人。
- 残留：最高真源仍有旧 UC-24，见 N-01。
- 判断：本 finding 涉及文件完全修复。

### H-03 核验证据

- 核对对象：contact-classification tasks 删除范围。
- `openspec/changes/v3-contact-classification/tasks.md:47`：删除 tenant router contact-rules 路由。
- `tasks.md:48`：删除 Settings/ContactRules 目录。
- `tasks.md:49`：删除 Onboarding StepContactRules。
- `tasks.md:50`：删除 shared-api contact-rules 客户端和 queryKeys。
- `tasks.md:51`：删除后端 settings.py contact-rules CRUD。
- `tasks.md:52`：加全仓残留搜索。
- 判断：完全修复。

### H-04 核验证据

- 核对对象：gap-audit、delivery-plan、data-foundation、tenant-companies。
- `_control/v3/02-current-implementation-gap-audit.md:65`：C1-G4 写 +11 字段。
- `_control/v3/02-current-implementation-gap-audit.md:178-179`：C5 也写 +11 字段，映射 9 字段。
- `_control/v3/03-v3-delivery-plan.md:146`：Slice 1.B 写 clean_companies +11 字段。
- `openspec/changes/v3-data-foundation/proposal.md:35`：proposal 写 D-038 9 + D-039 2。
- `openspec/changes/v3-data-foundation/tasks.md:35-36`：tasks 拆 T-DF-33-A 9 字段、T-DF-33-B 2 字段。
- `openspec/changes/v3-tenant-companies/tasks.md:8`：依赖写 +11 字段。
- 判断：完全修复。

### H-05 核验证据

- 核对对象：data-foundation proposal Why。
- `openspec/changes/v3-data-foundation/proposal.md:8`：明确这是 codex H-05 修订。
- `proposal.md:10-13`：第一层写生产真值、迁移层已写未上线、schema.sql 漂移。
- `proposal.md:14`：第二层写 D-008 与 +11 字段等 V3 业务规则不支撑。
- `proposal.md:15`：第三层写 worker 代码 ready 但未部署。
- 判断：完全修复。

### H-06 核验证据

- 核对对象：tenant-companies proposal/tasks + Delivery Plan。
- `openspec/changes/v3-tenant-companies/proposal.md:3-5`：明确不阻塞 Slice 3，阻塞 Slice 5 全 V3 E2E。
- `openspec/changes/v3-tenant-companies/tasks.md:3`：tasks 顶部同样写“Slice 5 E2E 验收需完成”。
- `_control/v3/03-v3-delivery-plan.md:98`：Slice 5 前置依赖含 v3-tenant-companies。
- `_control/v3/03-v3-delivery-plan.md:105-107`：C4/C5/C6 表达为独立能力，但 Slice 5 验收。
- 判断：完全修复。

### M-01 核验证据

- 核对对象：collection-pushback tasks。
- `openspec/changes/v3-collection-pushback/tasks.md:12`：小节标题已含 D-035 channel 限制。
- `tasks.md:17`：UI 隐藏或禁用 direct channel。
- `tasks.md:18`：后端拒绝 `channel=direct`。
- `proposal.md:28`：proposal What Changes 也写仅允反推。
- 判断：完全修复。

### M-02 核验证据

- 核对对象：contact-classification tasks 字段。
- `openspec/changes/v3-contact-classification/tasks.md:17`：level 有 display_name、sort_order、created_at、updated_at。
- `tasks.md:18`：category 有 display_name、sort_order、created_at。
- `tasks.md:19`：keyword 有 keyword 小写、created_at。
- 残留：本轮用户重点验证文字要求 level/category 含 updated_at；category 仍未列 updated_at。
- 判断：部分修复。

### M-03 核验证据

- 核对对象：Gap Audit C6。
- `_control/v3/02-current-implementation-gap-audit.md:194-196`：前端和后端状态已拆分。
- `02-current-implementation-gap-audit.md:196`：明确 admin platform 模板已有 industry 字段查询雏形。
- 同行也明确 tenant 权重分离未实现。
- `02-current-implementation-gap-audit.md:197`：DB schema 仍需行业模板和 tenant_scoring_weights。
- 判断：完全修复。

### M-04 核验证据

- 核对对象：contact-classification proposal/tasks。
- `openspec/changes/v3-contact-classification/tasks.md:15`：tasks 写删 compiled 表。
- `openspec/changes/v3-contact-classification/proposal.md:33`：proposal 写不做 compiled 缓存表。
- 残留：`proposal.md:48` 又写 compiled 表预编译加速。
- 判断：部分修复，和 B-03 同源。

### M-05 核验证据

- 核对对象：D-041 后 email-delivery tasks。
- `openspec/changes/v3-email-delivery/tasks.md:49`：新增 EmailMonitor + D-041 投递追踪小节。
- `tasks.md:53-55`：DB 字段和事件表任务。
- `tasks.md:59-63`：EngageLab open_tracking、webhook、签名校验、兜底拉取。
- `tasks.md:67-70`：监控 UI 接 6 指标和退信原因。
- 判断：原“拨测语义” finding 被 D-041 覆盖，不再按旧口径判定。

### L-01 核验证据

- 核对对象：Gap Audit 缺口编号与全仓搜索。
- `_control/v3/02-current-implementation-gap-audit.md:86-95`：C2 子项为 C2-G1~G5。
- 本轮 `rg C2-G0 _control/v3 openspec/changes/v3-*` 未发现残留。
- 判断：完全修复。

### L-02 核验证据

- 核对对象：5 个 tasks 的 Review 输出路径。
- `openspec/changes/v3-data-foundation/tasks.md:61-64`：统一到 `ce-review-v3-data-foundation.md` 等。
- `openspec/changes/v3-collection-pushback/tasks.md:61-64`：统一。
- `openspec/changes/v3-email-delivery/tasks.md:87-90`：统一。
- `openspec/changes/v3-tenant-companies/tasks.md:98-101`：统一。
- `openspec/changes/v3-contact-classification/tasks.md:65-68`：统一。
- 判断：完全修复。

## 7. 建议修复清单（给下一轮执行者）

### 必修 1：同步最高真源

- 文件：`_control/v3/00-v3-target-spec.md`。
- 删除或改写 D-022 旧口径：不要再写 UC-21~24 + 主联系人切换。
- 删除或改写 UC-24 主联系人表格项：标 OUT-OF-V3 或按 D-033 注释保留 schema 但 V3 不写入。
- 删除或改写 Non-goals 中“不记录退信 / 不开信追踪”两条。
- 删除或改写路径 B 中 UC-30 手动标已回复、公司级中断、UC-31~33 复盘。
- 删除或改写 edge case 中 SMTP 250 但退信仍投递完成。
- 加入 D-041 到决策表，并引用 business-goals §5.4。

### 必修 2：修 Delivery Plan 残留

- 文件：`_control/v3/03-v3-delivery-plan.md`。
- `line 122`：把写 `CLAUDE.md` 改为写 slice-0 baseline 报告。
- `line 157`：把“加启动首采按钮”改为“复核现有触发按钮 + 限制 direct channel”。
- `line 266-270`：把 5 个 change 状态从 `__待创建__` 改为已创建/待签字，避免 PM 误读。

### 必修 3：修联系人分类 proposal/tasks 自相矛盾

- 文件：`openspec/changes/v3-contact-classification/proposal.md`。
- 删除 `position_classification_compiled` 缓存表句子。
- 把“新增 4 张表”改成“新增 3 张表 + 1 个视图”。
- 文件：`openspec/changes/v3-contact-classification/tasks.md`。
- 把 T-CC-01 的“4 表 schema”改为“3 表 + 1 视图 schema”。
- 把 T-CC-99-A 的“4 表数据正确落库”改为“3 表数据正确落库 + 视图查询正确”。
- 顺手确认 category 是否需要 updated_at；若要，补进 T-CC-11。

### 应修 4：修 email-delivery Impact

- 文件：`openspec/changes/v3-email-delivery/proposal.md`。
- 如果 `email_events` 已存在：把 tasks 的“建表”改成“对齐/扩展事件表字段”。
- 如果 `email_events` 不存在：把 proposal Impact 的“不加新表”改为“emails 加字段 + email_events 事件表”。
