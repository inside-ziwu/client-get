# Proposal · v3-collection-pushback

> **Wave 2（v3-data-foundation 已完成并归档后启动）**
> 关联：[`_control/v3/02-current-implementation-gap-audit.md`](../../../_control/v3/02-current-implementation-gap-audit.md) C2
> **2026-05-08 迁移说明**：`keyword_master / tenant_keyword / collection_runs / collection_tasks` 的基础 schema 与数据迁移职责已迁入归档 change [`2026-05-09-v3-data-foundation`](../archive/2026-05-09-v3-data-foundation)。本 change 后续只负责基于这些表实现 UC-11 fan-out、collection worker 跨天续采行为、admin/tenant 前端语义与验收。

## Why

V3 业务能力 R-2 当前先收敛为："admin 平台关键词页能正确管理全平台关键词采集任务，励销云 stage 1 可跨天续采并可停止"。腾道 stage 2 因 Cookie 会话失效，暂时不作为本 change 的完成前置。

当前阻塞：

1. **UC-10 admin 启动首采按钮已实现，但需按 D-035 限制 channel** — admin/CollectionTasks 已有 `triggerMutation` + `adminApi.collection.trigger` + 行内"触发"按钮 + Popconfirm（`frontend/apps/admin/src/pages/CollectionTasks/index.tsx:230-302`）；后端 `POST collection-keywords/trigger` 也存在（`backend/app/api/admin/collection.py:19`）。**真实缺口** = 现有 UI 仍渲染 direct / reverse 两类 channel，需按 D-035 把 direct（外贸通直采）禁用 / 隐藏，V3 仅允许反推链路。
2. **UC-11 跨租户复用未实现（D-009=A）** — A 租户已采过的关键词，B 租户配同关键词后**不能立即看到**历史数据；当前 collection_keywords 与 keyword_master 未解耦
3. **采集状态层级混乱** — admin 关键词页管理的是"全平台关键词采集任务"，tenant 只是订阅者；但当前实现仍容易把 tenant keyword 行状态、全局关键词状态、单次 worker task 状态混在一起。
4. **跨天续采缺少一轮采集模型** — `collection_tasks` 只能表达一次执行；"今天达到励销云 1000 上限，明天北京时间 08:00 继续同一轮采集"需要 `collection_run` 承载跨天状态与 cursor。

业务后果：每个新租户配关键词 → 即使别人采过 → 也要重新走励销云 + 腾道（每日 1000 条上限）→ 浪费 API 配额 + 用户等待时间长。

## What Changes

### 引入

- **基于已归档的 [`2026-05-09-v3-data-foundation`](../archive/2026-05-09-v3-data-foundation) 已落地的关键词 / run / task 模型**
  - `keyword_master` / `tenant_keyword`
  - `collection_runs` / `collection_tasks`
- **UC-06 命中分支** — 租户配关键词时查 keyword_master 判定"已采/未采"，UI 提示文案不同
- **UC-11 fan-out worker** — 命中老关键词时，把 shared_companies 中命中该关键词的公司复制到新租户的 tenant_companies（可见视图）

### 修改

- **admin/CollectionTasks 语义调整** — 页面管理全平台关键词采集任务，不管理 tenant 私有任务；tenant 只是订阅者
- **tenant 新增同词只增加订阅关系** — 不创建、不重启、不停止、不改变该关键词采集状态
- **admin 触发采集** — 为 keyword_master 创建或复用 active `collection_run`，再创建首个 `collection_task`
- **跨天续采** — 励销云每天每关键词最多采 1000；达到上限后 run 状态为 `daily_limit_reached`，立即生成次日北京时间 08:00 的 pending task，继续同一个 run 的 cursor
- **停止采集** — admin 点"停止"后，取消当前 running task 与未来 pending/scheduled continuation tasks；run 进入 `stopped`，次日不自动继续
- **采完状态** — 励销云无更多数据时，run 进入 `completed`，admin 显示"已采完"
- **请求批量** — 励销云单次请求最大 100，系统默认保持 10
- **stage2 腾道暂时忽略** — 不因 Cookie 失效阻塞 stage1 的 run/task 状态闭环
- **UC-12 collection worker**：关键词归一化处理；以 `collection_task.run_id` 找到 run 与 cursor
- **UC-14 分发逻辑**：通过 keyword_master 显式分发到所有命中租户

### 移除

- 无

## Non-Goals

- ❌ 不做外贸通直采（V3 N-01；D-035 推迟 V3.1+）
- ❌ 暂不自动执行腾道 stage 2（Cookie 会话过期问题另行处理）
- ❌ 不做重采机制（V3 N-06；数据冻结后不再变）
- ❌ 不做完整 UC-30 公司级中断（V3 N-03；D-021 已决"V3 不做"）
- ❌ 不做 EngageLab 接入（→ v3-email-delivery）
- ❌ 不动 cleanup_service（已在 v3-data-foundation 完成）

## Impact

| 维度 | 影响 |
|---|---|
| **破坏兼容** | 否 — 新表为主，老表 collection_keywords 保留作兼容/迁移桥 |
| **DB 改动** | 小 — 基础 schema 已迁入归档 change `2026-05-09-v3-data-foundation`；本 change 只在 fan-out / worker 行为需要时补充最小索引或兼容字段 |
| **Worker** | 是 — collection_scheduler / collection worker 改为 run → task 模型；新增 UC-11 fan-out worker |
| **前端** | 中 — admin/CollectionTasks 状态与操作按全平台 run 显示；tenant/Intelligence 加"已采过"提示 |
| **依赖** | `2026-05-09-v3-data-foundation` 已完成并归档（cleanup_service + clean schema 就绪） |

## 关联

- **能力域**：C2 KeywordMaster
- **覆盖 Slice**：Slice 1.C（UC-10 admin 启动）/ Slice 1.D（KeywordMaster + UC-11）/ Slice 2（去重 + 租户隔离）
- **覆盖验收 ID**：V3-COL-001 / V3-COL-002 / V3-COL-003 / V3-COL-007 / V3-AUTH-001
- **决策追溯**：D-009=A（KeywordMaster 完整做）/ D-035（V3 仅 tendata + lixiaoyun）/ UC-10 / UC-11
