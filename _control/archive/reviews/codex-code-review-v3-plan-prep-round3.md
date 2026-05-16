# Codex Code Review · 第 3 轮（轻量）— Round 2 finding 验证

> 审查日期：2026-05-06
> 审查范围：仅验证第 2 轮报告 §2 的 N-01~N-04 + §3 两条残留。
> 明确不做：不重审 Round 1/2 已 ✅ 的 finding，不扩展代码审查，不修改被审文件。

## 0. 总体结论

本轮 6 处验证中，**5 处已修复，1 处未完全修复**。N-02、N-03、N-04、残留 1、残留 2 均已按第 2 轮要求同步；但 **N-01 仍有最高真源残留**：`_control/v3/00-v3-target-spec.md` 的 §4.2 路径 B 流程图仍出现“主联系人 / UC-30 / UC-31~33”相关文字，和本轮要求“路径 B 不含这些旧口径”不一致。结论：**暂不建议签字**；签字阻塞集中在 N-01 的 §4.2 路径 B 残留，修掉后可再做一次只看该文件的轻量复核。

## 1. 6 处修复验证表

| ID | 修复点 | 状态 | 文件:行号 证据 |
|---|---|:-:|---|
| N-01 | `_control/v3/00-v3-target-spec.md` 最高真源同步 D-041 / D-033 / D-034 | ⚠️ 部分修复 | D-022 已改为“群组管理 + D-033 已取消”：`_control/v3/00-v3-target-spec.md:59`；UC-24 已删除线并标“已取消（D-033 ✅）”：`_control/v3/00-v3-target-spec.md:140`；Non-goals 5-8 已分别标 D-034 推迟 / D-041 撤销送达分级 / D-041 撤销开信追踪 / D-034 推迟：`_control/v3/00-v3-target-spec.md:170-173`；SMTP 250 已引用 D-041：`_control/v3/00-v3-target-spec.md:411`；决策表已有 D-041：`_control/v3/00-v3-target-spec.md:76`。但 §4.2 路径 B 仍含“UC-24 主联系人 D-033 已取消”：`_control/v3/00-v3-target-spec.md:202`，仍含“UC-30”：`_control/v3/00-v3-target-spec.md:208`，仍含“UC-31~33”：`_control/v3/00-v3-target-spec.md:210`。 |
| N-02 | `_control/v3/03-v3-delivery-plan.md` 删除误导执行指令 | ✅ | Slice 0 AI 任务已改为记录到 `_control/v3/slices/slice-0-dev-runtime-baseline.md`，并明确“不直接改 AGENTS.md / CLAUDE.md”：`_control/v3/03-v3-delivery-plan.md:122`；Slice 1.C 已改为复核现有按钮 + 按 D-035 限制 channel：`_control/v3/03-v3-delivery-plan.md:156-157`；5 个 change 状态均为“✅ 已创建（待签字）”：`_control/v3/03-v3-delivery-plan.md:266-270`。 |
| N-03 | `v3-contact-classification` proposal/tasks 删除 compiled / 4 表口径 | ✅ | proposal 已声明 3 张表 + 1 视图：`openspec/changes/v3-contact-classification/proposal.md:16`、`openspec/changes/v3-contact-classification/proposal.md:26`；proposal classify 节写直接查视图且“不做 compiled 表预编译”：`openspec/changes/v3-contact-classification/proposal.md:48`；Impact DB 改动为“新增 3 张表 + 1 视图”：`openspec/changes/v3-contact-classification/proposal.md:82`；Non-Goals 引用为“3 表 + 1 视图”：`openspec/changes/v3-contact-classification/proposal.md:74`；tasks T-CC-01 写“3 表 + 1 视图 schema”：`openspec/changes/v3-contact-classification/tasks.md:9`；T-CC-99-A 写“3 表数据正确落库 + 视图查询”：`openspec/changes/v3-contact-classification/tasks.md:72`。 |
| N-04 | `v3-email-delivery` proposal 同步 D-041 DB 改动 | ✅ | Impact “DB 改动”已从“不加新表”改为 emails 表加 6 字段 + 新建 `email_events` 事件表：`openspec/changes/v3-email-delivery/proposal.md:72`。同文件前文也列出 open 字段与送达分级字段：`openspec/changes/v3-email-delivery/proposal.md:56-57`。 |
| 残留 1 | `v3-contact-classification/tasks.md` T-CC-11 categories 表补 `updated_at` | ✅ | T-CC-11 categories 字段已包含 `updated_at`：`openspec/changes/v3-contact-classification/tasks.md:18`。 |
| 残留 2 | `v3-data-foundation/proposal.md` 下游依赖改为 3 硬依赖 + 1 软依赖 | ✅ | Impact “下游 change”已写“3 硬依赖 + 1 软依赖”，并明确 contact-classification 是软依赖：`openspec/changes/v3-data-foundation/proposal.md:68`；前文也拆出硬依赖与软依赖：`openspec/changes/v3-data-foundation/proposal.md:17`、`openspec/changes/v3-data-foundation/proposal.md:22`。 |

