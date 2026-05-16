# Codex Code Review — V3 Plan 准备

> 审查日期：2026-05-06
> 审查范围：02-gap-audit + 03-delivery-plan + 5 个 OpenSpec change 骨架
> 方法：交叉验证业务目标 / 决策池 / 实际代码 / DB schema

## 0. 总体结论

不建议用户现在签字。

这 7 份交付物的总体方向是对的：
它们已经把 V3 拆成数据基座、采集反推、邮件投递、客户库、联系人分类 5 个 change，
也基本覆盖了 R-1/R-2/R-3/R-4。

但里面存在几处会直接导致返工的事实错误：

- UC-10 admin 启动首采被误判为前端 MISSING，但实际代码已经有触发按钮和 API 调用。
- UC-21 评分调整被写成“后端 API 完整”，但实际 patch 接口没有更新分数/评分调整字段，DB 也没有评分调整字段。
- 联系人职位分类的表/视图模型与 D-037 决策池不一致。
- 邮件相关 tasks 把 V3 明确不做的开信、退信、送达分级又放回来了。
- acceptance ID 映射有缺漏和语义错位。

建议：
先修 Blocker，再让用户签字。

本报告只审查并写报告；
未修改任何待审文件。

---

## 1. Blocker（必须修才能签字）

### B-01 · UC-10 被误判为前端 MISSING，实际 admin 端已存在“触发”按钮

**问题**

`02-current-implementation-gap-audit.md` 与 `v3-collection-pushback` 把 UC-10 写成：
后端 API 完整，但 admin 前端缺“启动首采”按钮。

这和实际代码不一致。

实际 admin `CollectionTasks` 页面已经有：

- `triggerMutation`
- `adminApi.collection.trigger(...)`
- 行内“触发”按钮
- Popconfirm 确认
- loading / success / error 处理

如果按当前 plan 执行，
开发者会重复实现一个已经存在的按钮，
并可能改坏现有 CollectionTasks 交互。

**证据**

待审文档把 UC-10 判为前端缺口：

- `_control/v3/03-r1-readiness-matrix.md:37`
- `openspec/changes/v3-collection-pushback/proposal.md:10`
- `openspec/changes/v3-collection-pushback/proposal.md:25`
- `openspec/changes/v3-collection-pushback/tasks.md:12`
- `openspec/changes/v3-collection-pushback/tasks.md:14`
- `openspec/changes/v3-collection-pushback/tasks.md:15`

实际前端已实现 trigger：

- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:230`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:232`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:283`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:286`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:292`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:302`

实际后端 API 也存在：

- `backend/app/api/admin/collection.py:19`
- `backend/app/api/admin/collection.py:24`

**建议修法**

修 `02-current-implementation-gap-audit.md`：

- C2 不要再把 UC-10 admin 按钮列为 MISSING。
- C2 缺口改为“需验证现有按钮是否符合 V3 仅反推路径 + D-035 外贸通推迟后的 channel 限制”。
- 如果按钮仍显示 direct / reverse 两个 channel，需要把 V3 行为改成只允许反推链路，或明确 direct=禁用/隐藏。

修 `openspec/changes/v3-collection-pushback/tasks.md`：

- 删除或改写 T-CP-10/T-CP-11。
- 新任务应是“复核现有触发按钮并按 D-035 禁用外贸通直采入口”。
- 保留 T-CP-12 状态轮询核验，但不要当作 from-scratch。

---

### B-02 · UC-21“评分调整后端就绪”结论不成立

**问题**

`02-current-implementation-gap-audit.md` 把 C4 写成：
“后端就绪，缺前端 4 个表单”。

其中 UC-21 是“租户级评分调整”。
实际代码没有看到评分调整字段和 API 行为。

当前 `PATCH /prospects/{prospect_id}` 只更新：

- `notes`
- `tags`
- `business_status`

它不更新：

- `total_score`
- `grade`
- `score_adjustment`
- `manual_score_adjustment`
- 调分理由
- 调分审计字段

DB `tenant_companies` 也没有评分调整字段。

如果开发者按“后端已 ready”执行，
只补前端表单会产生假按钮：
用户提交调分后没有地方正确落库。

**证据**

待审文档把 C4 后端写为 PARTIAL / 就绪：

- `_control/v3/02-current-implementation-gap-audit.md:136`
- `_control/v3/02-current-implementation-gap-audit.md:137`
- `_control/v3/02-current-implementation-gap-audit.md:141`
- `openspec/changes/v3-tenant-companies/proposal.md:10`
- `openspec/changes/v3-tenant-companies/tasks.md:21`
- `openspec/changes/v3-tenant-companies/tasks.md:22`

实际 patch API：

- `backend/app/api/tenant/ops.py:104`
- `backend/app/api/tenant/ops.py:111`

实际 service 只更新 notes/tags/business_status：

- `backend/app/services/tenant_ops_service.py:344`
- `backend/app/services/tenant_ops_service.py:345`
- `backend/app/services/tenant_ops_service.py:346`
- `backend/app/services/tenant_ops_service.py:347`

实际 `tenant_companies` schema 没有评分调整字段：

- `_control/inputs/database/schema.sql:390`
- `_control/inputs/database/schema.sql:396`
- `_control/inputs/database/schema.sql:397`
- `_control/inputs/database/schema.sql:402`
- `_control/inputs/database/schema.sql:403`

