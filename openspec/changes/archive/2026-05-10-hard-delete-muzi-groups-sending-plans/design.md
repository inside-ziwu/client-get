## Context

当前租户侧数据模型以 `tenant_id` 隔离公司私有状态、群组和发送计划。日常删除语义偏向软删除：`groups.deleted_at`、`sending_plans.deleted_at` 会让前端列表不可见，但数据库仍保留业务行。用户本次要求的是赵奎租户（tenant slug: `t-019dc238`）下三类数据“全部硬删除”：通过 tenant 手工添加且公司名精确匹配 `muzi` 的公司、全部群组、全部发送计划。

这类操作有破坏性，且发送计划和群组存在多层关联：群组成员会影响 `tenant_companies.business_status`，发送计划会关联步骤、收件人、sequence enrollment、邮件、事件与发送锁。实现时必须先预览，再在明确租户范围内事务执行，最后核验目标行不存在。

## Goals / Non-Goals

**Goals:**
- 提供一次性、受控、可预览、可核验的硬删除操作。
- 只清理赵奎租户 `t-019dc238` 范围内的数据，避免误删其他租户数据。
- 硬删除赵奎租户内公司名精确匹配 `muzi` 的 tenant company 及其租户侧派生数据。
- 硬删除赵奎租户下全部群组和群组成员。
- 硬删除赵奎租户下全部发送计划及其关联运行态数据；用户确认这些是测试数据，即使已产生邮件或事件记录也全部硬删除。
- 记录执行前后的数量，便于人工复核。

**Non-Goals:**
- 不把现有日常 `DELETE /groups/{id}` 或 `DELETE /sending-plans/{id}` API 改成硬删除。
- 不删除平台级 `clean_companies`、`clean_contacts`、provider raw 数据，除非实施时证明该行仅由本次手工公司产生且无任何其他 tenant/shared 依赖。
- 不新增租户前端 UI。
- 不修改发送计划创建、启动、暂停等正常产品流程。
- 不自动操作线上数据库；正式执行仍需用户明确触发。

## Decisions

1. **用一次性后端脚本/管理命令承载清理，不复用日常 API。**
   - 理由：日常 API 的软删除语义仍然符合产品需要，本次硬删除是数据修复/运营清理，不应改变用户可触达的产品行为。
   - 备选：改造现有 API 增加 `hard=true`。拒绝原因是误触成本高，也会扩大权限与测试面。

2. **所有删除以赵奎租户 `t-019dc238` 解析出的 `tenant_id` 为强制输入边界。**
   - 理由：用户已确认本次范围是“赵奎这个租户下的”；公司、群组和发送计划都是租户私有操作数据，不能跨租户全库清空。
   - 实施要求：脚本必须先解析并打印 tenant slug `t-019dc238`、tenant id、tenant name、待删除数量；slug 不存在或匹配异常时直接失败。

3. **先预览，再执行；执行必须显式确认。**
   - 理由：硬删除不可通过软删除字段恢复。预览应至少输出 `muzi` 匹配公司数量、tenant contacts 数量、group/group_members 数量、sending_plans/sequence_steps/sending_plan_recipients/sequence_enrollments/emails/email_events/email_send_locks 数量。
   - 实施建议：支持 `--dry-run` 默认模式；只有传入 `--execute --confirm t-019dc238` 才真正删除。
   - `muzi` 选择器：按公司名精确匹配 `muzi`，实施时建议使用归一化公司名等于 `muzi` 或大小写不敏感精确匹配，不做模糊包含匹配。
   - 若 dry-run 返回多个 `muzi` 精确匹配候选，默认仍拒绝执行；只有用户逐个确认候选都是目标手工数据，并且执行命令显式传入完整候选 `tenant_company_id` 列表时，才允许作为受控多候选清理继续执行。

4. **按依赖从叶子表到主表删除。**
   - 发送链路建议顺序：`email_events` → `email_send_locks` → `emails` → `sequence_enrollments` → `sending_plan_recipients` → `sequence_steps` → `sending_plans`。
   - 群组建议顺序：`group_members` → `groups`。
   - `muzi` tenant company 建议顺序：删除引用该 company/contact 的发送与群组关联后，再删 `scoring_jobs`、`company_scores`、`tenant_contacts`、`tenant_companies` 等租户侧行。最终是否删除 clean 层由实施时依赖审计决定。

5. **清理不通过状态字段表达。**
   - 理由：本次要求是硬删除，不是 `visibility_status = hidden`、`business_status` 迁移或 `deleted_at` 软删除。删除完成后，相关列表和详情应因为数据库行不存在而不可见。

## Risks / Trade-offs

- [Risk] `muzi` 名称匹配过宽导致误删其他公司 → Mitigation：只允许公司名精确匹配 `muzi`，预览输出候选 `tenant_company_id`、clean company 名称、国家、域名；若候选异常，暂停执行。
- [Risk] 发送计划已有邮件或 provider 事件，硬删除会丢失历史事实 → Mitigation：用户已确认这是测试数据并同意硬删除；预览仍必须显示邮件与事件数量，作为执行证据。
- [Risk] 外键类型历史上从 uuid 迁到 bigint，脚本直接写 SQL 容易漏表 → Mitigation：实施前用当前数据库 schema/SQLAlchemy inspection 列出引用 `sending_plans`、`tenant_companies`、`tenant_contacts`、`groups` 的外键，再按实际 schema 调整删除顺序。
- [Risk] 清理后 dashboard 或发送统计变化明显 → Mitigation：这是预期影响；任务中要记录执行前后 dashboard 关键数量。
- [Risk] 硬删除无法普通回滚 → Mitigation：执行前必须导出目标行快照或要求数据库备份已存在；脚本自身 rollback 仅限事务未提交前。

## Migration Plan

1. 实施阶段新增一次性清理脚本/管理命令，并配套测试。
2. 在本地库先运行 dry-run，确认预览数量与目标一致。
3. 在本地库执行一次清理，核验目标行不存在，相关列表/详情返回空或 404。
4. 若需要线上执行，先由用户明确触发，并确认已有数据库快照。
5. 线上执行先 dry-run 输出待删数量，再 execute；执行后保存核验输出到 `_control/evidence/` 的当前 change 证据文件。

## User Decisions

- 目标租户：赵奎租户，tenant slug 为 `t-019dc238`。
- `muzi` 匹配规则：按公司名精确匹配 `muzi`。
- 发送计划关联邮件/事件：用户确认均为测试数据，即使已有 `emails` / `email_events` 也全部硬删除。
- 本地 dry-run 出现的 2 个 `muzi` 精确匹配候选均为用户手工创建测试数据，可通过显式确认候选 ID 的受控步骤清理；默认执行门禁不放宽。

## Open Questions

- 无。