## 2. 新引入问题（如有）

### I-01 · Medium · N-01 修复不彻底：§4.2 仍用“旧词 + 已取消说明”的写法

这不是新的业务方向问题，而是第 2 轮 N-01 的残留。

本轮要求明确写了：

- `4.2 路径 B 流程图：应不含"主联系人 / UC-30 / UC-31~33 复盘"`

当前文件虽然把旧口径都标成“已取消 / 推迟”，但仍把这些词放进路径 B 流程图：

- `_control/v3/00-v3-target-spec.md:202`：仍写 `UC-24 主联系人 D-033 已取消`。
- `_control/v3/00-v3-target-spec.md:208`：仍写 `UC-30 手动标已回复 + 公司级中断 V3 不做`。
- `_control/v3/00-v3-target-spec.md:210`：仍写 `UC-31~33 完整复盘 V3 不做`。

判断：

- 业务方向已经修正，问题不在“选错方案”。
- 但最高真源的流程图仍出现旧概念，会继续污染实施人员对 V3 主流程的理解。
- 按用户本轮验证标准，此项不能记为 ✅。

建议修法：

- §4.2 路径 B 只保留 V3 要做的正向流程。
- 删除路径图中的取消项解释。
- 如需保留取消说明，放在 §3 Non-goals 或决策表，不放进主流程图。

### I-02 · Low · 同一文件其他章节仍有旧词，但不纳入本轮阻塞

本轮只要求验证 N-01 指定点。

额外看到 `_control/v3/00-v3-target-spec.md` 其他位置仍出现旧概念：

- `_control/v3/00-v3-target-spec.md:37`：D-007 历史行仍写 UC-30 手动标记保留。
- `_control/v3/00-v3-target-spec.md:96-97`：挂起问题仍提主联系人、复盘类 UC-31~33。
- `_control/v3/00-v3-target-spec.md:146-149`：UC 表仍列 UC-30~33。
- `_control/v3/00-v3-target-spec.md:307`：时序图仍出现 UC-30。
- `_control/v3/00-v3-target-spec.md:366`：私有状态字段仍列主联系人。
- `_control/v3/00-v3-target-spec.md:456-457`：E2E-6/E2E-7 仍覆盖 UC-30、UC-31~33。

判断：

- 这些不是本轮 6 处清单逐字要求中的阻塞项。
- 但如果用户希望最高真源彻底去旧口径，建议后续单独做一次 `00-v3-target-spec.md` 全文一致性清理。
- 本报告不把这些扩展项计入本轮“未修复”数量。

## 3. 给用户的无技术背景版摘要

- **不能全绿签字**：6 处里有 5 处修好了，但最高权威文件的邮件流程图还留着已取消/推迟的旧功能词。
- **最关键的一处残留**：`00-v3-target-spec.md` §4.2 路径 B 还写“主联系人、UC-30、UC-31~33”，即使旁边标了取消，也不符合“流程图不出现这些词”的要求。
- **其他计划文件已明显收敛**：Delivery Plan 不再要求改 `CLAUDE.md`，不再要求重复新建启动按钮，5 个 OpenSpec change 状态也已改成“已创建（待签字）”。
- **联系人分类已回到简单方案**：现在是 3 张表 + 1 个视图，不再做 compiled 缓存表。
- **邮件投递追踪已补上**：proposal 已写 emails 加 6 个追踪字段，并新增 `email_events` 表。