**建议修法**

修 `02-current-implementation-gap-audit.md`：

- C4 的“后端 API”不能写“UC-21 后端完整”。
- 应拆成：
  - UC-22 备注：后端已有 notes 更新。
  - UC-23 标签：后端已有 tags 更新。
  - UC-21 调分：后端/DB MISSING。
  - UC-19 群组：后端已有 groups/group_members，但前端入口缺。

修 `v3-tenant-companies/tasks.md`：

- 在 T-TC-20/T-TC-21 前补 DB/API 任务：
  - 明确调分字段设计。
  - 明确 `total_score` 是否直接覆盖，还是保存 `score_adjustment` 后由 scoring worker 重算。
  - 明确审计字段。
  - 明确分数调整范围 ±20 如何约束。

建议不要把调分直接写进 `total_score` 而丢失原始模型分。
更稳妥的是新增调分字段或单独调分表。

---

### B-03 · D-037 联系人分类数据模型与决策池不一致

**问题**

待审文件把联系人分类写成 4 张表：

- `position_classification_levels`
- `position_classification_categories`
- `position_classification_keywords`
- `position_classification_compiled`

但决策池详细设计写的是：

- 3 张实体表
- 1 个运行时视图 `v_tenant_contact_classified`

Target Spec 又写成“新增 4 张表 + 1 视图 `position_classification_*`”。

当前 change 骨架没有提 `v_tenant_contact_classified`。
它新增的 `position_classification_compiled` 也没有在决策池 M.1 的核心模型里出现。

这是签字前必须澄清的结构性冲突。

否则后续会出现两类返工：

- DB 迁移建了 compiled 表，但邮件计划筛选实际需要视图。
- 设计文档和实现互相不认，验收时无法判断“4 张表”到底是哪 4 张。

**证据**

Target Spec 的高层表述：

- `_control/v3/00-v3-target-spec.md:72`

决策池 M.1 的详细模型：

- `_control/04-open-questions.md:147`
- `_control/04-open-questions.md:148`
- `_control/04-open-questions.md:149`

决策池 M.6 只给出前缀，不定义 compiled 表：

- `_control/04-open-questions.md:185`

待审 audit 写“4 张 position_classification_* 表”：

- `_control/v3/02-current-implementation-gap-audit.md:109`
- `_control/v3/02-current-implementation-gap-audit.md:118`

change proposal 引入 compiled 表：

- `openspec/changes/v3-contact-classification/proposal.md:26`
- `openspec/changes/v3-contact-classification/proposal.md:31`

tasks 也建 compiled 表：

- `openspec/changes/v3-contact-classification/tasks.md:15`
- `openspec/changes/v3-contact-classification/tasks.md:18`

但 tasks 没有建视图：

- `openspec/changes/v3-contact-classification/tasks.md:13`
- `openspec/changes/v3-contact-classification/tasks.md:47`

**建议修法**

先让用户或 PM 拍板一个唯一模型。

推荐两种可签字版本之一：

方案 A：

- 3 张表：
  - `position_classification_levels`
  - `position_classification_categories`
  - `position_classification_keywords`
- 1 个视图：
  - `v_tenant_contact_classified`
- 无 compiled 表。

方案 B：

- 3 张表 + 1 张 compiled 表 + 1 个视图。
- 明确 compiled 表只是性能缓存。
- 明确 admin 修改规则后如何重建 compiled。
- 明确邮件计划调用视图还是 classify 函数。

无论选哪种，
`02-gap-audit`、`03-delivery-plan`、`v3-contact-classification/proposal.md`、`tasks.md` 必须统一。

---

### B-04 · 邮件 tasks 把 V3 Non-Goals 重新引入：开信、退信、送达分级

**问题**

业务真源明确：

- V3 不做开信追踪 / 嵌追踪像素。
- V3 不做退信记录 / 送达分级。
- 发出即认为投递完成。
- V3 不做回复识别。

但 `v3-email-delivery/tasks.md` 重新加入了：

- EngageLab 6 指标。
- sent / delivered / opens 多系列柱图。
- 发送 / 送达 / 首次打开详情时间轴。
- 退信原因展示。

这会把 V3 从“真实发出 + 状态回写”扩大成邮件营销分析平台，
明显偏离 N-08 / N-09。

实际代码里确实存在 opened/bounced 等历史字段和 UI，
但 V3 plan 应该写“保留但不增强 / 不作为验收”，
不能把它们列成 V3 实施任务。

**证据**

业务真源 Non-Goals：

- `_control/v3/00-v3-business-goals.md:151`
- `_control/v3/00-v3-business-goals.md:162`
- `_control/v3/00-v3-business-goals.md:163`
- `_control/v3/00-v3-target-spec.md:68`

待审 tasks 重新引入：

- `openspec/changes/v3-email-delivery/tasks.md:51`
- `openspec/changes/v3-email-delivery/tasks.md:52`
- `openspec/changes/v3-email-delivery/tasks.md:53`
- `openspec/changes/v3-email-delivery/tasks.md:54`

实际旧代码里已有相关字段/展示，说明更应谨慎“删验收不删历史字段”：

