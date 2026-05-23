## Why

`visibility_status` 列是为"取消关键词时隐藏公司"而设计的，但实际造成了更多问题：
- 默认值 `'hidden'` 导致收件人查询过滤掉了合法公司（已修 bug）
- 17 处查询都带 `AND visibility_status = 'visible'` 过滤，增加了每次改动的认知负担
- `hide_tenant_companies_for_cancelled_keyword` 函数在隐藏时无差别清空用户数据（score/note/tags/groups），行为过于激进
- 生产数据显示 99% 的 tenant_companies 是扇出空壳，visibility 状态管理收益极低

决策：当前阶段不支持取消关键词（关键词只增不减，公司只进不出），`visibility_status` 彻底移除。

## What Changes

- 数据库 DROP COLUMN `visibility_status`（含约束和索引）
- 移除所有查询中的 `visibility_status = 'visible'` 过滤（17 处）
- 删除 `hide_tenant_companies_for_cancelled_keyword` 函数
- fan-out 写入逻辑去掉 visibility_status 相关列和 ON CONFLICT 条件
- 关键词删除时只 soft-delete keyword 记录，不再触碰 tenant_companies
- wmt_lineage_repair 的 stale relation 处理从 SET hidden 改为 DELETE

## Non-Goals

- 不改变 fan-out 预物化架构（保留 tenant_companies 作为租户可见集合）
- 不改变关键词创建/更新时的即时 fan-out 触发机制
- 不改变 business_status / data_status 等其他状态字段

## Key Decisions

- D1: 线上无实际运营，迁移直接 DROP COLUMN，不需要先刷存量数据
- D2: 关键词只增不减——delete_keyword 只 soft-delete keyword 记录，tenant_companies 不动
- D3: wmt_lineage_repair 的孤儿清理从 UPDATE hidden 改为 DELETE（无条件删除，CASCADE 清理关联数据）
- D4: `_assert_visible_tenant_company` 重命名为 `_assert_tenant_company_exists`，所有调用点同步更新

## Impact

| 路径 | 变更类型 | 说明 |
|------|---------|------|
| `backend/alembic/versions/新迁移` | 新增 | DROP COLUMN visibility_status + 删约束 + 删索引 |
| `backend/app/services/tenant_query_service.py` | 修改 | 移除 4 处 visibility_status 过滤 |
| `backend/app/services/tenant_ops_service.py` | 修改 | 移除 7 处 visibility_status 过滤 + INSERT 去掉该列 |
| `backend/app/services/tenant_messaging_service.py` | 修改 | 移除 5 处 visibility_status 过滤 |
| `backend/app/services/webhook_service.py` | 修改 | 移除 1 处 visibility_status 过滤 |
| `backend/app/workers/fan_out.py` | 修改 | INSERT/ON CONFLICT 去掉 visibility_status；删除 hide 函数 |
| `backend/app/workers/wmt_lineage_repair.py` | 修改 | fan-out SQL 去掉 visibility_status；stale 改为 DELETE；统计 SQL 去掉过滤 |
| `backend/app/services/tenant_settings_service.py` | 修改 | 去掉 hide import 和调用 |
| `backend/scripts/rebuild_tenant_companies.py` | 修改 | 去掉 visibility_status 引用 |

## NOT in scope

- fan-out 架构重构（直接查 wmt 替代预物化）—— 影子查询显示当前规模无性能差异，保留预物化
- 关键词取消/撤回功能 —— 当前阶段不支持，未来需求时再设计
- tenant_companies 存量清理 —— 线上无运营，无需清理历史数据
- 前端代码改动 —— 前端无 visibility_status 引用

## What already exists

- fan-out 即时触发（tenant_settings_service.py 中 create/update keyword 已调用 run_fan_out_for_tenant_keyword）—— 保留不动
- tenant_companies UNIQUE(tenant_id, clean_company_id) 约束 —— 保证 fan-out 幂等，保留不动
- ON DELETE CASCADE 外键（group_members, scoring_jobs, company_scores, sending_plan_recipients）—— 支撑 stale DELETE 行为

## Implementation Tasks

纯减法变更，所有 task 来源于 review findings。

- [ ] **T1 (P1, human: ~1h / CC: ~10min)** — alembic — DROP COLUMN visibility_status 迁移
  - Surfaced by: proposal D1
  - Files: `backend/alembic/versions/` (新文件)
  - Verify: `alembic upgrade head` 成功
- [ ] **T2 (P1, human: ~2h / CC: ~15min)** — services — 移除 17 处 visibility_status 过滤
  - Surfaced by: proposal "What Changes"
  - Files: `tenant_query_service.py`, `tenant_ops_service.py`, `tenant_messaging_service.py`, `webhook_service.py`
  - Verify: 公司列表正常、发送计划收件人不为空
- [ ] **T3 (P1, human: ~30min / CC: ~5min)** — fan_out — 简化 INSERT + 删除 hide 函数
  - Surfaced by: proposal D3
  - Files: `backend/app/workers/fan_out.py`
  - Verify: 创建关键词后 fan-out 正常
- [ ] **T4 (P1, human: ~30min / CC: ~5min)** — wmt_lineage_repair — 去掉 visibility + stale 改 DELETE
  - Surfaced by: Architecture Review D1
  - Files: `backend/app/workers/wmt_lineage_repair.py`
  - Verify: 手动触发一次无报错
- [ ] **T5 (P2, human: ~20min / CC: ~5min)** — tenant_settings_service — 去掉 hide 调用
  - Surfaced by: proposal D2
  - Files: `backend/app/services/tenant_settings_service.py`
  - Verify: 关键词删除后 tenant_companies 不变
- [ ] **T6 (P2, human: ~10min / CC: ~2min)** — rename — _assert_visible_tenant_company 重命名
  - Surfaced by: Code Quality Review D2
  - Files: `backend/app/services/tenant_ops_service.py`
  - Verify: grep 确认无残留旧名
- [ ] **T7 (P2, human: ~10min / CC: ~2min)** — cleanup — rebuild_tenant_companies.py
  - Surfaced by: proposal "Impact"
  - Files: `backend/scripts/rebuild_tenant_companies.py`
  - Verify: 脚本语法正确

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 2 issues, 0 critical gaps |
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| Adversarial | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Outside Voice | codex plan review | Cross-model challenge | 1 | CLEAR (PLAN) | 14 concerns raised, 12 already covered by eng review/user decisions, 2 surfaced (D5 deployment order, D6 rollback) — both resolved as non-issues |

- **UNRESOLVED:** 0
- **VERDICT:** ENG + OUTSIDE VOICE CLEARED — ready to implement

### Outside Voice 审查摘要（Codex, 2026-05-23）

**已驳回（12 项）**：隐藏行重入、CASCADE 风险、需数据迁移、需先刷存量、前端引用、测试覆盖等——均已被 D1-D4 决策或用户确认覆盖。

**用户裁决（2 项）**：
- D5 部署顺序 → 已解决：/start.sh 先跑 alembic upgrade head 再启动 uvicorn，迁移天然先于代码
- D6 回滚策略 → 不需要：线上无运营，出问题 ADD COLUMN + 重跑 fan-out 即可