## 4. 逐项证据日志

### N-01 证据展开

核对目标：

- D-022 行。
- UC-24 行。
- Non-goals 行 5-8。
- §4.2 路径 B 流程图。
- SMTP 250 行。
- 决策表 D-041。

已修复证据：

- `_control/v3/00-v3-target-spec.md:59`：D-022 已写“评分调整 + 备注 textarea + 标签 add/remove + 群组管理”。
- 同一行还写“原‘主联系人’D-033 已取消”。
- `_control/v3/00-v3-target-spec.md:140`：UC-24 行已删除线。
- 同一行写“已取消（D-033 ✅）”。
- `_control/v3/00-v3-target-spec.md:170`：Non-goals 第 5 项标 D-034 整体推迟 V3.1+。
- `_control/v3/00-v3-target-spec.md:171`：Non-goals 第 6 项标 D-041 撤销，并做送达分级。
- `_control/v3/00-v3-target-spec.md:172`：Non-goals 第 7 项标 D-041 撤销，并做开信追踪。
- `_control/v3/00-v3-target-spec.md:173`：Non-goals 第 8 项标 D-034 推迟 V3.1+。
- `_control/v3/00-v3-target-spec.md:411`：SMTP 250 场景已改为 D-041 修订。
- `_control/v3/00-v3-target-spec.md:76`：决策表已有 D-041。

未完全修复证据：

- `_control/v3/00-v3-target-spec.md:202`：§4.2 路径 B 仍出现“UC-24 主联系人”。
- `_control/v3/00-v3-target-spec.md:208`：§4.2 路径 B 仍出现“UC-30”。
- `_control/v3/00-v3-target-spec.md:210`：§4.2 路径 B 仍出现“UC-31~33”。

结论：

- N-01 不是方向错，而是最高真源主流程图未按本轮要求清干净。
- 状态为 ⚠️ 部分修复。
- 这是本轮唯一签字阻塞。

### N-02 证据展开

核对目标：

- Slice 0 AI 任务不再写“补 CLAUDE.md”。
- Slice 1.C 不再写“加启动首采按钮”。
- 5 个 change 状态不再写 `__待创建__`。

证据：

- `_control/v3/03-v3-delivery-plan.md:122`：AI 任务写入 `_control/v3/slices/slice-0-dev-runtime-baseline.md`。
- 同一行明确“不直接改 AGENTS.md / CLAUDE.md”。
- `_control/v3/03-v3-delivery-plan.md:156`：针对缺口写“UC-10 启动按钮已实现”。
- `_control/v3/03-v3-delivery-plan.md:157`：AI 任务改为复核现有按钮并按 D-035 限制 channel。
- `_control/v3/03-v3-delivery-plan.md:266-270`：5 个 change 状态均为“✅ 已创建（待签字）”。

结论：

- N-02 已修复。

### N-03 证据展开

核对目标：

- proposal classify 函数节不再含“compiled 表预编译加速”。
- Impact DB 改动为 3 张表 + 1 视图。
- Non-Goals 引用为 3 表 + 1 视图。
- tasks T-CC-01 写 3 表 + 1 视图 schema。
- tasks T-CC-99-A 写 3 表 + 视图查询。

证据：