- `frontend/apps/tenant/src/pages/EmailMonitor/index.tsx:216`
- `frontend/apps/tenant/src/pages/EmailMonitor/index.tsx:226`
- `frontend/apps/tenant/src/pages/EmailMonitor/index.tsx:403`
- `frontend/apps/tenant/src/pages/EmailMonitor/index.tsx:404`
- `frontend/apps/tenant/src/pages/EmailMonitor/index.tsx:407`
- `backend/app/services/tenant_messaging_service.py:1041`
- `backend/app/services/tenant_messaging_service.py:1044`

**建议修法**

修 `v3-email-delivery/tasks.md`：

- 删除 T-ED-50~T-ED-53，或改为：
  - EmailMonitor 仅展示 V3 允许状态。
  - V3 只验收“发出/失败/取消/投递中”这类联系人级状态。
  - opened/bounced/replied 历史字段保留但 V3 不写入、不新增 UI、不验收。

修 `v3-email-delivery/proposal.md`：

- Impact / Non-Goals 里明确“旧 UI 若已有 opened/bounced 展示，V3 可隐藏或置灰，不作为新增开发任务”。

---

### B-05 · `v3-data-foundation` 任务要求修改 CLAUDE.md，违反工作区规则

**问题**

`v3-data-foundation/tasks.md` 的 T-DF-10 要把 `CLAUDE.md` §6 命令占位补成实测命令。

但工作区规则明确：
AGENTS.md / CLAUDE.md 由人类维护，AI 可以在 `_control/04-open-questions.md` 提修订建议，
不要直接改 AGENTS.md / CLAUDE.md。

如果后续 agent 按 tasks 执行，
会直接违反工作区规则。

**证据**

禁止直接改 AGENTS.md / CLAUDE.md：

- `AGENTS.md:41`
- `AGENTS.md:43`

待审 tasks 要改 CLAUDE.md：

- `openspec/changes/v3-data-foundation/tasks.md:14`

**建议修法**

把 T-DF-10 改为：

- 读取 `package.json` / `pyproject.toml`。
- 在 `_control/04-open-questions.md` 或 `_control/v3/slices/slice-0-dev-runtime-baseline.md` 记录实测命令。
- 如确需更新 `CLAUDE.md`，列为“人类维护者手动更新建议”，不作为 AI 编码任务。

---

### B-06 · Acceptance Matrix 与 Delivery Plan / tasks 的验收 ID 映射不完整且有错位

**问题**

`03-v3-delivery-plan.md` 要求每个任务对应 V3-* 验收 ID。
但现在存在几个明显错位：

1. `V3-COL-004` 没有被 Slice 1.B / Data Foundation 验收覆盖。
2. `v3-collection-pushback` 把 `V3-COL-001` 写成“tenant 配新关键词成功落库”，但 acceptance matrix 定义的 `V3-COL-001` 是“Admin 配置数据源 + 凭证”。
3. Acceptance matrix 的 `V3-COL-003` 仍写“调用外贸通/腾道”，与 D-035 “外贸通推迟 V3.1+”冲突。
4. Acceptance matrix 的 `V3-COL-005` 仍把 `waimaotong_raw_contacts` 作为 V3 入库目标之一，和 D-035 “V3 外贸通表空”冲突。
5. Acceptance matrix 的 `V3-MAIL-001` 仍写“租户配置发件邮箱 + 凭证 / tenant_ai_provider_configs”，和 D-002/D-024/D-031 的 admin 域名配置架构冲突。

如果不先修验收 ID，
后续每个 change 即使完成，也会在验收时争论“到底验哪件事”。

**证据**

Delivery Plan 要求每任务绑定 V3-*：

- `_control/v3/03-v3-delivery-plan.md:20`
- `_control/v3/03-v3-delivery-plan.md:280`

Acceptance matrix 当前定义：

- `_control/v3/01-v3-acceptance-matrix.md:29`
- `_control/v3/01-v3-acceptance-matrix.md:31`
- `_control/v3/01-v3-acceptance-matrix.md:32`
- `_control/v3/01-v3-acceptance-matrix.md:33`
- `_control/v3/01-v3-acceptance-matrix.md:36`

Delivery Plan / tasks 漏掉或错配：

- `_control/v3/03-v3-delivery-plan.md:147`
- `openspec/changes/v3-data-foundation/proposal.md:72`
- `openspec/changes/v3-data-foundation/tasks.md:67`
- `openspec/changes/v3-data-foundation/tasks.md:68`
- `openspec/changes/v3-collection-pushback/tasks.md:66`

D-035 / D-002 事实真源：

- `_control/v3/00-v3-target-spec.md:33`
- `_control/v3/00-v3-target-spec.md:70`

**建议修法**

先修 `_control/v3/01-v3-acceptance-matrix.md` 或在本批 plan 中显式标注“acceptance matrix 待同步”。

建议最小修订：

- `V3-COL-001` = admin 配数据源 + 凭证，归 `v3-data-foundation` 或单独 R-1 baseline 验证。
- `V3-COL-002` = 创建采集任务，归 `v3-collection-pushback`。
- `V3-COL-003` = collection worker 调用励销云 + 腾道，删除外贸通。
- `V3-COL-004` = cleanup_service 字段结构化，归 `v3-data-foundation`。
- `V3-COL-005` = tendata/lixiaoyun raw + clean 表有行，删除 V3 外贸通目标。
- `V3-MAIL-001` = admin 配租户发件域名 + 起始预热档位 + domain_warmup_status 落库。

