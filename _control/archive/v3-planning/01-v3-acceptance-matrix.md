# V3 · 01 · Acceptance Matrix

> **状态**：v1.0 起草（2026-05-06）—— codex B-06 修订：18 项验收 ID 同步 D-002 / D-024 / D-031 / D-035 / D-041 决策
> **责任**：AI 起草 → 用户标 P0/P1/P2 → 用户签字
> **Gate**：本文件未签字前，[Gate 2](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止下游 Gap Audit
> **关联**：[`00-v3-target-spec.md`](00-v3-target-spec.md) / [`02-current-implementation-gap-audit.md`](02-current-implementation-gap-audit.md)（9 能力域）/ [`03-v3-delivery-plan.md`](03-v3-delivery-plan.md)（5 OpenSpec change）

## 0. 元数据

- 版本：v1.0（codex B-06 修订）
- 起草日期：2026-05-06
- 用户签字：__未签字__

---

## 1. 优先级定义

- **P0**：V3 不做就不能上线
- **P1**：V3 应该做，但可以后补
- **P2**：未来优化

## 2. 验收矩阵（候选 18 项 + 待补）

> 每行有验证证据后填到 [`02-current-implementation-gap-audit.md`](02-current-implementation-gap-audit.md)。

| ID | 验收项 | 用户路径 | 相关模块 | 验收方式 | E2E | P0/P1/P2 | 通过标准 | 关联 change |
| --- | --- | --- | --- | --- | :-: | :-: | --- | --- |
| V3-AUTH-001 | 登录与租户隔离 | 租户 A 登录 → 看不到租户 B 私有数据（评分调整 / 备注 / 标签 / 群组） | shared-api / api/auth / RLS | 真实 E2E | ✅ | **P0** | A 看不到 B | v3-collection-pushback / v3-tenant-companies |
| V3-COL-001 | Admin 配数据源凭证 | Admin 配置 tendata + lixiaoyun 凭证（D-035：外贸通推迟 V3.1+，不配） | admin/DataSources / data_source_credentials | UI + DB | ✅ | **P0** | 凭证落库 | v3-data-foundation（前置）|
| V3-COL-002 | Admin 启动首采任务 | Admin/CollectionTasks 点"触发"（已有按钮）→ collection_tasks 入库 | admin/CollectionTasks / collection_tasks | UI + API | ✅ | **P0** | 任务入库 + channel=reverse | v3-collection-pushback |
| V3-COL-003 | collection worker 反推真实采集 | worker pickup → 励销云 stage 1 + 腾道 stage 2（D-035：不调外贸通） | collection.py / lixiaoyun + tendata provider | 日志 + DB | ✅ | **P0** | 至少 1 家公司入 raw 表 | v3-collection-pushback |
| V3-COL-004 | cleanup_service 字段结构化 | raw → cleanup_service 多源合并 → shared_companies / shared_contacts；clean_companies +11 字段（D-038 9 + D-039 2）| cleanup_service / shared_* / clean_companies | DB | ✅ | **P0** | 字段标准化 + 11 新字段写入 | v3-data-foundation |
| V3-COL-005 | clean 层有真实数据 | tendata + lixiaoyun raw → clean 入库（D-035：waimaotong_raw_* 表 V3 期间空）| shared_* / clean_companies | DB | ✅ | **P0** | clean_companies 行数 > 0 | v3-data-foundation |
| V3-COL-006 | 采集结果去重 | 同公司重复采集（跨源 / 跨租户）→ shared_companies UNIQUE 1 行 + tenant_companies fan-out | shared_companies UNIQUE | DB | ✅ | **P0** | 1 行 | v3-data-foundation + v3-collection-pushback |
| V3-COL-007 | 采集结果 tenant 隔离 | 租户 A 私有状态字段（评分 / 备注 / 标签 / 群组），B 看不到 | tenant_companies / RLS | A/B 验证 | ✅ | **P0** | A 可见 B 不可见 | v3-collection-pushback |
| V3-MAIL-001 | Admin 配发件域名 + 预热档位（D-031）| Admin 创建租户 Modal 同步配置发件域名 + 起始预热档位 → domain_warmup_status 落库 | admin/Tenants Create Modal / domain_warmup_status | UI + DB | ✅ | **P0** | 域名 + 档位落库 | v3-email-delivery |
| V3-MAIL-002 | 域名验证拨测 | Admin 域名 Tab 触发 EngageLab Domain API 验证 → SPF/DKIM/DMARC verified | admin Domain Tab / EngageLab API | 真实拨测 | ✅ | **P0** | verified ✅ | v3-email-delivery |
| V3-MAIL-003 | 创建邮件计划 | tenant 选群组 + 模板 + 计划时间 → sending_plans / sequence_steps 入库（D-033：自动按 classify 取联系人，无目标策略 3 选 1）| sending_plans / sending_plan_recipients | UI + DB | ✅ | **P0** | 任务入库 | v3-email-delivery + v3-contact-classification |
| V3-MAIL-004 | sending worker 真发 | worker pickup → EngageLab → 真实收件箱收到邮件 | sending.py | 收件箱 + 日志 | ✅ | **P0** | 收件箱真实收到 | v3-email-delivery |
| V3-MAIL-005 | 邮件状态回写 + D-041 追踪 | 发送结果 → emails / email_events；EngageLab webhook 回写 opens / soft_bounce / invalid_email / report_spam / unsubscribe | emails / email_events | DB | ✅ | **P0** | 4 态状态正确 + D-041 追踪字段写入 | v3-email-delivery |
| V3-MAIL-006 | 失败 error_code | 故意错邮箱 → emails.error_code / error_message 有值 | sending.py / emails | 日志 + DB | ✅ | **P0** | error_code 非空 | v3-email-delivery |
| V3-WORKER-001 | 任务重试 | worker 失败任务自动重试 + 退避策略 | 各 worker base class | 日志 | ✅ | **P0** | 重试可见 | v3-data-foundation（模板）|
| V3-WORKER-002 | 防重复发送 | 重复点击 / worker 重启 不重复发送 | email_send_locks / 幂等键 | 日志 | ✅ | **P0** | 1 次执行 | v3-data-foundation + v3-email-delivery |
| V3-UI-001 | 前端任务状态展示 | tenant + admin UI 实时显示 pending/running/success/failed | tenant / admin | UI | 手测 | **P1** | 状态实时更新 | 跨 change |
| V3-DEPLOY-001 | Sealos 部署后完整 E2E | 上线后端到端打通：登录 → 配置 → 关键词 → 启动首采 → worker 反推 → 客户库 → 私有操作 → 邮件计划 → 真发 → 收件箱 ✅ | 全部 | E2E + 截图 | ✅ | **P0** | 全链路通 | v3-email-delivery（Slice 5 收尾）|

> ⚠️ ChatGPT 方案 §7 "至少覆盖" 的 18 项已全部纳入。其他能力（情报中心 / 评分 / 预热 / 群组等）默认 P2 或不在 V3 范围，待用户确认。

## 3. 增补能力（用户补充）

| ID | 验收项 | P0/P1/P2 |
| --- | --- | --- |
| `<TODO>` | | |

## 4. PM 优先级建议（来自 ChatGPT §7）

```
P0：
- 真实采集任务跑通（V3-COL-001~007）
- tenant 隔离（V3-AUTH-001、V3-COL-007）
- 邮件真实发送 + 状态回写 + 失败记录（V3-MAIL-001~006）
- worker 不丢任务（V3-WORKER-001~002）
- Sealos E2E 通过（V3-DEPLOY-001）

P1：
- 高级筛选
- 更丰富的邮件模板
- 更细的任务统计
- 批量导出
- 更完善的运营后台

P2：
- 高级 CRM
- 自动营销编排
- 多渠道触达
```

## 5. PM Review Checklist

- [ ] 18 项验收候选全部分级（P0/P1/P2）
- [ ] P0 项每条都有 E2E 验收方式
- [ ] 测试数据列已对应 [`_control/inputs/test-data/`](../inputs/test-data/) 里的内容
- [ ] §3 增补能力（如有）已签字

签字行：

```
__________________________ (用户)   日期：__________
```