- `openspec/changes/v3-contact-classification/proposal.md:16`：写“3 张表 + 1 视图全部 from-scratch”。
- `openspec/changes/v3-contact-classification/proposal.md:26`：数据模型标题写“3 张表 + 1 视图”。
- `openspec/changes/v3-contact-classification/proposal.md:33`：明确“不做 compiled 缓存表”。
- `openspec/changes/v3-contact-classification/proposal.md:48`：classify 节写直接查视图，且“不做 compiled 表预编译”。
- `openspec/changes/v3-contact-classification/proposal.md:74`：Non-Goals 写“仅新增 position_classification_* 3 表 + 1 视图”。
- `openspec/changes/v3-contact-classification/proposal.md:82`：DB 改动写“新增 3 张表 + 1 视图”。
- `openspec/changes/v3-contact-classification/tasks.md:9`：T-CC-01 写“3 表 + 1 视图 schema”。
- `openspec/changes/v3-contact-classification/tasks.md:72`：T-CC-99-A 写“3 表数据正确落库 + 视图查询返回正确分类”。

结论：

- N-03 已修复。

### N-04 证据展开

核对目标：

- proposal Impact “DB 改动”不再写“不加新表”。
- 应写 emails 加 6 字段 + 新建 `email_events` 表。

证据：

- `openspec/changes/v3-email-delivery/proposal.md:72`：DB 改动写 emails 表加 6 字段。
- 同一行列出 `first_opened_at / open_count / soft_bounce / invalid_email / report_spam / unsubscribe`。
- 同一行写“新建 `email_events` 事件表”。
- `openspec/changes/v3-email-delivery/proposal.md:56`：开信追踪字段在正文中已列出。
- `openspec/changes/v3-email-delivery/proposal.md:57`：送达分级字段在正文中已列出。

结论：

- N-04 已修复。

### 残留 1 证据展开

核对目标：

- `openspec/changes/v3-contact-classification/tasks.md` 的 T-CC-11 categories 表应包含 `updated_at` 字段。

证据：

- `openspec/changes/v3-contact-classification/tasks.md:18`：T-CC-11 categories 字段列表包含 `updated_at`。

结论：

- 残留 1 已修复。

### 残留 2 证据展开

核对目标：

- `openspec/changes/v3-data-foundation/proposal.md` Impact “下游 change”应写 3 硬依赖 + 1 软依赖。
- 不再写“全部 4 个 Wave 2 change 阻塞”。

证据：

- `openspec/changes/v3-data-foundation/proposal.md:17`：硬依赖段落已单独列出。
- `openspec/changes/v3-data-foundation/proposal.md:22`：软依赖段落已单独列出。
- `openspec/changes/v3-data-foundation/proposal.md:68`：Impact “下游 change”写“3 硬依赖 + 1 软依赖”。
- 同一行明确软依赖为 `v3-contact-classification`。

结论：

- 残留 2 已修复。

## 5. 原始需求 → 已实现 / 未实现 对照清单

| 原始需求 | 状态 | 证据 |
|---|:-:|---|
| 只验证 Round 2 报告 §2 的 N-01~N-04 | ✅ 已实现 | 本报告 §1 与 §4 仅覆盖 N-01~N-04。 |
| 只验证 Round 2 报告 §3 残留 1、残留 2 | ✅ 已实现 | 本报告 §1 与 §4 覆盖两个残留项。 |
| 不重审 Round 1/2 已 ✅ 的 finding | ✅ 已实现 | 未重新展开 Round 1/2 已 ✅ finding，仅引用 Round 2 问题边界。 |
| 输出报告到指定路径 | ✅ 已实现 | `_control/reviews/codex-code-review-v3-plan-prep-round3.md`。 |
| 报告 150-300 行 | ✅ 已实现 | `wc -l _control/reviews/codex-code-review-v3-plan-prep-round3.md` = 225 行。 |
| 简体中文 | ✅ 已实现 | 全文中文。 |
| 判断是否全修好、是否签字、残留阻塞 | ✅ 已实现 | §0 明确：5 处已修，N-01 部分修复，暂不建议签字。 |
| 修复验证表含 ID / 修复点 / 状态 / 文件行号证据 | ✅ 已实现 | 见 §1。 |
| 输出新引入问题 | ✅ 已实现 | 见 §2。 |
| 输出无技术背景版摘要 3-5 条 | ✅ 已实现 | 见 §3，共 5 条。 |
| 完成后回复 `ROUND 3 DONE: <path>` | ⏳ 待最终消息执行 | 本报告落盘后由 agent_message 回复。 |