---

## 2. High Risk（强烈建议修）

### H-01 · Wave 1 被过度声明为 Wave 2 全部 change 的硬依赖

**问题**

`03-v3-delivery-plan.md` 和 `v3-data-foundation/proposal.md` 都说：
Wave 1 必须完整完成，才能启动全部 4 个 Wave 2 change。

这对部分能力是对的：

- C5 10 项筛选依赖 clean_companies 新字段。
- C6 scoring 的 factory_type / has_china_pcb_supplier 依赖 clean 字段。
- C7 sending 真实部署依赖 worker 基线。
- C2 fan-out 依赖 clean/shared 层。

但对 C3 联系人分类不完全成立。

联系人分类的核心是：

- 4 层分类规则。
- admin 配置页。
- classify(position) 函数。
- 删除 tenant contact-rules。

它不依赖 D-008 raw/clean 重构才能做。
最多依赖 alembic 命名和迁移排队策略。

如果把 C3 强行等到 Wave 1 全结束，
会压缩邮件投递 Slice 3.4 的开发窗口。
而 C7 又依赖 classify(position)。

**证据**

Delivery Plan 写 Wave 1 独占：

- `_control/v3/03-v3-delivery-plan.md:21`
- `_control/v3/03-v3-delivery-plan.md:42`
- `_control/v3/03-v3-delivery-plan.md:46`
- `_control/v3/03-v3-delivery-plan.md:223`

Data Foundation proposal 写全部 4 个 Wave 2 依赖：

- `openspec/changes/v3-data-foundation/proposal.md:14`
- `openspec/changes/v3-data-foundation/proposal.md:19`
- `openspec/changes/v3-data-foundation/proposal.md:62`

C3 的实际依赖更独立：

- `_control/v3/02-current-implementation-gap-audit.md:118`
- `_control/v3/02-current-implementation-gap-audit.md:119`
- `_control/v3/02-current-implementation-gap-audit.md:120`
- `_control/v3/02-current-implementation-gap-audit.md:121`
- `openspec/changes/v3-contact-classification/proposal.md:83`

**建议修法**

不要写“Wave 2 全部硬依赖 Wave 1 完成”。

改成：

- Wave 1.A alembic 升级和迁移策略确认后，C3 可提前并行设计/编码。
- C3 的 DB migration merge 顺序由 v3-data-foundation 统一协调。
- C3 的最终联调在 Wave 1 完成后进行。

这样既不破坏 Gate，
也避免把独立工作人为串行化。

---

### H-02 · C4 把 UC-24 放进“私有操作 4 件套”的口径仍有残留

**问题**

D-033 已取消 UC-24 主联系人概念。
D-022 在 2026-05-06 修订后把“4 件套”重新定义为：

- 评分调整
- 备注
- 标签
- 群组管理

不是：

- 评分调整
- 备注
- 标签
- 主联系人

待审文件大体修对了，
但仍有几处写“UC-21~24”或“4 个表单”，容易让后续开发者把主联系人按钮做回来。

**证据**

D-033 取消 UC-24：

- `_control/v3/00-v3-target-spec.md:69`
- `_control/04-open-questions.md:130`

D-022 修订为群组管理：

- `_control/04-open-questions.md:138`

待审文件仍写 UC-21~24：

- `_control/v3/02-current-implementation-gap-audit.md:129`
- `openspec/changes/v3-tenant-companies/proposal.md:10`
- `openspec/changes/v3-tenant-companies/proposal.md:23`
- `openspec/changes/v3-tenant-companies/tasks.md:12`

实际前端 Companies 仍显示默认联系人列，说明“主联系人残留”需要明确清理或保留只读：

- `frontend/apps/tenant/src/pages/Companies/index.tsx:301`
- `frontend/apps/tenant/src/pages/Companies/index.tsx:304`

**建议修法**

把所有“UC-21~24 私有操作 4 件套”改成：

- “D-022 客户库私有操作 4 件套：UC-21 调分 + UC-22 备注 + UC-23 标签 + D-020 群组管理”。

同时在 Non-Goals 里明确：

- UC-24 主联系人按钮不补。
- `tenant_contacts.is_default` 只保留历史字段，V3 不写入。
- Companies 联系人表中的“默认”列是否隐藏/只读，由 design.md 决定。

---

### H-03 · tenant contact-rules 删除范围写得太窄，遗漏 Onboarding 和 shared-api 引用

**问题**

`v3-contact-classification/tasks.md` 写了删除：

- tenant/Settings/contact-rules 路由 + 页面
- 后端 tenant 端配置 API

但实际代码引用不止这些。

tenant onboarding 也读取 contact rules，
并渲染 `StepContactRules`。
shared-api 还有 `contactRules` query key 和 API 模块。

如果只删页面和路由，
会留下编译错误、死代码、或 onboarding 继续展示旧规则。

**证据**

tasks 删除范围：

- `openspec/changes/v3-contact-classification/tasks.md:41`
- `openspec/changes/v3-contact-classification/tasks.md:43`
- `openspec/changes/v3-contact-classification/tasks.md:44`
- `openspec/changes/v3-contact-classification/tasks.md:45`

实际 tenant 路由：

- `frontend/apps/tenant/src/router.tsx:56`

实际页面：

- `frontend/apps/tenant/src/pages/Settings/ContactRules/index.tsx:37`
- `frontend/apps/tenant/src/pages/Settings/ContactRules/index.tsx:55`
- `frontend/apps/tenant/src/pages/Settings/ContactRules/index.tsx:76`

实际 onboarding 引用：

- `frontend/apps/tenant/src/pages/Onboarding/index.tsx:289`
- `frontend/apps/tenant/src/pages/Onboarding/index.tsx:291`
- `frontend/apps/tenant/src/pages/Onboarding/index.tsx:363`

实际后端 API：

- `backend/app/api/tenant/settings.py:86`
- `backend/app/api/tenant/settings.py:92`

**建议修法**

在 `v3-contact-classification/tasks.md` T-CC-40~42 下补：

- 删除 onboarding 联系人规则步骤。
- 删除 shared-api tenant/contact-rules 客户端或改为 admin-only。
- 删除 queryKeys.contactRules。
- 搜索全仓 `contactRules` / `contact-rules` 后清干净。
- 明确 tenant 首登流程不再包含联系人规则配置。

---

### H-04 · clean_companies 字段数量表述容易误导：D-038 是 9 个，D-039 再加 2 个，总计 11 个

**问题**

多处文档写“clean_companies +9 字段”，后面括号又把：

- D-038 的 9 个字段
- D-039 的 `factory_type`
- D-039 的 `has_china_pcb_supplier`

放在同一句里。

这容易让开发者误以为总共只加 9 个字段，
实际 D-038 + D-039 是 11 个字段。

**证据**

Target Spec 明确总计 11 字段：

- `_control/v3/00-v3-target-spec.md:73`
- `_control/v3/00-v3-target-spec.md:74`

决策池 D-038 9 字段：

- `_control/04-open-questions.md:227`
- `_control/04-open-questions.md:236`

决策池 D-039 第 10、11 字段：

- `_control/04-open-questions.md:342`
- `_control/04-open-questions.md:345`
- `_control/04-open-questions.md:346`

待审文档混写：

- `_control/v3/02-current-implementation-gap-audit.md:65`
- `openspec/changes/v3-data-foundation/proposal.md:29`
- `openspec/changes/v3-data-foundation/tasks.md:35`
- `openspec/changes/v3-tenant-companies/proposal.md:35`

**建议修法**

统一写法：

- D-038：clean_companies 新增 9 字段。
- D-039：clean_companies 追加 2 字段。
- V3 新增字段总计 11 个。

并在 tasks 中拆成：

- T-DF-33-A D-038 9 字段。
- T-DF-33-B D-039 2 字段。

---

### H-05 · Data Foundation proposal 对当前 DB 状态的描述不够精确

**问题**

`v3-data-foundation/proposal.md` 写：
“当前只有 6 raw，无干净库 / 无 cleanup_service”。

这句话容易造成混乱。

实际情况分三层：

1. `_control/inputs/database/schema.sql` 里有旧 `shared_companies/shared_contacts/company_sources`。
2. alembic 0009 已经包含 `tendata_raw_companies`、`lixiaoyun_raw_companies`、`clean_companies`、`cleanup_queue`。
3. 生产真值据文档说停在 0006，所以 0009 结构未上线。

如果文档只写“当前只有 6 raw”，
无法表达“设计文件有、迁移文件有、生产未跑”的真实状态。

**证据**

proposal 当前描述：

- `openspec/changes/v3-data-foundation/proposal.md:10`
- `openspec/changes/v3-data-foundation/proposal.md:11`

schema.sql 旧 shared 层：

- `_control/inputs/database/schema.sql:270`
- `_control/inputs/database/schema.sql:297`
- `_control/inputs/database/schema.sql:310`

alembic 0009 已含 raw/clean/queue：

- `backend/alembic/versions/20260430_0009_phase1_collection_schema.py:42`
- `backend/alembic/versions/20260430_0009_phase1_collection_schema.py:66`
- `backend/alembic/versions/20260430_0009_phase1_collection_schema.py:85`
- `backend/alembic/versions/20260430_0009_phase1_collection_schema.py:122`

Audit 也写 alembic 停在 0006：

- `_control/v3/02-current-implementation-gap-audit.md:53`

**建议修法**

把 Data Foundation 的 Why 改为三段：

- 生产/当前 DB 真值：停在 0006。
- 迁移链 0007~0013：已有但未上线，且与 schema.sql 未完全回写。
- V3 新增：D-008/D-038/D-039/D-009 等重构迁移。

这样能避免开发者误以为 0009 代码不存在。

---

### H-06 · `v3-tenant-companies` 写“附属，不阻塞主链”，但它是 Slice 5 E2E 前置

**问题**

`v3-tenant-companies` proposal 开头写：
“Wave 2 附属（与主链并行，不阻塞 Slice 3 / 5）”。

但同一份文档和 delivery plan 又写：
Slice 5 E2E 前需要 `v3-tenant-companies` 完成。

这不是纯文字问题。

客户库筛选、私有状态、评分模板如果没完成，
R-1 的客户库体验和 D-038/D-039 业务决策都无法验收。

**证据**

不阻塞 Slice 5 的说法：

- `openspec/changes/v3-tenant-companies/proposal.md:3`

但 Delivery Plan 写 Slice 5 依赖 tenant-companies：

- `_control/v3/03-v3-delivery-plan.md:98`
- `_control/v3/03-v3-delivery-plan.md:223`

tenant-companies 自己也写 Slice 5 验收需完成：

- `openspec/changes/v3-tenant-companies/tasks.md:3`
- `openspec/changes/v3-tenant-companies/tasks.md:95`

**建议修法**

把措辞改成：

- 不阻塞 Slice 3 邮件投递开发。
- 阻塞 Slice 5 全 V3 E2E 和 PM Acceptance。

---

## 3. Medium / Low（排期处理）

### M-01 · D-035 外贸通推迟后，CollectionTasks 现有 direct channel 需要明确处理

**问题**

D-035 明确 V3 不做外贸通直采。
实际 admin CollectionTasks UI 仍渲染 direct / reverse 两类 channel。

这不一定是 bug，
但计划里需要明确：

- V3 隐藏 direct？
- direct 禁用？
- direct 保留但状态说明“V3.1+”？

**证据**

D-035：

- `_control/v3/00-v3-target-spec.md:70`
- `_control/04-open-questions.md:132`

实际 UI flatMap direct / reverse：

- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:274`
- `frontend/apps/admin/src/pages/CollectionTasks/index.tsx:275`

**建议修法**

在 `v3-collection-pushback/tasks.md` 补一个任务：

- “按 D-035 处理现有 direct channel UI 和后端触发限制”。

---

### M-02 · `v3-contact-classification` 的 level/category 字段少于决策池

**问题**

决策池 M.1 写：

- level 有 `display_name`、`created_at`、`updated_at`
- category 有 `display_name`、`sort_order`、`created_at`

tasks 里只写了：

- levels: id / name / is_sendable / sort_order
- categories: id / level_id / name

这会导致 UI 展示名和排序能力缺失。

**证据**

决策池字段：

- `_control/04-open-questions.md:147`
- `_control/04-open-questions.md:148`

tasks 字段：

- `openspec/changes/v3-contact-classification/tasks.md:15`
- `openspec/changes/v3-contact-classification/tasks.md:16`

**建议修法**

tasks 字段列表对齐 M.1，
至少补：

- `display_name`
- `sort_order`
- `created_at`
- `updated_at`

---

### M-03 · Scoring 当前代码已有 platform 模板 industry 字段，audit 的“非按行业版”要更精确

**问题**

`02-gap-audit` 写 admin/ScoringTemplates “已有，但非按行业版”。

实际代码和 schema 里至少存在 platform scoring template 的 `industry` 查询/字段逻辑。
不过 tenant 侧 scoring_templates 表仍是租户级模板，
且 tenant Settings/Scoring 还能改 dimensions / grade_thresholds。

所以正确说法不是“完全非按行业”，
而是：

- admin/platform 模板层有 industry 雏形；
- tenant 权重分离未实现；
- D-039 的 7 维 PCB 模板和租户仅调权重未实现。

**证据**

Audit 当前表述：

- `_control/v3/02-current-implementation-gap-audit.md:192`
- `_control/v3/02-current-implementation-gap-audit.md:193`

代码存在 industry 查询：

- `backend/app/services/admin_config_service.py:330`
- `backend/app/services/admin_config_service.py:357`

tenant scoring 仍可改 dimensions / thresholds：

- `backend/app/services/tenant_settings_service.py:162`
- `backend/app/services/tenant_settings_service.py:170`

schema 租户 scoring_templates 仍是 tenant_id 模型：

- `_control/inputs/database/schema.sql:413`
- `_control/inputs/database/schema.sql:415`
- `_control/inputs/database/schema.sql:419`
- `_control/inputs/database/schema.sql:420`

**建议修法**

把 C6 现状改成更精确：

- admin 平台模板：PARTIAL，已有 industry 雏形。
- tenant 权重模型：MISSING。
- D-039 PCB 7 维默认模板：MISSING。

---

### M-04 · `position_classification_compiled` 如果保留，应补重建和失效策略

**问题**

proposal 写 compiled 表用于高性能查询，
tasks 写 admin 修改后自动重建。

但没有明确：

- 全量重建还是增量重建。
- 同时编辑时如何避免读到半成品。
- 是否需要版本号。
- classify 读取 compiled 失败时是否 fallback 到原表。

**证据**

compiled 表：

- `openspec/changes/v3-contact-classification/proposal.md:31`
- `openspec/changes/v3-contact-classification/proposal.md:46`

自动重建：

- `openspec/changes/v3-contact-classification/tasks.md:30`

**建议修法**

如果保留 compiled 表，
在 design.md 前置任务里明确：

- 版本号。
- 事务内 swap。
- fallback。
- 性能目标。

如果只是 V3 小规模使用，
建议先不用 compiled 表，KISS。

---

### M-05 · E2E 任务里 “测试收件箱真实收到邮件” 与 EngageLab 状态语义需要分清

**问题**

`v3-email-delivery/tasks.md` 同时写：

- 测试收件箱真实收到邮件。
- emails.status = delivered。

但业务真源 N-09 写“发出 = 投递完成”，不做送达分级。

如果状态字段仍叫 `delivered`，可以保留；
但验收语义应是“EngageLab 接受发送 + 收件箱拨测收到”，不是建立完整送达追踪体系。

**证据**

N-09：

- `_control/v3/00-v3-business-goals.md:163`

tasks：

- `openspec/changes/v3-email-delivery/tasks.md:62`
- `openspec/changes/v3-email-delivery/tasks.md:63`

**建议修法**

把文案改成：

- “测试收件箱真实收到邮件（拨测证据）”。
- “emails.status 写 V3 简化状态：sent/completed 或现有 delivered，但不代表完整送达分级”。

---

### L-01 · 任务编号体系基本一致，但缺口编号引用有一处不存在

**问题**

`v3-collection-pushback/tasks.md` 写 Slice 1.C 针对 `C2-G0 / UC-10`。

但 `02-gap-audit` 里 C2-G1~G5，没有 C2-G0。

**证据**

tasks：

- `openspec/changes/v3-collection-pushback/tasks.md:12`

gap audit：

- `_control/v3/02-current-implementation-gap-audit.md:90`
- `_control/v3/02-current-implementation-gap-audit.md:94`

**建议修法**

如果 UC-10 仍需保留核验，新增 `C2-G0` 到 gap audit；
如果按 B-01 修正为已实现，则删除 `C2-G0`。

---

### L-02 · Review 输出文件名体系不完全一致

**问题**

有些 tasks 写完整 review 输出路径，
有些只写 `gstack eng review` 或 `Codex code review`，没有文件名。

**证据**

完整路径示例：

- `openspec/changes/v3-data-foundation/tasks.md:60`
- `openspec/changes/v3-data-foundation/tasks.md:61`
- `openspec/changes/v3-data-foundation/tasks.md:62`

缺路径示例：

- `openspec/changes/v3-collection-pushback/tasks.md:60`
- `openspec/changes/v3-collection-pushback/tasks.md:61`
- `openspec/changes/v3-email-delivery/tasks.md:72`
- `openspec/changes/v3-email-delivery/tasks.md:73`

**建议修法**

统一每个 change 的 review 输出文件名。

---

## 4. 已验证正确的关键点（让用户安心）

### K-01 · 9 能力域 C1~C9 的总体覆盖基本完整

已覆盖：

- R-1：C3/C4/C5/C6/C7/C8。
- R-2：C1/C2/C8。
- R-3：C3/C7/C9。
- R-4：C8/C9。

证据：

- `_control/v3/00-v3-business-goals.md:32`
- `_control/v3/00-v3-business-goals.md:33`
- `_control/v3/00-v3-business-goals.md:34`
- `_control/v3/00-v3-business-goals.md:35`
- `_control/v3/02-current-implementation-gap-audit.md:303`
- `_control/v3/02-current-implementation-gap-audit.md:309`
- `_control/v3/02-current-implementation-gap-audit.md:317`

结论：

能力域拆分方向可以保留。

---

### K-02 · D-035 外贸通推迟在大多数文档里已正确表达

正确点：

- V3 仅做反推路径。
- 外贸通 provider 不实现。
- 外贸通 raw 表保留但 V3 期间不写入。

证据：

- `_control/v3/00-v3-target-spec.md:70`
- `_control/04-open-questions.md:132`
- `_control/v3/02-current-implementation-gap-audit.md:62`
- `openspec/changes/v3-data-foundation/proposal.md:26`
- `openspec/changes/v3-collection-pushback/proposal.md:38`

注意：

acceptance matrix 仍需按 B-06 同步。

---

### K-03 · D-037 删除 tenant 老 contact-rules 模块是真实需要，不是假设

实际代码存在 tenant 端老模块：

- 路由。
- 页面。
- 后端 tenant API。
- onboarding 引用。

所以 `v3-contact-classification` 需要删除老模块这个方向是对的。

证据：

- `frontend/apps/tenant/src/router.tsx:56`
- `frontend/apps/tenant/src/pages/Settings/ContactRules/index.tsx:37`
- `frontend/apps/tenant/src/pages/Settings/ContactRules/index.tsx:55`
- `backend/app/api/tenant/settings.py:86`
- `backend/app/api/tenant/settings.py:92`

结论：

删除老模块必须做。
但删除范围要按 H-03 扩大。

---

### K-04 · D-038 第 10 项“联系人数量档位筛”已正确进入 tenant-companies change

证据：

- `_control/v3/00-v3-business-goals.md:99`
- `_control/v3/00-v3-business-goals.md:100`
- `_control/04-open-questions.md:222`
- `openspec/changes/v3-tenant-companies/proposal.md:40`
- `openspec/changes/v3-tenant-companies/tasks.md:49`

结论：

第 10 项更正已进入 change 骨架。

---

### K-05 · D-039 的核心评分规则在 tenant-companies change 中基本覆盖

已覆盖：

- 平台模板。
- 租户仅调权重。
- PCB 7 维。
- S/A/B/C/D 阈值。
- 档位外 / 缺失 = 0。

证据：

- `_control/v3/00-v3-target-spec.md:74`
- `_control/04-open-questions.md:315`
- `_control/04-open-questions.md:321`
- `openspec/changes/v3-tenant-companies/proposal.md:45`
- `openspec/changes/v3-tenant-companies/proposal.md:48`
- `openspec/changes/v3-tenant-companies/proposal.md:49`
- `openspec/changes/v3-tenant-companies/proposal.md:50`
- `openspec/changes/v3-tenant-companies/tasks.md:71`
- `openspec/changes/v3-tenant-companies/tasks.md:84`
- `openspec/changes/v3-tenant-companies/tasks.md:85`

注意：

字段数和当前代码现状需按 H-04 / M-03 修精确。

---

### K-06 · D-031 创建租户同步配置域名和预热档位已进入 email-delivery change

证据：

- `_control/v3/00-v3-target-spec.md:65`
- `_control/04-open-questions.md:128`
- `openspec/changes/v3-email-delivery/proposal.md:22`
- `openspec/changes/v3-email-delivery/proposal.md:23`
- `openspec/changes/v3-email-delivery/tasks.md:15`
- `openspec/changes/v3-email-delivery/tasks.md:16`
- `openspec/changes/v3-email-delivery/tasks.md:17`

结论：

这个关键业务决策已被正确纳入。

---

### K-07 · D-034 / N-02 / N-03 的“回复识别和公司级中断不做”在 proposal Non-Goals 中有体现

证据：

- `_control/v3/00-v3-business-goals.md:151`
- `_control/v3/00-v3-business-goals.md:152`
- `_control/v3/00-v3-target-spec.md:68`
- `openspec/changes/v3-email-delivery/proposal.md:51`
- `openspec/changes/v3-email-delivery/proposal.md:52`

注意：

tasks 里仍有开信/退信问题，见 B-04。

---

### K-08 · D-020 精选 = 群组模型方向与实际 DB/code 对得上

实际 schema 有：

- `groups`
- `group_members`

实际 service 有 group_members 增删。

证据：

- `_control/inputs/database/schema.sql:535`
- `backend/app/services/tenant_ops_service.py:615`
- `backend/app/services/tenant_ops_service.py:648`
- `backend/app/services/tenant_ops_service.py:694`
- `openspec/changes/v3-tenant-companies/tasks.md:40`

结论：

群组管理作为 D-022 第 4 件套是合理的。

---

## 5. 给用户的“无技术背景版”摘要

1. 这份计划的大方向可以用：
   它把 V3 拆成 5 个项目包，整体覆盖了采集、客户库、邮件、上线。

2. 但现在不能签字：
   里面有几处“以为没做，其实已做”或“以为后端好了，其实没好”的错误。
   最典型的是“启动首采按钮”已经存在；
   而“评分调整”后端并没有真的准备好。

3. 联系人分类这个新功能必须先把表结构说清楚：
   现在有的文档说 3 张表 + 1 个视图，
   有的说 4 张表，
   change 里又新增了一个 compiled 表。
   不统一会让开发者建错数据库。

4. 邮件计划里混进了 V3 明确不做的内容：
   开信追踪、退信记录、送达分级这些都应该推迟。
   V3 只需要证明“邮件真的发出、失败能记录、状态能回写”。

5. 建议用户让团队先修 6 个 Blocker：
   修完后再签字。
   这些修订不一定增加开发量，
   很多只是把错误任务删掉或改成“复核现有功能”。

---

## 6. 原始需求 → 已实现 / 未实现 对照清单

| 原始需求 | 状态 | 说明 |
|---|---:|---|
| 审查 `_control/v3/02-current-implementation-gap-audit.md` | 已实现 | 已对 C1~C9、状态判定、缺口编号、代码事实做交叉检查 |
| 审查 `_control/v3/03-v3-delivery-plan.md` | 已实现 | 已检查 Wave 1/2、Slice ↔ change、验收 ID 映射 |
| 审查 5 个 OpenSpec change 骨架 | 已实现 | 已审 proposal.md + tasks.md |
| 验证 C1~C9 有无重叠/遗漏 | 已实现 | 总体覆盖完整；发现 UC-10、UC-21、C3 模型等事实错误 |
| 验证 Wave 1/2 依赖关系 | 已实现 | 发现 C3 被过度绑定到 Wave 1 完成后 |
| 验证 Slice ↔ change 映射 | 已实现 | 主体可用；发现 tenant-companies “不阻塞 Slice 5”表述冲突 |
| 验证缺口编号 Cn-Gx 是否反映代码实际状态 | 已实现 | 发现 UC-10、UC-21 两处关键误判 |
| 验证 DB 字段/表名引用 | 已实现 | 发现 D-037 表/视图不一致；D-038/D-039 字段数量表述需修 |
| 验证 D-XXX 引用 | 已实现 | D-035/D-037/D-038/D-039/D-040 大体正确；D-033/D-034 在部分 tasks 仍有残留风险 |
| 验证 V3-* 验收 ID 映射 | 已实现 | 发现 V3-COL-004 缺失、V3-COL-001/V3-MAIL-001 语义错位 |
| 验证 Non-Goals 是否漏剔除 | 已实现 | 发现 N-08/N-09 被 email-delivery tasks 重新引入 |
| 验证 tenant ContactRules 老模块确实存在且应删除 | 已实现 | 已确认路由、页面、后端 API、Onboarding 引用均存在 |
| 不修改被审文件 | 已实现 | 本次只新增 review 报告 |
| 不写代码 | 已实现 | 未改业务代码 |
| 报告写到磁盘指定路径 | 已实现 | `_control/reviews/codex-code-review-v3-plan-prep.md` |

